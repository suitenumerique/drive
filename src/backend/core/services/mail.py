"""Render and send the transactional emails of Drive."""

import smtplib
from logging import getLogger

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import get_language, override

logger = getLogger(__name__)


def get_email_base_url():
    """Return the base url of the links put in emails."""
    return settings.EMAIL_URL_APP or Site.objects.get_current().domain


def get_branding_context():
    """Return the instance branding shared by all the email templates."""
    return {
        "brandname": settings.EMAIL_BRAND_NAME,
        "domain": get_email_base_url(),
        "logo_img": settings.EMAIL_LOGO_IMG,
    }


def send_templated_email(subject, recipients, template_name, context=None, language=None):
    """
    Render the html and plain text versions of a mail template and send them.

    `template_name` is the name of a template built from src/mail/mjml, without
    extension. Sending is skipped when no SMTP host is configured, and SMTP errors
    are logged instead of raised so that they never break the calling request.
    """
    if not settings.EMAIL_HOST:
        logger.debug("EMAIL_HOST host is not set, skipping email sending")
        return

    context = {**(context or {}), **get_branding_context()}

    with override(language or get_language()):
        msg_html = render_to_string(f"mail/html/{template_name}.html", context)
        msg_plain = render_to_string(f"mail/text/{template_name}.txt", context)
        subject = str(subject)  # Force translation

        try:
            send_mail(
                subject.capitalize(),
                msg_plain,
                settings.EMAIL_FROM,
                recipients,
                html_message=msg_html,
                fail_silently=False,
            )
        except smtplib.SMTPException as exception:
            logger.error("email to %s was not sent: %s", recipients, exception)
