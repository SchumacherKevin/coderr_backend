"""Views for the base_info_app API."""
from django.db.models import Avg
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from offers_app.models import Offer
from profile_app.models import UserProfile
from reviews_app.models import Review


def get_average_rating():
    """Average of all ratings with one decimal place, 0 without reviews."""
    average = Review.objects.aggregate(avg=Avg('rating'))['avg']
    return round(average or 0, 1)


class BaseInfoView(APIView):
    """Public statistics about reviews, business users and offers."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return the counts and the average rating."""
        return Response({
            'review_count': Review.objects.count(),
            'average_rating': get_average_rating(),
            'business_profile_count': UserProfile.objects.filter(
                type=UserProfile.ProfileType.BUSINESS).count(),
            'offer_count': Offer.objects.count(),
        })
