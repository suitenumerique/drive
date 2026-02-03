"""Client serializers for the drive core app."""

import json
import logging
from datetime import timedelta
from os.path import splitext
from urllib.parse import quote

from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from lasuite.drf.models.choices import LinkReachChoices, get_equivalent_link_definition
from rest_framework import serializers

from core import models
from core.api import utils
from core.storage import get_storage_compute_backend
from wopi import utils as wopi_utils

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """Serialize users."""

    last_release_note_seen = serializers.RegexField(
        r"^[0-9]+\.[0-9]+\.[0-9]+$",
        max_length=85,
        required=False,
        allow_null=True,
        allow_blank=False,
    )

    class Meta:
        model = models.User
        fields = [
            "id",
            "email",
            "full_name",
            "short_name",
            "language",
            "last_release_note_seen",
        ]
        read_only_fields = ["id", "email", "full_name", "short_name"]


class UserLightSerializer(UserSerializer):
    """Serialize users with limited fields."""

    class Meta:
        model = models.User
        fields = ["id", "full_name", "short_name"]
        read_only_fields = ["id", "full_name", "short_name"]


# pylint: disable=abstract-method
class UsageMetricSerializer(serializers.BaseSerializer):
    """Serialize usage metrics."""

    def to_representation(self, instance):
        """Return the usage metric."""
        storage_compute_backend = get_storage_compute_backend()
        output = {
            "account": {
                "type": "user",
                "id": instance.sub,
                "email": instance.email,
            },
            "metrics": {
                "storage_used": storage_compute_backend.compute_storage_used(instance),
            },
        }
        for claim in settings.METRICS_USER_CLAIMS_EXPOSED:
            output[claim] = instance.claims.get(claim)
        return output


class ItemLightSerializer(serializers.ModelSerializer):
    """Minimal item serializer for nesting in item accesses."""

    class Meta:
        model = models.Item
        fields = ["id", "path", "depth"]
        read_only_fields = ["id", "path", "depth"]


class ItemAccessSerializer(serializers.ModelSerializer):
    """Serialize item accesses."""

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=models.User.objects.all(),
        write_only=True,
        source="user",
        required=False,
        allow_null=True,
    )
    user = UserSerializer(read_only=True)
    team = serializers.CharField(required=False, allow_blank=True)
    abilities = serializers.SerializerMethodField(read_only=True)
    max_role = serializers.SerializerMethodField(read_only=True)
    item = ItemLightSerializer(read_only=True)
    is_explicit = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.ItemAccess
        resource_field_name = "item"
        fields = [
            "id",
            "user",
            "user_id",
            "team",
            "role",
            "abilities",
            "max_ancestors_role",
            "max_ancestors_role_item_id",
            "max_role",
            "item",
            "is_explicit",
        ]
        read_only_fields = [
            "id",
            "abilities",
            "max_ancestors_role",
            "max_ancestors_role_item_id",
            "max_role",
            "item",
            "is_explicit",
        ]

    def get_abilities(self, instance):
        """Return abilities of the logged-in user on the instance."""
        request = self.context.get("request")
        if request:
            return instance.get_abilities(
                request.user, is_explicit=self.get_is_explicit(instance)
            )
        return {}

    def get_max_role(self, instance):
        """Return max_ancestors_role if annotated; else None."""
        return models.RoleChoices.max(
            instance.max_ancestors_role,
            instance.role,
        )

    def get_is_explicit(self, instance):
        """Return whether the item access is explicit."""
        item_id = self.context.get("resource_id")
        if not item_id:
            return False

        return str(instance.item_id) == str(item_id)

    def update(self, instance, validated_data):
        """Make "user" field is readonly but only on update."""
        validated_data.pop("user", None)
        validated_data.pop("team", None)
        return super().update(instance, validated_data)


