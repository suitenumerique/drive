"""Drive core API endpoints"""

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError

from drf_standardized_errors.handler import exception_handler as drf_exception_handler
from rest_framework import exceptions as drf_exceptions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception.

    For the parameters, see ``exception_handler``
    This code comes from twidi's gist:
    https://gist.github.com/twidi/9d55486c36b6a51bdcb05ce3a763e79f
    """
    # Return 401 instead of 403 when the user is anonymous. An anonymous user
    # should be redirected to login rather than shown an "access denied" screen,
    # so the frontend can preserve the attempted URL across the login flow.
    request = context.get("request")
    view = context.get("view")
    if isinstance(exc, drf_exceptions.PermissionDenied):
        user = getattr(request, "user", None)
        # The "media-auth" subrequest is used by an Nginx auth_request and must keep
        # returning 403 to control file serving access, even for anonymous users.
        is_media_auth = getattr(view, "action", None) == "media_auth"
        if not is_media_auth and (user is None or not user.is_authenticated):
            exc = drf_exceptions.NotAuthenticated("Authentication credentials were not provided.")

    if isinstance(exc, DjangoValidationError):
        exc = drf_exceptions.ValidationError(as_serializer_error(exc))

    return drf_exception_handler(exc, context)


# pylint: disable=unused-argument
@api_view(["GET"])
def get_frontend_configuration(request):
    """Returns the frontend configuration dict as configured in settings."""
    frontend_configuration = {
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
    }
    frontend_configuration.update(settings.FRONTEND_CONFIGURATION)
    return Response(frontend_configuration)
