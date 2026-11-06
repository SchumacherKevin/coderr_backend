"""Views for the base_info_app API."""
from django.db.models import Avg
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from offers_app.models import Offer
from profile_app.models import UserProfile
from reviews_app.models import Review


class BaseInfoView(APIView):
    """Public statistics about reviews, business users and offers."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return the counts and the average rating."""
        average = Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        return Response({
            'review_count': Review.objects.count(),
            'average_rating': round(average, 1),
            'business_profile_count': UserProfile.objects.filter(
                type=UserProfile.ProfileType.BUSINESS).count(),
            'offer_count': Offer.objects.count(),
        })
