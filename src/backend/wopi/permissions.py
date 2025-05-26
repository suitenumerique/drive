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
