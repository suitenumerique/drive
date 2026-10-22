"""Tests for the announcement admin."""

from django.contrib import admin
from django.test import RequestFactory

import pytest
from rest_framework.test import APIClient

from core import factories, models
from core.admin import AnnouncementAdmin

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def static_files_without_manifest(settings):
    """Render the admin pages without a static files manifest."""
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


ADD_URL = "/admin/core/announcement/add/?language=en-us"


@pytest.fixture(name="admin_client")
def fixture_admin_client(client):
    """A Django test client logged in as a superuser."""
    client.force_login(factories.UserFactory(is_staff=True, is_superuser=True))
    return client


def _form_data(**data):
    """The data posted by the announcement add form."""
    return {
        "display": models.AnnouncementDisplayChoices.HEADER_BANNER,
        "level": models.AnnouncementLevelChoices.INFO,
        "title": "",
        "body": "Maintenance today",
        "cta_label": "",
        "cta_url": "",
        "cta_new_tab": "on",
        "is_active": "on",
        "starts_at_0": "",
        "starts_at_1": "",
        "ends_at_0": "",
        "ends_at_1": "",
        "priority": "0",
        "is_dismissible": "on",
        **data,
    }


def test_admin_announcements_changelist(admin_client):
    """The list of announcements renders."""
    factories.AnnouncementFactory(body="Maintenance today")

    response = admin_client.get("/admin/core/announcement/")

    assert response.status_code == 200
    assert "Maintenance today" in response.content.decode()


def test_admin_announcements_add(admin_client):
    """An announcement is created in the language of the form."""
    response = admin_client.post(
        ADD_URL,
        _form_data(cta_label="Read more", cta_url="https://status.example.com"),
    )

    assert response.status_code == 302
    announcement = models.Announcement.objects.get()
    translation = announcement.translations.get()
    assert translation.language_code == "en-us"
    assert translation.body == "Maintenance today"
    assert translation.cta_label == "Read more"
    assert announcement.cta_url == "https://status.example.com"
    assert len(APIClient().get("/api/v1.0/announcements/").json()) == 1


def test_admin_announcements_add_header_banner_too_long(admin_client):
    """A header banner is a single line, its body is limited."""
    max_length = models.Announcement.HEADER_BANNER_BODY_MAX_LENGTH

    response = admin_client.post(ADD_URL, _form_data(body="a" * (max_length + 1)))

    assert response.status_code == 200
    assert response.context["adminform"].form.errors["body"] == [
        f"A header banner is limited to {max_length} characters."
    ]
    assert not models.Announcement.objects.exists()


def test_admin_announcements_add_cta_label_without_url(admin_client):
    """A link label needs a URL."""
    response = admin_client.post(ADD_URL, _form_data(cta_label="Read more"))

    assert response.status_code == 200
    assert response.context["adminform"].form.errors["cta_url"] == ["The link needs a URL."]


def test_admin_announcements_add_cta_url_without_label(admin_client):
    """A link URL needs a label."""
    response = admin_client.post(ADD_URL, _form_data(cta_url="https://example.com"))

    assert response.status_code == 200
    assert response.context["adminform"].form.errors["cta_label"] == ["The link needs a label."]


def test_admin_announcements_change_cta_label_in_other_language(admin_client):
    """A link URL can rely on the label given in another language."""
    announcement = factories.AnnouncementFactory(
        body="Maintenance today",
        cta_label="Read more",
        cta_url="https://status.example.com",
    )

    response = admin_client.post(
        f"/admin/core/announcement/{announcement.pk}/change/?language=fr-fr",
        _form_data(body="Maintenance aujourd'hui", cta_url="https://status.example.com"),
    )

    assert response.status_code == 302
    assert announcement.translations.count() == 2


def test_admin_announcements_actions():
    """The actions (de)activate the announcements and publish it right away."""
    announcement = factories.AnnouncementFactory(is_active=False)
    model_admin = AnnouncementAdmin(models.Announcement, admin.site)
    request = RequestFactory().post("/")
    queryset = models.Announcement.objects.all()
    client = APIClient()
    assert client.get("/api/v1.0/announcements/").json() == []

    model_admin.activate(request, queryset)

    announcement.refresh_from_db()
    assert announcement.is_active is True
    assert len(client.get("/api/v1.0/announcements/").json()) == 1

    model_admin.deactivate(request, queryset)

    announcement.refresh_from_db()
    assert announcement.is_active is False
    assert client.get("/api/v1.0/announcements/").json() == []
