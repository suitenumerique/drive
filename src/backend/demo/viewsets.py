from core.api import viewsets
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework import response as drf_response
from core import models
import rest_framework as drf
from django.contrib.auth import login


class UserAuthViewSet(drf.viewsets.ViewSet):
    
    """Viewset to handle user authentication"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request):
        """
        POST /api/v1.0/demo/user-auth/
        Create a user with the given email and log them in
        """
        email = request.data.get('email')
        if not email:
            return drf_response.Response(
                {'error': 'Email is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user if doesn't exist
        user = models.User.objects.filter(
            email=email
        ).first()
        if not user:
            user = models.User(
                email=email
            )
            user.set_unusable_password()
            user.save()

        login(request, user, 'django.contrib.auth.backends.ModelBackend')

        return drf_response.Response(
            {'user': user.email},
            status=status.HTTP_200_OK
        )
