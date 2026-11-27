"""Collabora Online server-to-server conversion backend."""

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import requests

from wopi.conversion.exceptions import ConversionProviderError

# (connect, read) timeouts in seconds; rendering a large document can take a while.
HTTP_TIMEOUT = (5, 60)


class CollaboraConversionBackend:
    """Run a synchronous Collabora conversion through the /cool/convert-to endpoint."""

    def __init__(self, convert_service_url):
        self.convert_service_url = convert_service_url.rstrip("/")

    def thumbnail(self, item, _size):
        """Render the first page of the item as a PNG.

        Collabora renders at page size, the caller is responsible for resizing.
        """
        with default_storage.open(item.file_key, "rb") as file:
            try:
                response = requests.post(
                    f"{self.convert_service_url}/png",
                    files={"data": (item.filename, file)},
                    timeout=HTTP_TIMEOUT,
                )
            except requests.exceptions.RequestException as exc:
                raise ConversionProviderError(str(exc)) from exc

        if not response.ok:
            raise ConversionProviderError(
                f"Collabora /convert-to returned status {response.status_code}"
            )
        return ContentFile(response.content, name="thumbnail.png")
