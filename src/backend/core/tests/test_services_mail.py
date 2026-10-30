"""Tests for the email sending service."""

import smtplib
from unittest import mock

from django.core import mail
from django.utils.html import format_html

import pytest

from core.services.mail import (
    get_branding_context,
    get_plain_text_context,
    send_templated_email,
)

pytestmark = pytest.mark.django_db

CONTEXT = {
    "title": "My title",
    "message": "My message",
    "link": "https://example.com/some-link/",
    "link_label": "Click here",
    "button_label": "Confirm",
}

OPTIONAL_BRANDING_SETTINGS = [
    "EMAIL_FONT_REGULAR_URL",
    "EMAIL_FONT_BOLD_URL",
    "EMAIL_GOVERNMENT_LOGO_IMG",
    "EMAIL_LOGO_IMG",
    "EMAIL_NEWSLETTER_URL",
    "EMAIL_SUITE_LOGO_IMG",
    "EMAIL_SUITE_URL",
    "EMAIL_SUPPORT_URL",
    "EMAIL_TERMS_OF_SERVICE_URL",
]


@pytest.fixture(name="full_branding")
def fixture_full_branding(settings):
    """Configure every branding setting of the email templates."""
    settings.EMAIL_URL_APP = "https://files.example.com"
    settings.EMAIL_APP_NAME = "Files"
    settings.EMAIL_BRAND_NAME = "My brand"
    settings.EMAIL_FONT_FAMILY = "Inter"
    settings.EMAIL_FONT_REGULAR_URL = "https://cdn.example.com/inter-400.woff2"
    settings.EMAIL_FONT_BOLD_URL = "https://cdn.example.com/inter-700.woff2"
    settings.EMAIL_GOVERNMENT_LOGO_IMG = "https://cdn.example.com/gov.png"
    settings.EMAIL_LOGO_IMG = "https://cdn.example.com/logo.png"
    settings.EMAIL_NEWSLETTER_URL = "https://example.com/newsletter"
    settings.EMAIL_PRODUCT_ICONS = {
        "Docs": {"img": "https://cdn.example.com/docs.png", "href": "https://docs.example.com"}
    }
    settings.EMAIL_SUITE_LOGO_IMG = "https://cdn.example.com/suite.png"
    settings.EMAIL_SUITE_URL = "https://suite.example.com"
    settings.EMAIL_SUPPORT_URL = "https://example.com/support"
    settings.EMAIL_TERMS_OF_SERVICE_URL = "https://example.com/terms"
    return settings


@pytest.fixture(name="no_branding")
def fixture_no_branding(settings):
    """Leave every optional branding setting of the email templates unset."""
    for name in OPTIONAL_BRANDING_SETTINGS:
        setattr(settings, name, None)
    settings.EMAIL_PRODUCT_ICONS = {}
    settings.EMAIL_BRAND_NAME = "My brand"
    settings.FRONTEND_HELP_MENU_CONFIG = {}
    return settings


@pytest.mark.usefixtures("full_branding")
def test_services_mail_branding_context():
    """Every branding value of the email templates comes from settings."""
    assert get_branding_context() == {
        "app_name": "Files",
        "brandname": "My brand",
        "domain": "https://files.example.com",
        "font_family": "Inter",
        "font_stack": "Inter, Arial, Helvetica, sans-serif",
        "font_regular_url": "https://cdn.example.com/inter-400.woff2",
        "font_bold_url": "https://cdn.example.com/inter-700.woff2",
        "government_logo_img": "https://cdn.example.com/gov.png",
        "logo_img": "https://cdn.example.com/logo.png",
        "newsletter_url": "https://example.com/newsletter",
        "product_icons": {
            "Docs": {"img": "https://cdn.example.com/docs.png", "href": "https://docs.example.com"}
        },
        "suite_logo_img": "https://cdn.example.com/suite.png",
        "suite_url": "https://suite.example.com",
        "support_url": "https://example.com/support",
        "terms_of_service_url": "https://example.com/terms",
    }


@pytest.mark.parametrize(
    "font_family,font_stack",
    [
        ("Marianne", "Marianne, Arial, Helvetica, sans-serif"),
        ("", "Arial, Helvetica, sans-serif"),
        (None, "Arial, Helvetica, sans-serif"),
    ],
)
def test_services_mail_branding_context_font_stack(font_family, font_stack, settings):
    """The configured font always comes with fonts every email client knows."""
    settings.EMAIL_FONT_FAMILY = font_family

    assert get_branding_context()["font_stack"] == font_stack


@pytest.mark.parametrize(
    "support_email,support_url",
    [
        ("mailto:support@example.com", "mailto:support@example.com"),
        ("support@example.com", "mailto:support@example.com"),
        ("https://example.com/support", "https://example.com/support"),
    ],
)
def test_services_mail_branding_context_help_menu_links(support_email, support_url, settings):
    """Without email specific links, the links of the frontend help menu are used."""
    settings.EMAIL_SUPPORT_URL = None
    settings.EMAIL_TERMS_OF_SERVICE_URL = None
    settings.FRONTEND_HELP_MENU_CONFIG = {
        "supportEmail": support_email,
        "legal": {"termsOfUseUrl": "https://example.com/help-terms"},
    }

    context = get_branding_context()

    assert context["support_url"] == support_url
    assert context["terms_of_service_url"] == "https://example.com/help-terms"


