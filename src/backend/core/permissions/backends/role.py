"""Role-based permissions backend."""

from __future__ import annotations

from functools import cached_property

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q, QuerySet

from lasuite.drf.models.choices import LinkReachChoices, RoleChoices

from core import models
from core.permissions.backends.base import PermissionsBackend
from wopi.conversion.policy import target_extension_for


class ItemAbilities:  # pylint: disable=too-many-public-methods
    """Compute the abilities of a user on an item, one property per ability."""

    def __init__(self, user: models.User | AnonymousUser, item: models.Item) -> None:
        self.user = user
        self.item = item

    @cached_property
    def access_role(self) -> str | None:
        """Return the role held through accesses only, before any link boost."""
        return self.item.get_role(self.user)

    @cached_property
    def role(self) -> str | None:
        """Return the effective role, link definition included."""
        link_definition = self.item.computed_link_definition
        link_reach = link_definition["link_reach"]
        if link_reach == LinkReachChoices.PUBLIC or (
            link_reach == LinkReachChoices.AUTHENTICATED and self.user.is_authenticated
        ):
            # The highest of the access role and the link role, needed for a user
            # with an access lower than the link role and for a user without access
            return RoleChoices.max(self.access_role, link_definition["link_role"])
        return self.access_role

    @cached_property
    def is_deleted(self) -> bool:
        """Return whether the item or one of its ancestors is soft deleted."""
        return bool(self.item.ancestors_deleted_at)

    @cached_property
    def is_owner(self) -> bool:
        """Return whether the user holds an owner role through accesses."""
        return self.access_role == RoleChoices.OWNER

    @cached_property
    def is_owner_or_admin(self) -> bool:
        """Return whether the user holds an owner or administrator role through accesses."""
        return self.is_owner or self.access_role == RoleChoices.ADMIN

    @cached_property
    def has_access_role(self) -> bool:
        """Return whether the user holds a role through accesses on a live item."""
        # Based on accesses only so that anonymous users granted by a link
        # cannot see item accesses or versions
        return bool(self.access_role) and not self.is_deleted

    @cached_property
    def link_select_options(self) -> dict[str, list[str]]:
        """Return the link reach and role options selectable on the item."""
        if not self.has_access_role:
            return {}
        return LinkReachChoices.get_select_options(**self.item.ancestors_link_definition)

    @property
    def can_get(self) -> bool:
        """Return whether the user can read the item."""
        return bool(self.role) and not self.is_deleted

    @property
    def can_retrieve(self) -> bool:
        """Return whether the user can retrieve the item, even soft deleted."""
        return self.can_get or self.is_owner

    @property
    def can_manage(self) -> bool:
        """Return whether the user can manage the item and its accesses."""
        return self.is_owner_or_admin and not self.is_deleted

    @property
    def can_update(self) -> bool:
        """Return whether the user can modify the item."""
        return (self.is_owner_or_admin or self.role == RoleChoices.EDITOR) and not self.is_deleted

    @property
    def can_create_children(self) -> bool:
        """Return whether the user can create children in the item."""
        return self.can_update and self.user.is_authenticated

    @cached_property
    def can_hard_delete(self) -> bool:
        """Return whether the user can delete the item permanently."""
        if self.item.is_root:
            return self.is_owner
        creator_can_delete = self.user.is_authenticated and self.item.creator_id == self.user.id
        return self.is_owner_or_admin or creator_can_delete

    @property
    def can_destroy(self) -> bool:
        """Return whether the user can remove the item."""
        return self.can_hard_delete and not self.is_deleted

    @property
    def can_duplicate(self) -> bool:
        """Return whether the user can duplicate the file."""
        return (
            self.can_get
            and self.user.is_authenticated
            and self.item.type == models.ItemTypeChoices.FILE
            and self.item.upload_state == models.ItemUploadStateChoices.READY
        )

    @property
    def can_export(self) -> bool:
        """Return whether the user can export the folder as an archive."""
        return self.can_get and self.item.type == models.ItemTypeChoices.FOLDER

    @property
    def can_convert(self) -> bool:
        """Return whether the user can convert the file to another format."""
        return (
            self.can_update
            and self.item.type == models.ItemTypeChoices.FILE
            and self.item.upload_state
            in (
                models.ItemUploadStateChoices.READY,
                models.ItemUploadStateChoices.ANALYZING,
            )
            and bool(target_extension_for(self.item.extension))
            and bool(settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET)
        )

    @property
    def can_restrict(self) -> bool:
        """Return whether the user can toggle restriction on the folder."""
        # A restricted folder lives at the tree root: deactivation must stay
        # possible there, while activation requires a parent for the shortcut
        return (
            self.is_owner
            and not self.is_deleted
            and self.item.type == models.ItemTypeChoices.FOLDER
            and (self.item.is_restricted or self.item.depth > 1)
        )

    @property
    def can_favorite(self) -> bool:
        """Return whether the user can mark the item as favorite."""
        return self.can_get and self.user.is_authenticated

    @property
    def can_invite_owner(self) -> bool:
        """Return whether the user can invite another owner on the item."""
        return self.is_owner and not self.is_deleted

    @property
    def can_restore(self) -> bool:
        """Return whether the user can restore the item from the trash."""
        return self.is_owner

    @property
    def can_upload_ended(self) -> bool:
        """Return whether the user can mark an upload on the item as ended."""
        return self.can_update and self.user.is_authenticated

    def as_dict(self) -> dict[str, bool | dict[str, list[str]]]:
        """Return the ability mapping exposed by the API."""
        return {
            "accesses_manage": self.can_manage,
            "accesses_view": self.has_access_role,
            "breadcrumb": self.can_get,
            "children_list": self.can_get,
            "children_create": self.can_create_children,
            "destroy": self.can_destroy,
            "download": self.can_get,
            "duplicate": self.can_duplicate,
            "export": self.can_export,
            "hard_delete": self.can_hard_delete,
            "favorite": self.can_favorite,
            "link_configuration": self.can_manage,
            "invite_owner": self.can_invite_owner,
            "link_select_options": self.link_select_options,
            "move": self.can_manage,
            "restrict": self.can_restrict,
            "restore": self.can_restore,
            "retrieve": self.can_retrieve,
            "tree": self.can_get,
            "media_auth": self.can_get,
            "partial_update": self.can_update,
            "update": self.can_update,
            "upload_ended": self.can_upload_ended,
            "wopi": self.can_get,
            "convert": self.can_convert,
        }


class RolePermissionsBackend(PermissionsBackend):
    """Role-based engine inheriting roles along the item tree."""

    def effective_accesses(self, item: models.Item) -> QuerySet[models.ItemAccess]:
        """Return the accesses applying to the item, direct or inherited."""
        return models.ItemAccess.objects.filter(
            item__path__ancestors=item.path,
        )

    def roles_at(self, user: models.User | AnonymousUser, path: str) -> QuerySet[str]:
        """Return the roles the user holds at the given path, direct or inherited."""
        return models.ItemAccess.objects.filter(
            Q(user=user) | Q(team__in=user.teams),
            item__path__ancestors=path,
        ).values_list("role", flat=True)

    def roles_for(self, user: models.User | AnonymousUser, item: models.Item) -> QuerySet[str]:
        """Return the roles the user holds on the item, direct or inherited."""
        return self.roles_at(user, item.path)

    def abilities(
        self, user: models.User | AnonymousUser, item: models.Item
    ) -> dict[str, bool | dict[str, list[str]]]:
        """Compute and return abilities for a given user on the item."""
        return ItemAbilities(user, item).as_dict()
