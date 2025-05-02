"""Client serializers for the drive core app."""

from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from core import models
from core.api import utils


class UserSerializer(serializers.ModelSerializer):
    """Serialize users."""

    class Meta:
        model = models.User
        fields = ["id", "email", "full_name", "short_name"]
        read_only_fields = ["id", "email", "full_name", "short_name"]


class UserLiteSerializer(UserSerializer):
    """Serialize users with limited fields."""

    class Meta:
        model = models.User
        fields = ["full_name", "short_name"]
        read_only_fields = ["full_name", "short_name"]


class BaseAccessSerializer(serializers.ModelSerializer):
    """Serialize template accesses."""

    abilities = serializers.SerializerMethodField(read_only=True)

    def update(self, instance, validated_data):
        """Make "user" field is readonly but only on update."""
        validated_data.pop("user", None)
        return super().update(instance, validated_data)

    def get_abilities(self, access) -> dict:
        """Return abilities of the logged-in user on the instance."""
        request = self.context.get("request")
        if request:
            return access.get_abilities(request.user)
        return {}

    def validate(self, attrs):
        """
        Check access rights specific to writing (create/update)
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role = attrs.get("role")

        # Update
        if self.instance:
            can_set_role_to = self.instance.get_abilities(user)["set_role_to"]

            if role and role not in can_set_role_to:
                message = (
                    f"You are only allowed to set role to {', '.join(can_set_role_to)}"
                    if can_set_role_to
                    else "You are not allowed to set this role for this template."
                )
                raise exceptions.PermissionDenied(message)

        # Create
        else:
            try:
                resource_id = self.context["resource_id"]
            except KeyError as exc:
                raise exceptions.ValidationError(
                    "You must set a resource ID in kwargs to create a new access."
                ) from exc

            if not self.Meta.model.objects.filter(  # pylint: disable=no-member
                Q(user=user) | Q(team__in=user.teams),
                role__in=[models.RoleChoices.OWNER, models.RoleChoices.ADMIN],
                **{self.Meta.resource_field_name: resource_id},  # pylint: disable=no-member
            ).exists():
                raise exceptions.PermissionDenied(
                    "You are not allowed to manage accesses for this resource."
                )

            if (
                role == models.RoleChoices.OWNER
                and not self.Meta.model.objects.filter(  # pylint: disable=no-member
                    Q(user=user) | Q(team__in=user.teams),
                    role=models.RoleChoices.OWNER,
                    **{self.Meta.resource_field_name: resource_id},  # pylint: disable=no-member
                ).exists()
            ):
                raise exceptions.PermissionDenied(
                    "Only owners of a resource can assign other users as owners."
                )

        # pylint: disable=no-member
        attrs[f"{self.Meta.resource_field_name}_id"] = self.context["resource_id"]
        return attrs


class ItemAccessSerializer(BaseAccessSerializer):
    """Serialize item accesses."""

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(),
        write_only=True,
        source="user",
        required=False,
        allow_null=True,
    )
    user = UserSerializer(read_only=True)

    class Meta:
        model = models.ItemAccess
        resource_field_name = "item"
        fields = ["id", "user", "user_id", "team", "role", "abilities"]
        read_only_fields = ["id", "abilities"]


class ListItemSerializer(serializers.ModelSerializer):
    """Serialize items with limited fields for display in lists."""

    abilities = serializers.SerializerMethodField(read_only=True)
    is_favorite = serializers.BooleanField(read_only=True)
    nb_accesses = serializers.IntegerField(read_only=True)
    user_roles = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    creator = UserLiteSerializer(read_only=True)

    class Meta:
        model = models.Item
        fields = [
            "id",
            "abilities",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "link_role",
            "link_reach",
            "nb_accesses",
            "numchild",
            "numchild_folder",
            "path",
            "title",
            "updated_at",
            "user_roles",
            "type",
            "upload_state",
            "url",
            "filename",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "abilities",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "link_role",
            "link_reach",
            "nb_accesses",
            "numchild",
            "numchild_folder",
            "path",
            "updated_at",
            "user_roles",
            "type",
            "upload_state",
            "url",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
        ]

    def get_abilities(self, item) -> dict:
        """Return abilities of the logged-in user on the instance."""
        request = self.context.get("request")
        if request:
            paths_links_mapping = self.context.get("paths_links_mapping", None)
            # Retrieve ancestor links from paths_links_mapping (if provided)
            ancestors_links = (
                paths_links_mapping.get(str(item.path[:-1]))
                if paths_links_mapping
                else None
            )
            return item.get_abilities(request.user, ancestors_links=ancestors_links)
        return {}

    def get_user_roles(self, item):
        """
        Return roles of the logged-in user for the current item,
        taking into account ancestors.
        """
        request = self.context.get("request")
        if request:
            return item.get_roles(request.user)
        return []

    def get_url(self, item):
        """Return the URL of the item."""
        if (
            item.type != models.ItemTypeChoices.FILE
            or item.upload_state != models.ItemUploadStateChoices.UPLOADED
            or item.filename is None
        ):
            return None

        return f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL}{item.file_key}"


class ItemSerializer(ListItemSerializer):
    """Serialize items with all fields for display in detail views."""

    class Meta:
        model = models.Item
        fields = [
            "id",
            "abilities",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "link_role",
            "link_reach",
            "nb_accesses",
            "numchild",
            "numchild_folder",
            "path",
            "title",
            "updated_at",
            "user_roles",
            "type",
            "upload_state",
            "url",
            "filename",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "abilities",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "link_role",
            "link_reach",
            "nb_accesses",
            "numchild",
            "numchild_folder",
            "path",
            "updated_at",
            "user_roles",
            "type",
            "upload_state",
            "url",
            "mimetype",
            "main_workspace",
            "size",
            "deleted_at",
        ]

    def create(self, validated_data):
        raise NotImplementedError("Create method can not be used.")

    def update(self, instance, validated_data):
        """Validate that the title is unique in the current path."""
        if (
            instance.title != validated_data.get("title")
            and instance.depth > 1
            and instance.is_item_title_existing(validated_data.get("title"))
        ):
            raise serializers.ValidationError(
                {
                    "title": _(
                        "An item with this title already exists in the current path."
                    )
                }
            )

        return super().update(instance, validated_data)


class CreateItemSerializer(ItemSerializer):
    """Serializer used to create a new item"""

    policy = serializers.SerializerMethodField()
    title = serializers.CharField(max_length=255, required=False)
    numchild_folder = serializers.SerializerMethodField()
    numchild = serializers.SerializerMethodField()

    class Meta:
        model = models.Item
        fields = [
            "id",
            "abilities",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "link_role",
            "link_reach",
            "nb_accesses",
            "numchild",
            "numchild_folder",
            "path",
            "title",
            "updated_at",
            "user_roles",
            "type",
            "upload_state",
            "url",
            "filename",
            "policy",
            "main_workspace",
            "size",
            "description",
        ]
        read_only_fields = [
            "abilities",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "link_role",
            "link_reach",
            "nb_accesses",
            "numchild",
            "numchild_folder",
            "path",
            "updated_at",
            "user_roles",
            "upload_state",
            "url",
            "policy",
            "main_workspace",
            "size",
        ]

    def get_fields(self):
        """Force the id field to be writable."""
        fields = super().get_fields()
        fields["id"].read_only = False

        return fields

    def validate_id(self, value):
        """Ensure the provided ID does not already exist when creating a new item."""
        request = self.context.get("request")

        # Only check this on POST (creation)
        if request:
            if models.Item.objects.filter(id=value).exists():
                raise serializers.ValidationError(
                    "An item with this ID already exists. You cannot override it."
                )

        return value

    def validate(self, attrs):
        """Validate that filename is set for files."""
        if attrs["type"] == models.ItemTypeChoices.FILE:
            if attrs.get("filename") is None:
                raise serializers.ValidationError(
                    {"filename": _("This field is required for files.")}
                )

            # When it's a file we force the title with the filename
            attrs["title"] = attrs["filename"]

        if (
            attrs["type"] == models.ItemTypeChoices.FOLDER
            and attrs.get("title") is None
        ):
            raise serializers.ValidationError(
                {"title": _("This field is required for folders.")}
            )

        return super().validate(attrs)

    def get_policy(self, item):
        """Return the policy to use if the item is a file."""
        if item.type != models.ItemTypeChoices.FILE:
            return None

        return utils.generate_upload_policy(item)

    def get_numchild(self, _item):
        """On creation, an item can not have children, return directly 0"""
        return 0

    def get_numchild_folder(self, _item):
        """On creation, an item can not have folders' children, return directly 0"""
        return 0

    def update(self, instance, validated_data):
        raise NotImplementedError("Update method can not be used.")