class ItemAccessLightSerializer(ItemAccessSerializer):
    """Serialize item accesses with limited fields."""

    user = UserLightSerializer(read_only=True)

    class Meta:
        model = models.ItemAccess
        resource_field_name = "item"
        fields = [
            "id",
            "item",
            "user",
            "team",
            "role",
            "abilities",
            "max_ancestors_role",
            "max_ancestors_role_item_id",
            "max_role",
            "is_explicit",
        ]
        read_only_fields = [
            "id",
            "item",
            "user",
            "team",
            "role",
            "abilities",
            "max_ancestors_role",
            "max_ancestors_role_item_id",
            "max_role",
            "is_explicit",
        ]


class ListItemSerializer(serializers.ModelSerializer):
    """Serialize items with limited fields for display in lists."""

    abilities = serializers.SerializerMethodField(read_only=True)
    is_favorite = serializers.BooleanField(read_only=True)
    nb_accesses = serializers.IntegerField(read_only=True)
    user_role = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    url_preview = serializers.SerializerMethodField()
    creator = UserLightSerializer(read_only=True)
    hard_delete_at = serializers.SerializerMethodField(read_only=True)
    is_wopi_supported = serializers.SerializerMethodField()

    class Meta:
        model = models.Item
        fields = [
            "id",
            "abilities",
            "ancestors_link_reach",
            "ancestors_link_role",
            "computed_link_reach",
            "computed_link_role",
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
            "user_role",
            "type",
            "upload_state",
            "url",
            "url_preview",
            "filename",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
            "hard_delete_at",
            "is_wopi_supported",
        ]
        read_only_fields = [
            "id",
            "abilities",
            "ancestors_link_reach",
            "ancestors_link_role",
            "computed_link_reach",
            "computed_link_role",
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
            "user_role",
            "type",
            "upload_state",
            "url",
            "url_preview",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
            "hard_delete_at",
            "is_wopi_supported",
        ]

    def to_representation(self, instance):
        """Precompute once per instance"""
        paths_links_mapping = self.context.get("paths_links_mapping")

        if paths_links_mapping is not None:
            links = paths_links_mapping.get(str(instance.path[:-1]), [])
            instance.ancestors_link_definition = get_equivalent_link_definition(links)

        return super().to_representation(instance)

    def get_abilities(self, item) -> dict:
        """Return abilities of the logged-in user on the instance."""
        request = self.context.get("request")
        if not request:
            return {}

        return item.get_abilities(request.user)

    def get_user_role(self, item):
        """
        Return roles of the logged-in user for the current item,
        taking into account ancestors.
        """
        request = self.context.get("request")
        if request:
            return item.get_role(request.user)
        return None

    def get_url(self, item):
        """Return the URL of the item."""
        if (
            item.type != models.ItemTypeChoices.FILE
            or item.upload_state == models.ItemUploadStateChoices.PENDING
            or item.filename is None
        ):
            return None

        return f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL}{quote(item.file_key)}"

    def get_url_preview(self, item):
        """Return the URL of the item."""
        if (
            item.type != models.ItemTypeChoices.FILE
            or item.upload_state == models.ItemUploadStateChoices.PENDING
            or item.filename is None
            or not utils.is_previewable_item(item)
        ):
            return None
        return f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL_PREVIEW}{quote(item.file_key)}"

    def get_hard_delete_at(self, item):
        """Return the hard delete date of the item."""
        if item.deleted_at is None:
            return None

        hard_delete_at = item.deleted_at + timedelta(days=settings.TRASHBIN_CUTOFF_DAYS)
        return hard_delete_at.isoformat()

    def get_is_wopi_supported(self, item):
        """Return whether the item is supported by WOPI protocol."""
        request = self.context.get("request")
        return wopi_utils.is_item_wopi_supported(
            item, request.user if request else None
        )


