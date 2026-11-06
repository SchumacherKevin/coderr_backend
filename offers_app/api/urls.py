"""URL routes for the offers_app API."""
from django.urls import path

from .views import OfferListView

urlpatterns = [
    path('offers/', OfferListView.as_view(), name='offer-list'),
]