class LinkItemSerializer(serializers.ModelSerializer):
    """
    Serialize link configuration for items.
    We expose it separately from item in order to simplify and secure access control.
    """

    class Meta:
        model = models.Item
        fields = [
            "link_role",
            "link_reach",
        ]


class InvitationSerializer(serializers.ModelSerializer):
    """Serialize invitations."""

    abilities = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Invitation
        fields = [
            "id",
            "abilities",
            "created_at",
            "email",
            "item",
            "role",
            "issuer",
            "is_expired",
        ]
        read_only_fields = [
            "id",
            "abilities",
            "created_at",
            "item",
            "issuer",
            "is_expired",
        ]

    def get_abilities(self, invitation) -> dict:
        """Return abilities of the logged-in user on the instance."""
        request = self.context.get("request")
        if request:
            return invitation.get_abilities(request.user)
        return {}

    def validate(self, attrs):
        """Validate invitation data."""
        request = self.context.get("request")
        user = getattr(request, "user", None)

        attrs["item_id"] = self.context["resource_id"]

        # Only set the issuer if the instance is being created
        if self.instance is None:
            attrs["issuer"] = user

        return attrs

    def validate_role(self, role):
        """Custom validation for the role field."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        item_id = self.context["resource_id"]

        # If the role is OWNER, check if the user has OWNER access
        if role == models.RoleChoices.OWNER:
            if not models.ItemAccess.objects.filter(
                Q(user=user) | Q(team__in=user.teams),
                item=item_id,
                role=models.RoleChoices.OWNER,
            ).exists():
                raise serializers.ValidationError(
                    "Only owners of a item can invite other users as owners."
                )

        return role


# Suppress the warning about not implementing `create` and `update` methods
# since we don't use a model and only rely on the serializer for validation
# pylint: disable=abstract-method
class MoveItemSerializer(serializers.Serializer):
    """
    Serializer for validating input data to move an item within the tree structure.

    Fields:
        - target_item_id (UUIDField): The ID of the target parent item where the
            item should be moved. This field is required and must be a valid UUID.

    Example:
        Input payload for moving a item:
        {
            "target_item_id": "123e4567-e89b-12d3-a456-426614174000",
        }

    Notes:
        - The `target_item_id` is mandatory.
    """

    target_item_id = serializers.UUIDField(required=True)