def test_services_mail_branding_context_email_links_win(settings):
    """Email specific links take precedence over the frontend help menu ones."""
    settings.EMAIL_SUPPORT_URL = "https://example.com/email-support"
    settings.EMAIL_TERMS_OF_SERVICE_URL = "https://example.com/email-terms"
    settings.FRONTEND_HELP_MENU_CONFIG = {
        "supportEmail": "mailto:support@example.com",
        "legal": {"termsOfUseUrl": "https://example.com/help-terms"},
    }

    context = get_branding_context()

    assert context["support_url"] == "https://example.com/email-support"
    assert context["terms_of_service_url"] == "https://example.com/email-terms"


def test_services_mail_plain_text_context():
    """
    HTML marked safe is turned into plain text, other values are left untouched.
    Escaped user content, like an item title, is restored as typed.
    """
    context = {
        "message": format_html("<strong>{}</strong> shared {}", "Alice", "R&D <notes>"),
        "title": "R&D",
        "count": 3,
    }

    assert get_plain_text_context(context) == {
        "message": "Alice shared R&D <notes>",
        "title": "R&D",
        "count": 3,
    }


def test_services_mail_send_templated_email(settings):
    """The html and plain text versions of the template are sent to the recipients."""
    settings.EMAIL_BRAND_NAME = "My brand"

    send_templated_email(
        "my subject", ["a@example.com", "b@example.com"], "reconciliation", CONTEXT, "en"
    )

    # pylint: disable-next=no-member
    assert len(mail.outbox) == 1
    # pylint: disable-next=no-member
    email = mail.outbox[0]
    assert email.subject == "My subject"
    assert email.to == ["a@example.com", "b@example.com"]
    assert "My message" in email.body
    html, mimetype = email.alternatives[0]
    assert mimetype == "text/html"
    assert "https://example.com/some-link/" in html


def test_services_mail_send_templated_email_subject_case():
    """Only the first letter of the subject is uppercased, names keep their case."""
    send_templated_email(
        "alice Martin shared an item with you: Q3 Report",
        ["a@example.com"],
        "reconciliation",
        CONTEXT,
    )

    # pylint: disable-next=no-member
    assert mail.outbox[0].subject == "Alice Martin shared an item with you: Q3 Report"


@pytest.mark.usefixtures("full_branding")
def test_services_mail_send_templated_email_branding_wins():
    """A caller cannot override the instance branding through its context."""
    send_templated_email(
        "my subject", ["a@example.com"], "reconciliation", {**CONTEXT, "brandname": "Fake"}
    )

    # pylint: disable-next=no-member
    html = mail.outbox[0].alternatives[0][0]
    assert 'alt="My brand"' in html
    assert "Fake" not in html


@pytest.mark.usefixtures("full_branding")
def test_services_mail_send_templated_email_full_branding():
    """Every configured branding block is shown in the email."""
    send_templated_email("my subject", ["a@example.com"], "reconciliation", CONTEXT, "en")

    # pylint: disable-next=no-member
    email = mail.outbox[0]
    html = email.alternatives[0][0]
    assert 'src="https://cdn.example.com/logo.png"' in html
    assert 'src="https://cdn.example.com/gov.png"' in html
    assert 'src="https://cdn.example.com/suite.png"' in html
    assert 'href="https://suite.example.com"' in html
    assert 'src="https://cdn.example.com/docs.png"' in html
    assert 'href="https://docs.example.com"' in html
    assert 'url("https://cdn.example.com/inter-400.woff2")' in html
    assert 'url("https://cdn.example.com/inter-700.woff2")' in html
    assert "font-family:Inter, Arial, Helvetica, sans-serif" in html
    assert "The Files team" in email.body
    assert "Subscribe to the My brand newsletter [https://example.com/newsletter]" in email.body
    assert "Contact support [https://example.com/support]" in email.body
    assert "Terms of use [https://example.com/terms]" in email.body


@pytest.mark.usefixtures("no_branding")
def test_services_mail_send_templated_email_no_branding():
    """Branding blocks without a configured value are not shown."""
    send_templated_email("my subject", ["a@example.com"], "reconciliation", CONTEXT, "en")

    # pylint: disable-next=no-member
    email = mail.outbox[0]
    html = email.alternatives[0][0]
    assert "@font-face" not in html
    # Only the banner icon is left, it is part of the template
    assert html.count("<img") == 1
    assert "/assets/email/icon-users.png" in html
    assert "newsletter" not in email.body
    assert "Contact support" not in email.body
    assert "Terms of use" not in email.body
    # The message itself is still there
    assert "My message" in email.body


@mock.patch("core.services.mail.send_mail")
def test_services_mail_send_templated_email_no_host(mock_send_mail, settings):
    """Nothing is sent when no SMTP host is configured."""
    settings.EMAIL_HOST = None

    send_templated_email("my subject", ["a@example.com"], "reconciliation", CONTEXT)

    mock_send_mail.assert_not_called()


@mock.patch(
    "core.services.mail.send_mail",
    side_effect=smtplib.SMTPException("Error SMTPException"),
)
def test_services_mail_send_templated_email_smtp_error(_mock_send_mail, caplog):
    """SMTP errors are logged and not raised to the caller."""
    with caplog.at_level("ERROR", logger="core.services.mail"):
        send_templated_email("my subject", ["a@example.com"], "reconciliation", CONTEXT)

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == (
        "email to ['a@example.com'] was not sent: Error SMTPException"
    )
