"""Role-based permissions backend."""

from django.db.models import Q

from core import models
from core.permissions.backends.base import PermissionsBackend


class RolePermissionsBackend(PermissionsBackend):
    """Role-based engine inheriting roles along the item tree."""

    def effective_accesses(self, item):
        """Return the accesses applying to the item, direct or inherited."""
        return models.ItemAccess.objects.filter(
            item__path__ancestors=item.path,
        )

    def roles_at(self, user, path):
        """Return the roles the user holds at the given path, direct or inherited."""
        return models.ItemAccess.objects.filter(
            Q(user=user) | Q(team__in=user.teams),
            item__path__ancestors=path,
        ).values_list("role", flat=True)
