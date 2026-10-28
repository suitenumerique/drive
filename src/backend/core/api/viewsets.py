"""API endpoints"""
# pylint: disable=too-many-lines

import json
import logging
import os
import re
import uuid
from io import BytesIO
from urllib.parse import quote, unquote, urlparse

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db import models as db
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.http import StreamingHttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.text import capfirst, slugify
from django.utils.translation import gettext_lazy as _

import rest_framework as drf
from botocore.exceptions import ClientError
from corsheaders.middleware import (
    ACCESS_CONTROL_ALLOW_METHODS,
    ACCESS_CONTROL_ALLOW_ORIGIN,
)
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from lasuite.drf.models.choices import (
    PRIVILEGED_ROLES,
    LinkReachChoices,
    get_equivalent_link_definition,
)
from lasuite.malware_detection import malware_detection
from lasuite.oidc_login.decorators import refresh_oidc_access_token
from rest_framework import response as drf_response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.throttling import UserRateThrottle
from rest_framework_api_key.permissions import HasAPIKey

from core import enums, models
from core.entitlements import get_entitlements_backend
from core.services.accesses import (
    batch_share_process_rows,
    synchronize_descendants_accesses,
)
from core.services.encryption_key_wraps import (
    WouldStrandPendingUsersError,
    chain_key_wraps,
    prune_unreachable_key_wraps,
)
from core.services.item_exports import build_zip_stream, export_descendants
from core.services.sdk_relay import SDKRelayManager
from core.services.search_indexers import (
    get_file_indexer,
    get_visited_items_ids_of,
)
from core.services.uploads import reserve_upload
from core.storage.cache import invalidate_storage_used_cache
from core.tasks.item import duplicate_file, process_item_purge, rename_file
from core.utils.analytics import posthog_capture
from wopi.conversion import exceptions as conversion_exceptions
from wopi.conversion.services import prepare_conversion
from wopi.services import access as access_service
from wopi.tasks.conversion import convert_file
from wopi.utils import compute_wopi_launch_url, get_wopi_client_config

from . import permissions, serializers, utils
from .filters import (
    ItemFilter,
    ItemOrdering,
    ListItemFilter,
    OrganizationUsageMetricFilter,
    SearchItemFilter,
    UsageMetricAccountTypeChoices,
    UsageMetricFilter,
)

logger = logging.getLogger(__name__)

ITEM_FOLDER = "item"
UUID_REGEX = r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
FILE_EXT_REGEX = '[^.\\/:*?&"<>|\r\n]+'
MEDIA_STORAGE_URL_PATTERN = re.compile(
    f"{settings.MEDIA_URL:s}(?P<preview>preview/)?"
    f"(?P<key>{ITEM_FOLDER:s}/(?P<pk>{UUID_REGEX:s})/.*{FILE_EXT_REGEX:s})$"
)
# pylint: disable=too-many-ancestors


class NestedGenericViewSet(viewsets.GenericViewSet):
    """
    A generic Viewset aims to be used in a nested route context.
    e.g: `/api/v1.0/resource_1/<resource_1_pk>/resource_2/<resource_2_pk>/`

    It allows to define all url kwargs and lookup fields to perform the lookup.
    """

    lookup_fields: list[str] = ["pk"]
    lookup_url_kwargs: list[str] = []

    def __getattribute__(self, item):
        """
        This method is overridden to allow to get the last lookup field or lookup url kwarg
        when accessing the `lookup_field` or `lookup_url_kwarg` attribute. This is useful
        to keep compatibility with all methods used by the parent class `GenericViewSet`.
        """
        if item in ["lookup_field", "lookup_url_kwarg"]:
            return getattr(self, item + "s", [None])[-1]

        return super().__getattribute__(item)

    def get_queryset(self):
        """
        Get the list of items for this view.

        `lookup_fields` attribute is enumerated here to perform the nested lookup.
        """
        queryset = super().get_queryset()

        # The last lookup field is removed to perform the nested lookup as it corresponds
        # to the object pk, it is used within get_object method.
        lookup_url_kwargs = (
            self.lookup_url_kwargs[:-1] if self.lookup_url_kwargs else self.lookup_fields[:-1]
        )

        filter_kwargs = {}
        for index, lookup_url_kwarg in enumerate(lookup_url_kwargs):
            if lookup_url_kwarg not in self.kwargs:
                raise KeyError(
                    f"Expected view {self.__class__.__name__} to be called with a URL "
                    f'keyword argument named "{lookup_url_kwarg}". Fix your URL conf, or '
                    "set the `.lookup_fields` attribute on the view correctly."
                )

            filter_kwargs.update({self.lookup_fields[index]: self.kwargs[lookup_url_kwarg]})

        return queryset.filter(**filter_kwargs)


class SerializerPerActionMixin:
    """
    A mixin to allow to define serializer classes for each action.

    This mixin is useful to avoid to define a serializer class for each action in the
    `get_serializer_class` method.

    Example:
    ```
    class MyViewSet(SerializerPerActionMixin, viewsets.GenericViewSet):
        serializer_class = MySerializer
        list_serializer_class = MyListSerializer
        retrieve_serializer_class = MyRetrieveSerializer
    ```
    """

    def get_serializer_class(self):
        """
        Return the serializer class to use depending on the action.
        """
        if serializer_class := getattr(self, f"{self.action}_serializer_class", None):
            return serializer_class
        return super().get_serializer_class()


class Pagination(drf.pagination.PageNumberPagination):
    """Pagination to display no more than 100 objects per page sorted by creation date."""

    ordering = "-created_on"
    max_page_size = settings.MAX_PAGE_SIZE
    page_size_query_param = "page_size"


class UserListThrottleBurst(UserRateThrottle):
    """Throttle for the user list endpoint."""

    scope = "user_list_burst"


class UserListThrottleSustained(UserRateThrottle):
    """Throttle for the user list endpoint."""

    scope = "user_list_sustained"


class ItemCreateThrottleBurst(UserRateThrottle):
    """Throttle for the item creation endpoints."""

    scope = "item_create_burst"


class ItemCreateThrottleSustained(UserRateThrottle):
    """Throttle for the item creation endpoints."""

    scope = "item_create_sustained"


class UserViewSet(
    SerializerPerActionMixin,
    drf.mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
    drf.mixins.ListModelMixin,
):
    """User ViewSet"""

    permission_classes = [permissions.IsSelf]
    queryset = models.User.objects.all().filter(is_active=True)
    serializer_class = serializers.UserSerializer
    get_me_serializer_class = serializers.UserMeSerializer
    contacts_serializer_class = serializers.UserLightSerializer
    pagination_class = None
    throttle_classes = []

    def get_throttles(self):
        self.throttle_classes = []
        if self.action == "list":
            self.throttle_classes = [UserListThrottleBurst, UserListThrottleSustained]

        return super().get_throttles()

    def get_queryset(self):
        """
        Limit listed users by querying the email field with a trigram similarity
        search if a query is provided.
        Limit listed users by excluding users already in the item if a item_id
        is provided.
        """
        queryset = self.queryset

        if self.action != "list":
            return queryset

        # Exclude all users already in the given item
        if item_id := self.request.query_params.get("item_id", ""):
            queryset = queryset.exclude(itemaccess__item_id=item_id)

        if not (query := self.request.query_params.get("q", "")) or len(query) < 5:
            return queryset.none()

        # For emails, match emails by Levenstein distance to prevent typing errors
        if "@" in query:
            return (
                queryset.annotate(distance=RawSQL("levenshtein(email::text, %s::text)", (query,)))
                .filter(distance__lte=3)
                .order_by("distance", "email")[: settings.API_USERS_LIST_LIMIT]
            )

        # Use trigram similarity for non-email-like queries
        # For performance reasons we filter first by similarity, which relies on an
        # index, then only calculate precise similarity scores for sorting purposes
        return (
            queryset.filter(email__trigram_word_similar=query)
            .annotate(similarity=TrigramSimilarity("email", query))
            .filter(similarity__gt=0.2)
            .order_by("-similarity", "email")[: settings.API_USERS_LIST_LIMIT]
        )

    @drf.decorators.action(
        detail=False,
        methods=["get"],
        url_name="me",
        url_path="me",
    )
    def get_me(self, request):
        """
        Return information on currently logged user
        """
        context = {"request": request}
        return drf.response.Response(self.get_serializer(request.user, context=context).data)

    @drf.decorators.action(detail=False, methods=["get"], url_path="contacts")
    def contacts(self, request):
        """
        Return the people involved in sharing with the current user, in either
        direction, most frequent first.

        A contact either holds an access on one of the user's items ("shared
        with") or created one of them ("shared by"). Frequency is the number of
        such items they hold an access on, so a contact's own private items do
        not inflate their ranking.
        """
        user = request.user
        # Restrict to live items the user has access to, directly or through a
        # team, matching the contact filter perimeter so every returned contact
        # yields at least one item.
        shared_items = models.Item.objects.filter(
            db.Q(accesses__user=user) | db.Q(accesses__team__in=user.teams),
            hard_deleted_at__isnull=True,
            ancestors_deleted_at__isnull=True,
        )

        shared_with = db.Q(itemaccess__item_id__in=shared_items.values("pk"))
        shared_by = db.Q(pk__in=shared_items.values("creator_id"))
        created_shared = db.Q(items_created__in=shared_items)
        frequency = db.Count("itemaccess", filter=shared_with) + db.Count(
            "items_created", filter=created_shared
        )
        contacts = (
            models.User.objects.filter(is_active=True)
            .filter(shared_with | shared_by)
            .exclude(pk=user.pk)
            .annotate(frequency=frequency)
        )

        if query := request.query_params.get("q", ""):
            if "@" in query:
                contacts = contacts.annotate(
                    distance=RawSQL("levenshtein(email::text, %s::text)", (query,))
                ).filter(distance__lte=3)
                ordering = ("distance", "email")
            else:
                contacts = (
                    contacts.filter(email__trigram_word_similar=query)
                    .annotate(similarity=TrigramSimilarity("email", query))
                    .filter(similarity__gt=0.2)
                )
                ordering = ("-similarity", "email")
        else:
            ordering = ("-frequency", "email")

        contacts = contacts.order_by(*ordering)[: settings.API_USERS_LIST_LIMIT]

        return drf.response.Response(self.get_serializer(contacts, many=True).data)


class ItemMetadata(drf.metadata.SimpleMetadata):
    """Custom metadata class to add information"""

    def determine_metadata(self, request, view):
        """Add language choices only for the list endpoint."""
        simple_metadata = super().determine_metadata(request, view)

        if request.path.endswith("/items/"):
            simple_metadata["actions"]["POST"]["language"] = {
                "choices": [
                    {"value": code, "display_name": name}
                    for code, name in enums.ALL_LANGUAGES.items()
                ]
            }
        return simple_metadata


# =============================================================================
# Subtree-encryption helpers
#
# Both `/encrypt/` (encrypt a subtree at its root) and `/move/` (move a
# plaintext subtree INTO an encrypted chain) need to:
#   1. Determine the effective scope, excluding inner encrypted subtrees.
#   2. Write `is_encrypted=True` + a wrapped key + (optionally) a new
#      filename onto the root and every descendant in scope.
#   3. Schedule best-effort post-commit cleanup of the old S3 keys.
#
# The differences (per-user wraps + RESTRICTED check at /encrypt/, the
# `item.move(target)` + chain wrap at /move/) stay in the views; these
# helpers cover the strictly shared mechanics.
# =============================================================================


def describe_maintenance_escrow(root, user):
    """What a holder entering the tree at its root needs to refresh or backfill
    the root's maintenance escrow copy: the root's owner, whose organization
    decides the maintenance key, and whether they may store the copy."""
    return {
        "root_item_id": str(root.pk),
        "owner_sub": root.creator.sub if root.creator else None,
        "has_maintenance_key": bool(root.maintenance_wrapped_item_key),
        "can_store": bool(root.get_abilities(user).get("maintenance_key")),
    }


def check_encrypt_on_move(data, *, source_is_encrypted, target_is_encrypted):
    """Encrypt-on-move (plaintext into an encrypted folder): the plaintext source picks
    up the chain wrap inline, no /encrypt/ round trip, no per-user wraps."""
    encrypted_symmetric_key = data.get("encrypted_symmetric_key")
    is_encryption_root_flag = data.get("is_encryption_root")
    per_user_encrypted_keys = data.get("per_user_encrypted_keys")
    if source_is_encrypted:
        raise drf.exceptions.ValidationError(
            {"detail": _("Encrypt-on-move payload is only valid for plaintext source items.")},
            code="item_move_encrypt_on_move_source_encrypted",
        )
    if not target_is_encrypted:
        raise drf.exceptions.ValidationError(
            {"detail": _("Encrypt-on-move requires moving INTO an encrypted folder.")},
            code="item_move_encrypt_on_move_plain_target",
        )
    if not encrypted_symmetric_key:
        raise drf.exceptions.ValidationError(
            {
                "encrypted_symmetric_key": _(
                    "Required for encrypt-on-move (chain wrap of the item's symmetric key)."
                )
            },
            code="item_move_chain_wrap_required",
        )
    if is_encryption_root_flag is not None:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Not applicable to encrypt-on-move; the item enters as a chain descendant."
                )
            },
            code="item_move_conflicting_flag",
        )
    if per_user_encrypted_keys is not None:
        raise drf.exceptions.ValidationError(
            {
                "per_user_encrypted_keys": _(
                    "Encrypt-on-move uses chain wraps only — no per-user wraps."
                )
            },
            code="item_move_conflicting_wrap",
        )


def check_encrypted_move(data, *, item, user, target_is_encrypted):
    """Refuse a move payload incoherent with the encryption state of the item and its
    target, before anything moves. Return whether the item moves between folders of
    the same encrypted tree."""
    # `source_is_root` means the item currently holds its key per-user (no chain
    # wrap of its own).
    source_is_encrypted = bool(item.is_encrypted)
    source_is_root = bool(source_is_encrypted and item.encrypted_symmetric_key is None)
    source_in_chain = source_is_encrypted and not source_is_root

    # Reject plaintext-into-encrypted without the encrypt-on-move
    # payload: the caller has to either encrypt first, or use the
    # encrypt-on-move shape above.
    if not source_is_encrypted and target_is_encrypted:
        raise drf.exceptions.ValidationError(
            {
                "detail": _(
                    "Plaintext items cannot be moved into an encrypted "
                    "folder. Encrypt the item first."
                )
            },
            code="item_move_plaintext_into_encrypted",
        )

    is_encryption_root_flag = data.get("is_encryption_root")
    # Only a re-anchor makes a new root, and only a root carries the escrow copy.
    if data.get("maintenance_key") and is_encryption_root_flag is not True:
        raise drf.exceptions.ValidationError(
            {
                "maintenance_key": _(
                    "Only an item re-anchored as its own encryption root carries a "
                    "maintenance escrow copy."
                )
            },
            code="item_move_maintenance_key_not_root",
        )
    if is_encryption_root_flag is True:
        check_re_anchor(
            data,
            user=user,
            source_is_encrypted=source_is_encrypted,
            target_is_encrypted=target_is_encrypted,
        )
    elif is_encryption_root_flag is False:
        check_demote(data, source_is_root=source_is_root, target_is_encrypted=target_is_encrypted)
    else:
        check_unflagged_move(
            data,
            source_is_root=source_is_root,
            source_in_chain=source_in_chain,
            target_is_encrypted=target_is_encrypted,
        )
    return source_in_chain and target_is_encrypted


def check_re_anchor(data, *, user, source_is_encrypted, target_is_encrypted):
    """Re-anchor: a chained source moves to plaintext or the workspace root, becomes its
    own encryption root and has `K_item` re-wrapped per collaborator."""
    encrypted_symmetric_key = data.get("encrypted_symmetric_key")
    per_user_encrypted_keys = data.get("per_user_encrypted_keys")
    version_per_user = data.get("encryption_public_key_versions", {})
    if not source_is_encrypted:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Cannot promote a plaintext item to an encryption root via /move/."
                )
            },
            code="item_move_promote_plain",
        )
    if target_is_encrypted:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Cannot re-anchor an item INTO an encrypted "
                    "subtree — it would be inside another root."
                )
            },
            code="item_move_promote_into_encrypted",
        )
    if not per_user_encrypted_keys:
        raise drf.exceptions.ValidationError(
            {"per_user_encrypted_keys": _("Required when promoting an item to encryption root.")},
            code="item_move_per_user_keys_required",
        )
    if encrypted_symmetric_key:
        raise drf.exceptions.ValidationError(
            {
                "encrypted_symmetric_key": _(
                    "Cannot supply a chain wrap when promoting to encryption root."
                )
            },
            code="item_move_conflicting_wrap",
        )

    # The mover MUST hold a non-null wrap for themselves; otherwise
    # they'd lock themselves out. Other collaborators can be null
    # (pending — same semantics as /encrypt/).
    caller_sub = user.sub
    if caller_sub not in per_user_encrypted_keys or per_user_encrypted_keys[caller_sub] is None:
        raise drf.exceptions.ValidationError(
            {
                "per_user_encrypted_keys": _(
                    "You must include a wrapped key for yourself when re-anchoring an item."
                )
            },
            code="item_move_caller_wrap_required",
        )

    # Per-user versions must cover the same set as the wraps.
    provided_user_subs = set(per_user_encrypted_keys.keys())
    version_subs = set(version_per_user.keys())
    if version_subs != provided_user_subs:
        version_missing = provided_user_subs - version_subs
        version_extra = version_subs - provided_user_subs
        errors = {}
        if version_missing:
            errors["missing_users"] = sorted(version_missing)
        if version_extra:
            errors["extra_users"] = sorted(version_extra)
        raise drf.exceptions.ValidationError(
            {
                "encryption_public_key_versions": _("Version set must match per-user key set."),
                **errors,
            },
            code="item_move_versions_mismatch",
        )


