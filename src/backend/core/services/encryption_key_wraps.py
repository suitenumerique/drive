"""Service for the per-user wraps of encrypted items' keys."""

from django.db import models as db

from core import models


class WouldStrandPendingUsersError(Exception):
    """Removing wraps would leave members of an encrypted root with nobody holding its key."""


def chain_key_wraps(item):
    """Return the wraps on `item` and its ancestors: the entry points into its key chain."""
    return models.ItemEncryptionKeyWrap.objects.filter(item__path__ancestors=item.path)


def prune_unreachable_key_wraps(item):
    """
    Delete the wraps on `item` and its descendants whose user no longer holds a role
    reaching their item, once an access was removed or the item moved.

    Raise WouldStrandPendingUsersError, deleting nothing, when an encryption root
    would keep members but lose its last wrap: nobody could then wrap its key for
    them. The caller runs inside a transaction to roll back what led here.
    """
    if not models.Item.objects.filter(path__descendants=item.path, is_encrypted=True).exists():
        return

    unreachable = models.ItemEncryptionKeyWrap.objects.filter(
        item__path__descendants=item.path
    ).exclude(
        db.Exists(
            models.ItemAccess.objects.filter(
                user=db.OuterRef("user"),
                item__path__ancestors=db.OuterRef("item__path"),
            )
        )
    )
    unreachable_ids = set(unreachable.values_list("pk", flat=True))
    if not unreachable_ids:
        return

    roots = models.Item.objects.filter(
        encryption_key_wraps__in=unreachable_ids,
        is_encrypted=True,
        encrypted_symmetric_key__isnull=True,
    ).distinct()
    for root in roots:
        keeps_a_wrap = (
            models.ItemEncryptionKeyWrap.objects.filter(item=root)
            .exclude(pk__in=unreachable_ids)
            .exists()
        )
        keeps_members = models.ItemAccess.objects.filter(
            item__path__ancestors=root.path, user__isnull=False
        ).exists()
        if keeps_members and not keeps_a_wrap:
            raise WouldStrandPendingUsersError()

    models.ItemEncryptionKeyWrap.objects.filter(pk__in=unreachable_ids).delete()
