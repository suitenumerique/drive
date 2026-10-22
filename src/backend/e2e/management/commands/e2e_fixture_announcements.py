"""Publish the announcements used by the e2e tests."""

from django.core.management.base import BaseCommand

from core import models


class Command(BaseCommand):
    """
    Replace the announcements by a header banner translated in English and
    French. Scenarios: `header_banner` (default), `not_dismissible`, or `none`
    to remove them all.

    Announcements are deleted through the ORM, not truncated, so that the cache
    of the announcements is cleared as well.
    """

    def add_arguments(self, parser):
        parser.add_argument("scenario", nargs="?", default="header_banner")

    def handle(self, *args, **options):
        for announcement in models.Announcement.objects.all():
            announcement.delete()

        if options["scenario"] == "none":
            self.stdout.write("No announcement.")
            return

        announcement = models.Announcement(
            display=models.AnnouncementDisplayChoices.HEADER_BANNER,
            level=models.AnnouncementLevelChoices.WARNING,
            cta_url="https://status.example.com/",
            is_active=True,
            is_dismissible=options["scenario"] != "not_dismissible",
        )
        announcement.set_current_language("en-us")
        announcement.body = "An update is scheduled today at 1 p.m."
        announcement.cta_label = "Read more"
        announcement.save()
        announcement.set_current_language("fr-fr")
        announcement.body = "Une mise à jour est prévue aujourd'hui à 13h."
        announcement.cta_label = "En savoir plus"
        announcement.save()

        self.stdout.write(f"Header banner announcement {announcement.id} published.")
