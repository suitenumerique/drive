"""Permissions Backend base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet

from lasuite.drf.models.choices import RoleChoices

if TYPE_CHECKING:
    from core import models


class PermissionsBackend(ABC):
    """Abstract base class for item permissions backends."""

    @abstractmethod
    def effective_accesses(self, item: models.Item) -> QuerySet[models.ItemAccess]:
        """Return the accesses applying to the item, direct or inherited."""

    @abstractmethod
    def roles_at(self, user: models.User | AnonymousUser, path: str) -> QuerySet[str]:
        """Return the roles the user holds at the given path, direct or inherited."""

    def roles_for(self, user: models.User | AnonymousUser, item: models.Item) -> QuerySet[str]:
        """Return the roles the user holds on the item, direct or inherited."""
        return self.roles_at(user, item.path)

    def role_at(self, user: models.User | AnonymousUser, path: str) -> str | None:
        """Return the highest role the user holds at the given path."""
        return RoleChoices.max(*self.roles_at(user, path))
