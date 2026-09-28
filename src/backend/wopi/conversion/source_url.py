"""Build the short-lived WOPI URL OnlyOffice uses to fetch the source bytes."""

from django.conf import settings

from wopi.conversion.exceptions import ConversionMisconfigured
from wopi.services.access import AccessUserItemService


def build_source_url(item, user):
    """Return a short-lived WOPI GetFile URL pointing at the item for the user."""
    base_url = settings.WOPI_SRC_BASE_URL

    if not base_url:
        raise ConversionMisconfigured("Missing WOPI_SRC_BASE_URL for conversion source URL")

    access_token, _ttl_ms = AccessUserItemService().insert_new_access(
        item, user, ttl=settings.WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT
    )
    return (
        f"{base_url.rstrip('/')}/api/{settings.API_VERSION}"
        f"/wopi/files/{item.id}/contents/?access_token={access_token}"
    )
