from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer


class RegistrationView(APIView):
    """Register a new customer or business user."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create the user and return token and basic user data."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = {
            'token': user.auth_token.key,
            'username': user.username,
            'email': user.email,
            'user_id': user.id,
        }
        return Response(data, status=status.HTTP_201_CREATED)
