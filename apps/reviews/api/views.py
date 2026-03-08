from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Listing
from apps.reviews.models import Review
from apps.reviews.serializers import ReviewCreateSerializer, ReviewSerializer


class ReviewListCreateView(APIView):
    """
    GET  /api/v1/reviews/?listing={listing_id}&limit=4&offset=0
    POST /api/v1/reviews/
    """

    permission_classes = [permissions.AllowAny]  # GET is public
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get(self, request):
        listing_id = request.query_params.get("listing")
        if not listing_id:
            return Response(
                {"detail": "listing query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        get_object_or_404(Listing, id=listing_id, is_active=True)

        try:
            limit = min(int(request.query_params.get("limit", 4)), 20)
        except (TypeError, ValueError):
            limit = 4
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except (TypeError, ValueError):
            offset = 0

        qs = (
            Review.objects.filter(listing_id=listing_id)
            .select_related("author")
            .order_by("-created_at")
        )
        total = qs.count()
        reviews = qs[offset : offset + limit]
        serializer = ReviewSerializer(reviews, many=True, context={"request": request})
        return Response({
            "results": serializer.data,
            "count": total,
            "next_offset": offset + limit if offset + limit < total else None,
        })

    def post(self, request):
        serializer = ReviewCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.context["booking"]
        rating = serializer.validated_data["rating"]
        comment = serializer.validated_data["comment"]

        review = Review.objects.create(
            booking=booking,
            listing=booking.listing,
            author=booking.guest,
            rating=rating,
            comment=comment,
        )
        read_serializer = ReviewSerializer(review, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