def check_demote(data, *, source_is_root, target_is_encrypted):
    """Demote: a self-rooted source attaches under the destination chain."""
    encrypted_symmetric_key = data.get("encrypted_symmetric_key")
    per_user_encrypted_keys = data.get("per_user_encrypted_keys")
    if not source_is_root:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Item is not currently an encryption root; cannot demote it."
                )
            },
            code="item_move_not_root",
        )
    if not target_is_encrypted:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Demoting from encryption root requires moving INTO an encrypted folder."
                )
            },
            code="item_move_demote_to_plain",
        )
    if not encrypted_symmetric_key:
        raise drf.exceptions.ValidationError(
            {
                "encrypted_symmetric_key": _(
                    "Required when demoting from encryption root into a chain."
                )
            },
            code="item_move_chain_wrap_required",
        )
    if per_user_encrypted_keys is not None:
        raise drf.exceptions.ValidationError(
            {
                "per_user_encrypted_keys": _(
                    "Cannot supply per-user wraps when demoting into a chain."
                )
            },
            code="item_move_conflicting_wrap",
        )


def check_unflagged_move(data, *, source_is_root, source_in_chain, target_is_encrypted):
    """No flag toggle: plain to plain (no encryption fields), or chained to chained in the
    same tree (chain wrap required). Self-rooted to plaintext is also allowed and leaves
    the encryption state untouched (the item stays a root)."""
    encrypted_symmetric_key = data.get("encrypted_symmetric_key")
    if source_in_chain and target_is_encrypted and not encrypted_symmetric_key:
        raise drf.exceptions.ValidationError(
            {"encrypted_symmetric_key": _("Required when moving between encrypted folders.")},
            code="item_move_encrypted_key_required",
        )
    if source_in_chain and not target_is_encrypted:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Moving an encrypted item out of its tree must "
                    "set is_encryption_root=true and supply "
                    "per_user_encrypted_keys."
                )
            },
            code="item_move_re_anchor_required",
        )
    if source_is_root and target_is_encrypted:
        raise drf.exceptions.ValidationError(
            {
                "is_encryption_root": _(
                    "Moving a self-rooted encrypted item INTO a "
                    "chain must set is_encryption_root=false and "
                    "supply encrypted_symmetric_key."
                )
            },
            code="item_move_demote_required",
        )


def apply_moved_encryption_state(item, data, *, moves_within_chain):
    """Write the encryption state a checked move payload gives the moved item, and
    return the fields to save."""
    encrypted_symmetric_key = data.get("encrypted_symmetric_key")
    is_encryption_root_flag = data.get("is_encryption_root")
    update_fields = []

    if is_encryption_root_flag is True:
        # Re-anchor: clear chain wrap, set flag (already True), then
        # store the per-user wraps on this item — same pattern as
        # /encrypt/.
        item.is_encrypted = True
        item.encrypted_symmetric_key = None
        item.maintenance_wrapped_item_key = data.get("maintenance_key")
        update_fields += ["is_encrypted", "encrypted_symmetric_key", "maintenance_wrapped_item_key"]
        write_key_wraps(
            item,
            data.get("per_user_encrypted_keys"),
            data.get("encryption_public_key_versions", {}),
        )

    elif is_encryption_root_flag is False:
        # Demote: add chain wrap. Existing per-user wraps on this
        # item's access rows are KEPT — the destination chain may
        # not cover the same set of users that held explicit
        # access on this self-rooted item, and clearing the
        # per-user wraps would silently revoke those collaborators'
        # ability to decrypt despite their ItemAccess role staying
        # intact. The chain wrap is additive: chain users decrypt
        # via the chain, original explicit users decrypt via their
        # preserved per-user wrap (the encrypted-key resolver
        # already prefers a non-null wrap on the item itself over
        # walking the chain).
        item.is_encrypted = True
        item.encrypted_symmetric_key = encrypted_symmetric_key
        # No longer a root: the destination root's copy covers it through the chain.
        item.maintenance_wrapped_item_key = None
        update_fields += ["is_encrypted", "encrypted_symmetric_key", "maintenance_wrapped_item_key"]

    elif moves_within_chain:
        # Same-tree chain rewrap.
        item.encrypted_symmetric_key = encrypted_symmetric_key
        update_fields.append("encrypted_symmetric_key")

    return update_fields


def encryptable_item_refusal(item):
    """Why `item` cannot be encrypted, or None."""
    # The item must be RESTRICTED (computed_link_reach accounts for inheritance:
    # a file inside a restricted folder is effectively restricted even if its own
    # link_reach is NULL).
    if item.computed_link_reach != LinkReachChoices.RESTRICTED:
        return _("Item must be restricted before it can be encrypted.")
    if item.is_encrypted:
        return _("Item is already encrypted.")
    if item.ancestors().filter(is_encrypted=True).exists():
        return _("Item is inside an already encrypted subtree.")
    return None


def encryption_wraps_refusal(item, caller, encrypted_key_per_user, version_per_user):
    """The error body refusing per-user wraps that do not match who can access
    `item`, or None."""
    # All users with access (direct OR inherited via an ancestor's ItemAccess)
    # must be present. Values may be a wrapped key or explicit null (pending:
    # the user has not completed their encryption onboarding yet).
    user_subs_with_access = set(
        models.ItemAccess.objects.filter(
            item__path__ancestors=item.path,
            user__isnull=False,
        )
        .values_list("user__sub", flat=True)
        .distinct()
    )
    provided_user_subs = set(encrypted_key_per_user.keys())
    if user_subs_with_access != provided_user_subs:
        return {
            "detail": _("Provided user keys do not match users with access."),
            **set_differences(user_subs_with_access, provided_user_subs),
        }

    # The caller is the one performing the encryption: they must hold the key.
    # Explicit null for themselves is never legitimate.
    if caller.sub in encrypted_key_per_user and encrypted_key_per_user[caller.sub] is None:
        return {
            "detail": _(
                "You cannot mark yourself as pending encryption "
                "onboarding — provide a wrapped key for your "
                "own user."
            ),
            "code": "caller_cannot_be_pending",
        }

    version_subs = set(version_per_user.keys())
    if version_subs != provided_user_subs:
        return {
            "detail": _(
                "Provided versions do not match the users in encrypted_symmetric_key_per_user."
            ),
            **set_differences(provided_user_subs, version_subs),
        }
    return None


def set_differences(expected, provided):
    """The `missing_users` and `extra_users` of a refused user set."""
    errors = {}
    if expected - provided:
        errors["missing_users"] = list(expected - provided)
    if provided - expected:
        errors["extra_users"] = list(provided - expected)
    return errors


def compute_effective_descendants_for_encryption(item):
    """Descendants of `item` minus everything inside inner encrypted roots.

    Stacked encryption: a folder may already contain inner encrypted
    subtrees. Those keep their existing keys and per-user ItemAccess
    rows; we only operate on the "outer" subtree they don't cover.
    Restrictions are excluded too: they only point at a folder living at
    the tree root and hold no content to encrypt.
    """
    inner_roots = list(
        item.descendants().filter(
            is_encrypted=True,
            encrypted_symmetric_key__isnull=True,
        )
    )
    qs = item.descendants().exclude(type=models.ItemTypeChoices.RESTRICTION)
    for inner in inner_roots:
        qs = qs.exclude(path__descendants=inner.path)
    return qs


def write_subtree_encryption(
    *,
    item,
    root_chain_wrap,
    encrypted_keys_for_descendants,
    file_key_mapping,
    effective_descendants,
):
    """Set `is_encrypted=True` + encryption fields on item + descendants.

    `root_chain_wrap`:
        - None: the item is itself the encryption root — its
          `encrypted_symmetric_key` stays NULL. The caller is responsible
          for writing per-user wraps onto access rows.
        - str:  the item is being attached under a destination chain —
          its `encrypted_symmetric_key` carries the chain wrap.

    `encrypted_keys_for_descendants` and `file_key_mapping` are keyed by
    str(uuid). Caller is responsible for validating that the descendant
    set matches the live one (mutation 409) before calling this — by
    the time we get here we trust the inputs.

    Returns the list of old S3 keys (filenames) that the caller should
    pass to `schedule_s3_cleanup` after the transaction commits.
    """
    old_s3_keys = []

    item.is_encrypted = True
    item.encrypted_symmetric_key = root_chain_wrap
    update_fields = ["is_encrypted", "encrypted_symmetric_key"]
    if str(item.pk) in file_key_mapping:
        old_s3_keys.append(item.file_key)
        item.filename = file_key_mapping[str(item.pk)]
        update_fields.append("filename")
    item.save(update_fields=update_fields)

    for descendant in effective_descendants:
        descendant.is_encrypted = True
        descendant.encrypted_symmetric_key = encrypted_keys_for_descendants.get(str(descendant.pk))
        desc_fields = ["is_encrypted", "encrypted_symmetric_key"]
        if str(descendant.pk) in file_key_mapping:
            old_s3_keys.append(descendant.file_key)
            descendant.filename = file_key_mapping[str(descendant.pk)]
            desc_fields.append("filename")
        descendant.save(update_fields=desc_fields)

    return old_s3_keys


def write_key_wraps(item, wrapped_key_per_sub, version_per_sub):
    """Store the wraps of `item`'s key for the users of `wrapped_key_per_sub` (OIDC sub →
    wrapped key), replacing those they held. A null wrap is a pending user: nothing is stored."""
    users_by_sub = {
        user.sub: user
        for user in models.User.objects.filter(
            sub__in=[sub for sub, wrapped_key in wrapped_key_per_sub.items() if wrapped_key]
        )
    }
    for sub, user in users_by_sub.items():
        models.ItemEncryptionKeyWrap.objects.update_or_create(
            item=item,
            user=user,
            defaults={
                "wrapped_key": wrapped_key_per_sub[sub],
                "encryption_public_key_version": version_per_sub.get(sub) or None,
            },
        )


def prune_key_wraps_or_refuse(item):
    """Delete the wraps under `item` of users who lost their role there, or refuse the
    change that led here (the caller's transaction rolls it back) when it would leave
    an encryption root's members with nobody holding its key."""
    try:
        prune_unreachable_key_wraps(item)
    except WouldStrandPendingUsersError as excpt:
        raise drf.exceptions.ValidationError(
            {
                "detail": _(
                    "This change would leave pending collaborators unable to "
                    "decrypt the folder, as nobody else holds its key. Either wait "
                    "for them to finish their encryption onboarding, or remove "
                    "encryption from the folder first."
                ),
            },
            code="would_strand_pending_users",
        ) from excpt


def compute_removal_scope(item):
    """Descendants whose encryption goes with `item`'s: all of them, minus inner encrypted roots.

    Stacked encryption: inner roots are independent encrypted trees with their own
    per-user keys and stay intact when the outer one goes back to plaintext.
    """
    scope = item.descendants()
    for inner in item.descendants().filter(is_encrypted=True, encrypted_symmetric_key__isnull=True):
        scope = scope.exclude(path__descendants=inner.path)
    return scope


def clear_subtree_encryption(*, item, file_key_mapping, effective_descendants, file_metadata=None):
    """Set `item` and its effective descendants back to plaintext.

    `file_key_mapping` maps str(file item id) to the filename under which its
    plaintext was uploaded (a new object key: objects are never overwritten). The
    per-user wrapped keys on the root's accesses and its maintenance copy are cleared.
    `file_metadata` maps str(file item id) to fields to set with the new filename
    (the plaintext's `mimetype` and `size`), when the caller already knows them.

    Returns the old S3 keys to delete and the (file key, item id) pairs to scan,
    both for after the transaction commits.
    """
    old_s3_keys = []
    file_metadata = file_metadata or {}

    def switch_file(target, fields):
        if str(target.pk) not in file_key_mapping:
            return
        old_s3_keys.append(target.file_key)
        target.filename = file_key_mapping[str(target.pk)]
        fields.append("filename")
        for name, value in file_metadata.get(str(target.pk), {}).items():
            setattr(target, name, value)
            fields.append(name)

    update_fields = ["is_encrypted", "encrypted_symmetric_key", "maintenance_wrapped_item_key"]
    switch_file(item, update_fields)
    item.is_encrypted = False
    item.encrypted_symmetric_key = None
    item.maintenance_wrapped_item_key = None
    item.save(update_fields=update_fields)

    for descendant in effective_descendants.iterator():
        desc_fields = ["is_encrypted", "encrypted_symmetric_key"]
        descendant.is_encrypted = False
        descendant.encrypted_symmetric_key = None
        switch_file(descendant, desc_fields)
        descendant.save(update_fields=desc_fields)

    models.ItemEncryptionKeyWrap.objects.filter(
        db.Q(item=item) | db.Q(item__in=effective_descendants)
    ).delete()

    # Plaintext again: the server can now inspect them.
    files_to_scan = []
    if item.type == models.ItemTypeChoices.FILE and item.filename:
        files_to_scan.append((item.file_key, item.pk))
    for descendant in effective_descendants.iterator():
        if descendant.type == models.ItemTypeChoices.FILE and descendant.filename:
            files_to_scan.append((descendant.file_key, descendant.pk))

    return old_s3_keys, files_to_scan


def stored_file_metadata(file_key, filename):
    """The `mimetype` and `size` of a stored plaintext file, detected as `upload_ended`
    does, or None when it cannot be read."""
    s3_client = default_storage.connection.meta.client
    bucket = default_storage.bucket_name

    try:
        size = s3_client.head_object(Bucket=bucket, Key=file_key)["ContentLength"]
        if size > 2048:
            head = s3_client.get_object(Bucket=bucket, Key=file_key, Range="bytes=0-2047")
        else:
            head = s3_client.get_object(Bucket=bucket, Key=file_key)
    except ClientError:
        logger.warning("Could not read %s to detect its type", file_key)
        return None

    return {"mimetype": utils.detect_mimetype(head["Body"].read(), filename=filename), "size": size}


def refresh_file_metadata(files, file_key_mapping):
    """Give the files switched to their plaintext (those in `file_key_mapping`) the
    plaintext's type and size: uploaded encrypted, they carry the ciphertext's."""
    for file_key, item_id in files:
        if str(item_id) not in file_key_mapping:
            continue
        metadata = stored_file_metadata(file_key, file_key_mapping[str(item_id)])
        if metadata:
            models.Item.objects.filter(pk=item_id).update(**metadata)


def schedule_s3_cleanup(old_s3_keys):
    """Best-effort post-commit deletion of S3 objects.

    Failures are logged, never raised — by the time we get here the
    DB transaction has committed and we can't undo it.
    """
    if not old_s3_keys:
        return

    def _cleanup():
        s3_client = default_storage.connection.meta.client
        bucket = default_storage.bucket_name
        for old_key in old_s3_keys:
            try:
                s3_client.delete_object(Bucket=bucket, Key=old_key)
            except ClientError:
                logger.warning("Failed to delete old S3 key: %s", old_key)

    transaction.on_commit(_cleanup)


