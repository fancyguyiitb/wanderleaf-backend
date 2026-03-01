import uuid

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.listings.models import Listing
from apps.listings.serializers import ListingListSerializer
from apps.wishlist.models import WishlistItem


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def wishlist_list(request):
    """
    GET /api/v1/wishlist/
    Returns the current user's wishlisted listings.
    """
    items = WishlistItem.objects.filter(user=request.user).select_related("listing", "listing__host")
    listings = [item.listing for item in items]
    serializer = ListingListSerializer(listings, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def wishlist_toggle(request, listing_id):
    """
    POST   /api/v1/wishlist/{listing_id}/
    Adds a listing to the user's wishlist.

    DELETE /api/v1/wishlist/{listing_id}/
    Removes a listing from the user's wishlist.
    """
    try:
        listing_uuid = uuid.UUID(str(listing_id))
    except (ValueError, TypeError):
        return Response(
            {"detail": "Invalid listing ID format. Expected a UUID."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "POST":
        listing = get_object_or_404(Listing, id=listing_uuid, is_active=True)
        _, created = WishlistItem.objects.get_or_create(user=request.user, listing=listing)
        serializer = ListingListSerializer(listing, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # DELETE
    deleted, _ = WishlistItem.objects.filter(user=request.user, listing_id=listing_uuid).delete()
    if deleted:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        {"detail": "Listing was not in your wishlist."},
        status=status.HTTP_404_NOT_FOUND,
    )
