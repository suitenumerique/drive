"""Service for sharing items with registered users and inviting contacts."""

from django.db import models as db

from core import models


def synchronize_descendants_accesses(item, access):
    """
    Syncronize the accesses of the descendants of the item
    by removing accesses with roles lower than the current user's role.
    """
    descendants = item.descendants().filter(ancestors_deleted_at__isnull=True)

    condition_filter = db.Q()
    if access.user:
        condition_filter |= db.Q(user=access.user)
    if access.team:
        condition_filter |= db.Q(team=access.team)

    role_priority = models.RoleChoices.get_priority(access.role)

    lower_roles = [
        role
        for role in models.RoleChoices.values
        if models.RoleChoices.get_priority(role) <= role_priority
    ]

    models.ItemAccess.objects.filter(
        condition_filter, item__in=descendants, role__in=lower_roles
    ).delete()
