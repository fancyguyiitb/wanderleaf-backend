from django.contrib import admin
from .models import WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["user", "listing", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "listing__title"]
