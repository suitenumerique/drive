"""
Unit tests for the User model
"""

import pytest
from configurations import values

from drive.settings import Base, Feature, LoadTest, PreProduction, Production, Staging


def test_invalid_settings_oidc_email_configuration():
    """
    The OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION and OIDC_ALLOW_DUPLICATE_EMAILS settings
    should not be both set to True simultaneously.
    """

    class TestSettings(Base):
        """Fake test settings."""

        OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION = True
        OIDC_ALLOW_DUPLICATE_EMAILS = True

    # The validation is performed during post_setup
    with pytest.raises(ValueError) as excinfo:
        TestSettings().post_setup()

    # Check the exception message
    assert str(excinfo.value) == (
        "Both OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION and "
        "OIDC_ALLOW_DUPLICATE_EMAILS cannot be set to True simultaneously. "
    )


def test_load_e2e_urls_is_not_environment_configurable():
    """
    LOAD_E2E_URLS exposes credential-less login endpoints: it must be a plain
    literal so it can never be flipped through an environment variable.
    """
    assert Base.LOAD_E2E_URLS is False
    assert not isinstance(Base.LOAD_E2E_URLS, values.Value)


@pytest.mark.parametrize("configuration", [Production, Feature, Staging, PreProduction])
def test_load_e2e_urls_disabled_on_production_configurations(configuration):
    """No production-facing configuration may expose the e2e auth endpoints."""
    assert configuration.LOAD_E2E_URLS is False


def test_load_e2e_urls_refused_outside_allowlist():
    """
    Even if a configuration sets LOAD_E2E_URLS to True, the application must
    refuse to start unless the configuration is explicitly allowlisted.
    """

    class EvilProduction(Production):
        """Fake production settings trying to expose the e2e auth endpoints."""

        LOAD_E2E_URLS = True

    with pytest.raises(ValueError) as excinfo:
        EvilProduction().post_setup()

    assert str(excinfo.value) == (
        "LOAD_E2E_URLS must never be enabled on the EvilProduction configuration."
    )


def test_load_e2e_urls_allowed_on_load_test_configuration():
    """The dedicated LoadTest configuration exposes the e2e auth endpoints."""
    assert LoadTest.LOAD_E2E_URLS is True
    LoadTest().post_setup()
