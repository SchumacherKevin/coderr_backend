"""Admin configuration of reviews_app."""
from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Admin configuration for reviews."""

    list_display = ('business_user', 'reviewer', 'rating', 'updated_at')
    list_filter = ('rating',)
    search_fields = (
        'description', 'business_user__username', 'reviewer__username')
