"""Drive core API endpoints"""

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError

from drf_standardized_errors.handler import exception_handler as drf_exception_handler
from rest_framework import exceptions as drf_exceptions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error

from core.entitlements.backends.base import CanUploadReason
from core.monitoring_utils import log_audit_event

QUOTA_DENIAL_CODES = {
    CanUploadReason.USER_QUOTA_EXCEEDED,
    CanUploadReason.USER_OVERRIDE_QUOTA_EXCEEDED,
    CanUploadReason.ORGANIZATION_QUOTA_EXCEEDED,
}


def exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception.

    For the parameters, see ``exception_handler``
    This code comes from twidi's gist:
    https://gist.github.com/twidi/9d55486c36b6a51bdcb05ce3a763e79f
    """
    if isinstance(exc, DjangoValidationError):
        exc = drf_exceptions.ValidationError(as_serializer_error(exc))

    response = drf_exception_handler(exc, context)
    if response is not None and response.status_code == 403:
        # Storage exhaustion is not access probing; keep the original API response.
        errors = response.data.get("errors", [])
        if errors and all(error.get("code") in QUOTA_DENIAL_CODES for error in errors):
            return response
        request = context.get("request")
        view = context.get("view")
        kwargs = getattr(view, "kwargs", None) or context.get("kwargs", {})
        resource_id = (
            getattr(request, "security_resource_id", None)
            or kwargs.get("resource_id")
            or kwargs.get("item_id")
            or kwargs.get("pk")
        )
        log_audit_event(
            "permission_denied",
            request=request,
            resource_id=resource_id,
            view=type(view).__name__ if view is not None else None,
            method=getattr(request, "method", None),
            status_code=403,
        )
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
