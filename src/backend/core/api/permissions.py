"""Permission handlers for the drive core app."""

from django.core import exceptions
from django.http import Http404

from lasuite.drf.models.choices import PRIVILEGED_ROLES
from rest_framework import permissions

from core.models import RoleChoices, get_trashbin_cutoff

ACTION_FOR_METHOD_TO_PERMISSION = {
    "versions_detail": {"DELETE": "versions_destroy", "GET": "versions_retrieve"},
    "children": {"GET": "children_list", "POST": "children_create"},
}


class IsAuthenticated(permissions.BasePermission):
    """
    Allows access only to authenticated users. Alternative method checking the presence
    of the auth token to avoid hitting the database.
    """

    def has_permission(self, request, view):
        return bool(request.auth) or request.user.is_authenticated


class IsAuthenticatedOrSafe(IsAuthenticated):
    """Allows access to authenticated users (or anonymous users but only on safe methods)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return super().has_permission(request, view)


class IsSelf(IsAuthenticated):
    """
    Allows access only to authenticated users. Alternative method checking the presence
    of the auth token to avoid hitting the database.
    """

    def has_object_permission(self, request, view, obj):
        """Write permissions are only allowed to the user itself."""
        return obj == request.user


class IsOwnedOrPublic(IsAuthenticated):
    """
    Allows access to authenticated users only for objects that are owned or not related
    to any user via the "owner" field.
    """

    def has_object_permission(self, request, view, obj):
        """Unsafe permissions are only allowed for the owner of the object."""
        if obj.owner == request.user:
            return True

        if request.method in permissions.SAFE_METHODS and obj.owner is None:
            return True

        try:
            return obj.user == request.user
        except exceptions.ObjectDoesNotExist:
            return False


class CreateWithPriviliegedRolesMixin:
    """
    Implement a common has_permission method checking that
    the user has privileged role on the item in order to
    perform the create action.
    This mixin must be used with the IsAuthenticated permission class
    """

    resources = None

    def has_permission(self, request, view):
        """Check the current user has privileged roles on the related item."""
        if super().has_permission(request, view) is False:
            return False

        if view.action == "create":
            role = getattr(view, view.resource_field_name).get_role(request.user)
            if role not in PRIVILEGED_ROLES:
                raise exceptions.PermissionDenied(
                    f"You are not allowed to manage {self.resources} for this resource."
                )

        return True


class InvitationPermission(CreateWithPriviliegedRolesMixin, IsAuthenticated):
    """A permission class for the InvitationViewset."""

    resources = "invitations"

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)
        return abilities.get(view.action, False)


class ItemAccessPermission(CreateWithPriviliegedRolesMixin, IsAuthenticated):
    """Permission class for the ItemAccessViewSet."""

    resources = "accesses"

    def has_object_permission(self, request, view, obj):
        """Check permission for a given object."""
        abilities = obj.get_abilities(request.user)

        requested_role = request.data.get("role")
        if requested_role and requested_role not in abilities.get("set_role_to", []):
            return False

        return abilities.get(view.action, False)


class ItemPermission(permissions.BasePermission):
    """Subclass to handle soft deletion specificities."""

    def has_permission(self, request, view):
        return request.user.is_authenticated or view.action not in [
            "create",
            "trashbin",
            "search",
        ]

    def has_object_permission(self, request, view, obj):
        """
        Return a 404 on deleted items
        - for which the trashbin cutoff is past
        - for which the current user is not owner of the item or one of its ancestors
        """
        if (
            deleted_at := obj.ancestors_deleted_at
        ) and deleted_at < get_trashbin_cutoff():
            raise Http404

        abilities = obj.get_abilities(request.user)
        action = view.action
        try:
            action = ACTION_FOR_METHOD_TO_PERMISSION[view.action][request.method]
        except KeyError:
            pass

        has_permission = abilities.get(action, False)

        if obj.ancestors_deleted_at and not RoleChoices.OWNER in obj.user_roles:
            raise Http404

        return has_permission
