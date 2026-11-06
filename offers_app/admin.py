from django.contrib import admin

from .models import Offer, OfferDetail


class OfferDetailInline(admin.TabularInline):
    """Edit the three packages directly inside the offer."""

    model = OfferDetail
    extra = 0


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Admin configuration for offers."""

    list_display = ('title', 'user', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'user__username')
    inlines = [OfferDetailInline]


@admin.register(OfferDetail)
class OfferDetailAdmin(admin.ModelAdmin):
    """Admin configuration for offer details."""

    list_display = ('offer', 'offer_type', 'price', 'delivery_time_in_days')
    list_filter = ('offer_type',)
    list_select_related = ('offer__user',)
