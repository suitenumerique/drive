"""Build the short-lived URLs OnlyOffice uses to fetch the source bytes."""

from django.conf import settings
from django.core import signing

from wopi.conversion.exceptions import ConversionMisconfigured
from wopi.services.access import AccessUserItemService

SOURCE_TOKEN_SALT = "wopi.conversion.source"  # noqa: S105


def _api_base_url():
    """Return the API base URL the WOPI client can reach."""
    base_url = settings.WOPI_SRC_BASE_URL

    if not base_url:
        raise ConversionMisconfigured("Missing WOPI_SRC_BASE_URL for conversion source URL")
    return f"{base_url.rstrip('/')}/api/{settings.API_VERSION}"


def build_source_url(item, user):
    """Return a short-lived WOPI GetFile URL pointing at the item for the user."""
    api_base_url = _api_base_url()

    access_token, _ttl_ms = AccessUserItemService().insert_new_access(
        item, user, ttl=settings.WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT
    )
    return f"{api_base_url}/wopi/files/{item.id}/contents/?access_token={access_token}"


def build_system_source_url(item):
    """Return a short-lived URL to the item content, signed for no user in particular.

    Used for background jobs such as thumbnails, which act on behalf of nobody and must
    keep working when the item creator is gone or has lost access.
    """
    token = signing.dumps(str(item.id), salt=SOURCE_TOKEN_SALT)
    return f"{_api_base_url()}/wopi/sources/{item.id}/?token={token}"


def read_system_source_token(token):
    """Return the item id signed in a system source token, raise BadSignature if invalid."""
    return signing.loads(
        token, salt=SOURCE_TOKEN_SALT, max_age=settings.WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT
    )
