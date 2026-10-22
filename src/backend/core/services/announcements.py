"""Announcements published by the administrators to the frontend."""

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from core import models

CACHE_KEY = "announcements:live"


def _language(code):
    """Return the language part of a language code, e.g. "fr" for "fr-fr"."""
    return code.replace("_", "-").split("-")[0].lower()


def _localized(announcement, field):
    """
    Return the non empty translations of a field, keyed by language, with a
    `default` fallback taken from the default language or the first translated
    language. None when the field is not translated at all.
    """
    texts = {}
    for translation in announcement.translations.all():
        value = getattr(translation, field)
        if value:
            texts[_language(translation.language_code)] = value
    if not texts:
        return None

    languages = [_language(settings.LANGUAGE_CODE)] + [
        _language(code) for code, _name in settings.LANGUAGES
    ]
    default = next((texts[lang] for lang in languages if lang in texts), None)
    texts["default"] = default or next(iter(texts.values()))
    return texts


def serialize_announcement(announcement):
    """Return the announcement as sent to the frontend, None if it has no body."""
    body = _localized(announcement, "body")
    if not body:
        return None

    cta_label = _localized(announcement, "cta_label")
    return {
        "id": str(announcement.id),
        "display": announcement.display,
        "level": announcement.level,
        "title": _localized(announcement, "title"),
        "body": body,
        "cta": (
            {
                "label": cta_label,
                "url": announcement.cta_url,
                "new_tab": announcement.cta_new_tab,
            }
            if announcement.cta_url and cta_label
            else None
        ),
        "is_dismissible": announcement.is_dismissible,
    }


def get_live_announcements():
    """Return the live announcements, ordered by priority. Cached."""
    announcements = cache.get(CACHE_KEY)
    if announcements is None:
        queryset = models.Announcement.objects.live().prefetch_related("translations")
        announcements = [
            serialized
            for announcement in queryset
            if (serialized := serialize_announcement(announcement))
        ]
        cache.set(CACHE_KEY, announcements, settings.ANNOUNCEMENTS_CACHE_TIMEOUT)
    return announcements


def invalidate_announcements_cache():
    """
    Clear the cache now, and again once the transaction is committed so that a
    request running meanwhile cannot cache the previous announcements.
    """
    cache.delete(CACHE_KEY)
    transaction.on_commit(lambda: cache.delete(CACHE_KEY))
