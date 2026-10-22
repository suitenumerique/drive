"""Tests for the announcements API endpoint."""

from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

URL = "/api/v1.0/announcements/"


def _translate(announcement, language_code, **fields):
    """Add a translation to an announcement."""
    announcement.set_current_language(language_code)
    for name, value in fields.items():
        setattr(announcement, name, value)
    announcement.save()


@pytest.mark.parametrize("is_authenticated", [False, True])
def test_api_announcements_list_empty(is_authenticated):
    """Anyone can list the announcements, there are none by default."""
    client = APIClient()
    if is_authenticated:
        client.force_login(factories.UserFactory())

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


@override_settings(LANGUAGE_CODE="en-us")
def test_api_announcements_list_translated():
    """Texts are given per language, with a default fallback."""
    announcement = factories.AnnouncementFactory(
        display=models.AnnouncementDisplayChoices.HEADER_BANNER,
        level=models.AnnouncementLevelChoices.WARNING,
        body="Maintenance today",
        cta_label="Read more",
        cta_url="https://status.example.com",
        cta_new_tab=False,
        is_dismissible=False,
    )
    _translate(announcement, "fr-fr", body="Maintenance aujourd'hui", cta_label="En savoir plus")

    response = APIClient().get(URL)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(announcement.id),
            "display": "header_banner",
            "level": "warning",
            "title": None,
            "body": {
                "default": "Maintenance today",
                "en": "Maintenance today",
                "fr": "Maintenance aujourd'hui",
            },
            "cta": {
                "label": {
                    "default": "Read more",
                    "en": "Read more",
                    "fr": "En savoir plus",
                },
                "url": "https://status.example.com",
                "new_tab": False,
            },
            "is_dismissible": False,
        }
    ]


@override_settings(LANGUAGE_CODE="en-us")
def test_api_announcements_list_default_fallback():
    """Without a text in the default language, the first translated language is used."""
    announcement = models.Announcement(is_active=True)
    announcement.set_current_language("de-de")
    announcement.body = "Wartung"
    announcement.save()

    response = APIClient().get(URL)

    assert response.json()[0]["body"] == {"default": "Wartung", "de": "Wartung"}


def test_api_announcements_list_incomplete_cta():
    """A link without a URL or without a label is not sent."""
    factories.AnnouncementFactory(cta_label="Read more", priority=1)
    factories.AnnouncementFactory(cta_url="https://example.com")

    response = APIClient().get(URL)

    assert [announcement["cta"] for announcement in response.json()] == [None, None]


def test_api_announcements_list_title():
    """The title is sent when it is set."""
    factories.AnnouncementFactory(title="Hello")

    response = APIClient().get(URL)

    assert response.json()[0]["title"]["default"] == "Hello"


def test_api_announcements_list_live_only_ordered():
    """Only live announcements are listed, by priority."""
    now = timezone.now()
    low = factories.AnnouncementFactory(priority=0)
    high = factories.AnnouncementFactory(priority=5)
    factories.AnnouncementFactory(is_active=False)
    factories.AnnouncementFactory(starts_at=now + timedelta(hours=1))

    response = APIClient().get(URL)

    assert [announcement["id"] for announcement in response.json()] == [
        str(high.id),
        str(low.id),
    ]


def test_api_announcements_list_cached():
    """The list is cached, changes bypassing the model signals are not seen."""
    announcement = factories.AnnouncementFactory()
    client = APIClient()
    assert len(client.get(URL).json()) == 1

    models.Announcement.objects.filter(pk=announcement.pk).update(is_active=False)

    assert len(client.get(URL).json()) == 1


def test_api_announcements_list_cache_invalidated_on_save():
    """Saving an announcement publishes the change right away."""
    announcement = factories.AnnouncementFactory()
    client = APIClient()
    assert len(client.get(URL).json()) == 1

    announcement.is_active = False
    announcement.save()

    assert client.get(URL).json() == []


def test_api_announcements_list_cache_invalidated_on_translation_save():
    """Saving a translation publishes the change right away."""
    announcement = factories.AnnouncementFactory(body="Before")
    client = APIClient()
    assert client.get(URL).json()[0]["body"]["default"] == "Before"

    translation = announcement.translations.get()
    translation.body = "After"
    translation.save()

    assert client.get(URL).json()[0]["body"]["default"] == "After"


def test_api_announcements_list_cache_invalidated_on_delete():
    """Deleting an announcement publishes the change right away."""
    announcement = factories.AnnouncementFactory()
    client = APIClient()
    assert len(client.get(URL).json()) == 1

    announcement.delete()

    assert client.get(URL).json() == []
