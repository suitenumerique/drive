"""Deterministic folders and permissions for restriction browser tests."""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core import factories, models

from e2e.utils import get_or_create_e2e_user


def folder(title, parent=None, creator=None, **kwargs):
    """Create a folder owned by its parent creator unless explicitly overridden."""
    return factories.ItemFactory(
        title=title,
        type=models.ItemTypeChoices.FOLDER,
        parent=parent,
        creator=creator or parent.creator,
        **kwargs,
    )


def grant(item, user, role):
    """Assign a direct role for a fixture user."""
    factories.UserItemAccessFactory(item=item, user=user, role=role)


def file(title, parent):
    """Store a ready-to-preview text file in the fixture folder."""
    return factories.ItemFactory(
        title=title,
        parent=parent,
        creator=parent.creator,
        type=models.ItemTypeChoices.FILE,
        filename=f"{title}.txt",
        upload_bytes=b"Restriction integration fixture\n",
        upload_bytes__filename=f"{title}.txt",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )


class Command(BaseCommand):
    """Seed the isolated browser-test database, never the development database."""

    help = "Generate folder restriction E2E fixtures (drive_e2e only)."

    @transaction.atomic
    def handle(self, *args, **options):
        if connection.settings_dict["NAME"] != "drive_e2e":
            raise CommandError("Restriction fixtures require the drive_e2e database.")

        owner, reader, editor, admin, other, _link = [
            get_or_create_e2e_user(email)
            for email in (
                "drive@example.com",
                "inherited@example.com",
                "direct@example.com",
                "administrator@example.com",
                "other-owner@example.com",
                "link-only@example.com",
            )
        ]
        for user, name in (
            (owner, "Owner"),
            (reader, "Inherited Reader"),
            (editor, "Direct Editor"),
            (admin, "Administrator"),
        ):
            user.full_name = name
            user.save(update_fields=["full_name"])

        parent = folder("Restrictions parent", creator=owner)
        grant(parent, owner, models.RoleChoices.OWNER)
        grant(parent, reader, models.RoleChoices.READER)
        grant(parent, editor, models.RoleChoices.READER)
        grant(parent, admin, models.RoleChoices.ADMIN)
        child = folder("Restrictable folder", parent)
        grant(child, editor, models.RoleChoices.EDITOR)
        file("Child document", child)
        folder("Normal folder", parent)
        file("Ordinary document", parent)
        folder("Movable one", parent)
        folder("Movable two", parent)

        for title, access in (
            ("Accessible restricted", models.RoleChoices.OWNER),
            ("Confidential.folder.v2", None),
            ("Read-only restricted", models.RoleChoices.READER),
            ("Deleted restricted", None),
            ("Link restricted", None),
        ):
            target_owner = owner if access == models.RoleChoices.OWNER else other
            target = folder(title, parent, creator=target_owner)
            grant(target, target_owner, models.RoleChoices.OWNER)
            if access and target_owner != owner:
                grant(target, owner, access)
            if title == "Link restricted":
                target.link_reach = models.LinkReachChoices.AUTHENTICATED
                target.save(update_fields=["link_reach"])
            descendant = folder(
                "Cycle descendant" if title == "Accessible restricted" else f"{title} descendant",
                target,
                creator=target_owner,
            )
            target = target.restrict(target_owner)
            entry = models.Item.objects.get(target=target)
            if title == "Accessible restricted":
                # Restriction entries are leaves; star the descendant separately
                # so a real pointer gesture can exercise cycle prevention.
                models.ItemFavorite.objects.create(item=descendant, user=owner)
            if title == "Deleted restricted":
                target.soft_delete()
                # Retain a stale entry to exercise unavailable-target handling.
                models.Item.objects.filter(pk=entry.pk).update(
                    deleted_at=None, ancestors_deleted_at=None
                )
            models.ItemFavorite.objects.create(item=entry, user=owner)

        for item in (parent, child):
            models.ItemFavorite.objects.create(item=item, user=owner)
        self.stdout.write("Restriction fixtures created in drive_e2e")
