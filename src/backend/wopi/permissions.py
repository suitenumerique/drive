"""Permissions related to WOPI API."""

from rest_framework.permissions import BasePermission


class AccessTokenPermission(BasePermission):
    """
    Check if the user has access to the item by checking its abilities
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission to access the item.
        request.auth should contains AccessUserItem object.
        """
        if request.auth is None:
            return False

        item = request.auth.item

        if item.id != view.get_file_id():
            return False

        abilities = item.get_abilities(request.user)

        return abilities["retrieve"]


class MountAccessTokenPermission(BasePermission):
    """
    Check if the user has access to the mount-backed WOPI resource.

    request.auth should contain an AccessUserMountEntry object.
    """

    def has_permission(self, request, view):
        if request.auth is None:
            return False

        if getattr(request.auth, "file_id", None) != view.get_file_id():
            return False

        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated)
