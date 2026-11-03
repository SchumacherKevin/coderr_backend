"""Views for the auth_app API."""
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer


def build_auth_response(user):
    """Return the token and basic user data."""
    token, _ = Token.objects.get_or_create(user=user)
    return {
        'token': token.key,
        'username': user.username,
        'email': user.email,
        'user_id': user.pk,
    }


class RegistrationView(APIView):
    """Register a new customer or business user."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create the user and return token and basic user data."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = build_auth_response(user)
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(ObtainAuthToken):
    """Log a user in with username and password."""

    def post(self, request, *args, **kwargs):
        """Validate the credentials and return token and basic user data."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        data = build_auth_response(user)
        return Response(data, status=status.HTTP_200_OK)
