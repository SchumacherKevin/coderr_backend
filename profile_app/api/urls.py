"""URL routes for the profile_app API."""
from django.urls import path

from .views import ProfileDetailView

urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(),
         name='profile-detail'),
]
