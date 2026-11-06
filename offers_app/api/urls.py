"""URL routes for the offers_app API."""
from django.urls import path

from .views import OfferDetailView, OfferListView, OfferSingleView

urlpatterns = [
    path('offers/', OfferListView.as_view(), name='offer-list'),
    path('offers/<int:pk>/', OfferSingleView.as_view(),
         name='offer-detail'),
    path('offerdetails/<int:pk>/', OfferDetailView.as_view(),
         name='offerdetail-detail'),
]