class ListItemLightSerializer(ListItemSerializer):
    """
    Serialize items with limited fields to avoid N+1 queries on the
    nb_accesses and compute_link_(reach|role) attributes.
    """

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
            "numchild",
            "numchild_folder",
            "path",
            "title",
            "updated_at",
            "user_role",
            "type",
            "upload_state",
            "url",
            "url_preview",
            "filename",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
            "hard_delete_at",
            "is_wopi_supported",
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
            "numchild",
            "numchild_folder",
            "path",
            "updated_at",
            "user_role",
            "type",
            "upload_state",
            "url",
            "url_preview",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
            "hard_delete_at",
            "is_wopi_supported",
        ]


class SearchItemSerializer(ListItemSerializer):
    """Serialize items for search."""

    parents = ListItemSerializer(many=True, read_only=True)

    class Meta:
        model = models.Item
        fields = ListItemSerializer.Meta.fields + ["parents"]
        read_only_fields = ListItemSerializer.Meta.read_only_fields + ["parents"]


class ItemSerializer(ListItemSerializer):
    """Serialize items with all fields for display in detail views."""

    class Meta:
        model = models.Item
        fields = [
            "id",
            "abilities",
            "ancestors_link_reach",
            "ancestors_link_role",
            "computed_link_reach",
            "computed_link_role",
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
            "user_role",
            "type",
            "upload_state",
            "url",
            "url_preview",
            "filename",
            "mimetype",
            "main_workspace",
            "size",
            "description",
            "deleted_at",
            "hard_delete_at",
            "is_wopi_supported",
        ]
        read_only_fields = [
            "id",
            "abilities",
            "ancestors_link_reach",
            "ancestors_link_role",
            "computed_link_reach",
            "computed_link_role",
            "created_at",
            "creator",
            "depth",
            "is_favorite",
            "nb_accesses",
            "link_role",
            "link_reach",
            "numchild",
            "numchild_folder",
            "path",
            "updated_at",
            "user_role",
            "type",
            "upload_state",
            "url",
            "url_preview",
            "filename",
            "mimetype",
            "main_workspace",
            "size",
            "deleted_at",
            "hard_delete_at",
            "is_wopi_supported",
        ]

    def create(self, validated_data):
        raise NotImplementedError("Create method can not be used.")

    def update(self, instance, validated_data):
        """Validate that the title is unique in the current path."""
        if (
            validated_data.get("title")
            and instance.title != validated_data.get("title")
            and instance.depth > 1
        ):
            validated_data["title"] = instance.manage_unique_title(
                validated_data.get("title")
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
            "ancestors_link_reach",
            "ancestors_link_role",
            "computed_link_reach",
            "computed_link_role",
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
            "user_role",
            "type",
            "upload_state",
            "url",
            "filename",
            "policy",
            "main_workspace",
            "size",
            "description",
            "hard_delete_at",
        ]
        read_only_fields = [
            "abilities",
            "ancestors_link_reach",
            "ancestors_link_role",
            "computed_link_reach",
            "computed_link_role",
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
            "user_role",
            "upload_state",
            "url",
            "policy",
            "main_workspace",
            "size",
            "hard_delete_at",
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
                    "An item with this ID already exists. You cannot override it.",
                    code="item_create_existing_id",
                )

        return value

    def validate(self, attrs):
        """Validate that filename is set for files."""
        if attrs["type"] == models.ItemTypeChoices.FILE:
            if attrs.get("filename") is None:
                raise serializers.ValidationError(
                    {"filename": _("This field is required for files.")},
                    code="item_create_file_filename_required",
                )

            if settings.RESTRICT_UPLOAD_FILE_TYPE:
                _root, extension = splitext(attrs["filename"])
                if extension.lower() not in settings.FILE_EXTENSIONS_ALLOWED:
                    logger.info(
                        "create_item: file extension not allowed %s for filename %s",
                        extension,
                        attrs["filename"],
                    )
                    raise serializers.ValidationError(
                        {"filename": _("This file extension is not allowed.")},
                        code="item_create_file_extension_not_allowed",
                    )

            # When it's a file we force the title with the filename
            attrs["title"] = attrs["filename"]

        if (
            attrs["type"] == models.ItemTypeChoices.FOLDER
            and attrs.get("title") is None
        ):
            raise serializers.ValidationError(
                {"title": _("This field is required for folders.")},
                code="item_create_folder_title_required",
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


class BreadcrumbItemSerializer(serializers.ModelSerializer):
    """Serialize breadcrumb items."""

    class Meta:
        model = models.Item
        fields = ["id", "title", "path", "depth", "main_workspace"]
        read_only_fields = ["id", "title", "path", "depth", "main_workspace"]


class UserMeSerializer(UserSerializer):
    """Serialize users for me endpoint."""

    class Meta:
        model = models.User
        fields = UserSerializer.Meta.fields
        read_only_fields = UserSerializer.Meta.read_only_fields


class LinkItemSerializer(serializers.ModelSerializer):
    """
    Serialize link configuration for items.
    We expose it separately from item in order to simplify and secure access control.
    """

    link_reach = serializers.ChoiceField(
        choices=LinkReachChoices.choices, required=True
    )

    class Meta:
        model = models.Item
        fields = [
            "link_role",
            "link_reach",
        ]

    def validate(self, attrs):
        """Validate that link_role and link_reach are compatible using get_select_options."""
        link_reach = attrs.get("link_reach")
        link_role = attrs.get("link_role")

        if not link_reach:
            raise serializers.ValidationError(
                {"link_reach": _("This field is required.")}
            )

        # Get available options based on ancestors' link definition
        available_options = LinkReachChoices.get_select_options(
            **self.instance.ancestors_link_definition
        )

        # Validate link_reach is allowed
        if link_reach not in available_options:
            msg = _(
                "Link reach '%(link_reach)s' is not allowed based on parent item configuration."
            )
            raise serializers.ValidationError(
                {"link_reach": msg % {"link_reach": link_reach}}
            )

        # Validate link_role is compatible with link_reach
        allowed_roles = available_options[link_reach]

        # Restricted reach: link_role must be None
        if link_reach == LinkReachChoices.RESTRICTED:
            if link_role is not None:
                raise serializers.ValidationError(
                    {
                        "link_role": (
                            "Cannot set link_role when link_reach is 'restricted'. "
                            "Link role must be null for restricted reach."
                        )
                    }
                )
        # Non-restricted: link_role must be in allowed roles
        elif link_role not in allowed_roles:
            allowed_roles_str = ", ".join(allowed_roles) if allowed_roles else "none"
            raise serializers.ValidationError(
                {
                    "link_role": (
                        f"Link role '{link_role}' is not allowed for link reach '{link_reach}'. "
                        f"Allowed roles: {allowed_roles_str}"
                    )
                }
            )

        return attrs


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

        if attrs.get("email"):
            attrs["email"] = attrs["email"].lower()

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
                    "Only owners of a item can invite other users as owners.",
                    code="invitation_role_owner_limited_to_owners",
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
        - The `target_item_id` is optional. If not provided, the item will be moved to the root.
    """

    target_item_id = serializers.UUIDField(required=False)


class SDKRelayEventSerializer(serializers.Serializer):
    """Serializer for SDK relay events."""

    token = serializers.RegexField(regex=r"^[0-9a-zA-Z]{32}$", required=True)
    event = serializers.JSONField(required=True)

    def validate_event(self, value):
        """Validate that the event JSON data doesn't exceed maximum length."""

        # Convert the JSON data to a string to check its length
        json_string = json.dumps(value)
        # One selected file could use up to 1000 characters, this limit is set to
        # avoid DDOS attacks to fullfill the redis.
        max_length = 1000 * 100

        if len(json_string) > max_length:
            raise serializers.ValidationError(
                f"Event data exceeds maximum length of {max_length} characters."
            )

        return value
