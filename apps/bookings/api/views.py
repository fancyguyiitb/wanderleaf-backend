import uuid
from datetime import date

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.bookings.serializers import (
    BookingListSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    BookingCancelSerializer,
    CheckAvailabilitySerializer,
    PriceCalculationSerializer,
)
from apps.bookings.services import BookingService, PaymentService
from apps.common.email_service import NotificationEmailService
from apps.listings.models import Listing


class IsBookingParticipant(permissions.BasePermission):
    """
    Permission check for booking access:
    - Guest can view/cancel their own bookings
    - Host can view/cancel bookings for their listings
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        is_guest = str(obj.guest_id) == str(user.id)
        is_host = str(obj.listing.host_id) == str(user.id)
        return is_guest or is_host


class BookingViewSet(viewsets.ModelViewSet):
    """
    API endpoints for booking management.

    Endpoints:
        GET    /api/v1/bookings/                    - List user's bookings (as guest)
        POST   /api/v1/bookings/                    - Create a new booking
        GET    /api/v1/bookings/{uuid}/             - Get booking details
        DELETE /api/v1/bookings/{uuid}/             - Cancel a booking
        
        GET    /api/v1/bookings/host/               - List bookings for host's listings
        POST   /api/v1/bookings/{uuid}/cancel/      - Cancel with reason
        
        POST   /api/v1/bookings/check-availability/ - Check listing availability
        POST   /api/v1/bookings/calculate-price/    - Calculate booking price
        GET    /api/v1/bookings/listing/{uuid}/booked-dates/ - Get booked dates
    """

    permission_classes = [permissions.IsAuthenticated, IsBookingParticipant]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        user = self.request.user
        return (
            Booking.objects
            .select_related("listing", "guest", "listing__host")
            .filter(Q(guest=user) | Q(listing__host=user))
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        if self.action in ("retrieve", "cancel"):
            return BookingDetailSerializer
        return BookingListSerializer

    def get_object(self):
        """Override to handle UUID validation."""
        pk = self.kwargs.get("pk", "")
        try:
            uuid.UUID(str(pk))
        except ValueError:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Booking not found.")
        return super().get_object()

    def get_permissions(self):
        """Allow check-availability and calculate-price without auth for listing detail page."""
        if self.action in ("check_availability", "calculate_price", "booked_dates"):
            return [permissions.AllowAny()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        """List bookings where the user is the guest."""
        queryset = self.get_queryset().filter(guest=request.user)
        
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        upcoming = request.query_params.get("upcoming")
        if upcoming and upcoming.lower() == "true":
            queryset = queryset.filter(
                check_in__gte=date.today(),
                status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED],
            )

        past = request.query_params.get("past")
        if past and past.lower() == "true":
            queryset = queryset.filter(check_out__lt=date.today())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create a new booking."""
        serializer = BookingCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        listing = serializer.context["listing"]
        data = serializer.validated_data

        booking, error = BookingService.create_booking(
            listing=listing,
            guest=request.user,
            check_in=data["check_in"],
            check_out=data["check_out"],
            num_guests=data["num_guests"],
            special_requests=data.get("special_requests", ""),
        )

        if error:
            payload = error if isinstance(error, dict) else {"detail": error}
            response_status = (
                status.HTTP_409_CONFLICT
                if payload.get("code") == BookingService.BOOKING_DATES_OVERLAP_CODE
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(
                payload,
                status=response_status,
            )

        payment_info = PaymentService.create_payment_intent(booking)
        if payment_info is None:
            booking.delete()
            return Response(
                {
                    "detail": "Payment gateway is not available. Please ensure Razorpay is configured (RZP_TEST_KEY_ID, RZP_TEST_KEY_SECRET).",
                    "code": "payment_gateway_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_serializer = BookingDetailSerializer(
            booking, context={"request": request}
        )
        NotificationEmailService.send_booking_created(booking)
        return Response(
            {
                "booking": response_serializer.data,
                "payment": payment_info,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        """Get booking details. Auto-cancels expired pending payments."""
        booking = self.get_object()
        if BookingService.check_and_cancel_expired(booking):
            booking.refresh_from_db()
            NotificationEmailService.send_payment_failed(
                booking,
                reason="expired",
            )
        serializer = BookingDetailSerializer(booking, context={"request": request})
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Cancel a booking (DELETE method)."""
        booking = self.get_object()
        success, message, refund_code = BookingService.cancel_booking(
            booking=booking,
            cancelled_by=request.user,
            reason="Cancelled by user",
        )

        if not success:
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {"detail": message}
        if refund_code:
            payload["refund_code"] = refund_code
        NotificationEmailService.send_booking_cancelled(
            booking=booking,
            cancelled_by=request.user,
            refund_code=refund_code,
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["get"],
        url_path="host",
        permission_classes=[permissions.IsAuthenticated],
    )
    def host_bookings(self, request):
        """
        GET /api/v1/bookings/host/
        List all bookings for listings owned by the current user (as host).
        """
        queryset = (
            Booking.objects
            .select_related("listing", "guest", "listing__host")
            .filter(listing__host=request.user)
            .order_by("-created_at")
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        listing_id = request.query_params.get("listing_id")
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)

        upcoming = request.query_params.get("upcoming")
        if upcoming and upcoming.lower() == "true":
            queryset = queryset.filter(
                check_in__gte=date.today(),
                status__in=[Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED],
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = BookingListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = BookingListSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        permission_classes=[permissions.IsAuthenticated, IsBookingParticipant],
    )
    def cancel(self, request, pk=None):
        """
        POST /api/v1/bookings/{uuid}/cancel/
        Cancel a booking with an optional reason.
        """
        booking = self.get_object()
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, message, refund_code = BookingService.cancel_booking(
            booking=booking,
            cancelled_by=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )

        if not success:
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = BookingDetailSerializer(
            booking, context={"request": request}
        )
        payload = {
            "detail": message,
            "booking": response_serializer.data,
        }
        if refund_code:
            payload["refund_code"] = refund_code
        NotificationEmailService.send_booking_cancelled(
            booking=booking,
            cancelled_by=request.user,
            refund_code=refund_code,
        )
        return Response(payload)

    @action(
        detail=True,
        methods=["post"],
        url_path="verify-payment",
        permission_classes=[permissions.IsAuthenticated],
    )
    def verify_payment(self, request, pk=None):
        """
        POST /api/v1/bookings/{uuid}/verify-payment/
        Verify Razorpay payment and confirm booking.
        Body: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
        """
        booking = self.get_object()

        if str(booking.guest_id) != str(request.user.id):
            return Response(
                {"detail": "Only the guest can verify payment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if BookingService.check_and_cancel_expired(booking):
            booking.refresh_from_db()
            NotificationEmailService.send_payment_failed(
                booking,
                reason="expired",
            )
            return Response(
                {
                    "detail": "Payment window expired (15 minutes). The booking has been cancelled and dates freed.",
                    "code": "payment_window_expired",
                },
                status=status.HTTP_410_GONE,
            )

        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response(
                {"detail": "razorpay_order_id, razorpay_payment_id, and razorpay_signature are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success, message = PaymentService.verify_razorpay_payment(
            booking_id=str(booking.id),
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        if not success:
            BookingService.mark_payment_retry_disallowed(booking)
            NotificationEmailService.send_payment_failed(
                booking,
                reason="verification_failed",
            )
            return Response(
                {
                    "detail": message,
                    "code": "payment_verification_failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.refresh_from_db()
        NotificationEmailService.send_payment_success(booking)
        response_serializer = BookingDetailSerializer(
            booking, context={"request": request}
        )
        return Response({
            "detail": message,
            "booking": response_serializer.data,
        })

    @action(
        detail=True,
        methods=["post"],
        url_path="retry-payment",
        permission_classes=[permissions.IsAuthenticated],
    )
    def retry_payment(self, request, pk=None):
        """
        POST /api/v1/bookings/{uuid}/retry-payment/
        Get a new Razorpay order for a pending booking. Only allowed within 15 minutes
        and only if payment_retry_disallowed is False (user cancelled / pre-deduction failure).
        """
        booking = self.get_object()

        if str(booking.guest_id) != str(request.user.id):
            return Response(
                {"detail": "Only the guest can retry payment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status != Booking.Status.PENDING_PAYMENT:
            return Response(
                {"detail": "This booking is not pending payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.payment_retry_disallowed:
            return Response(
                {
                    "detail": "Payment retry is not allowed. Your payment may have been processed. Please contact support with your booking ID if you were charged.",
                    "code": "payment_retry_disallowed",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if BookingService.check_and_cancel_expired(booking):
            booking.refresh_from_db()
            NotificationEmailService.send_payment_failed(
                booking,
                reason="expired",
            )
            return Response(
                {
                    "detail": "Payment window expired (15 minutes). The booking has been cancelled and dates freed.",
                    "code": "payment_window_expired",
                },
                status=status.HTTP_410_GONE,
            )

        payment_info = PaymentService.create_payment_intent(booking)
        if payment_info is None:
            return Response(
                {
                    "detail": "Payment gateway is not available.",
                    "code": "payment_gateway_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(payment_info)

    @action(
        detail=False,
        methods=["post"],
        url_path="check-availability",
        permission_classes=[permissions.AllowAny],
    )
    def check_availability(self, request):
        """
        POST /api/v1/bookings/check-availability/
        Check if a listing is available for the given dates.
        
        Request body:
            {
                "listing_id": "uuid",
                "check_in": "2024-03-15",
                "check_out": "2024-03-20"
            }
        """
        serializer = CheckAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        is_available, conflicts = BookingService.check_availability(
            listing_id=str(data["listing_id"]),
            check_in=data["check_in"],
            check_out=data["check_out"],
        )

        return Response({
            "is_available": is_available,
            "check_in": data["check_in"],
            "check_out": data["check_out"],
            "conflicts_count": len(conflicts),
            "conflicts": BookingService.serialize_conflicts(conflicts),
        })

    @action(
        detail=False,
        methods=["post"],
        url_path="calculate-price",
        permission_classes=[permissions.AllowAny],
    )
    def calculate_price(self, request):
        """
        POST /api/v1/bookings/calculate-price/
        Calculate the price breakdown for a potential booking.
        
        Request body:
            {
                "listing_id": "uuid",
                "check_in": "2024-03-15",
                "check_out": "2024-03-20",
                "num_guests": 2
            }
        """
        serializer = PriceCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        
        try:
            listing = Listing.objects.get(id=data["listing_id"], is_active=True)
        except Listing.DoesNotExist:
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if data["num_guests"] > listing.max_guests:
            return Response(
                {"detail": f"This listing allows a maximum of {listing.max_guests} guests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        price = BookingService.calculate_price(
            listing=listing,
            check_in=data["check_in"],
            check_out=data["check_out"],
        )

        return Response({
            "listing_id": str(listing.id),
            "check_in": data["check_in"],
            "check_out": data["check_out"],
            "num_guests": data["num_guests"],
            "price_per_night": float(price.price_per_night),
            "num_nights": price.num_nights,
            "subtotal": float(price.subtotal),
            "service_fee": float(price.service_fee),
            "cleaning_fee": float(price.cleaning_fee),
            "total_price": float(price.total_price),
            "currency": "INR",
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="listing/(?P<listing_id>[^/.]+)/booked-dates",
        permission_classes=[permissions.AllowAny],
    )
    def booked_dates(self, request, listing_id=None):
        """
        GET /api/v1/bookings/listing/{uuid}/booked-dates/
        Get all booked date ranges for a listing.
        Useful for disabling dates in the calendar picker.
        """
        try:
            listing_uuid = uuid.UUID(str(listing_id))
        except ValueError:
            return Response(
                {"detail": "Invalid listing ID format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not Listing.objects.filter(id=listing_uuid, is_active=True).exists():
            return Response(
                {"detail": "Listing not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        booked_dates = BookingService.get_booked_dates(str(listing_uuid))

        return Response({
            "listing_id": str(listing_uuid),
            "booked_ranges": booked_dates,
        })
