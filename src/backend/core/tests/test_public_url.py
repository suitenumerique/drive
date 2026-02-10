"""Tests for canonical DRIVE_PUBLIC_URL validation/normalization."""

import pytest

from core.utils.public_url import (
    PublicUrlValidationError,
    join_public_url,
    normalize_drive_public_url,
    normalize_public_surface_base_url,
)


def test_normalize_drive_public_url_removes_trailing_slash():
    """Normalization should remove trailing slashes for deterministic derivations."""

    assert (
        normalize_drive_public_url(
            "https://drive.example.com/",
            https_only_posture=True,
            debug=False,
            allow_insecure_http=False,
        )
        == "https://drive.example.com"
    )


@pytest.mark.parametrize(
    "raw",
    [
        "https://drive.example.com/path",
        "https://drive.example.com/path/",
        "https://drive.example.com/?q=1",
        "https://drive.example.com/#frag",
        "https://user:pass@drive.example.com",
    ],
)
def test_normalize_drive_public_url_rejects_non_canonical_components(raw):
    """Reject query/fragment/userinfo/path to keep a canonical base URL."""

    with pytest.raises(PublicUrlValidationError) as excinfo:
        normalize_drive_public_url(
            raw,
            https_only_posture=True,
            debug=False,
            allow_insecure_http=False,
        )

    assert excinfo.value.failure_class == "config.public_url.invalid"
    assert excinfo.value.next_action_hint


def test_normalize_drive_public_url_requires_https_in_https_only_posture():
    """HTTPS-only posture rejects HTTP regardless of override."""

    with pytest.raises(PublicUrlValidationError) as excinfo:
        normalize_drive_public_url(
            "http://drive.example.com",
            https_only_posture=True,
            debug=False,
            allow_insecure_http=True,
        )

    assert excinfo.value.failure_class == "config.public_url.https_required"


def test_normalize_drive_public_url_allows_http_in_dev_with_override():
    """HTTP is allowed only when DEBUG=true and the centralized override is enabled."""

    assert (
        normalize_drive_public_url(
            "http://drive.example.com/",
            https_only_posture=False,
            debug=True,
            allow_insecure_http=True,
        )
        == "http://drive.example.com"
    )


def test_normalize_public_surface_base_url_accepts_wopi_src_base_url_https():
    """WOPI public-surface base URLs should be normalized the same way."""

    assert (
        normalize_public_surface_base_url(
            "https://wopi.example.com/",
            setting_name="WOPI_SRC_BASE_URL",
            https_only_posture=True,
            debug=False,
            allow_insecure_http=False,
        )
        == "https://wopi.example.com"
    )


def test_join_public_url_avoids_double_slashes():
    """URL derivations should not introduce double slashes."""

    assert join_public_url("https://drive.example.com", "/api/v1.0/") == (
        "https://drive.example.com/api/v1.0/"
    )
    assert join_public_url("https://drive.example.com/", "api/v1.0/") == (
        "https://drive.example.com/api/v1.0/"
    )
