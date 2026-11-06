"""URL routes for the reviews_app API."""
from django.urls import path

from .views import ReviewListView, ReviewSingleView

urlpatterns = [
    path('reviews/', ReviewListView.as_view(), name='review-list'),
    path('reviews/<int:pk>/', ReviewSingleView.as_view(),
         name='review-detail'),
]
