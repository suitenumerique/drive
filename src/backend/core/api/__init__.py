"""Drive core API endpoints"""

import logging

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.log import request_logger

from drf_standardized_errors.handler import exception_handler as drf_exception_handler
from rest_framework import exceptions as drf_exceptions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error


def _log_error_response(request, response):
    """Log the error like Django does, with its codes and user, never its details."""
    user_id = request.user.pk
    request_logger.log(
        logging.ERROR if response.status_code >= 500 else logging.WARNING,
        "%s: %s",
        response.reason_phrase,
        request.path,
        extra={
            "status_code": response.status_code,
            "request": request._request,  # noqa: SLF001  # pylint: disable=protected-access
            "codes": [error["code"] for error in response.data.get("errors", [])],
            "uid": str(user_id) if user_id else None,
        },
    )
    # Tells Django's handler that this response is already logged
    response._has_been_logged = True  # noqa: SLF001  # pylint: disable=protected-access


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception.

    For the parameters, see ``exception_handler``
    This code comes from twidi's gist:
    https://gist.github.com/twidi/9d55486c36b6a51bdcb05ce3a763e79f
    """
    if isinstance(exc, DjangoValidationError):
        exc = drf_exceptions.ValidationError(as_serializer_error(exc))

    response = drf_exception_handler(exc, context)
    if response is not None:
        _log_error_response(context["request"], response)
    return response


# pylint: disable=unused-argument
@api_view(["GET"])
def get_frontend_configuration(request):
    """Returns the frontend configuration dict as configured in settings."""
    frontend_configuration = {
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
    }
    frontend_configuration.update(settings.FRONTEND_CONFIGURATION)
    return Response(frontend_configuration)
