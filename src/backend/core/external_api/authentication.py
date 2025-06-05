"""Authentication for external API using JWT token."""

import logging

from django.conf import settings

import jwt
from rest_framework import authentication

from core.models import User

logger = logging.getLogger(__name__)


class JWTAuthentication(authentication.BaseAuthentication):
    """Authentication for external API using JWT token."""

    def authenticate(self, request):
        """Authenticate the request using JWT token."""

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("No Authorization header found in request")
            return None

        # Check if the header starts with 'Bearer '
        if not auth_header.startswith("Bearer "):
            logger.warning(
                "Invalid Authorization header format. Expected 'Bearer <token>'"
            )
            return None

        # Extract the token
        token = auth_header.split(" ")[1]

        # Validate the token
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                options={"require": settings.JWT_REQUIRED_CLAIMS},
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.InvalidTokenError as e:
            logger.error("Invalid JWT token: %s", e)
            return None

        if not payload.get("sub") or not payload.get("email"):
            logger.warning("Invalid JWT token. Missing 'sub' or 'email' in payload")
            return None

        user = User.objects.get_user_by_sub_or_email(
            payload.get("sub"), payload.get("email")
        )
        if not user:
            logger.warning("User not found")
            return None

        return user, None
