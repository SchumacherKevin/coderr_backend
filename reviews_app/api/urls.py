"""URL routes for the reviews_app API."""
from django.urls import path

from .views import ReviewListView

urlpatterns = [
    path('reviews/', ReviewListView.as_view(), name='review-list'),
]
