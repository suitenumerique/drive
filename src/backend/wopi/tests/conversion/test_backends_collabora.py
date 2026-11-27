"""Tests for the Collabora server-to-server conversion backend."""

from io import BytesIO

from django.core.files.storage import default_storage

import pytest
import requests
import responses

from core import factories, models
from wopi.conversion import exceptions
from wopi.conversion.backends.collabora import CollaboraConversionBackend

pytestmark = pytest.mark.django_db

CONVERT_URL = "http://collabora:9980/cool/convert-to"


@pytest.fixture(name="item")
def _item():
    """Create a stored .docx file."""
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        filename="report.docx",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )
    default_storage.save(item.file_key, BytesIO(b"my report"))
    return item


@responses.activate
def test_thumbnail_posts_file_to_convert_to_png(item):
    """Upload the stored file as multipart data to the png conversion endpoint."""
    responses.add(responses.POST, f"{CONVERT_URL}/png", body=b"png-bytes", status=200)

    thumbnail = CollaboraConversionBackend(convert_service_url=f"{CONVERT_URL}/").thumbnail(
        item, 512
    )

    assert thumbnail.read() == b"png-bytes"
    request = responses.calls[0].request
    assert b'name="data"; filename="report.docx"' in request.body
    assert b"my report" in request.body


@responses.activate
def test_thumbnail_raises_provider_error_on_http_error(item):
    """Translate a non-2xx response into a provider error."""
    responses.add(responses.POST, f"{CONVERT_URL}/png", status=403)

    backend = CollaboraConversionBackend(convert_service_url=CONVERT_URL)

    with pytest.raises(exceptions.ConversionProviderError, match="status 403"):
        backend.thumbnail(item, 512)


@responses.activate
def test_thumbnail_raises_provider_error_on_transport_error(item):
    """Translate a transport failure into a provider error."""
    responses.add(
        responses.POST, f"{CONVERT_URL}/png", body=requests.exceptions.ConnectionError("down")
    )

    backend = CollaboraConversionBackend(convert_service_url=CONVERT_URL)

    with pytest.raises(exceptions.ConversionProviderError, match="down"):
        backend.thumbnail(item, 512)
