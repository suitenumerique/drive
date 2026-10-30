"""Render and send the transactional emails of Drive."""

import html
import smtplib
from logging import getLogger

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.safestring import SafeString
from django.utils.text import capfirst
from django.utils.translation import get_language, override

logger = getLogger(__name__)

# Used when the configured font is not loaded. Outlook on Windows needs a font it
# knows, or it falls back to Times New Roman.
FALLBACK_FONTS = ["Arial", "Helvetica", "sans-serif"]


def get_email_base_url():
    """Return the base url of the links put in emails."""
    return settings.EMAIL_URL_APP or Site.objects.get_current().domain


def get_help_menu_links():
    """
    Return the support and terms of use links of the frontend help menu, so that
    emails show the same links without configuring them twice.
    """
    help_menu = settings.FRONTEND_HELP_MENU_CONFIG or {}
    support_url = help_menu.get("supportEmail")
    if support_url and ":" not in support_url:
        support_url = f"mailto:{support_url}"
    terms_of_service_url = (help_menu.get("legal") or {}).get("termsOfUseUrl")
    return support_url, terms_of_service_url


def get_branding_context():
    """Return the instance branding shared by all the email templates."""
    font_family = settings.EMAIL_FONT_FAMILY
    help_support_url, help_terms_of_service_url = get_help_menu_links()
    return {
        "app_name": settings.EMAIL_APP_NAME,
        "brandname": settings.EMAIL_BRAND_NAME,
        "domain": get_email_base_url(),
        "font_family": font_family,
        "font_stack": ", ".join(filter(None, [font_family, *FALLBACK_FONTS])),
        "font_regular_url": settings.EMAIL_FONT_REGULAR_URL,
        "font_bold_url": settings.EMAIL_FONT_BOLD_URL,
        "government_logo_img": settings.EMAIL_GOVERNMENT_LOGO_IMG,
        "logo_img": settings.EMAIL_LOGO_IMG,
        "newsletter_url": settings.EMAIL_NEWSLETTER_URL,
        "product_icons": settings.EMAIL_PRODUCT_ICONS,
        "suite_logo_img": settings.EMAIL_SUITE_LOGO_IMG,
        "suite_url": settings.EMAIL_SUITE_URL,
        "support_url": settings.EMAIL_SUPPORT_URL or help_support_url,
        "terms_of_service_url": (settings.EMAIL_TERMS_OF_SERVICE_URL or help_terms_of_service_url),
    }


def get_plain_text_context(context):
    """
    Return the context used to render the plain text version of an email.

    Values marked safe hold HTML meant for the html version: their tags and entities
    are removed so that they read well as plain text.
    """
    return {
        key: html.unescape(strip_tags(value)) if isinstance(value, SafeString) else value
        for key, value in context.items()
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
        msg_plain = render_to_string(
            f"mail/text/{template_name}.txt", get_plain_text_context(context)
        )
        # Force translation. Only the first letter is uppercased: str.capitalize
        # would lowercase the rest, names and item titles included.
        subject = capfirst(str(subject))

        try:
            send_mail(
                subject,
                msg_plain,
                settings.EMAIL_FROM,
                recipients,
                html_message=msg_html,
                fail_silently=False,
            )
        except smtplib.SMTPException as exception:
            logger.exception("email to %s was not sent: %s", recipients, exception)
