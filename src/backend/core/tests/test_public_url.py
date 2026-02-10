"""Tests for canonical DRIVE_PUBLIC_URL validation/normalization."""

import pytest

from core.utils.public_url import PublicUrlValidationError, normalize_drive_public_url


def test_normalize_drive_public_url_removes_trailing_slash():
    """Normalization should remove trailing slashes for deterministic derivations."""

    assert (
        normalize_drive_public_url(
            "https://drive.example.com/",
            production_posture=True,
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
            production_posture=True,
            allow_insecure_http=False,
        )

    assert excinfo.value.failure_class == "config.public_url.invalid"
    assert excinfo.value.next_action_hint


def test_normalize_drive_public_url_requires_https_in_production_posture():
    """Production posture requires HTTPS unless a dev-only override is set."""

    with pytest.raises(PublicUrlValidationError) as excinfo:
        normalize_drive_public_url(
            "http://drive.example.com",
            production_posture=True,
            allow_insecure_http=False,
        )

    assert excinfo.value.failure_class == "config.public_url.https_required"


def test_normalize_drive_public_url_allows_http_in_production_posture_with_override():
    """The dev-only override allows HTTP even in production posture."""

    assert (
        normalize_drive_public_url(
            "http://drive.example.com/",
            production_posture=True,
            allow_insecure_http=True,
        )
        == "http://drive.example.com"
    )
