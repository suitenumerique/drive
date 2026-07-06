"""Role-based permissions backend."""

from django.conf import settings
from django.db.models import Q

from lasuite.drf.models.choices import LinkReachChoices, RoleChoices

from core import models
from core.permissions.backends.base import PermissionsBackend
from wopi.conversion.policy import target_extension_for


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

    def abilities(self, user, item):  # pylint: disable=too-many-locals
        """Compute and return abilities for a given user on the item."""
        # First get the role based on specific access
        role = item.get_role(user)
        # Characteristics that are based only on specific access
        is_owner = role == RoleChoices.OWNER
        is_deleted = item.ancestors_deleted_at
        is_owner_or_admin = is_owner or role == RoleChoices.ADMIN

        # Compute access roles before adding link roles because we don't
        # want anonymous users to access versions (we wouldn't know from
        # which date to allow them anyway)
        # Anonymous users should also not see item accesses
        has_access_role = bool(role) and not is_deleted
        link_select_options = (
            LinkReachChoices.get_select_options(**item.ancestors_link_definition)
            if has_access_role
            else {}
        )

        link_definition = item.computed_link_definition

        link_reach = link_definition["link_reach"]
        if link_reach == LinkReachChoices.PUBLIC or (
            link_reach == LinkReachChoices.AUTHENTICATED and user.is_authenticated
        ):
            # Set the user role to the highest role between the item role and the link role
            # Needed for a user with an access lower than link_role
            # Needed for a user without access to determine the role he has.
            role = RoleChoices.max(role, link_definition["link_role"])
        can_get = bool(role) and not is_deleted
        retrieve = can_get or is_owner
        can_manage = is_owner_or_admin and not is_deleted
        can_update = (is_owner_or_admin or role == RoleChoices.EDITOR) and not is_deleted
        can_create_children = can_update and user.is_authenticated
        can_hard_delete = (
            is_owner
            if item.is_root
            else (
                is_owner_or_admin
                or (
                    user.is_authenticated
                    and item.creator_id == user.pk
                    and role == RoleChoices.EDITOR
                )
            )
        )
        can_destroy = can_hard_delete and not is_deleted
        can_duplicate = (
            can_get
            and user.is_authenticated
            and item.type == models.ItemTypeChoices.FILE
            and item.upload_state == models.ItemUploadStateChoices.READY
        )
        can_export = can_get and item.type == models.ItemTypeChoices.FOLDER
        can_convert = (
            can_update
            and item.type == models.ItemTypeChoices.FILE
            and item.upload_state
            in (
                models.ItemUploadStateChoices.READY,
                models.ItemUploadStateChoices.ANALYZING,
            )
            and bool(target_extension_for(item.extension))
            and bool(settings.WOPI_ONLYOFFICE_CONVERT_JWT_SECRET)
        )

        return {
            "accesses_manage": can_manage,
            "accesses_view": has_access_role,
            "breadcrumb": can_get,
            "children_list": can_get,
            "children_create": can_create_children,
            "destroy": can_destroy,
            "download": can_get,
            "duplicate": can_duplicate,
            "export": can_export,
            "hard_delete": can_hard_delete,
            "favorite": can_get and user.is_authenticated,
            "link_configuration": can_manage,
            "invite_owner": is_owner and not is_deleted,
            "link_select_options": link_select_options,
            "move": can_manage,
            "restore": is_owner,
            "retrieve": retrieve,
            "tree": can_get,
            "media_auth": can_get,
            "partial_update": can_update,
            "update": can_update,
            "upload_ended": can_update and user.is_authenticated,
            "wopi": can_get,
            "convert": can_convert,
        }
