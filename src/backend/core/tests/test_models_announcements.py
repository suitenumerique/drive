"""Unit tests for the Announcement model."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

import pytest

from core import factories, models

pytestmark = pytest.mark.django_db


def test_models_announcements_live():
    """Only active announcements whose display window contains now are live."""
    now = timezone.now()
    hour = timedelta(hours=1)
    no_window = factories.AnnouncementFactory()
    in_window = factories.AnnouncementFactory(starts_at=now - hour, ends_at=now + hour)
    started = factories.AnnouncementFactory(starts_at=now - hour)
    factories.AnnouncementFactory(is_active=False)
    factories.AnnouncementFactory(starts_at=now + hour)
    factories.AnnouncementFactory(ends_at=now - hour, starts_at=now - 2 * hour)

    live = models.Announcement.objects.live(now)

    assert set(live) == {no_window, in_window, started}
    for announcement in models.Announcement.objects.all():
        assert announcement.is_live(now) == (announcement in live)


def test_models_announcements_ordering():
    """Announcements with a higher priority come first, then the last updated."""
    low = factories.AnnouncementFactory(priority=0)
    high = factories.AnnouncementFactory(priority=10)
    newer_low = factories.AnnouncementFactory(priority=0)

    assert list(models.Announcement.objects.all()) == [high, newer_low, low]


def test_models_announcements_end_after_start():
    """An announcement cannot end before it starts."""
    now = timezone.now()
    with pytest.raises(ValidationError) as excinfo:
        factories.AnnouncementFactory(starts_at=now, ends_at=now)

    assert "ends_at" in excinfo.value.message_dict


def test_models_announcements_str():
    """An announcement is represented by its body."""
    assert str(factories.AnnouncementFactory(body="Maintenance")) == "Maintenance"
