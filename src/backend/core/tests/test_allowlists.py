"""Allowlist normalization/validation tests (no-leak, deterministic errors)."""

# pylint: disable=missing-function-docstring

import pytest

from core.utils.allowlists import (
    AllowlistValidationError,
    TlsPosture,
    extract_host_from_url_form,
    normalize_allowlisted_host,
    normalize_allowlisted_origin,
    normalize_allowlisted_redirect_uri,
)


def test_normalize_allowlisted_redirect_uri_adds_root_path():
    assert (
        normalize_allowlisted_redirect_uri(
            "https://Drive.Example.com",
            setting_name="DRIVE_ALLOWED_REDIRECT_URIS",
            posture=TlsPosture(
                https_only_posture=True,
                debug=False,
                allow_insecure_http=False,
            ),
        )
        == "https://drive.example.com/"
    )


def test_normalize_allowlisted_redirect_uri_rejects_query_no_leak():
    with pytest.raises(AllowlistValidationError) as excinfo:
        normalize_allowlisted_redirect_uri(
            "https://drive.example.com/cb?token=super-secret",
            setting_name="DRIVE_ALLOWED_REDIRECT_URIS",
            posture=TlsPosture(
                https_only_posture=True,
                debug=False,
                allow_insecure_http=False,
            ),
        )

    message = str(excinfo.value)
    assert "failure_class=config.allowlist.redirect_uri.invalid" in message
    assert "super-secret" not in message
    assert "token=" not in message


def test_normalize_allowlisted_redirect_uri_rejects_http_in_https_only_posture():
    with pytest.raises(AllowlistValidationError) as excinfo:
        normalize_allowlisted_redirect_uri(
            "http://drive.example.com/cb",
            setting_name="DRIVE_ALLOWED_REDIRECT_URIS",
            posture=TlsPosture(
                https_only_posture=True,
                debug=True,
                allow_insecure_http=True,
            ),
        )

    assert excinfo.value.failure_class == "config.allowlist.redirect_uri.https_required"


def test_normalize_allowlisted_redirect_uri_allows_http_only_in_dev_with_override():
    assert (
        normalize_allowlisted_redirect_uri(
            "http://drive.example.com/cb",
            setting_name="DRIVE_ALLOWED_REDIRECT_URIS",
            posture=TlsPosture(
                https_only_posture=False,
                debug=True,
                allow_insecure_http=True,
            ),
        )
        == "http://drive.example.com/cb"
    )


def test_normalize_allowlisted_origin_normalizes_and_enforces_tls_posture():
    assert (
        normalize_allowlisted_origin(
            "https://Drive.Example.com/",
            setting_name="DRIVE_ALLOWED_ORIGINS",
            posture=TlsPosture(
                https_only_posture=True,
                debug=False,
                allow_insecure_http=False,
            ),
        )
        == "https://drive.example.com"
    )

    with pytest.raises(AllowlistValidationError):
        normalize_allowlisted_origin(
            "http://drive.example.com",
            setting_name="DRIVE_ALLOWED_ORIGINS",
            posture=TlsPosture(
                https_only_posture=True,
                debug=False,
                allow_insecure_http=True,
            ),
        )


def test_normalize_allowlisted_host_normalizes_and_rejects_scheme():
    assert (
        normalize_allowlisted_host(
            "Drive.Example.com:3000",
            setting_name="DRIVE_ALLOWED_HOSTS",
        )
        == "drive.example.com:3000"
    )

    with pytest.raises(AllowlistValidationError):
        normalize_allowlisted_host(
            "https://drive.example.com",
            setting_name="DRIVE_ALLOWED_HOSTS",
        )


def test_extract_host_from_url_form_validates_tls_posture():
    assert (
        extract_host_from_url_form(
            "http://localhost:3000",
            setting_name="OIDC_REDIRECT_ALLOWED_HOSTS",
            posture=TlsPosture(
                https_only_posture=False,
                debug=True,
                allow_insecure_http=True,
            ),
        )
        == "localhost:3000"
    )
