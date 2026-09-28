"""Tests for the OnlyOffice server-to-server conversion backend."""

import json
from unittest import mock

import jwt
import pytest
import requests
import responses

from core import factories
from wopi.conversion import exceptions
from wopi.conversion.backends.onlyoffice import OnlyOfficeConversionBackend

CONVERT_URL = "https://office.example/converter"
FILE_URL = "https://office.example/result/converted.docx"
SOURCE_URL = "https://drive.example/source"
JWT_SECRET = "test-secret-with-enough-length-for-hs256"


def _item(filename="document.doc"):
    """Build a minimal in-memory Item for backend tests."""
    return factories.ItemFactory.build(filename=filename)


def _ok_body():
    """Return a successful OnlyOffice /converter response body."""
    return json.dumps({"endConvert": True, "fileUrl": FILE_URL, "percent": 100})


@responses.activate
def test_convert_sends_synchronous_payload_with_shardkey(settings):
    """Send a synchronous /converter call with required fields and shardkey."""
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = None
    responses.add(responses.POST, CONVERT_URL, body=_ok_body(), status=200)
    responses.add(responses.GET, FILE_URL, body=b"converted", status=200)

    backend = OnlyOfficeConversionBackend(convert_service_url=CONVERT_URL)
    item = _item()

    backend.convert(item, SOURCE_URL, "docx")

    request = responses.calls[0].request
    payload = json.loads(request.body)
    key = payload.pop("key")
    assert payload == {
        "async": False,
        "filetype": "doc",
        "outputtype": "docx",
        "title": "document.doc",
        "url": SOURCE_URL,
    }
    assert str(item.id) in key
    # OnlyOffice routes synchronous conversions by the ``shardkey`` query param,
    # not by the body — load balancers can pin a key to a worker.
    assert f"shardkey={key}" in request.url


@responses.activate
def test_convert_signs_payload_when_jwt_secret_is_set(settings):
    """Encode conversion parameters directly in a body JWT token."""
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = JWT_SECRET
    responses.add(responses.POST, CONVERT_URL, body=_ok_body(), status=200)
    responses.add(responses.GET, FILE_URL, body=b"converted", status=200)

    backend = OnlyOfficeConversionBackend(convert_service_url=CONVERT_URL)
    item = _item()
    backend.convert(item, SOURCE_URL, "docx")

    request = responses.calls[0].request
    body = json.loads(request.body)
    assert list(body.keys()) == ["token"]

    decoded = jwt.decode(body["token"], JWT_SECRET, algorithms=["HS256"])
    key = decoded.pop("key")
    assert decoded == {
        "async": False,
        "filetype": "doc",
        "outputtype": "docx",
        "title": item.filename,
        "url": SOURCE_URL,
    }
    assert str(item.id) in key
    assert "Authorization" not in request.headers


@responses.activate
def test_convert_does_not_sign_when_no_secret(settings):
    """Skip the token field when the backend has no JWT secret."""
    settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET = None
    responses.add(responses.POST, CONVERT_URL, body=_ok_body(), status=200)
    responses.add(responses.GET, FILE_URL, body=b"converted", status=200)

    backend = OnlyOfficeConversionBackend(convert_service_url=CONVERT_URL)
    backend.convert(_item(), SOURCE_URL, "docx")

    request = responses.calls[0].request
    payload = json.loads(request.body)
    assert "token" not in payload


@responses.activate
def test_convert_returns_content_file_with_downloaded_bytes():
    """Wrap the downloaded bytes in a ContentFile named after the target."""
    responses.add(responses.POST, CONVERT_URL, body=_ok_body(), status=200)
    responses.add(responses.GET, FILE_URL, body=b"converted-bytes", status=200)

    backend = OnlyOfficeConversionBackend(convert_service_url=CONVERT_URL)
    result = backend.convert(_item(), SOURCE_URL, "docx")

    assert result.read() == b"converted-bytes"
    assert result.name.endswith(".docx")


def test_convert_uses_separate_connect_and_read_timeouts(settings):
    """Apply the configured connect/read timeouts to /converter and the download."""
    with mock.patch("wopi.conversion.backends.onlyoffice.requests") as requests_mock:
        post_response = mock.Mock(ok=True)
        post_response.json.return_value = {"endConvert": True, "fileUrl": FILE_URL}
        get_response = mock.Mock(ok=True, content=b"x")
        requests_mock.post.return_value = post_response
        requests_mock.get.return_value = get_response
        requests_mock.exceptions = requests.exceptions

        OnlyOfficeConversionBackend(convert_service_url=CONVERT_URL).convert(
            _item(), SOURCE_URL, "docx"
        )

        assert requests_mock.post.call_args.kwargs["timeout"] == (
            settings.WOPI_ONLYOFFICE_CONVERT_HTTP_CONNECT_TIMEOUT,
            settings.WOPI_ONLYOFFICE_CONVERT_HTTP_READ_TIMEOUT,
        )
        assert requests_mock.get.call_args.kwargs["timeout"] == (
            settings.WOPI_ONLYOFFICE_CONVERT_DOWNLOAD_CONNECT_TIMEOUT,
            settings.WOPI_ONLYOFFICE_CONVERT_DOWNLOAD_READ_TIMEOUT,
        )


@pytest.mark.parametrize(
    ("post_kwargs", "get_kwargs", "expected_message"),
    [
        ({"body": requests.exceptions.Timeout()}, None, None),
        ({"body": "not json", "status": 200}, None, "non-JSON body"),
        (
            {"body": json.dumps({"endConvert": False, "percent": 50}), "status": 200},
            None,
            "did not report a completed",
        ),
        (
            {"body": "<html>boom</html>", "status": 500},
            None,
            "/converter returned status 500",
        ),
        (
            {"body": json.dumps({"error": -3}), "status": 200},
            None,
            "error code -3",
        ),
        (
            {"body": _ok_body(), "status": 200},
            {"body": requests.exceptions.Timeout()},
            None,
        ),
        (
            {"body": _ok_body(), "status": 200},
            {"body": "boom", "status": 500},
            "file download returned status 500",
        ),
    ],
    ids=[
        "convert_timeout",
        "convert_non_json_body",
        "convert_incomplete_sync_response",
        "convert_5xx",
        "convert_error_code",
        "download_timeout",
        "download_5xx",
    ],
)
@responses.activate
def test_convert_maps_provider_failures_to_provider_error(
    post_kwargs, get_kwargs, expected_message
):
    """Map any transport or HTTP failure from OnlyOffice to ConversionProviderError."""
    responses.add(responses.POST, CONVERT_URL, **post_kwargs)
    if get_kwargs is not None:
        responses.add(responses.GET, FILE_URL, **get_kwargs)

    backend = OnlyOfficeConversionBackend(convert_service_url=CONVERT_URL)

    with pytest.raises(exceptions.ConversionProviderError, match=expected_message):
        backend.convert(_item(), SOURCE_URL, "docx")
