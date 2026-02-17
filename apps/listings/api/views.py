import uuid

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.listings.models import Listing
from apps.listings.serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateUpdateSerializer,
)


class IsHostOrReadOnly(permissions.BasePermission):
    """
    - Any request can read (GET, HEAD, OPTIONS).
    - Write requests (POST) require authentication.
    - Object-level writes (PUT, PATCH, DELETE) require the user to be the host.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return str(obj.host_id) == str(request.user.id)


class ListingViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for property listings.

    List / Retrieve : open to everyone (no auth needed).
    Create           : authenticated users only.
    Update / Delete  : only the host who owns the listing.

    Endpoints (via router):
        GET    /api/v1/listings/                    list
        POST   /api/v1/listings/                    create
        GET    /api/v1/listings/{uuid}/             retrieve
        PUT    /api/v1/listings/{uuid}/             full update
        PATCH  /api/v1/listings/{uuid}/             partial update
        DELETE /api/v1/listings/{uuid}/             destroy
        GET    /api/v1/listings/my/                 list current user's listings
        GET    /api/v1/listings/host/{uuid}/        list a host's public listings
    """

    permission_classes = [IsHostOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "location", "description", "category"]
    ordering_fields = ["price_per_night", "created_at", "bedrooms", "max_guests"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Listing.objects.select_related("host").all()

        if self.action == "list":
            qs = qs.filter(is_active=True)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        min_price = self.request.query_params.get("min_price")
        if min_price:
            qs = qs.filter(price_per_night__gte=min_price)

        max_price = self.request.query_params.get("max_price")
        if max_price:
            qs = qs.filter(price_per_night__lte=max_price)

        bedrooms = self.request.query_params.get("bedrooms")
        if bedrooms:
            qs = qs.filter(bedrooms__gte=bedrooms)

        guests = self.request.query_params.get("guests")
        if guests:
            qs = qs.filter(max_guests__gte=guests)

        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ListingCreateUpdateSerializer
        if self.action == "retrieve":
            return ListingDetailSerializer
        return ListingListSerializer

    def get_object(self):
        """Override to return 404 on malformed UUIDs instead of 500."""
        pk = self.kwargs.get("pk", "")
        try:
            uuid.UUID(str(pk))
        except ValueError:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Listing not found.")
        return super().get_object()

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)

    @action(detail=False, methods=["get"], url_path="my", permission_classes=[permissions.IsAuthenticated])
    def my_listings(self, request):
        """
        GET /api/v1/listings/my/
        Returns all listings owned by the current user (including inactive).
        """
        qs = Listing.objects.filter(host=request.user).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ListingListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = ListingListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="host/(?P<host_id>[^/.]+)", permission_classes=[permissions.AllowAny])
    def host_listings(self, request, host_id=None):
        """
        GET /api/v1/listings/host/{user_uuid}/
        Returns all active listings from a specific host. Public endpoint.
        """
        try:
            host_uuid = uuid.UUID(str(host_id))
        except (ValueError, AttributeError):
            return Response(
                {"detail": "Invalid host ID format. Expected a UUID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = (
            Listing.objects.select_related("host")
            .filter(host_id=host_uuid, is_active=True)
            .order_by("-created_at")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ListingListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = ListingListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)