# pylint: disable=too-many-public-methods
class ItemViewSet(
    SerializerPerActionMixin,
    drf.mixins.CreateModelMixin,
    drf.mixins.DestroyModelMixin,
    drf.mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ItemViewSet API.

    This view set provides CRUD operations and additional actions for managing items.
    Supports filtering, ordering, and annotations for enhanced querying capabilities.

    ### API Endpoints:
    1. **List**: Retrieve a paginated list of items.
       Example: GET /items/?page=2
    2. **Retrieve**: Get a specific item by its ID.
       Example: GET /items/{id}/
    3. **Create**: Create a new item.
       Example: POST /items/
    4. **Update**: Update a item by its ID.
       Example: PUT /items/{id}/
    5. **Delete**: Soft delete a item by its ID.
       Example: DELETE /items/{id}/

    ### Additional Actions:
    1. **Trashbin**: List soft deleted items for an items owner
        Example: GET /items/trashbin/

    2. **Children**: List or create child items.
        Example: GET, POST /items/{id}/children/

    3. **Favorite**: Get list of favorite items for a user. Mark or unmark
        a item as favorite.
        Examples:
        - GET /items/favorites/
        - POST, DELETE /items/{id}/favorite/

    4. **Link Configuration**: Update item link configuration.
        Example: PUT /items/{id}/link-configuration/

    5. **Media Auth**: Authorize access to item media.
        Example: GET /items/media-auth/

    6. **Duplicate**: Duplicate an item of type file.
        Example:

    ### Ordering: created_at, updated_at, is_favorite, title

        Example:
        - Ascending: GET /api/v1.0/items/?ordering=created_at
        - Desceding: GET /api/v1.0/items/?ordering=-title

    ### Filtering:
        - `is_creator_me=true`: Returns items created by the current user.
        - `is_creator_me=false`: Returns items created by other users.
        - `is_favorite=true`: Returns items marked as favorite by the current user
        - `is_favorite=false`: Returns items not marked as favorite by the current user
        - `title=hello`: Returns items which title contains the "hello" string

        Example:
        - GET /api/v1.0/items/?is_creator_me=true&is_favorite=true
        - GET /api/v1.0/items/?is_creator_me=false&title=hello

    ### Annotations:
    1. **is_favorite**: Indicates whether the item is marked as favorite by the current user.
    2. *`*user_roles**: Roles the current user has on the item or its ancestors.

    ### Notes:
    - Only the highest ancestor in a item hierarchy is shown in list views.
    - Implements soft delete logic to retain item tree structures.
    """

    metadata_class = ItemMetadata
    ordering = ["-updated_at"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "size",
        "title",
        "type",
        "updated_at",
        "creator__full_name",
    ]
    pagination_class = Pagination
    permission_classes = [
        permissions.ItemPermission,
    ]
    queryset = models.Item.objects.filter(hard_deleted_at__isnull=True)
    serializer_class = serializers.ItemSerializer
    list_serializer_class = serializers.ListItemSerializer
    trashbin_serializer_class = serializers.ListItemSerializer
    children_serializer_class = serializers.ListItemSerializer
    create_serializer_class = serializers.CreateItemSerializer
    tree_serializer_class = serializers.ListItemSerializer
    search_serializer_class = serializers.SearchItemSerializer
    breadcrumb_serializer_class = serializers.BreadcrumbItemSerializer
    recents_serializer_class = serializers.ListItemLightSerializer
    favorite_list_serializer_class = serializers.ListItemLightSerializer
    throttle_classes = []

    def get_throttles(self):
        """
        Rate limit the actions inserting an item, whatever its type: only files are
        bounded by the upload entitlement, so nothing else caps how many rows a
        client can create.
        """
        self.throttle_classes = []
        if self.action in {"create", "duplicate"} or (
            self.action == "children" and self.request.method == "POST"
        ):
            self.throttle_classes = [ItemCreateThrottleBurst, ItemCreateThrottleSustained]

        return super().get_throttles()

    def _filter_suspicious_items(self, queryset, user):
        """
        Filter out items with SUSPICIOUS upload_state for non-creators.

        Args:
            queryset: The queryset to filter
            user: The current user

        Returns:
            Filtered queryset excluding suspicious items from non-creators
        """
        # For authenticated users, exclude suspicious items they didn't create
        # For unauthenticated users, exclude all suspicious items
        if user.is_authenticated:
            return queryset.exclude(
                db.Q(upload_state=models.ItemUploadStateChoices.SUSPICIOUS) & ~db.Q(creator=user)
            )

        return queryset.exclude(upload_state=models.ItemUploadStateChoices.SUSPICIOUS)

    def _exclude_pending_items(self, queryset):
        """Exclude items with PENDING upload_state from listing views."""
        return queryset.exclude(upload_state=models.ItemUploadStateChoices.PENDING)

    def get_queryset(self):
        """Get queryset performing all annotation and filtering on the item tree structure."""
        user = self.request.user
        queryset = super().get_queryset().select_related("creator").annotate_has_restriction()
        # Remove items with upload_state SUSPICIOUS for non-creators
        queryset = self._filter_suspicious_items(queryset, user)

        # Only list views need filtering and annotation
        if self.detail:
            return queryset

        if not user.is_authenticated:
            return queryset.none()

        queryset = queryset.filter(ancestors_deleted_at__isnull=True)
        queryset = self._exclude_pending_items(queryset)

        # Filter items to which the current user has access...
        access_items_ids = models.ItemAccess.objects.filter(
            db.Q(user=user) | db.Q(team__in=user.teams)
        ).values_list("item_id", flat=True)

        # ...or that were previously accessed and are not restricted
        # For this we look for all items that have a link trace for the current user
        # and that are not in the access_items_ids list.
        # and we compute the ancestors link definition for each item.
        # Then we filter out the items that are restricted.
        traced_items = models.Item.objects.filter(
            db.Q(link_traces__user=user) & ~db.Q(id__in=access_items_ids)
        ).order_by("path")
        ancestors_link_definition = self._compute_ancestors_link_definition(traced_items)
        traced_items_ids = []
        for item in traced_items:
            links = ancestors_link_definition.get(str(item.path[:-1]), [])
            item.ancestors_link_definition = get_equivalent_link_definition(links)
            if item.computed_link_reach != LinkReachChoices.RESTRICTED:
                traced_items_ids.append(item.id)

        # Among all these items remove them that are restricted. A single subquery lets
        # Postgres look items up by primary key, an OR would scan the whole table.
        if traced_items_ids:
            access_items_ids = access_items_ids.order_by().union(
                models.Item.objects.filter(id__in=traced_items_ids)
                .order_by()
                .values_list("id", flat=True),
                all=True,
            )
        return queryset.filter(id__in=access_items_ids)

    def get_queryset_for_descendants(self):
        """
        Filter a queryset on all top level the user has access to
        and all items that are children of the top level items.

        The queryset is not annoated to let the function caller annotate it as needed.
        """

        user = self.request.user
        queryset = self.get_queryset()

        all_accessible_paths = queryset.order_by("path").values_list("path", flat=True)

        if not all_accessible_paths:
            return queryset.none()

        # Among the results, we may have items that are ancestors/descendants
        # of each other. In this case we want to keep only the highest ancestors.
        root_paths = utils.filter_root_paths(
            all_accessible_paths,
            skip_sorting=True,
        )

        queryset = self.queryset.select_related("creator").annotate_has_restriction()
        # Remove items with upload_state SUSPICIOUS for non-creators
        queryset = self._filter_suspicious_items(queryset, user)
        queryset = self._exclude_pending_items(queryset)
        queryset = queryset.filter(models.IdInSubtrees(db.F("id"), root_paths))
        queryset = queryset.filter(ancestors_deleted_at__isnull=True)

        return queryset

    def filter_queryset(self, queryset):
        """Override to apply annotations to generic views."""
        queryset = super().filter_queryset(queryset)
        user = self.request.user
        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()
        queryset = queryset.annotate_encryption_state(user)
        return queryset

    def get_response_for_queryset(
        self, queryset, context=None, with_ancestors_link_definition=False
    ):
        """Return paginated response for the queryset if requested."""
        context = context or self.get_serializer_context()
        page = self.paginate_queryset(queryset)
        if page is not None:
            items = list(page)
            if with_ancestors_link_definition:
                paths_links_mapping = self._compute_ancestors_link_definition(items)
                context["paths_links_mapping"] = paths_links_mapping
            serializer = self.get_serializer(items, many=True, context=context)
            result = self.get_paginated_response(serializer.data)
            return result

        items = list(queryset)
        if with_ancestors_link_definition:
            paths_links_mapping = self._compute_ancestors_link_definition(items)
            context["paths_links_mapping"] = paths_links_mapping
        serializer = self.get_serializer(items, many=True, context=context)
        return drf.response.Response(serializer.data)

    def _compute_ancestors_link_definition(self, items):
        """
        Compute ancestors link definition for the items collection, in order to inject
        it in the serializer context.
        """
        return models.Item.compute_items_ancestors_links_paths_mapping(items)

    def retrieve(self, request, *args, **kwargs):
        """
        Add a trace that the item was accessed by a user. This is used to list items
        on a user's list view even though the user has no specific role in the item (link
        access when the link reach configuration of the item allows it).
        """
        user = self.request.user
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # The `create` query generates 5 db queries which are much less efficient than an
        # `exists` query. The user will visit the item many times after the first visit
        # so that's what we should optimize for.
        if user.is_authenticated and not instance.link_traces.filter(user=user).exists():
            try:
                models.LinkTrace.objects.create(item=instance, user=request.user)
            except IntegrityError:
                pass  # Race condition: trace already created by concurrent request

        return drf.response.Response(serializer.data)

    def _create_file_from_template(self, item, extension):
        """Read template file and upload it to storage for the given item."""
        template_path = os.path.join(
            settings.BASE_DIR, "assets", "file_templates", enums.TEMPLATE_FILES[extension]
        )

        try:
            with open(template_path, "rb") as template_file:
                template_content = template_file.read()
        except OSError as e:
            logger.error(
                "Error reading template file %s: %s",
                template_path,
                str(e),
            )
            raise drf.exceptions.ValidationError(
                {"extension": _("Error reading template file.")},
                code="template_file_read_error",
            ) from e

        try:
            default_storage.save(item.file_key, BytesIO(template_content))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                "Error uploading template file to storage for item %s: %s",
                item.id,
                str(e),
            )
            item.soft_delete()
            item.delete()
            raise drf.exceptions.ValidationError(
                {"detail": _("Error uploading file to storage.")},
                code="storage_upload_error",
            ) from e

        item.upload_state = models.ItemUploadStateChoices.READY
        item.mimetype = utils.detect_mimetype(template_content, item.filename)
        item.size = len(template_content)
        item.save(update_fields=["upload_state", "mimetype", "size", "updated_at"])

        posthog_capture(
            "item_created_from_template",
            self.request.user,
            {"extension": extension},
            item=item,
        )

    def _check_can_upload(self, user, item_type):
        """Refuse the creation of a file when the upload entitlement is falsy."""
        if item_type != models.ItemTypeChoices.FILE:
            return

        can_upload = get_entitlements_backend().can_upload(user)
        if not can_upload["result"]:
            raise drf.exceptions.PermissionDenied(
                detail=can_upload.get("message", "You do not have permission to upload files."),
                code=can_upload.get("reason"),
            )

    def get_create_extra_attributes(self):
        """Extra model attributes applied to items created by this viewset (subclass hook)."""
        return {}

    def perform_create(self, serializer):
        """Set the current user as creator and owner of the newly created object."""
        self._create_item(serializer)
        models.ItemAccess.objects.create(
            item=serializer.instance,
            user=self.request.user,
            role=models.RoleChoices.OWNER,
        )

    def _create_item(self, serializer, parent=None):
        """Use the same admission check for root, child and external API uploads."""
        data = serializer.validated_data.copy()
        extension = data.pop("extension", None)
        attributes = self.get_create_extra_attributes()
        if parent is not None:
            attributes["parent"] = parent
        else:
            attributes["link_reach"] = LinkReachChoices.RESTRICTED

        if data["type"] == models.ItemTypeChoices.FILE and not extension:
            with reserve_upload(self.request.user, get_entitlements_backend()):
                serializer.instance = models.Item.objects.create_child(
                    creator=self.request.user, **data, **attributes
                )
        else:
            if extension:
                self._check_can_upload(self.request.user, data["type"])
            serializer.instance = models.Item.objects.create_child(
                creator=self.request.user, **data, **attributes
            )
            if extension:
                self._create_file_from_template(serializer.instance, extension)

    def perform_destroy(self, instance):
        """Override to implement a soft delete instead of dumping the record in database."""
        if instance.type == models.ItemTypeChoices.RESTRICTION:
            instance.detach()
        else:
            instance.soft_delete()
            posthog_capture("item_deleted", self.request.user, {}, item=instance)

    def perform_update(self, serializer):
        """Override to check if a file is renamed in order to rename file on storage."""
        instance = serializer.instance
        old_title = instance.title
        serializer.save()
        if instance.type == models.ItemTypeChoices.FILE:
            title = serializer.validated_data.get("title")
            if title and old_title != title:
                rename_file.delay(instance.id, title)

    @drf.decorators.action(detail=True, methods=["delete"], url_path="hard-delete")
    def hard_delete(self, request, *args, **kwargs):
        """
        Hard delete an item.
        """
        instance = self.get_object()
        instance.hard_delete()
        process_item_purge.delay(instance.id)
        posthog_capture("item_hard_deleted", request.user, {}, item=instance)
        return drf.response.Response(status=status.HTTP_204_NO_CONTENT)

    @drf.decorators.action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, *args, **kwargs):
        """Queue a legacy Office file conversion.

        Creates a placeholder Item in CONVERTING state in the destination folder
        and dispatches the celery task that will attach the converted bytes.
        """
        source = self.get_object()
        try:
            placeholder = prepare_conversion(source, request.user)
        except conversion_exceptions.ConversionPermissionDenied as exc:
            raise drf.exceptions.PermissionDenied() from exc
        except (
            conversion_exceptions.ConversionRejected,
            conversion_exceptions.ConversionMisconfigured,
        ) as exc:
            raise drf.exceptions.ValidationError({"detail": str(exc)}) from exc

        try:
            convert_file.delay(
                source_item_id=str(source.id),
                converted_item_id=str(placeholder.id),
                user_id=str(request.user.id),
            )
        except Exception:
            placeholder.soft_delete()
            placeholder.delete()
            raise

        posthog_capture(
            "item_converted",
            request.user,
            {"converted_item_id": placeholder.id},
            item=source,
        )

        serializer = self.get_serializer(placeholder)
        return drf.response.Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        """List top level items with pagination and filtering."""
        # Not calling filter_queryset. We do our own cooking.
        queryset = self.get_queryset()

        filterset = ListItemFilter(self.request.GET, queryset=queryset, request=self.request)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        filter_data = filterset.form.cleaned_data

        # Filter early, excluding is_favorite whose annotation does not exist yet
        for field in filterset.filters:
            if field != "is_favorite":
                queryset = filterset.filters[field].filter(queryset, filter_data[field])
        user = request.user
        queryset = queryset.annotate_user_roles(user)

        # Among the results, we may have items that are ancestors/descendants
        # of each other. In this case we want to keep only the highest ancestors.
        root_paths = utils.filter_root_paths(
            queryset.order_by("path").values_list("path", flat=True),
            skip_sorting=True,
        )
        queryset = queryset.filter(path__in=root_paths)

        # Hide restricted roots the user already reaches through a live
        # restriction, so the folder shows up in a single location
        if user.is_authenticated:
            reachable_restrictions = models.Item.objects.filter(
                type=models.ItemTypeChoices.RESTRICTION,
                target_id=db.OuterRef("pk"),
                ancestors_deleted_at__isnull=True,
            ).filter(
                db.Exists(
                    models.ItemAccess.objects.filter(
                        db.Q(user=user) | db.Q(team__in=user.teams),
                        models.IdInPath(db.F("item_id"), db.OuterRef("path")),
                    )
                )
                | (
                    db.Exists(
                        models.Item.objects.filter(
                            models.IdInPath(db.F("id"), db.OuterRef("path")),
                            link_reach__in=[
                                LinkReachChoices.PUBLIC,
                                LinkReachChoices.AUTHENTICATED,
                            ],
                        )
                    )
                    & db.Exists(
                        models.LinkTrace.objects.filter(
                            models.IdInPath(db.F("item_id"), db.OuterRef("path")), user=user
                        )
                    )
                )
            )
            queryset = queryset.exclude(db.Exists(reachable_restrictions))

        # Annotate the queryset with an attribute marking instances as highest ancestor
        # in order to save some time while computing abilities in the instance
        queryset = queryset.annotate(
            is_highest_ancestor_for_user=db.Value(True, output_field=db.BooleanField())
        )

        # Annotate favorite status and filter if applicable as late as possible
        queryset = queryset.annotate_is_favorite(user)
        queryset = filterset.filters["is_favorite"].filter(queryset, filter_data["is_favorite"])
        queryset = queryset.annotate_with_numchild()
        queryset = queryset.annotate_encryption_state(user)

        # Apply ordering only now that everyting is filtered and annotated
        queryset = ItemOrdering().filter_queryset(self.request, queryset, self)

        return self.get_response_for_queryset(queryset, with_ancestors_link_definition=True)

    @drf.decorators.action(detail=True, methods=["post"], url_path="upload-ended")
    def upload_ended(self, request, *args, **kwargs):
        """
        Start the analysis of an item after a successful upload.
        """

        item = self.get_object()

        if item.type != models.ItemTypeChoices.FILE:
            raise drf.exceptions.ValidationError(
                {"item": "This action is only available for items of type FILE."},
                code="item_upload_type_unavailable",
            )

        if item.upload_state != models.ItemUploadStateChoices.PENDING:
            raise drf.exceptions.ValidationError(
                {"item": "This action is only available for items in PENDING state."},
                code="item_upload_state_not_pending",
            )

        if item.size is None:
            can_upload = get_entitlements_backend().can_upload(item.creator)
            if not can_upload["result"]:
                self._complete_item_deletion(item)
                raise drf.exceptions.PermissionDenied(
                    detail=can_upload.get("message", "You do not have permission to upload files."),
                    code=can_upload.get("reason"),
                )

        s3_client = default_storage.connection.meta.client

        head_response = s3_client.head_object(Bucket=default_storage.bucket_name, Key=item.file_key)
        file_size = head_response["ContentLength"]

        self._validate_uploaded_size(item, file_size)

        # For encrypted files, skip MIME detection and malware scanning
        # (the server cannot inspect ciphertext)
        if item.is_encrypted:
            return self._end_encrypted_upload(item, file_size)

        if file_size > 2048:
            range_response = s3_client.get_object(
                Bucket=default_storage.bucket_name,
                Key=item.file_key,
                Range="bytes=0-2047",
            )
            file_head = range_response["Body"].read()
        else:
            file_head = s3_client.get_object(Bucket=default_storage.bucket_name, Key=item.file_key)[
                "Body"
            ].read()

        # Use improved MIME type detection combining magic bytes and file extension
        logger.info("upload_ended: detecting mimetype for file: %s", item.file_key)
        mimetype = utils.detect_mimetype(file_head, filename=item.filename)

        if settings.RESTRICT_UPLOAD_FILE_TYPE and mimetype not in settings.FILE_MIMETYPE_ALLOWED:
            self._complete_item_deletion(item)
            logger.info(
                "upload_ended: mimetype not allowed %s for filename %s",
                mimetype,
                item.filename,
            )
            raise drf.exceptions.ValidationError(
                detail="The file type is not allowed.",
                code="file_type_not_allowed",
            )

        if head_response["ContentType"] != mimetype:
            logger.info(
                "upload_ended: content type mismatch between object storage and item,"
                " updating from %s to %s",
                head_response["ContentType"],
                mimetype,
            )
            try:
                s3_client.copy_object(
                    Bucket=default_storage.bucket_name,
                    Key=item.file_key,
                    CopySource={
                        "Bucket": default_storage.bucket_name,
                        "Key": item.file_key,
                    },
                    ContentType=mimetype,
                    Metadata=head_response["Metadata"],
                    MetadataDirective="REPLACE",
                )
            except ClientError as error:
                # Log an exception but don't stop the action.
                logger.exception(
                    "Changing content type of item %s on object storage failed with error code %s"
                    " and error message %s",
                    item.id,
                    error.response["Error"]["Code"],
                    error.response["Error"]["Message"],
                )

        with transaction.atomic():
            item = models.Item.objects.select_for_update().get(pk=item.pk)
            if item.hard_deleted_at or item.ancestors_deleted_at:
                raise drf.exceptions.PermissionDenied()
            if item.upload_state != models.ItemUploadStateChoices.PENDING:
                raise drf.exceptions.ValidationError(
                    {"item": "This action is only available for items in PENDING state."},
                    code="item_upload_state_not_pending",
                )
            item.upload_state = models.ItemUploadStateChoices.ANALYZING
            item.mimetype = mimetype
            item.size = file_size
            item.save(update_fields=["upload_state", "mimetype", "size"])
            transaction.on_commit(
                lambda: malware_detection.analyse_file(item.file_key, item_id=item.id)
            )

        serializer = self.get_serializer(item)

        posthog_capture(
            "item_uploaded",
            request.user,
            {
                "id": item.id,
                "title": item.title,
                "size": item.size,
                "mimetype": item.mimetype,
            },
        )

        return drf_response.Response(serializer.data, status=status.HTTP_200_OK)

    def _end_encrypted_upload(self, item, file_size):
        """Mark an uploaded encrypted file ready: its ciphertext can be neither typed
        nor scanned."""
        item.upload_state = models.ItemUploadStateChoices.READY
        item.mimetype = "application/octet-stream"
        item.size = file_size
        item.save(update_fields=["upload_state", "mimetype", "size"])
        serializer = self.get_serializer(item)
        posthog_capture(
            "item_uploaded",
            self.request.user,
            {
                "id": item.id,
                "title": item.title,
                "size": item.size,
                "mimetype": item.mimetype,
                "is_encrypted": True,
            },
        )
        return drf_response.Response(serializer.data, status=status.HTTP_200_OK)

    def _validate_uploaded_size(self, item, file_size):
        """Verify storage metadata even though the PUT has a signed length."""
        if item.size is not None and file_size != item.size:
            self._complete_item_deletion(item)
            raise drf.exceptions.ValidationError(
                detail="The uploaded file size does not match the reserved size.",
                code="file_size_mismatch",
            )

        if file_size > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            self._complete_item_deletion(item)
            logger.info(
                "upload_ended: file size (%s) for file %s higher than the allowed max size",
                file_size,
                item.file_key,
            )
            raise drf.exceptions.ValidationError(
                detail="The file size is higher than the allowed max size.",
                code="file_size_exceeded",
            )

    def _complete_item_deletion(self, item):
        """Completely delete an item."""
        item.soft_delete()
        item.hard_delete()
        process_item_purge.delay(item.id)

    @drf.decorators.action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="favorites",
    )
    def favorite_list(self, request, *args, **kwargs):
        """Get list of favorite items for the current user."""
        user = request.user
        queryset = self.get_queryset_for_descendants()
        queryset = queryset.annotate(is_favorite=db.Value(True, output_field=db.BooleanField()))
        queryset = queryset.annotate_user_roles(user)

        filterset = ItemFilter(self.request.GET, queryset=queryset, request=self.request)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)

        queryset = filterset.filter_queryset(queryset)

        favorite_items_ids = models.ItemFavorite.objects.filter(user=user).values_list(
            "item_id", flat=True
        )

        queryset = queryset.filter(id__in=favorite_items_ids)
        queryset = queryset.annotate_with_numchild()

        # Apply ordering only now that everyting is filtered and annotated
        queryset = ItemOrdering().filter_queryset(self.request, queryset, self)

        return self.get_response_for_queryset(queryset, with_ancestors_link_definition=True)

    @drf.decorators.action(
        detail=False,
        methods=["get"],
    )
    def trashbin(self, request, *args, **kwargs):
        """
        Retrieve soft-deleted items for which the current user has the owner role.

        The selected items are those deleted within the cutoff period defined in the
        settings (see TRASHBIN_CUTOFF_DAYS), before they are considered permanently deleted.

        Owner access on items or their ancestors is resolved from the subtrees the user
        owns, see `trashed_owned_by`.
        """
        user = request.user

        # Restrict to soft-deleted items the user owns (directly or through an
        # ancestor access), read from the subtrees the user owns rather than checking
        # the owner of every deleted item.
        queryset = (
            self.queryset.select_related("creator")
            .annotate_has_restriction()
            .filter(deleted_at__gte=models.get_trashbin_cutoff())
            .trashed_owned_by(user)
        )

        # Apply filtering similar to children method
        filterset = ItemFilter(request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        queryset = filterset.qs

        # Only annotate with user roles for the filtered set if needed by serializer
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()
        queryset = queryset.annotate_encryption_state(user)

        return self.get_response_for_queryset(queryset, with_ancestors_link_definition=True)

    def _move_encrypting(self, item, target_item, data):
        """Move a plaintext item into an encrypted folder and encrypt it on the way:
        chain wraps only, the subtree's keys and content staged by the client."""
        encrypted_keys_for_descendants = data.get("encrypted_keys_for_descendants", {})
        file_key_mapping = data.get("file_key_mapping", {})
        encrypted_symmetric_key = data.get("encrypted_symmetric_key")
        user = self.request.user
        # Materialise the descendant set BEFORE the move. The path
        # filter on `descendants()` captures `item.path` at filter-
        # build time; once `item.move(target)` rewrites paths via
        # raw SQL, re-evaluating the queryset returns nothing
        # (filter still references the old path value).
        effective_descendants = list(compute_effective_descendants_for_encryption(item))
        live_descendant_ids = {str(d.pk) for d in effective_descendants}
        provided_descendant_ids = set(encrypted_keys_for_descendants.keys())
        if live_descendant_ids != provided_descendant_ids:
            return drf.response.Response(
                {
                    "detail": _("Folder contents changed during the operation. Please retry."),
                    "code": "subtree_mutated",
                    "missing": sorted(live_descendant_ids - provided_descendant_ids),
                    "extra": sorted(provided_descendant_ids - live_descendant_ids),
                },
                status=drf.status.HTTP_409_CONFLICT,
            )
        # Apply: move + write subtree encryption (chain-wrapped at
        # the root). No per-user wraps anywhere in this subtree —
        # decryption flows through the destination chain.
        item.move(target_item)
        old_s3_keys = write_subtree_encryption(
            item=item,
            root_chain_wrap=encrypted_symmetric_key,
            encrypted_keys_for_descendants=encrypted_keys_for_descendants,
            file_key_mapping=file_key_mapping,
            effective_descendants=effective_descendants,
        )
        # Sync link reach with the new (encrypted) parent — same
        # rule as plain moves: a child item's link_reach is None
        # so it inherits the parent's RESTRICTED.
        item.link_reach = None
        item.save(update_fields=["link_reach"])
        prune_key_wraps_or_refuse(item)
        schedule_s3_cleanup(old_s3_keys)
        posthog_capture("item_moved", user, {}, item=item)
        return drf.response.Response(
            {"message": "item moved successfully."}, status=status.HTTP_200_OK
        )

    @drf.decorators.action(detail=True, methods=["post"])
    @transaction.atomic
    def move(self, request, *args, **kwargs):
        """
        Move an item to another location within the item tree.

        The user must be an administrator or owner of both the item being moved
        and the target parent item.
        """
        user = request.user
        item = self.get_object()  # including permission checks

        # Validate the input payload
        serializer = serializers.MoveItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        target_item_id = validated_data.get("target_item_id")
        if not target_item_id:
            target_item = None
        else:
            try:
                target_item = models.Item.objects.get(
                    id=target_item_id, ancestors_deleted_at__isnull=True
                )
            except models.Item.DoesNotExist as excpt:
                raise drf.exceptions.ValidationError(
                    {"target_item_id": "Target parent item does not exist."},
                    code="item_move_target_does_not_exist",
                ) from excpt

        message = None
        if target_item and not target_item.get_abilities(user).get("children_create"):
            message = "You do not have permission to move items as a child to this target item."

        if message:
            posthog_capture("item_move_missing_permission", user, {}, item=item)
            raise drf.exceptions.ValidationError(
                {"target_item_id": message}, code="item_move_missing_permission"
            )

        # Moving a file to the root without a direct access reassigns its creator
        # (see below), shifting the file size to the mover's storage usage: gate it
        # like an upload so an over-quota user cannot take ownership of more storage.
        has_direct_access = models.ItemAccess.objects.filter(item=item, user=user).exists()
        if not target_item and not has_direct_access and item.type == models.ItemTypeChoices.FILE:
            can_upload = get_entitlements_backend().can_upload(user)
            if not can_upload["result"]:
                raise drf.exceptions.PermissionDenied(
                    detail=can_upload.get("message", "You cannot take ownership of more storage."),
                    code=can_upload.get("reason"),
                )

        # Encryption-aware move. Five resolved shapes — see
        # `MoveItemSerializer` for the payload schema. We validate first
        # (so a malformed payload never moves the item) then apply the
        # move, then apply the encryption state change atomically.
        target_is_encrypted = target_item.is_encrypted if target_item else False
        # Encrypt-on-move payload: the presence of either field is the
        # signal we're looking at the plaintext-into-chain shape (an
        # empty dict still counts — single-file moves have no
        # descendants but still go through this path).
        if (
            "encrypted_keys_for_descendants" in validated_data
            or "file_key_mapping" in validated_data
        ):
            check_encrypt_on_move(
                validated_data,
                source_is_encrypted=bool(item.is_encrypted),
                target_is_encrypted=target_is_encrypted,
            )
            return self._move_encrypting(item, target_item, validated_data)

        moves_within_chain = check_encrypted_move(
            validated_data, item=item, user=user, target_is_encrypted=target_is_encrypted
        )

        # ----- Apply the position change first; encryption state writes
        # depend on the target tree state being settled. -----
        item.move(target_item)

        update_fields = apply_moved_encryption_state(
            item, validated_data, moves_within_chain=moves_within_chain
        )

        # If the item is moved to the root and the user does not have an access on the item,
        # create an owner access for the user. Otherwise, the item will be invisible for the user.
        if not target_item and not models.ItemAccess.objects.filter(item=item, user=user).exists():
            models.ItemAccess.objects.create(
                item=item,
                user=self.request.user,
                role=models.RoleChoices.OWNER,
            )
            # Saving the item only invalidates the storage used cache of the
            # new creator, the previous one loses this item from its usage.
            previous_creator_id = item.creator_id
            transaction.on_commit(lambda: invalidate_storage_used_cache([previous_creator_id]))
            item.creator = user
            update_fields.append("creator")

        # When moving an item to the root and no link_reach is set
        # Force it to be restricted.
        if not target_item and not item.link_reach:
            item.link_reach = LinkReachChoices.RESTRICTED
            update_fields.append("link_reach")

        if target_item:
            # When moving an item in an other item, force it to be sync
            # with its parent's link reach.
            item.link_reach = None
            update_fields.append("link_reach")

        if update_fields:
            item.save(update_fields=update_fields)

        # Collaborators of the former parent lose their role in the moved subtree
        prune_key_wraps_or_refuse(item)

        posthog_capture("item_moved", user, {}, item=item)

        return drf.response.Response(
            {"message": "item moved successfully."}, status=status.HTTP_200_OK
        )

    @drf.decorators.action(
        detail=True,
        methods=["post"],
    )
    def restore(self, request, *args, **kwargs):
        """
        Restore a soft-deleted item if it was deleted less than x days ago.
        """
        item = self.get_object()
        item.restore()

        return drf_response.Response(
            {"detail": "item has been successfully restored."},
            status=status.HTTP_200_OK,
        )

    @drf.decorators.action(
        detail=True,
        methods=["get", "post"],
        ordering=["created_at"],
        url_path="children",
    )
    def children(self, request, *args, **kwargs):
        """Handle listing and creating children of a item"""
        item = self.get_object()

        if request.method == "POST":
            # Create a child item
            serializer = serializers.CreateItemSerializer(
                data=request.data, context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)

            encrypted_symmetric_key = serializer.validated_data.pop("encrypted_symmetric_key", None)

            # If parent is encrypted, child must provide an encrypted_symmetric_key
            if item.is_encrypted:
                if not encrypted_symmetric_key:
                    return drf.response.Response(
                        {
                            "detail": _(
                                "encrypted_symmetric_key is required when creating "
                                "a child in an encrypted folder."
                            )
                        },
                        status=drf.status.HTTP_400_BAD_REQUEST,
                    )
                # A template would be written in plaintext into the encrypted folder
                if serializer.validated_data.get("extension"):
                    return drf.response.Response(
                        {
                            "detail": _(
                                "Files cannot be created from a template in an encrypted folder."
                            )
                        },
                        status=drf.status.HTTP_400_BAD_REQUEST,
                    )
                serializer.validated_data["is_encrypted"] = True
                serializer.validated_data["encrypted_symmetric_key"] = encrypted_symmetric_key

            self._create_item(serializer, parent=item)

            headers = self.get_success_headers(serializer.data)
            return drf.response.Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

        # GET: List children
        queryset = (
            item.children()
            .select_related("creator", "target")
            .annotate_has_restriction()
            .filter(deleted_at__isnull=True)
        )
        if request.user.is_authenticated:
            queryset = queryset.prefetch_related(
                db.Prefetch(
                    "target__accesses",
                    queryset=models.ItemAccess.objects.filter(
                        db.Q(user=request.user) | db.Q(team__in=request.user.teams)
                    ),
                    to_attr="viewer_accesses",
                )
            )
        queryset = self._filter_suspicious_items(queryset, request.user)
        queryset = self._exclude_pending_items(queryset)
        queryset = self.filter_queryset(queryset)
        filterset = ItemFilter(request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        queryset = filterset.qs

        # Apply ordering only now that everything is filtered and annotated
        queryset = ItemOrdering().filter_queryset(self.request, queryset, self)

        # Pre-compute number of accesses. The direct accesses of each child are counted
        # in a subquery: joining them would group the whole query, including the
        # pagination count, which would then compute every annotation again
        item_nb_accesses = item.nb_accesses
        nb_direct_accesses = (
            models.ItemAccess.objects.filter(item_id=db.OuterRef("pk"))
            .order_by()
            .values("item_id")
            .annotate(count=db.Count("id"))
            .values("count")
        )
        queryset = queryset.annotate(
            _nb_accesses=db.Value(item_nb_accesses)
            + Coalesce(db.Subquery(nb_direct_accesses, output_field=db.IntegerField()), 0),
        )

        # Pass ancestors' links paths mapping to the serializer as a context variable
        # in order to allow saving time while computing abilities on the instance
        paths_links_mapping = item.compute_ancestors_links_paths_mapping()

        return self.get_response_for_queryset(
            queryset,
            context={
                "request": request,
                "paths_links_mapping": paths_links_mapping,
            },
        )

    @drf.decorators.action(detail=True, methods=["get"])
    def descendants(self, request, pk=None):
        """
        Return a flat list of every descendant of this item (files + folders),
        including the item itself. Used by recursive operations (encryption,
        bulk actions) so the frontend can enumerate a subtree in one query.
        """
        queryset = (
            self.queryset.select_related("creator")
            .annotate_has_restriction()
            .annotate_user_roles(request.user)
            .annotate_with_numchild()
            .annotate_encryption_state(request.user)
        )
        try:
            item = queryset.get(pk=pk)
        except models.Item.DoesNotExist as exc:
            raise drf.exceptions.NotFound from exc

        # Manual access check: the user must have read access to the root
        # item. Inheritance handles descendants — if you can read a folder,
        # you can read its contents.
        abilities = item.get_abilities(request.user)
        if not abilities.get("retrieve", False):
            raise drf.exceptions.PermissionDenied()

        if item.type != models.ItemTypeChoices.FOLDER:
            return drf.response.Response(
                self.get_serializer([item], many=True).data,
                status=drf.status.HTTP_200_OK,
            )

        # Restrictions are left out, consistently with the encryption scope
        subtree_qs = (
            queryset.filter(
                path__descendants=item.path,
                ancestors_deleted_at__isnull=True,
            )
            .exclude(type=models.ItemTypeChoices.RESTRICTION)
            .order_by("path")
        )
        serializer = self.get_serializer(subtree_qs, many=True)
        return drf.response.Response(serializer.data, status=drf.status.HTTP_200_OK)

    @drf.decorators.action(detail=True, methods=["get"])
    def tree(self, request, pk=None):
        """
        List ancestors tree above the item
        What we need to display is the tree structure opened for the current document.
        """
        try:
            item = self.queryset.only("path").get(pk=pk)
        except models.Item.DoesNotExist as exc:
            raise drf.exceptions.NotFound from exc

        prefixes = [str(item.path[:i]) for i in range(1, len(item.path) + 1)]
        highest_ancestor = (
            self.queryset.filter(path__in=prefixes, ancestors_deleted_at__isnull=True)
            .readable_per_se(request.user)
            .only("path")
            .order_by("path")
            .first()
        )

        if not highest_ancestor:
            raise (
                drf.exceptions.PermissionDenied()
                if request.user.is_authenticated
                else drf.exceptions.NotAuthenticated()
            )

        ancestors = (
            self.queryset.filter(
                path__ancestors=item.path,
                path__descendants=highest_ancestor.path,
                ancestors_deleted_at__isnull=True,
            )
            .order_by("path")
            .values_list("path", "link_reach", "link_role", named=True)
        )

        if len(ancestors) == 0:
            raise (
                drf.exceptions.PermissionDenied()
                if request.user.is_authenticated
                else drf.exceptions.NotAuthenticated()
            )

        paths_links_mapping = {}
        ancestors_links = []
        clause = db.Q()
        for i, ancestor in enumerate(ancestors):
            # exclude first iteration
            if i == 0:
                # this is the highest ancestor, select it directly
                clause |= db.Q(path=ancestor.path)
            else:
                # Select all siblings of the current ancestor
                clause |= db.Q(
                    path__descendants=".".join(ancestor.path[:-1]),
                    path__depth=len(ancestor.path),
                )

            # Compute cache for ancestors links to avoid many queries while computing
            # abilties for his items in the tree!
            ancestors_links.append(
                {"link_reach": ancestor.link_reach, "link_role": ancestor.link_role}
            )
            paths_links_mapping[str(ancestor.path)] = ancestors_links.copy()

        tree = (
            self.queryset.select_related("creator", "target")
            .annotate_has_restriction()
            .filter(
                clause,
                type__in=[models.ItemTypeChoices.FOLDER, models.ItemTypeChoices.RESTRICTION],
                deleted_at__isnull=True,
            )
            .order_by("created_at")
        )

        user = request.user
        tree = tree.annotate_user_roles(user)
        tree = tree.annotate_is_favorite(user)
        tree = tree.annotate_with_numchild()
        tree = tree.annotate_encryption_state(user)
        tree = self._filter_suspicious_items(tree, user)

        serializer = self.get_serializer(
            tree,
            many=True,
            context={
                "request": request,
                "paths_links_mapping": paths_links_mapping,
            },
        )

        return drf.response.Response(
            utils.flat_to_nested(serializer.data), status=drf.status.HTTP_200_OK
        )

    @drf.decorators.action(
        url_path="recents",
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def recents(self, request, *args, **kwargs):
        """Get list of recents items for the current user."""
        user = self.request.user
        queryset = self.get_queryset_for_descendants()

        filterset = ItemFilter(self.request.GET, queryset=queryset, request=self.request)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)

        queryset = filterset.filter_queryset(queryset)

        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()
        queryset = queryset.annotate_encryption_state(user)

        # Apply ordering only now that everyting is filtered and annotated
        queryset = ItemOrdering().filter_queryset(self.request, queryset, self)

        return self.get_response_for_queryset(queryset, with_ancestors_link_definition=True)

    @drf.decorators.action(detail=True, methods=["get"])
    def breadcrumb(self, request, *args, **kwargs):
        """
        List the breadcrumb for an item
        """
        item = self.get_object()

        prefixes = [str(item.path[:i]) for i in range(1, len(item.path) + 1)]
        highest_ancestor = (
            self.queryset.filter(path__in=prefixes, ancestors_deleted_at__isnull=True)
            .readable_per_se(request.user)
            .only("path")
            .order_by("path")
            .first()
        )

        if not highest_ancestor:
            raise (
                drf.exceptions.PermissionDenied()
                if request.user.is_authenticated
                else drf.exceptions.NotAuthenticated()
            )

        breadcrumb = self.queryset.filter(
            path__ancestors=item.path,
            path__descendants=highest_ancestor.path,
            ancestors_deleted_at__isnull=True,
        ).order_by("path")

        serializer = self.get_serializer(breadcrumb, many=True)
        return drf.response.Response(serializer.data, status=drf.status.HTTP_200_OK)

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    @method_decorator(refresh_oidc_access_token)
    def _indexed_search(self, request, queryset, indexer, text):
        """
        Returns a DRF response containding the results the fulltext search of Find
        sorted by score.
        """
        user = request.user
        token = request.session.get("oidc_access_token")

        # Retrieve the documents ids from Find. No pagination here the queryset is
        # already filtered
        result_ids = [
            r["_id"]
            for r in indexer.search(
                text=text, token=token, visited=get_visited_items_ids_of(queryset, user)
            )
        ]

        queryset = queryset.filter(pk__in=result_ids)
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_with_numchild()
        queryset = queryset.annotate_encryption_state(user)

        files_by_uuid = {str(d.pk): d for d in queryset}
        ordered_files = [files_by_uuid[id] for id in result_ids if id in files_by_uuid]

        page = self.paginate_queryset(ordered_files)

        if page is not None:
            items = self._compute_parents(page)
            serializer = self.get_serializer(items, many=True)
            result = self.get_paginated_response(serializer.data)
            return result

        items = self._compute_parents(ordered_files)
        serializer = self.get_serializer(items, many=True)
        return drf.response.Response(serializer.data)

    @drf.decorators.action(
        detail=False,
        methods=["get"],
        url_path="search",
        pagination_class=drf.pagination.PageNumberPagination,
    )
    def search(self, request, *args, **kwargs):
        """
        Returns a DRF response containing the filtered, annotated and ordered items.

        Applies filtering based on request parameter 'q' from `SearchItemFilter`.
        Depending of the configuration it can be:
         - A fulltext search through the opensearch indexation app "find" if the backend is
           enabled (see SEARCH_INDEXER_CLASS) and the feature flag INDEXED_SEARCH_ENABLED is True
         - A filtering by the model fields 'title' & 'type'.
        """
        queryset = self.queryset
        indexer = get_file_indexer()

        queryset = queryset.select_related("creator")
        filterset = SearchItemFilter(request.GET, queryset=queryset, request=self.request)

        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)

        workspace = filterset.form.cleaned_data.get("workspace")

        # First look for all top level items user has access to. Soft deleted items
        # are kept: a deleted root item is its own access holder and would become
        # unreachable, even from the trashbin. The scope filter excludes them from
        # the results.
        user = request.user
        item_access_queryset = models.ItemAccess.objects.select_related("item").filter(
            db.Q(user=user) | db.Q(team__in=user.teams),
            item__hard_deleted_at__isnull=True,
        )

        # Remove items with upload_state SUSPICIOUS for non-creators
        queryset = self._filter_suspicious_items(queryset, user)
        queryset = self._exclude_pending_items(queryset)

        # Restrictions are tree entries, not searchable content
        queryset = queryset.exclude(type=models.ItemTypeChoices.RESTRICTION)

        queryset = queryset.annotate_is_favorite(user)

        if workspace:
            item_access_queryset = item_access_queryset.filter(item__id=workspace)

        top_level_items = item_access_queryset.values_list("item__path", flat=True)
        # Then look for all items that are children of the top level items

        if not top_level_items:
            return self.get_response_for_queryset(queryset.none())

        # Among the results, we may have items that are ancestors/descendants
        # of each other. In this case we want to keep only the highest ancestors.
        root_paths = utils.filter_root_paths(
            top_level_items,
            skip_sorting=True,
        )

        path_list = db.Q()
        for top_level_item in root_paths:
            path_list |= db.Q(path__descendants=top_level_item)

        queryset = queryset.filter(path_list)

        # use indexed search ONLY when the feature flag is enabled
        if indexer and settings.FEATURES_INDEXED_SEARCH is True:
            # When the indexer is configured pop "title" from queryset search and use
            # fulltext results instead.
            return self._indexed_search(
                request,
                queryset,
                indexer,
                text=filterset.form.cleaned_data.pop("title"),
            )

        # Without the indexer, the "title" filtering is kept
        queryset = filterset.filter_queryset(queryset)
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()
        queryset = queryset.annotate_encryption_state(user)

        page = self.paginate_queryset(queryset)

        if page is not None:
            items = self._compute_parents(page)
            serializer = self.get_serializer(items, many=True)
            result = self.get_paginated_response(serializer.data)
            return result

        items = self._compute_parents(queryset)
        serializer = self.get_serializer(items, many=True)
        return drf.response.Response(serializer.data)

    def _compute_parents(self, items):
        """
        Compute parents for the items by analyzing their paths and fetching missing parents.
        """
        # Build parents dictionary and collect missing parent IDs
        parents = {str(item.id): item for item in items}
        missing_parent_ids = set()

        for item in items:
            for item_id in item.path:
                if item_id not in parents and item_id not in missing_parent_ids:
                    missing_parent_ids.add(item_id)

        # Fetch missing ancestors from database
        if missing_parent_ids:
            for parent in (
                models.Item.objects.annotate_with_numchild()
                .annotate_encryption_state(self.request.user)
                .filter(id__in=missing_parent_ids)
                .iterator()
            ):
                parents[str(parent.id)] = parent

        # Set parents for each item
        for item in items:
            item.parents = [parents[item_id] for item_id in item.path if item_id != str(item.id)]

        return items

    @drf.decorators.action(detail=True, methods=["put"], url_path="link-configuration")
    def link_configuration(self, request, *args, **kwargs):
        """Update link configuration with specific rights (cf get_abilities)."""
        # Check permissions first
        item = self.get_object()
        previous_link_reach = item.link_reach

        # Block link configuration changes for encrypted items (must stay RESTRICTED)
        if item.is_encrypted:
            new_reach = request.data.get("link_reach")
            if new_reach and new_reach != LinkReachChoices.RESTRICTED:
                return drf.response.Response(
                    {
                        "detail": _(
                            "Encrypted items must remain restricted. "
                            "Remove encryption before changing link configuration."
                        )
                    },
                    status=drf.status.HTTP_400_BAD_REQUEST,
                )

        # Deserialize and validate the data
        serializer = serializers.LinkItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        if models.LinkReachChoices.get_priority(
            item.link_reach
        ) >= models.LinkReachChoices.get_priority(previous_link_reach):
            item.descendants().update(link_reach=None)

        return drf.response.Response(serializer.data, status=drf.status.HTTP_200_OK)

    @drf.decorators.action(detail=True, methods=["post"], url_path="encryption-upload-url")
    def encryption_upload_url(self, request, *args, **kwargs):
        """Return a presigned S3 PUT URL for uploading encrypted file content.

        When `filename` is provided: generates a URL for a NEW S3 key
        (used during initial encryption to avoid overwriting the plaintext file).

        When `filename` is omitted: generates a URL for the EXISTING S3 key
        (used for auto-save — S3 versioning keeps previous versions).

        `size` is the exact length of the content to upload: the URL signs it,
        as for any upload, so it never grants a write of any length.
        """
        item = self.get_object()

        if item.type != models.ItemTypeChoices.FILE:
            return drf.response.Response(
                {"detail": _("Only files can be encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        size = request.data.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise drf.exceptions.ValidationError(
                {"size": _("This field is required for uploads.")},
                code="required",
            )
        if size > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            raise drf.exceptions.ValidationError(
                {"size": _("The file size is higher than the allowed max size.")},
                code="file_size_exceeded",
            )

        new_filename = request.data.get("filename")
        if new_filename:
            key = f"{item.key_base}/{new_filename}"
        else:
            # An editor still open on a file switched back to plaintext (by its owner
            # or a batch recovery) would write ciphertext over the plaintext, or to a
            # key nothing points to any more: its save must fail, visibly.
            if not item.is_encrypted:
                raise drf.exceptions.ValidationError(
                    {"item": _("This file is no longer encrypted.")},
                    code="item_not_encrypted",
                )
            key = item.file_key

        upload_url = utils.generate_upload_policy_for_key(
            key,
            size,
            content_type="application/octet-stream",
        )

        return drf.response.Response(
            {
                "upload_url": upload_url,
                "filename": new_filename or item.filename,
            },
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["patch"], url_path="encrypt")
    @transaction.atomic
    def encrypt(self, request, *args, **kwargs):
        """Encrypt an item (standalone file) or an item subtree (folder + all descendants)."""
        item = self.get_object()

        refusal = encryptable_item_refusal(item)
        if refusal:
            return drf.response.Response(
                {"detail": refusal}, status=drf.status.HTTP_400_BAD_REQUEST
            )

        serializer = serializers.EncryptItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        encrypted_key_per_user = serializer.validated_data["encrypted_symmetric_key_per_user"]
        encrypted_keys_for_descendants = serializer.validated_data["encrypted_keys_for_descendants"]
        # Per-user version map — required, must cover the same set
        # of user subs as the wrapped-key map. Stored alongside the
        # wrapped key so clients can later tell which key the file was
        # encrypted for (surfaced in the "key mismatch" panel when
        # decrypt fails on a rotated key).
        version_per_user = serializer.validated_data["encryption_public_key_version_per_user"]

        refusal = encryption_wraps_refusal(
            item, request.user, encrypted_key_per_user, version_per_user
        )
        if refusal:
            return drf.response.Response(refusal, status=drf.status.HTTP_400_BAD_REQUEST)

        # Effective scope = descendants minus inner encrypted subtrees.
        # Materialise into a list so subsequent operations (post-move
        # in the encrypt-on-move flow; here just defensive) don't
        # re-query against a possibly-stale path predicate.
        effective_descendants = list(compute_effective_descendants_for_encryption(item))

        # Validate descendant set: every effective descendant must be
        # covered by a wrapped key entry. Doubles as a mutation check —
        # if the subtree changed between frontend discovery and this
        # commit, the id sets won't match and we abort the whole op.
        live_descendant_ids = {str(d.pk) for d in effective_descendants}
        provided_descendant_ids = set(encrypted_keys_for_descendants.keys())
        if live_descendant_ids != provided_descendant_ids:
            return drf.response.Response(
                {
                    "detail": _("Folder contents changed during the operation. Please retry."),
                    "code": "subtree_mutated",
                    "missing": sorted(live_descendant_ids - provided_descendant_ids),
                    "extra": sorted(provided_descendant_ids - live_descendant_ids),
                },
                status=drf.status.HTTP_409_CONFLICT,
            )

        file_key_mapping = serializer.validated_data["file_key_mapping"]

        # Apply encryption to root + descendants. `root_chain_wrap=None`
        # because /encrypt/ produces a self-rooted item (per-user wraps
        # land below); chain mode is for /move/.
        old_s3_keys = write_subtree_encryption(
            item=item,
            root_chain_wrap=None,
            encrypted_keys_for_descendants=encrypted_keys_for_descendants,
            file_key_mapping=file_key_mapping,
            effective_descendants=effective_descendants,
        )
        # The copy is for the organization of the root's owner (its creator), but the
        # vault escrows a new key for the caller's: from an administrator encrypting
        # someone else's item it would be another organization's. Left empty, it is
        # backfilled for the creator by the next holder opening the tree.
        item.maintenance_wrapped_item_key = (
            serializer.validated_data["maintenance_key"]
            if item.creator_id is not None and item.creator_id == request.user.id
            else None
        )
        item.save(update_fields=["maintenance_wrapped_item_key"])

        # Per-user wraps sit on THIS item, the encryption root: /key-chain/
        # walks from the target item upward to the user's wrap, and expects
        # that entry point to be the root. They are stored apart from the
        # accesses, which keep granting roles as without encryption: a user
        # with a role inherited from an ancestor gets a wrap here without
        # any access row on this item, and a pending user (null wrap) gets
        # nothing stored at all.
        # Left over from a former encryption, a wrap would hide a pending user
        models.ItemEncryptionKeyWrap.objects.filter(item=item).delete()
        write_key_wraps(item, encrypted_key_per_user, version_per_user)

        schedule_s3_cleanup(old_s3_keys)

        return drf.response.Response(
            self.get_serializer(item).data,
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["patch"], url_path="remove-encryption")
    @transaction.atomic
    def remove_encryption(self, request, *args, **kwargs):
        """Remove encryption from an item or subtree.

        The frontend uploads decrypted file content to new S3 keys, then calls
        this endpoint with a file_key_mapping. The backend atomically swaps
        file_key_override and clears encryption fields. Old encrypted S3 objects
        are cleaned up after commit.
        """
        item = self.get_object()

        if not item.is_encrypted:
            return drf.response.Response(
                {"detail": _("Item is not encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # Only allow removing encryption from encryption roots
        if item.encrypted_symmetric_key is not None:
            return drf.response.Response(
                {
                    "detail": _(
                        "Encryption can only be removed from the encryption root, "
                        "not from items inside an encrypted subtree."
                    )
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # Stacked encryption: even if this item is its own encryption root,
        # we refuse to remove it while any ancestor is also encrypted.
        # Doing so would leave this subtree plaintext inside an outer
        # encrypted scope, and the ancestor check on /encrypt/ would then
        # prevent re-encrypting it — a dead-end state. The outer root has
        # to be decrypted first.
        if item.ancestors().filter(is_encrypted=True).exists():
            return drf.response.Response(
                {
                    "detail": _(
                        "This item is nested inside another encrypted subtree. "
                        "Remove encryption from the outer folder first."
                    )
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        serializer = serializers.RemoveEncryptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_key_mapping = serializer.validated_data["file_key_mapping"]

        # Stacked encryption: exclude inner encryption roots and their
        # subtrees from the removal scope. Those are independent encrypted
        # trees with their own per-user keys and must stay intact.
        effective_descendants_qs = compute_removal_scope(item)

        # Integrity check: keys must be provided for exactly the set of
        # encrypted FILES in the effective scope (plus the root if it's
        # a file and encrypted). Plaintext files don't need a mapping —
        # there's no ciphertext to replace. This matters when the root
        # still has is_encrypted=True but its effective descendants are
        # already plaintext (e.g. after an inner encrypted sub-root was
        # decrypted before this call — the root alone needs its flag
        # and ItemAccess keys cleared).
        live_file_ids = {
            str(pk)
            for pk in effective_descendants_qs.filter(
                type=models.ItemTypeChoices.FILE,
                is_encrypted=True,
            ).values_list("pk", flat=True)
        }
        if item.type == models.ItemTypeChoices.FILE and item.is_encrypted:
            live_file_ids.add(str(item.pk))
        provided_ids = set(file_key_mapping.keys())
        if live_file_ids != provided_ids:
            return drf.response.Response(
                {
                    "detail": _("Folder contents changed during the operation. Please retry."),
                    "code": "subtree_mutated",
                    "missing": sorted(live_file_ids - provided_ids),
                    "extra": sorted(provided_ids - live_file_ids),
                },
                status=drf.status.HTTP_409_CONFLICT,
            )

        old_s3_keys, file_items_to_scan = clear_subtree_encryption(
            item=item,
            file_key_mapping=file_key_mapping,
            effective_descendants=effective_descendants_qs,
        )

        # After DB commit: clean up old S3 objects and trigger malware scan
        # on newly decrypted files (the server can now inspect them)
        def _post_commit():
            s3_client = default_storage.connection.meta.client
            bucket = default_storage.bucket_name
            for old_key in old_s3_keys:
                try:
                    s3_client.delete_object(Bucket=bucket, Key=old_key)
                except ClientError:
                    logger.warning("Failed to delete old S3 key: %s", old_key)

            refresh_file_metadata(file_items_to_scan, file_key_mapping)
            for file_key, item_id in file_items_to_scan:
                malware_detection.analyse_file(file_key, item_id=item_id)

        transaction.on_commit(_post_commit)

        return drf.response.Response(
            self.get_serializer(item).data,
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["get"], url_path="key-chain")
    def key_chain(self, request, *args, **kwargs):
        """Return the decryption key chain from the user's access point down to this item.

        The response contains:
        - The user's encrypted entry-point key (their nearest ItemEncryptionKeyWrap)
        - The chain of wrapped keys from entry point down to the target item
        """
        item = self.get_object()

        if not item.is_encrypted:
            return drf.response.Response(
                {"detail": _("Item is not encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        # Walk up ancestors to find the user's access point (the item where they hold
        # a wrap of its key). `ancestors` is ordered shallowest
        # first (root of the tree) so we iterate deepest first to pick the
        # NEAREST ancestor carrying a wrapped key. This matters with stacked
        # encryption roots (e.g. T4 is an encrypted root and so is T4/sub):
        # for a file inside T4/sub, sub is the correct entry point, not T4.
        ancestors = list(item.ancestors().order_by("path"))
        candidate_items_deepest_first = [item] + list(reversed(ancestors))

        wraps_by_item_pk = {
            wrap.item_id: wrap
            for wrap in chain_key_wraps(item).filter(user=user).select_related("item")
        }
        # Two-pass walker: prefer entries on encryption-root items
        # (the canonical chain entry points — `is_encrypted=True AND
        # encrypted_symmetric_key IS NULL`). A hybrid item (chain
        # descendant that ALSO carries per-user wraps, e.g. a
        # self-rooted file demoted into a chain) is a
        # side-door for outsiders, NOT a chain entry. If a chain user
        # also happens to have a hybrid wrap on a descendant, we
        # still want them to enter at the root so chain operations
        # (move-rewrap, recursive walks) work — otherwise the chain
        # returned is empty and the frontend has nothing to walk.
        # Fall back to ANY non-null wrap (deepest first) only when no
        # root entry exists — that's the outsider case (B/C in the
        # demote-preserves-outsider-wrap scenario).
        user_wrap = None
        for candidate in candidate_items_deepest_first:
            wrap = wraps_by_item_pk.get(candidate.pk)
            if wrap and candidate.is_encrypted and candidate.encrypted_symmetric_key is None:
                user_wrap = wrap
                break
        if user_wrap is None:
            for candidate in candidate_items_deepest_first:
                if candidate.pk in wraps_by_item_pk:
                    user_wrap = wraps_by_item_pk[candidate.pk]
                    break

        if not user_wrap:
            # This means the user genuinely has no access to the item
            # (not pending — pending users are detected client-side via
            # `is_pending_encryption_for_user` on the Item serializer, so
            # the frontend skips this call entirely for them). 403 here
            # is a real "forbidden" and the global /403 redirect applies.
            return drf.response.Response(
                {"detail": _("No encryption key found for this user on this item chain.")},
                status=drf.status.HTTP_403_FORBIDDEN,
            )

        entry_point_item = user_wrap.item

        # Build the chain from entry point down to the target item
        chain = []
        if entry_point_item.pk != item.pk:
            # Get all items between entry point and target (exclusive of entry point)
            # These are descendants of entry_point that are ancestors of item (or item itself)
            entry_depth = len(entry_point_item.path)
            for ancestor in ancestors:
                if len(ancestor.path) > entry_depth:
                    chain.append(
                        {
                            "item_id": str(ancestor.pk),
                            "encrypted_symmetric_key": ancestor.encrypted_symmetric_key,
                        }
                    )
            # Add the target item itself
            chain.append(
                {
                    "item_id": str(item.pk),
                    "encrypted_symmetric_key": item.encrypted_symmetric_key,
                }
            )

        # Encryption tree root: the deepest encryption root that
        # contains this item — i.e. the nearest ancestor (or self) that
        # is encrypted with no chain wrap (`encrypted_symmetric_key IS
        # NULL`). Used by the frontend's cross-root check on moves:
        # `user_access_item_id` is unreliable for hybrid items (a
        # demoted self-rooted file keeps its OWN per-user wraps, so
        # the deepest-first walker picks the item
        # itself, not its tree root). `encryption_tree_root_item_id`
        # is stable: it ignores hybrid wraps and points at the actual
        # tree boundary.
        encryption_tree_root_pk = None
        for candidate in candidate_items_deepest_first:
            if candidate.is_encrypted and candidate.encrypted_symmetric_key is None:
                encryption_tree_root_pk = candidate.pk
                break

        return drf.response.Response(
            {
                "user_access_item_id": str(entry_point_item.pk),
                "encrypted_key_for_user": user_wrap.wrapped_key,
                # The version to decrypt with: the one of this wrap, which is not
                # always the item list's (that one is the user's latest wrap)
                "encryption_public_key_version": user_wrap.encryption_public_key_version,
                "encryption_tree_root_item_id": (
                    str(encryption_tree_root_pk) if encryption_tree_root_pk else None
                ),
                "item_creator_sub": item.creator.sub if item.creator else None,
                "maintenance_escrow": (
                    describe_maintenance_escrow(entry_point_item, user)
                    if entry_point_item.pk == encryption_tree_root_pk
                    else None
                ),
                "chain": chain,
            },
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["put"], url_path="encryption-key-wraps")
    @transaction.atomic
    def encryption_key_wraps(self, request, *args, **kwargs):
        """Accept a pending collaborator by wrapping this item's key for them.

        This is the "Accept" action: a member holding the key chain of this
        item wraps this item's key for a user who was given a role here or on
        an ancestor before completing their encryption onboarding. The item is
        the encryption root, or the item the user's access is on when lower,
        so the key opens only what they were given. It only gives the key to a
        pending user; to revoke it, remove the user's access.
        """
        item = self.get_object()

        if not item.is_encrypted:
            return drf.response.Response(
                {"detail": _("Item is not encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        serializer = serializers.AcceptEncryptionAccessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending_user = serializer.validated_data["user"]

        # Without a wrap on this item's key chain, the caller has no plaintext
        # key to have wrapped for the pending user.
        if not chain_key_wraps(item).filter(user=request.user).exists():
            return drf.response.Response(
                {
                    "detail": _(
                        "You do not currently hold a decryption key for this "
                        "item, so you cannot accept another user on it."
                    )
                },
                status=drf.status.HTTP_403_FORBIDDEN,
            )

        if not models.ItemAccess.objects.filter(
            item__path__ancestors=item.path, user=pending_user
        ).exists():
            return drf.response.Response(
                {
                    "detail": _("This user has no access to the item."),
                    "code": "user_without_access",
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        if chain_key_wraps(item).filter(user=pending_user).exists():
            return drf.response.Response(
                {
                    "detail": _(
                        "This user is not pending encryption onboarding. "
                        "Remove their access instead if you want to revoke it."
                    ),
                    "code": "access_not_pending",
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        models.ItemEncryptionKeyWrap.objects.create(
            item=item,
            user=pending_user,
            wrapped_key=serializer.validated_data["encrypted_item_symmetric_key_for_user"],
            encryption_public_key_version=serializer.validated_data[
                "encryption_public_key_version"
            ],
        )

        posthog_capture(
            "item_access_encryption_accepted",
            request.user,
            {"user_id": str(pending_user.id)},
            item=item,
        )

        return drf.response.Response(status=drf.status.HTTP_204_NO_CONTENT)

    @drf.decorators.action(detail=True, methods=["patch"], url_path="maintenance-key")
    def maintenance_key(self, request, *args, **kwargs):
        """Store a maintenance escrow copy on an encryption root, when it brings something.

        Accepted when the root has no copy (encrypted before the escrow was enabled,
        or before its owner's domain was covered: the frontend backfills it with an
        empty share), or when the stored copy names another maintenance key (the
        owner's organization moved to a new one). A copy for the key already stored
        is refused: it only differs by the randomness of its wrap.

        The backend cannot check that the copy is for the right key, nor that it
        wraps the root's key: the key list lives on the encryption service and only
        the custodians can open a copy. A forged header can therefore replace a good
        copy, but only by someone who can already edit the tree, so it corrupts the
        tree for them alone, outside the maintenance process.
        """
        item = self.get_object()

        if not item.is_encrypted or item.encrypted_symmetric_key is not None:
            return drf.response.Response(
                {"detail": _("Only an encryption root carries a maintenance escrow copy.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        serializer = serializers.MaintenanceKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_copy = serializer.validated_data["maintenance_key"]
        old_copy = item.maintenance_wrapped_item_key

        if old_copy:
            if serializers.maintenance_key_id(new_copy) == serializers.maintenance_key_id(old_copy):
                return drf.response.Response(
                    {
                        "detail": _("The root already carries a copy for this maintenance key."),
                        "code": "maintenance_key_already_stored",
                    },
                    status=drf.status.HTTP_409_CONFLICT,
                )
            # Filling an empty copy is a backfill any writer may run. Replacing one
            # could swap a copy the custodians can open for one they cannot: an owner
            # or an administrator only, and on the record.
            if item.get_role(request.user) not in PRIVILEGED_ROLES:
                raise drf.exceptions.PermissionDenied(
                    _("Only an owner or an administrator can replace a maintenance escrow copy.")
                )
            logger.warning(
                "Maintenance escrow copy of item %s replaced by user %s: key %s, was %s",
                item.pk,
                request.user.pk,
                serializers.maintenance_key_id(new_copy),
                serializers.maintenance_key_id(old_copy),
            )

        # `update_fields` keeps `updated_at` as it is: a copy is no edit of the item,
        # and the batch import compares `updated_at` with the export's.
        item.maintenance_wrapped_item_key = new_copy
        item.save(update_fields=["maintenance_wrapped_item_key"])

        return drf.response.Response(status=drf.status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=serializers.BatchShareSerializer,
        responses={
            200: inline_serializer(
                name="BatchShareResponse",
                fields={
                    "accesses_created": drf.serializers.IntegerField(),
                    "invitations_created": drf.serializers.IntegerField(),
                    "skipped": drf.serializers.ListField(child=drf.serializers.DictField()),
                },
            )
        },
    )
    @drf.decorators.action(detail=True, methods=["post"], url_path="batch-share")
    def batch_share(self, request, *args, **kwargs):
        """
        Share an item with a list of contacts in a single request.

        Emails matching an existing user get an access, unknown emails get an
        invitation. All rows are validated before any database write so a
        rejected batch never creates a partial share state.
        """
        if not settings.ALLOW_SHARE_IMPORT_FILE:
            raise drf.exceptions.PermissionDenied(
                "Batch sharing from an imported file is not enabled."
            )

        item = self.get_object()

        serializer = serializers.BatchShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Deduplicate rows by email, keeping the first occurrence
        rows = {}
        for row in serializer.validated_data["rows"]:
            rows.setdefault(row["email"], row["role"])

        # A user cannot grant a role higher than their own. This also enforces
        # that only owners can assign the owner role.
        user_role_priority = models.RoleChoices.get_priority(item.get_role(request.user))
        for role in rows.values():
            if models.RoleChoices.get_priority(role) > user_role_priority:
                raise drf.exceptions.PermissionDenied(
                    f"You cannot grant the role {role} which is higher than your own role."
                )

        created_accesses, created_invitations, skipped = batch_share_process_rows(
            item, request.user, rows
        )

        for email, role in created_accesses + created_invitations:
            item.send_invitation_email(
                email,
                role,
                request.user,
                request.user.language or settings.LANGUAGE_CODE,
            )

        posthog_capture(
            "item_batch_share",
            request.user,
            {
                "accesses_created": len(created_accesses),
                "invitations_created": len(created_invitations),
                "skipped": len(skipped),
            },
            item=item,
        )

        return drf.response.Response(
            {
                "accesses_created": len(created_accesses),
                "invitations_created": len(created_invitations),
                "skipped": skipped,
            },
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["post", "delete"], url_path="favorite")
    def favorite(self, request, *args, **kwargs):
        """
        Mark or unmark the item as a favorite for the logged-in user based on the HTTP method.
        """
        # Check permissions first
        item = self.get_object()
        user = request.user

        if request.method == "POST":
            # Try to mark as favorite
            try:
                models.ItemFavorite.objects.create(item=item, user=user)
            except ValidationError:
                return drf.response.Response(
                    {"detail": "item already marked as favorite"},
                    status=drf.status.HTTP_200_OK,
                )

            posthog_capture("item_favorited", user, {}, item=item)

            # At this point the annotation is_favorite is already made by the
            # queryset.annotate_is_favorite(user) and its value is False.
            # If we want a fresh data we have to make a new queryset, apply the annotation
            # and get the item again.
            # To avoid all of this we directly set item.is_favorite to True.
            item.is_favorite = True
            serializer = self.get_serializer(item)
            return drf.response.Response(serializer.data, status=drf.status.HTTP_201_CREATED)

        # Handle DELETE method to unmark as favorite
        deleted, _ = models.ItemFavorite.objects.filter(item=item, user=user).delete()
        if deleted:
            # At this point the annotation is_favorite is already made by the
            # queryset.annotate_is_favorite(user) and its value is True.
            # If we want a fresh data we have to make a new queryset, apply the annotation
            # and get the item again.
            # To avoid all of this we directly set item.is_favorite to False.
            posthog_capture("item_unfavorited", user, {}, item=item)
            item.is_favorite = False
            serializer = self.get_serializer(item)
            return drf.response.Response(serializer.data, status=drf.status.HTTP_200_OK)
        return drf.response.Response(
            {"detail": "item was already not marked as favorite"},
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["post", "delete"], url_path="restrict")
    def restrict(self, request, *args, **kwargs):
        """Activate or deactivate restriction on the folder based on the HTTP method."""
        item = self.get_object()

        if request.method == "POST":
            item = item.restrict(request.user)
        else:
            item = item.unrestrict()

        serializer = self.get_serializer(item)
        return drf.response.Response(serializer.data, status=drf.status.HTTP_200_OK)

    def _authorize_subrequest(self, request, pattern):
        """
        Shared method to authorize access based on the original URL of an Nginx subrequest
        and user permissions. Returns a dictionary of URL parameters if authorized.

        The original url is passed by nginx in the "HTTP_X_ORIGINAL_URL" header.
        See corresponding ingress configuration in Helm chart and read about the
        nginx.ingress.kubernetes.io/auth-url annotation to understand how the Nginx ingress
        is configured to do this.

        Based on the original url and the logged in user, we must decide if we authorize Nginx
        to let this request go through (by returning a 200 code) or if we block it (by returning
        a 403 error). Note that we return 403 errors without any further details for security
        reasons.

        Parameters:
        - pattern: The regex pattern to extract identifiers from the URL.

        Returns:
        - A dictionary of URL parameters if the request is authorized.
        Raises:
        - PermissionDenied if authorization fails.
        """
        # Extract the original URL from the request header
        original_url = request.META.get("HTTP_X_ORIGINAL_URL")
        if not original_url:
            logger.debug("Missing HTTP_X_ORIGINAL_URL header in subrequest")
            raise drf.exceptions.PermissionDenied()

        parsed_url = urlparse(original_url)
        match = pattern.search(unquote(parsed_url.path))

        # If the path does not match the pattern, try to extract the parameters from the query
        if not match:
            match = pattern.search(unquote(parsed_url.query))

        if not match:
            logger.debug(
                "Subrequest URL '%s' did not match pattern '%s'",
                parsed_url.path,
                pattern,
            )
            raise drf.exceptions.PermissionDenied()

        try:
            url_params = match.groupdict()
        except (ValueError, AttributeError) as exc:
            logger.debug("Failed to extract parameters from subrequest URL: %s", exc)
            raise drf.exceptions.PermissionDenied() from exc

        pk = url_params.get("pk")
        if not pk:
            logger.debug("item ID (pk) not found in URL parameters: %s", url_params)
            raise drf.exceptions.PermissionDenied()

        # Fetch the item and check if the user has access
        queryset = models.Item.objects.all()
        queryset = self._filter_suspicious_items(queryset, request.user)
        try:
            item = queryset.get(pk=pk)
        except models.Item.DoesNotExist as exc:
            logger.debug("item with ID '%s' does not exist", pk)
            raise drf.exceptions.PermissionDenied() from exc

        user_abilities = item.get_abilities(request.user)

        if not user_abilities.get(self.action, False):
            logger.debug("User '%s' lacks permission for item '%s'", request.user.id, pk)
            raise drf.exceptions.PermissionDenied()

        logger.debug("Subrequest authorization successful. Extracted parameters: %s", url_params)
        return url_params, user_abilities, request.user.id, item

    @drf.decorators.action(detail=True, methods=["get"], url_path="download")
    def download(self, request, *args, **kwargs):
        """
        Permalink endpoint for downloading an item's file.

        Returns a redirect to the current media URL for the item, so this link
        remains valid even after the item is renamed. Authentication is still
        enforced by the existing media-auth mechanism on the redirected URL.
        """
        item = self.get_object()

        if item.type != models.ItemTypeChoices.FILE:
            raise drf.exceptions.PermissionDenied()

        if item.upload_state == models.ItemUploadStateChoices.PENDING:
            raise drf.exceptions.PermissionDenied()

        redirect_url = f"{settings.MEDIA_BASE_URL}{settings.MEDIA_URL}{quote(item.file_key)}"
        return drf.response.Response(
            status=status.HTTP_302_FOUND,
            headers={"Location": redirect_url},
        )

    @drf.decorators.action(detail=True, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):
        """
        Stream a recursive ZIP archive of a folder's content.
        """
        folder = self.get_object()

        descendants = export_descendants(folder)
        zip_stream = build_zip_stream(descendants)

        posthog_capture("item_exported", request.user, {}, item=folder)

        encoded_name = quote(f"{folder.title}.zip", safe="")
        return StreamingHttpResponse(
            zip_stream,
            content_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
        )

    @drf.decorators.action(detail=False, methods=["get"], url_path="media-auth")
    def media_auth(self, request, *args, **kwargs):
        """
        This view is used by an Nginx subrequest to control access to an item's
        attachment file.

        When we let the request go through, we compute authorization headers that will be added to
        the request going through thanks to the nginx.ingress.kubernetes.io/auth-response-headers
        annotation. The request will then be proxied to the object storage backend who will
        respond with the file after checking the signature included in headers.
        """
        url_params, _, _, item = self._authorize_subrequest(request, MEDIA_STORAGE_URL_PATTERN)
        if item.type != models.ItemTypeChoices.FILE:
            logger.debug("Item '%s' is not a file", item.id)
            raise drf.exceptions.PermissionDenied()

        if item.upload_state == models.ItemUploadStateChoices.PENDING:
            logger.debug("Item '%s' is not ready", item.id)
            raise drf.exceptions.PermissionDenied()

        if url_params.get("preview") and not utils.is_previewable_item(item):
            logger.debug("Item '%s' is not previewable", item.id)
            raise drf.exceptions.PermissionDenied()

        # Generate S3 authorization headers using the extracted URL parameters
        request = utils.generate_s3_authorization_headers(f"{url_params.get('key'):s}")

        return drf.response.Response("authorized", headers=request.headers, status=200)

    @drf.decorators.action(detail=True, methods=["get"], url_path="wopi")
    def wopi(self, request, *args, **kwargs):
        """
        This view is used to generate an access token and access token ttl in order to start
        a WOPI session for the item and the current user.
        """
        item = self.get_object()

        if not (wopi_client := get_wopi_client_config(item, request.user)):
            raise drf.exceptions.ValidationError(
                {"detail": "This item does not suport WOPI integration."}
            )

        service = access_service.AccessUserItemService()
        access_token, access_token_ttl = service.insert_new_access(item, request.user)

        get_file_info = reverse("files-detail", kwargs={"pk": item.id})
        language = (
            request.user.language
            if request.user.is_authenticated and request.user.language
            else settings.LANGUAGE_CODE
        )
        launch_url = compute_wopi_launch_url(wopi_client.get("launch_url"), get_file_info, language)

        return drf.response.Response(
            {
                "access_token": access_token,
                "access_token_ttl": access_token_ttl,
                "launch_url": launch_url,
            },
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(
        detail=True,
        methods=["post"],
        url_path="duplicate",
    )
    def duplicate(self, request, *args, **kwargs):
        """
        Duplicate an item of type File. The item is duplicated in the folder where the original
        item is.
        The user who duplicates becomes the creator of the duplicate
        """

        item_to_duplicate = self.get_object()
        user = request.user

        # The duplicator becomes the creator of a new sized file: gate it like an
        # upload so an over-quota user cannot grow their storage usage.
        can_upload = get_entitlements_backend().can_upload(user)
        if not can_upload["result"]:
            raise drf.exceptions.PermissionDenied(
                detail=can_upload.get("message", "You do not have permission to upload files."),
                code=can_upload.get("reason"),
            )

        parent = item_to_duplicate.parent() if item_to_duplicate.depth > 1 else None

        if parent and parent.get_role(user) == models.RoleChoices.READER:
            # If the user as reader role on the parent folder, then the duplicated
            # item must be created at the user's root
            parent = None
        with transaction.atomic():
            duplicated_item = models.Item.objects.create_child(
                creator=user,
                link_reach=None if parent else LinkReachChoices.RESTRICTED,
                parent=parent,
                title=capfirst(
                    _("copy of {title}").format(title=item_to_duplicate.title)
                ),  # Title uniqueness is managed in the create_child method
                type=models.ItemTypeChoices.FILE,
                size=item_to_duplicate.size,
                upload_state=models.ItemUploadStateChoices.DUPLICATING,
                mimetype=item_to_duplicate.mimetype,
                filename=item_to_duplicate.filename,
                description=item_to_duplicate.description,
            )

            if duplicated_item.is_root:
                models.ItemAccess.objects.create(
                    item=duplicated_item,
                    user=user,
                    role=models.RoleChoices.OWNER,
                )

        # Then duplicate the file in async way
        duplicate_file.delay(
            item_to_duplicate_id=item_to_duplicate.id,
            duplicated_item_id=duplicated_item.id,
        )

        posthog_capture("item_duplicate", user, {}, item=duplicated_item)

        serializer = self.get_serializer(duplicated_item)
        return drf.response.Response(serializer.data, status=drf.status.HTTP_201_CREATED)


# Declare the schema statically because `get_serializer_class` depends on
# `self.item`, which reads `self.kwargs["resource_id"]` — unavailable during
# drf-spectacular introspection. Without this, spectacular fails to resolve
# the serializer and drops the requestBody for POST/PUT/PATCH operations.
@extend_schema(
    request=serializers.ItemAccessSerializer,
    responses=serializers.ItemAccessSerializer,
)
@extend_schema_view(
    list=extend_schema(responses=serializers.ItemAccessSerializer(many=True)),
)
class ItemAccessViewSet(
    drf.mixins.CreateModelMixin,
    drf.mixins.DestroyModelMixin,
    drf.mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API ViewSet for all interactions with item accesses.

    GET /api/v1.0/items/<resource_id>/accesses/:<item_access_id>
        Return list of all item accesses related to the logged-in user or one
        item access if an id is provided.

    POST /api/v1.0/items/<resource_id>/accesses/ with expected data:
        - user: str
        - role: str [administrator|editor|reader]
        Return newly created item access

    PUT /api/v1.0/items/<resource_id>/accesses/<item_access_id>/ with expected data:
        - role: str [owner|admin|editor|reader]
        Return updated item access

    PATCH /api/v1.0/items/<resource_id>/accesses/<item_access_id>/ with expected data:
        - role: str [owner|admin|editor|reader]
        Return partially updated item access

    DELETE /api/v1.0/items/<resource_id>/accesses/<item_access_id>/
        Delete targeted item access
    """

    lookup_field = "pk"
    # Forcing to None makes sure the OpenApi schema does not infer that the
    # list endpoint supports pagination.
    pagination_class = None
    permission_classes = [permissions.ItemAccessPermission]
    queryset = models.ItemAccess.objects.select_related("user", "item").all()
    resource_field_name = "item"
    serializer_class = serializers.ItemAccessSerializer

    @cached_property
    def item(self):
        """Get related item from resource ID in url and annotate user roles."""
        try:
            return models.Item.objects.annotate_user_roles(self.request.user).get(
                pk=self.kwargs["resource_id"]
            )
        except models.Item.DoesNotExist as excpt:
            raise drf.exceptions.NotFound() from excpt

    def get_serializer_class(self):
        """Use light serializer for unprivileged users."""
        return (
            serializers.ItemAccessSerializer
            if self.item.get_role(self.request.user) in PRIVILEGED_ROLES
            else serializers.ItemAccessLightSerializer
        )

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        context = super().get_serializer_context()
        context["resource_id"] = self.kwargs["resource_id"]
        context["item"] = self.item
        return context

    def filter_queryset(self, queryset):
        """Override to filter on related resource."""
        queryset = super().filter_queryset(queryset)
        return queryset.filter(**{self.resource_field_name: self.kwargs["resource_id"]})

    def list(self, request, *args, **kwargs):
        """
        List item accesses for an item and its ancestors.

        Returns the deepest access per target (user/team) with computed max_ancestors_role.
        For inherited accesses (not on current item), max_ancestors_role equals the access's role.

        Non-privileged users only see privileged roles to prevent information leakage.
        Results are ordered by item depth and creation date.
        """
        user = request.user
        role = self.item.get_role(user)
        if not role:
            return drf.response.Response([])

        # Get all accesses from ancestors (including current item)
        ancestors_qs = models.Item.objects.filter(
            path__ancestors=self.item.path, ancestors_deleted_at__isnull=True
        )
        accesses_qs = self.get_queryset().filter(item__in=ancestors_qs)
        if role not in PRIVILEGED_ROLES:
            accesses_qs = accesses_qs.filter(role__in=PRIVILEGED_ROLES)

        accesses_qs = accesses_qs.annotate_user_roles(user).order_by("item__path", "created_at")

        # Track max role and keep only deepest access per target
        max_role_by_target = {}
        deepest_access_by_target = {}

        for access in accesses_qs.iterator():
            target = access.target_key
            previous = max_role_by_target.get(target)
            previous_role = previous["role"] if previous else None

            # Set max_ancestors_role from previous accesses in hierarchy
            access.max_ancestors_role = previous_role
            access.max_ancestors_role_item_id = previous["item_id"] if previous else None

            max_role_by_target[target] = {
                "role": models.RoleChoices.max(previous_role, access.role),
                "item_id": access.item_id,
            }
            deepest_access_by_target[target] = access

        for access in deepest_access_by_target.values():
            # In case of inherited accesses, the max ancestors role and the max ancestors
            # item id should be the access itself because it is the one should go to update.
            if access.item.depth < self.item.depth:
                access.max_ancestors_role = access.role
                access.max_ancestors_role_item_id = access.item_id

        # Sort by depth and creation date, then serialize
        selected_accesses = sorted(
            deepest_access_by_target.values(),
            key=lambda a: (a.item.depth, a.created_at),
        )

        context = self.get_serializer_context()
        if self.item.is_encrypted:
            context["key_holder_ids"] = set(
                chain_key_wraps(self.item).values_list("user_id", flat=True)
            )
        serializer = self.get_serializer_class()(selected_accesses, many=True, context=context)
        return drf.response.Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        We not use the update mixin to apply a specific behavior we can't implement using
        perform_update method.

        If the role is updated and is the same role as the max ancestors role,
        we don't want to have two consecutive explicit accesses with the same role.
        We have to delete the current access, this item will have an inherited access
        with the correct role.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        old_role = instance.role
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data.get("role")

        # Check if the role is being updated and the new role is not "owner"
        if role and role != models.RoleChoices.OWNER:
            # Check if the access being updated is the last owner access for the resource
            if (
                self.item.is_root
                and instance.role == models.RoleChoices.OWNER
                and self.item.accesses.filter(role=models.RoleChoices.OWNER).count() == 1
            ):
                message = "Cannot change the role to a non-owner role for the last owner access."
                raise drf.exceptions.PermissionDenied({"detail": message})

        if role and instance.max_ancestors_role == role:
            # The submitted role is the same as the max ancestors role,
            # We don't want to have two consecutive explicit accesses with the same role.
            # We have to delete the current access, this item will have an inherited access
            # with the correct role.
            instance.delete()
            return drf.response.Response(status=drf.status.HTTP_204_NO_CONTENT)

        access = serializer.save()

        synchronize_descendants_accesses(self.item, access)

        if access.role != old_role:
            posthog_capture(
                "item_access_updated",
                request.user,
                {
                    "id": access.id,
                    "role": access.role,
                    "old_role": old_role,
                },
                item=access.item,
            )

        return drf.response.Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Partial update the item access."""
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Actually create the new item access:
        - Ensures the `item_id` is explicitly set from the URL
        - If the assigned role is `OWNER`, checks that the requesting user is an owner
          of the item. This is the only permission check deferred until this step;
          all other access checks are handled earlier in the permission lifecycle.
        - Sends an invitation email to the newly added user after saving the access.
        """
        role = serializer.validated_data.get("role")
        if (
            role == models.RoleChoices.OWNER
            and self.item.get_role(self.request.user) != models.RoleChoices.OWNER
        ):
            raise drf.exceptions.PermissionDenied(
                "Only owners of an item can assign other users as owners."
            )

        # Look for the max ancestors role of the item for the current user.
        ancestor_qs = (self.item.ancestors() | models.Item.objects.filter(pk=self.item.pk)).filter(
            ancestors_deleted_at__isnull=True
        )
        ancestors_roles = models.ItemAccess.objects.filter(
            item__in=ancestor_qs, user=serializer.validated_data.get("user")
        ).values_list("role", flat=True)
        max_ancestors_role = models.RoleChoices.max(*ancestors_roles)

        if models.RoleChoices.get_priority(max_ancestors_role) >= models.RoleChoices.get_priority(
            role
        ):
            raise drf.exceptions.ValidationError(
                {
                    "role": (
                        f"The role {role} you are trying to assign is lower or equal"
                        f" than the max ancestors role {max_ancestors_role}."
                    ),
                }
            )

        # Handle encryption: the key the access gives, wrapped for the user,
        # is stored apart from the access.
        #
        # For encrypted items the key is optional: if the invitee has no
        # public key yet (still pending their encryption onboarding) the
        # caller legitimately has nothing to wrap. The user is then pending
        # and can be "accepted" later via PUT /items/{id}/encryption-key-wraps/
        # once they have onboarded. Whether the invitee actually has a public
        # key is a client-side concern — the backend only enforces "key
        # provided ⇒ item must be encrypted".
        encrypted_key = serializer.validated_data.pop("encrypted_item_symmetric_key_for_user", None)
        key_version = serializer.validated_data.pop("encryption_public_key_version", None)
        if encrypted_key and not self.item.is_encrypted:
            raise drf.exceptions.ValidationError(
                {
                    "encrypted_item_symmetric_key_for_user": _(
                        "This field can only be provided when the item is encrypted."
                    )
                }
            )

        # Block team-based access for encrypted items
        if self.item.is_encrypted and serializer.validated_data.get("team"):
            raise drf.exceptions.ValidationError(
                {"team": _("Team-based access is not supported for encrypted items.")}
            )

        access = serializer.save(item_id=self.kwargs["resource_id"])
        if encrypted_key and access.user:
            write_key_wraps(
                access.item, {access.user.sub: encrypted_key}, {access.user.sub: key_version}
            )
        synchronize_descendants_accesses(self.item, access)
        if access.user:
            access.item.send_invitation_email(
                access.user.email,
                access.role,
                self.request.user,
                self.request.user.language or settings.LANGUAGE_CODE,
            )

        posthog_capture(
            "item_access_created",
            self.request.user,
            {
                "id": access.id,
                "role": access.role,
            },
            item=access.item,
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        """Delete the item access, with the keys it gave, and capture the event."""
        access_id = instance.id
        item = instance.item
        role = instance.role
        super().perform_destroy(instance)
        # Refused when it would leave the subtree undecryptable by anyone:
        # the last user holding its key gone while pending users remain.
        prune_key_wraps_or_refuse(item)
        posthog_capture(
            "item_access_deleted",
            self.request.user,
            {
                "id": access_id,
                "role": role,
            },
            item=item,
        )


class InvitationViewset(
    drf.mixins.CreateModelMixin,
    drf.mixins.ListModelMixin,
    drf.mixins.RetrieveModelMixin,
    drf.mixins.DestroyModelMixin,
    drf.mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """API ViewSet for user invitations to item.

    GET /api/v1.0/items/<item_id>/invitations/:<invitation_id>/
        Return list of invitations related to that item or one
        item access if an id is provided.

    POST /api/v1.0/items/<item_id>/invitations/ with expected data:
        - email: str
        - role: str [administrator|editor|reader]
        Return newly created invitation (issuer and item are automatically set)

    PATCH /api/v1.0/items/<item_id>/invitations/:<invitation_id>/ with expected data:
        - role: str [owner|admin|editor|reader]
        Return partially updated item invitation

    DELETE  /api/v1.0/items/<item_id>/invitations/<invitation_id>/
        Delete targeted invitation
    """

    lookup_field = "id"
    pagination_class = Pagination
    permission_classes = [permissions.InvitationPermission]
    queryset = models.Invitation.objects.all().select_related("item").order_by("-created_at")
    serializer_class = serializers.InvitationSerializer
    resource_field_name = "item"

    @cached_property
    def item(self) -> models.Item:
        """Get related item from resource ID in url and annotate user roles."""
        try:
            return models.Item.objects.annotate_user_roles(self.request.user).get(
                pk=self.kwargs["resource_id"]
            )
        except models.Item.DoesNotExist as excpt:
            raise drf.exceptions.NotFound() from excpt

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        context = super().get_serializer_context()
        context["resource_id"] = self.kwargs["resource_id"]
        return context

    def get_queryset(self):
        """Return the queryset according to the action."""
        queryset = super().get_queryset()
        queryset = queryset.filter(item=self.kwargs["resource_id"])

        user = self.request.user

        queryset = queryset.annotate_user_roles(user)

        if self.action == "list":
            if self.item.get_role(user) not in PRIVILEGED_ROLES:
                return queryset.none()

        return queryset

    def _validate_provided_role(self, validated_role):
        """Ensure that the validated_role can be used."""

        if (
            validated_role == models.RoleChoices.OWNER
            and self.item.get_role(self.request.user) != models.RoleChoices.OWNER
        ):
            raise drf.serializers.ValidationError(
                "Only owners of an item can invite other users as owners.",
                code="invitation_role_owner_limited_to_owners",
            )

    def perform_create(self, serializer):
        """Save invitation to an item then send an email to the invited user."""
        # On an encrypted item the invitee signs up without a key: their
        # invitation becomes a pending access, accepted once they have enabled
        # encryption.
        self._validate_provided_role(serializer.validated_data.get("role"))
        invitation = serializer.save()

        invitation.item.send_invitation_email(
            invitation.email,
            invitation.role,
            self.request.user,
            self.request.user.language or settings.LANGUAGE_CODE,
        )

        posthog_capture(
            "item_invitation_created",
            self.request.user,
            {
                "id": invitation.id,
                "role": invitation.role,
            },
            item=invitation.item,
        )

    def perform_update(self, serializer):
        """Update the invitation and capture the event."""
        self._validate_provided_role(serializer.validated_data.get("role"))

        old_role = serializer.instance.role
        super().perform_update(serializer)

        if serializer.instance.role != old_role:
            posthog_capture(
                "item_invitation_updated",
                self.request.user,
                {
                    "id": serializer.instance.id,
                    "role": serializer.instance.role,
                    "old_role": old_role,
                },
                item=serializer.instance.item,
            )

    def perform_destroy(self, instance):
        """Delete the invitation and capture the event."""
        invitation_id = instance.id
        item = instance.item
        role = instance.role
        super().perform_destroy(instance)

        posthog_capture(
            "item_invitation_deleted",
            self.request.user,
            {
                "id": invitation_id,
                "role": role,
            },
            item=item,
        )


class ReconciliationConfirmView(drf.views.APIView):
    """API endpoint to confirm user reconciliation emails.

    GET /user-reconciliations/{user_type}/{confirmation_id}/
    Marks `active_email_checked` or `inactive_email_checked` to True.
    """

    permission_classes = [AllowAny]

    def get(self, request, user_type, confirmation_id):
        """Check the confirmation ID and mark the corresponding email as checked."""
        try:
            # validate UUID
            uuid_obj = uuid.UUID(str(confirmation_id))
        except ValueError:
            return drf_response.Response(
                {"detail": "Badly formatted confirmation id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_type not in ("active", "inactive"):
            return drf_response.Response(
                {"detail": "Invalid user_type"}, status=status.HTTP_400_BAD_REQUEST
            )

        lookup = (
            {"active_email_confirmation_id": uuid_obj}
            if user_type == "active"
            else {"inactive_email_confirmation_id": uuid_obj}
        )

        try:
            reconciliation = models.UserReconciliation.objects.get(**lookup)
        except models.UserReconciliation.DoesNotExist:
            return drf_response.Response(
                {"detail": "Reconciliation entry not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        field_name = "active_email_checked" if user_type == "active" else "inactive_email_checked"
        if not getattr(reconciliation, field_name):
            setattr(reconciliation, field_name, True)
            reconciliation.save()

        return drf_response.Response({"detail": "Confirmation received"})


class ConfigView(drf.views.APIView):
    """API ViewSet for sharing some public settings."""

    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /api/v1.0/config/
            Return a dictionary of public settings.
        """
        array_settings = [
            "ALLOW_SHARE_IMPORT_FILE",
            "AWS_S3_UPLOAD_ACL",
            "CRISP_WEBSITE_ID",
            "DATA_UPLOAD_MAX_MEMORY_SIZE",
            "ENCRYPTION_FEATURE_ENABLED",
            "ENCRYPTION_INTERFACE_URL",
            "ENCRYPTION_VAULT_URL",
            "ENVIRONMENT",
            "FRONTEND_THEME",
            "FRONTEND_MORE_LINK",
            "FRONTEND_FEEDBACK_BUTTON_SHOW",
            "FRONTEND_FEEDBACK_BUTTON_IDLE",
            "FRONTEND_FEEDBACK_ITEMS",
            "FRONTEND_FEEDBACK_MESSAGES_WIDGET_ENABLED",
            "FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL",
            "FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL",
            "FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH",
            "FRONTEND_HELP_MENU_CONFIG",
            "FRONTEND_HIDE_GAUFRE",
            "FRONTEND_SILENT_LOGIN_ENABLED",
            "FRONTEND_EXTERNAL_HOME_URL",
            "FRONTEND_RELEASE_NOTE_ENABLED",
            "FRONTEND_ENTITLEMENTS_DISCLAIMERS",
            "FRONTEND_STORAGE_GAUGE_INFORMATION_LINK",
            "FRONTEND_CSS_URL",
            "FRONTEND_JS_URL",
            "MEDIA_BASE_URL",
            "POSTHOG_KEY",
            "POSTHOG_HOST",
            "LANGUAGES",
            "LANGUAGE_CODE",
            "SDK_ENABLED",
            "SENTRY_DSN",
        ]
        dict_settings = {}
        for setting in array_settings:
            if hasattr(settings, setting):
                dict_settings[setting] = getattr(settings, setting)

        dict_settings["theme_customization"] = self._load_theme_customization()

        return drf.response.Response(dict_settings)

    def _load_theme_customization(self):
        if not settings.THEME_CUSTOMIZATION_FILE_PATH:
            return {}

        cache_key = f"theme_customization_{slugify(settings.THEME_CUSTOMIZATION_FILE_PATH)}"
        theme_customization = cache.get(cache_key, {})
        if theme_customization:
            return theme_customization

        try:
            with open(settings.THEME_CUSTOMIZATION_FILE_PATH, "r", encoding="utf-8") as f:
                theme_customization = json.load(f)
        except FileNotFoundError:
            logger.error(
                "Configuration file not found: %s",
                settings.THEME_CUSTOMIZATION_FILE_PATH,
            )
        except json.JSONDecodeError:
            logger.error(
                "Configuration file is not a valid JSON: %s",
                settings.THEME_CUSTOMIZATION_FILE_PATH,
            )
        else:
            cache.set(
                cache_key,
                theme_customization,
                settings.THEME_CUSTOMIZATION_CACHE_TIMEOUT,
            )

        return theme_customization


class SDKRelayEventViewset(drf.viewsets.ViewSet):
    """API View for SDK relay interactions."""

    permission_classes = [AllowAny]

    throttle_scope = "sdk_event_relay"

    def initial(self, request, *args, **kwargs):
        """Hide the whole relay when the SDK is disabled."""
        if not settings.SDK_ENABLED:
            raise drf.exceptions.NotFound()
        super().initial(request, *args, **kwargs)

    def get_permissions(self):
        """
        Return the list of permissions that this view requires.
        """
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def handle_cors(self, request, response):
        """Handle CORS preflight requests."""
        # Same approach as here:
        # https://github.com/adamchainz/django-cors-headers/blob/b04460f37cbf458984bb377d8e6afb56776c3465/src/corsheaders/middleware.py#L96
        origin = request.headers.get("origin")
        if origin and origin in settings.SDK_CORS_ALLOWED_ORIGINS:
            response[ACCESS_CONTROL_ALLOW_ORIGIN] = origin
            response[ACCESS_CONTROL_ALLOW_METHODS] = "GET, OPTIONS"

    def retrieve(self, request, pk=None):
        """
        GET /api/v1.0/sdk-relay/events/<token>/
        """
        sdk_relay = SDKRelayManager()
        event = sdk_relay.get_event(pk)

        response = drf.response.Response(event)
        self.handle_cors(request, response)
        return response

    def create(self, request):
        """
        POST /api/v1.0/sdk-relay/events/
        """
        serializer = serializers.SDKRelayEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sdk_relay = SDKRelayManager()
        sdk_relay.register_event(
            serializer.validated_data.get("token"),
            serializer.validated_data.get("event"),
        )
        return drf.response.Response(status=status.HTTP_201_CREATED)

    def options(self, request, *args, **kwargs):
        """
        OPTIONS /api/v1.0/sdk-relay/events/<token>/
        Handle CORS preflight requests.
        """
        response = drf.response.Response(status=status.HTTP_200_OK)
        self.handle_cors(request, response)
        return response


class UsageMetricViewset(drf.mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Viewset for usage metrics.
    """

    permission_classes = [HasAPIKey]
    queryset = models.User.objects.all().filter(is_active=True)
    serializer_class = serializers.UserUsageMetricSerializer
    pagination_class = Pagination

    def get_queryset(self):
        """Return the queryset filtered through `UsageMetricFilter`."""
        filterset = UsageMetricFilter(
            self.request.GET, queryset=self.queryset, request=self.request
        )
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        return filterset.filter_queryset(self.queryset)

    def list(self, request, *args, **kwargs):
        """Handle listing with account_type branching."""
        account_type = request.query_params.get("account_type", UsageMetricAccountTypeChoices.USER)

        if account_type == UsageMetricAccountTypeChoices.ORGANIZATION:
            return self._list_organization(request)

        return super().list(request, *args, **kwargs)

    def _list_organization(self, request):
        """Aggregate storage metrics across users of an organization."""
        base_qs = models.User.objects.filter(is_active=True)
        filterset = OrganizationUsageMetricFilter(request.GET, queryset=base_qs, request=request)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        users = filterset.filter_queryset(base_qs)

        serializer = serializers.OrganizationUsageMetricSerializer(
            {
                "account_id_key": filterset.form.cleaned_data["account_id_key"],
                "account_id_value": filterset.form.cleaned_data["account_id_value"],
                "users": users,
            }
        )

        return drf.response.Response(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [serializer.data],
            }
        )


class EntitlementsViewset(viewsets.ViewSet):
    """API View for handling entitlements."""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1.0/entitlements/
        """
        entitlements_backend = get_entitlements_backend()
        entitlements = {}
        for method_name in dir(entitlements_backend):
            if method_name.startswith("can_"):
                method = getattr(entitlements_backend, method_name)
                if callable(method):
                    entitlements[method_name] = method(request.user)
        if quota := entitlements_backend.get_quota(request.user):
            entitlements["quota"] = quota
        entitlements["context"] = entitlements_backend.get_context(request.user)
        return drf.response.Response(entitlements)
