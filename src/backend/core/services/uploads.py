"""Create upload reservations and apply the existing entitlement decision."""

from contextlib import contextmanager

from django.db import transaction

from rest_framework.exceptions import PermissionDenied


@contextmanager
def reserve_upload(user, backend):
    """Roll back item creation if the existing can_upload decision refuses it."""
    with transaction.atomic():
        yield
        permission = backend.can_upload(user)
        if not permission["result"]:
            raise PermissionDenied(
                detail=permission.get("message", "You do not have permission to upload files."),
                code=permission.get("reason"),
            )
