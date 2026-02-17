import uuid

import cloudinary.uploader
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
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

    def create(self, request, *args, **kwargs):
        """Use the write serializer for validation, return the detail serializer."""
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        instance = write_serializer.instance
        read_serializer = ListingDetailSerializer(instance, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

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

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-images",
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_images(self, request):
        """
        POST /api/v1/listings/upload-images/
        Accepts multipart file uploads, pushes each to Cloudinary,
        and returns a list of secure URLs.

        Send files as 'images' (multiple files) in multipart/form-data.
        """
        files = request.FILES.getlist("images")
        if not files:
            return Response(
                {"detail": "No image files provided. Send files under the 'images' key."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(files) > 10:
            return Response(
                {"detail": "Maximum 10 images allowed per upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        max_size = 10 * 1024 * 1024  # 10 MB

        urls = []
        errors = []

        for i, f in enumerate(files):
            if f.content_type not in allowed_types:
                errors.append(f"File {i + 1} ({f.name}): unsupported type '{f.content_type}'.")
                continue
            if f.size > max_size:
                errors.append(f"File {i + 1} ({f.name}): exceeds 10 MB limit.")
                continue

            try:
                result = cloudinary.uploader.upload(
                    f,
                    folder="wanderleaf/listings",
                    resource_type="image",
                    transformation=[
                        {"width": 1200, "height": 800, "crop": "limit", "quality": "auto"},
                    ],
                )
                urls.append(result["secure_url"])
            except Exception as e:
                errors.append(f"File {i + 1} ({f.name}): upload failed — {str(e)}")

        return Response(
            {
                "urls": urls,
                "uploaded": len(urls),
                "errors": errors,
            },
            status=status.HTTP_200_OK if urls else status.HTTP_400_BAD_REQUEST,
        )

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
