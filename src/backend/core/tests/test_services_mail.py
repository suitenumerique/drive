"""Tests for the email sending service."""

import smtplib
from unittest import mock

from django.core import mail

import pytest

from core.services.mail import send_templated_email

pytestmark = pytest.mark.django_db


CONTEXT = {
    "title": "My title",
    "message": "My message",
    "link": "https://example.com/some-link/",
    "link_label": "Click here",
    "button_label": "Confirm",
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


def test_services_mail_send_templated_email_branding_wins(settings):
    """A caller cannot override the instance branding through its context."""
    settings.EMAIL_BRAND_NAME = "My brand"

    send_templated_email(
        "my subject", ["a@example.com"], "reconciliation", {**CONTEXT, "brandname": "Fake"}
    )

    # pylint: disable-next=no-member
    email_content = mail.outbox[0].body
    assert "My brand" in email_content
    assert "Fake" not in email_content


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
