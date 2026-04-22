"""API endpoints"""
# pylint: disable=too-many-lines

import json
import logging
import os
import re
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
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

import rest_framework as drf
from botocore.exceptions import ClientError
from corsheaders.middleware import (
    ACCESS_CONTROL_ALLOW_METHODS,
    ACCESS_CONTROL_ALLOW_ORIGIN,
)
from lasuite.drf.models.choices import (
    PRIVILEGED_ROLES,
    LinkReachChoices,
    get_equivalent_link_definition,
)
from lasuite.malware_detection import malware_detection
from lasuite.oidc_login.decorators import refresh_oidc_access_token
from rest_framework import filters, status, viewsets
from rest_framework import response as drf_response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import UserRateThrottle
from rest_framework_api_key.permissions import HasAPIKey

from core import enums, models
from core.entitlements import get_entitlements_backend
from core.services.mirror import mirror_item
from core.services.sdk_relay import SDKRelayManager
from core.services.search_indexers import (
    get_file_indexer,
    get_visited_items_ids_of,
)
from core.tasks.item import duplicate_file, process_item_deletion, rename_file
from core.utils.analytics import posthog_capture
from wopi.services import access as access_service
from wopi.utils import compute_wopi_launch_url, get_wopi_client_config

from . import permissions, serializers, utils
from .filters import ItemFilter, ListItemFilter, SearchItemFilter

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
    1. **Trashbin**: List soft deleted items for a item owner
        Example: GET /items/{id}/trashbin/

    2. **Children**: List or create child items.
        Example: GET, POST /items/{id}/children/

    3. **Favorite**: Get list of favorite items for a user. Mark or unmark
        a item as favorite.
        Examples:
        - GET /items/favorite/
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
    ordering_fields = ["created_at", "updated_at", "title", "type"]
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
        queryset = super().get_queryset().select_related("creator")
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

        # Among all these items remove them that are restricted
        return queryset.filter(db.Q(id__in=access_items_ids) | (db.Q(id__in=traced_items_ids)))

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

        path_list = db.Q()
        for path in root_paths:
            path_list |= db.Q(path__descendants=path)

        queryset = self.queryset.select_related("creator")
        # Remove items with upload_state SUSPICIOUS for non-creators
        queryset = self._filter_suspicious_items(queryset, user)
        queryset = self._exclude_pending_items(queryset)
        queryset = queryset.filter(path_list)
        queryset = queryset.filter(ancestors_deleted_at__isnull=True)

        return queryset

    def filter_queryset(self, queryset):
        """Override to apply annotations to generic views."""
        queryset = super().filter_queryset(queryset)
        user = self.request.user
        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()
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
        Compute ancestors link definition for the items collection.
        On the collection, we look for the deepest items, compute ancestors link definition
        for each item and aggregate them in order to inject it in the serializer context.
        """
        if not items:
            return {}

        # Find deepest items and group them by parent path
        # Items at the same depth in multiple trees (same parent path) share the same ancestors,
        items_sorted = sorted(items, key=lambda x: len(x.path), reverse=True)
        items_by_tree = {}  # Group deepest items by parent_path
        seen_paths = set()  # Track all paths we've processed

        for item in items_sorted:
            # Check if this item is a parent of any longer path we've already seen
            # A descendant path would start with the item's path followed by a dot
            item_path_prefix = f"{item.path}."
            has_descendants = any(
                seen_path.startswith(item_path_prefix) for seen_path in seen_paths
            )

            if not has_descendants:
                # Get parent path (empty string for root items)
                parent_path = str(item.path[:-1]) if item.depth > 1 else ""
                if parent_path not in items_by_tree:
                    items_by_tree[parent_path] = item

            # Add this item's path to the set for future checks (shorter paths)
            seen_paths.add(str(item.path))

        # Compute ancestors links paths mapping for one item per tree group and aggregate
        paths_links_mapping = {}
        for item in items_by_tree.values():
            item_mapping = item.compute_ancestors_links_paths_mapping()
            paths_links_mapping |= item_mapping

        # Update the serializer context with the aggregated mapping
        return paths_links_mapping

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
            settings.BASE_DIR, "assets", "file_templates", f"template.{extension}"
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

    def perform_create(self, serializer):
        """Set the current user as creator and owner of the newly created object."""
        extension = serializer.validated_data.pop("extension", None)

        obj = models.Item.objects.create_child(
            creator=self.request.user,
            link_reach=LinkReachChoices.RESTRICTED,
            **serializer.validated_data,
        )
        if extension:
            self._create_file_from_template(obj, extension)
        serializer.instance = obj
        models.ItemAccess.objects.create(
            item=obj,
            user=self.request.user,
            role=models.RoleChoices.OWNER,
        )

    def perform_destroy(self, instance):
        """Override to implement a soft delete instead of dumping the record in database."""
        instance.soft_delete()

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
        process_item_deletion.delay(instance.id)
        return drf.response.Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        """List top level items with pagination and filtering."""
        # Not calling filter_queryset. We do our own cooking.
        queryset = self.get_queryset()

        filterset = ListItemFilter(self.request.GET, queryset=queryset, request=self.request)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        filter_data = filterset.form.cleaned_data

        # Filter as early as possible on fields that are available on the model
        for field in ["is_creator_me", "title", "type"]:
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

        # Annotate the queryset with an attribute marking instances as highest ancestor
        # in order to save some time while computing abilities in the instance
        queryset = queryset.annotate(
            is_highest_ancestor_for_user=db.Value(True, output_field=db.BooleanField())
        )

        # Annotate favorite status and filter if applicable as late as possible
        queryset = queryset.annotate_is_favorite(user)
        queryset = filterset.filters["is_favorite"].filter(queryset, filter_data["is_favorite"])
        queryset = queryset.annotate_with_numchild()

        # Apply ordering only now that everyting is filtered and annotated
        queryset = filters.OrderingFilter().filter_queryset(self.request, queryset, self)

        return self.get_response_for_queryset(queryset)

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

        entitlements_backend = get_entitlements_backend()
        can_upload = entitlements_backend.can_upload(self.request.user)
        if not can_upload["result"]:
            self._complete_item_deletion(item)
            raise drf.exceptions.PermissionDenied(
                detail=can_upload.get("message", "You do not have permission to upload files.")
            )

        s3_client = default_storage.connection.meta.client

        head_response = s3_client.head_object(Bucket=default_storage.bucket_name, Key=item.file_key)
        file_size = head_response["ContentLength"]

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

        # For encrypted files, skip MIME detection and malware scanning
        # (the server cannot inspect ciphertext)
        if item.is_encrypted:
            item.upload_state = models.ItemUploadStateChoices.READY
            item.mimetype = "application/octet-stream"
            item.size = file_size
            item.save(update_fields=["upload_state", "mimetype", "size"])
            mirror_item(item)
            serializer = self.get_serializer(item)
            posthog_capture(
                "item_uploaded",
                request.user,
                {
                    "id": item.id,
                    "title": item.title,
                    "size": item.size,
                    "mimetype": item.mimetype,
                    "is_encrypted": True,
                },
            )
            return drf_response.Response(serializer.data, status=status.HTTP_200_OK)

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

        item.upload_state = models.ItemUploadStateChoices.ANALYZING
        item.mimetype = mimetype
        item.size = file_size

        item.save(update_fields=["upload_state", "mimetype", "size"])

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

        malware_detection.analyse_file(item.file_key, item_id=item.id)
        mirror_item(item)

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

    def _complete_item_deletion(self, item):
        """Completely delete an item."""
        item.soft_delete()
        item.hard_delete()
        process_item_deletion.delay(item.id)

    @drf.decorators.action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
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

        Optimized version that uses EXISTS instead of expensive subqueries to check
        owner access on items or their ancestors.
        """
        user = request.user

        # Build the EXISTS subquery to check if user has owner access
        # to the item or any of its ancestors
        owner_access_exists = models.ItemAccess.objects.filter(
            db.Q(user=user) | db.Q(team__in=user.teams),
            role=models.RoleChoices.OWNER,
            item__path__ancestors=db.OuterRef("path"),
        )

        # Filter trashbin items to only those where user has owner access
        # Before we were filtering on the user_roles annotation, but it was too slow
        # Here the optimization is to filter on the owner_access_exists subquery
        # which is much faster.
        queryset = (
            self.queryset.select_related("creator")
            .filter(
                deleted_at__gte=models.get_trashbin_cutoff(),
            )
            .filter(db.Exists(owner_access_exists))
        )

        # Apply filtering similar to children method
        filterset = ItemFilter(request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        queryset = filterset.qs

        # Only annotate with user roles for the filtered set if needed by serializer
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()

        return self.get_response_for_queryset(queryset)

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

        # Handle encryption when moving between encrypted/unencrypted contexts
        encrypted_symmetric_key = validated_data.get("encrypted_symmetric_key")
        target_is_encrypted = target_item.is_encrypted if target_item else False

        if target_is_encrypted and not encrypted_symmetric_key:
            raise drf.exceptions.ValidationError(
                {
                    "encrypted_symmetric_key": _(
                        "This field is required when moving into an encrypted folder."
                    )
                },
                code="item_move_encrypted_key_required",
            )

        item.move(target_item)

        # Update encryption state after move
        if target_is_encrypted and not item.is_encrypted:
            # Moving into encrypted folder: item must become encrypted
            item.is_encrypted = True
            item.encrypted_symmetric_key = encrypted_symmetric_key
        elif target_is_encrypted and item.is_encrypted:
            # Moving between encrypted folders: re-wrap key
            item.encrypted_symmetric_key = encrypted_symmetric_key
        elif not target_is_encrypted and item.is_encrypted and item.encrypted_symmetric_key:
            # Moving from encrypted subtree to unencrypted: item becomes its own root
            # The frontend must handle re-wrapping the key for direct user access
            item.encrypted_symmetric_key = None

        # If the item is moved to the root and the user does not have an access on the item,
        # create an owner access for the user. Otherwise, the item will be invisible for the user.
        update_fields = ["is_encrypted", "encrypted_symmetric_key"]
        if not target_item and not models.ItemAccess.objects.filter(item=item, user=user).exists():
            models.ItemAccess.objects.create(
                item=item,
                user=self.request.user,
                role=models.RoleChoices.OWNER,
            )
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

            entitlements_backend = get_entitlements_backend()
            can_upload = entitlements_backend.can_upload(self.request.user)
            if (
                serializer.validated_data.get("type") == models.ItemTypeChoices.FILE
                and not can_upload["result"]
            ):
                raise drf.exceptions.PermissionDenied(
                    detail=can_upload.get("message", "You do not have permission to upload files.")
                )

            extension = serializer.validated_data.pop("extension", None)
            encrypted_symmetric_key = serializer.validated_data.pop(
                "encrypted_symmetric_key", None
            )

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
                serializer.validated_data["is_encrypted"] = True
                serializer.validated_data["encrypted_symmetric_key"] = encrypted_symmetric_key

            child_item = models.Item.objects.create_child(
                creator=request.user,
                parent=item,
                **serializer.validated_data,
            )

            if extension:
                self._create_file_from_template(child_item, extension)

            # Set the created instance to the serializer
            serializer.instance = child_item

            headers = self.get_success_headers(serializer.data)
            return drf.response.Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

        # GET: List children
        queryset = item.children().select_related("creator").filter(deleted_at__isnull=True)
        queryset = self._filter_suspicious_items(queryset, request.user)
        queryset = self._exclude_pending_items(queryset)
        queryset = self.filter_queryset(queryset)
        filterset = ItemFilter(request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        queryset = filterset.qs

        # Apply ordering only now that everything is filtered and annotated
        queryset = filters.OrderingFilter().filter_queryset(self.request, queryset, self)

        # Pre-compute number of accesses
        item_nb_accesses = item.nb_accesses
        queryset = queryset.annotate(
            _nb_accesses=db.Value(item_nb_accesses)
            + Coalesce(db.Count("accesses", distinct=True), 0),
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
        try:
            item = self.queryset.get(pk=pk)
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

        subtree_qs = (
            self.queryset.filter(
                path__descendants=item.path,
                ancestors_deleted_at__isnull=True,
            )
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

        highest_ancestor = (
            self.queryset.filter(path__ancestors=item.path, ancestors_deleted_at__isnull=True)
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
            self.queryset.select_related("creator")
            .filter(clause, type=models.ItemTypeChoices.FOLDER, deleted_at__isnull=True)
            .order_by("created_at")
        )

        user = request.user
        tree = tree.annotate_user_roles(user)
        tree = tree.annotate_is_favorite(user)
        tree = tree.annotate_with_numchild()
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
        """Get list of favorite items for the current user."""
        user = self.request.user
        queryset = self.get_queryset_for_descendants()

        filterset = ItemFilter(self.request.GET, queryset=queryset, request=self.request)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)

        queryset = filterset.filter_queryset(queryset)

        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_user_roles(user)
        queryset = queryset.annotate_with_numchild()

        queryset = queryset.order_by("-updated_at")

        return self.get_response_for_queryset(queryset, with_ancestors_link_definition=True)

    @drf.decorators.action(detail=True, methods=["get"])
    def breadcrumb(self, request, *args, **kwargs):
        """
        List the breadcrumb for an item
        """
        item = self.get_object()

        highest_ancestor = (
            self.queryset.filter(path__ancestors=item.path, ancestors_deleted_at__isnull=True)
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

        # First look for all top level items user has access to
        user = request.user
        item_access_queryset = models.ItemAccess.objects.select_related("item").filter(
            db.Q(user=user) | db.Q(team__in=user.teams),
            item__deleted_at__isnull=True,
        )

        # Remove items with upload_state SUSPICIOUS for non-creators
        queryset = self._filter_suspicious_items(queryset, user)
        queryset = self._exclude_pending_items(queryset)

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

    @drf.decorators.action(
        detail=True, methods=["post"], url_path="encryption-upload-url"
    )
    def encryption_upload_url(self, request, *args, **kwargs):
        """Return a presigned S3 PUT URL for uploading encrypted file content.

        When `filename` is provided: generates a URL for a NEW S3 key
        (used during initial encryption to avoid overwriting the plaintext file).

        When `filename` is omitted: generates a URL for the EXISTING S3 key
        (used for auto-save — S3 versioning keeps previous versions).
        """
        item = self.get_object()

        if item.type != models.ItemTypeChoices.FILE:
            return drf.response.Response(
                {"detail": _("Only files can be encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        new_filename = request.data.get("filename")
        if new_filename:
            key = f"{item.key_base}/{new_filename}"
        else:
            key = item.file_key

        # epoch_ms anchors the relay history replay model, but is only
        # meaningful for subsequent saves of an already-encrypted file.
        # The initial encrypt-new-file upload has no prior collaborative
        # state to anchor against, so the field is optional there.
        epoch_ms = request.data.get("epoch_ms")
        epoch_int = None
        if epoch_ms is not None:
            try:
                epoch_int = int(epoch_ms)
            except (TypeError, ValueError):
                return drf.response.Response(
                    {"detail": _("epoch_ms must be an integer.")},
                    status=drf.status.HTTP_400_BAD_REQUEST,
                )
            if epoch_int <= 0:
                return drf.response.Response(
                    {"detail": _("epoch_ms must be a positive integer.")},
                    status=drf.status.HTTP_400_BAD_REQUEST,
                )

        metadata = {"epoch": str(epoch_int)} if epoch_int is not None else None
        upload_url = utils.generate_upload_policy_for_key(
            key,
            content_type="application/octet-stream",
            metadata=metadata,
        )

        required_headers = (
            {"x-amz-meta-epoch": str(epoch_int)} if epoch_int is not None else {}
        )
        return drf.response.Response(
            {
                "upload_url": upload_url,
                "filename": new_filename or item.filename,
                "required_headers": required_headers,
            },
            status=drf.status.HTTP_200_OK,
        )


    @drf.decorators.action(detail=True, methods=["patch"], url_path="encrypt")
    @transaction.atomic
    def encrypt(self, request, *args, **kwargs):
        """Encrypt an item (standalone file) or an item subtree (folder + all descendants)."""
        item = self.get_object()

        # Validate: item must be RESTRICTED (using computed_link_reach
        # which accounts for inheritance — a file inside a restricted
        # folder is effectively restricted even if its own link_reach
        # is NULL).
        if item.computed_link_reach != LinkReachChoices.RESTRICTED:
            return drf.response.Response(
                {"detail": _("Item must be restricted before it can be encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # Validate: item must not already be encrypted or inside an encrypted subtree
        if item.is_encrypted:
            return drf.response.Response(
                {"detail": _("Item is already encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )
        if item.ancestors().filter(is_encrypted=True).exists():
            return drf.response.Response(
                {"detail": _("Item is inside an already encrypted subtree.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # Validate: no pending invitations on item or descendants
        descendant_ids = list(item.descendants().values_list("pk", flat=True))
        all_item_ids = [item.pk] + descendant_ids
        if models.Invitation.objects.filter(item_id__in=all_item_ids).exists():
            return drf.response.Response(
                {
                    "detail": _(
                        "All pending invitations must be resolved before encrypting."
                    )
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        serializer = serializers.EncryptItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        encrypted_key_per_user = serializer.validated_data["encryptedSymmetricKeyPerUser"]
        encrypted_keys_for_descendants = serializer.validated_data[
            "encryptedKeysForDescendants"
        ]

        # Validate: all users with access (direct OR inherited via an
        # ancestor's ItemAccess) must be present in the payload. Values
        # may be a wrapped key (validated) or explicit null (pending —
        # user hasn't completed their encryption onboarding yet).
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
            missing = user_subs_with_access - provided_user_subs
            extra = provided_user_subs - user_subs_with_access
            errors = {}
            if missing:
                errors["missing_users"] = list(missing)
            if extra:
                errors["extra_users"] = list(extra)
            return drf.response.Response(
                {"detail": _("Provided user keys do not match users with access."), **errors},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # The caller is the one performing the encryption — they must hold
        # the key. Explicit null for themselves is never legitimate.
        caller_sub = request.user.sub
        if (
            caller_sub in encrypted_key_per_user
            and encrypted_key_per_user[caller_sub] is None
        ):
            return drf.response.Response(
                {
                    "detail": _(
                        "You cannot mark yourself as pending encryption "
                        "onboarding — provide a wrapped key for your "
                        "own user."
                    ),
                    "code": "caller_cannot_be_pending",
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # Find any inner encrypted subtrees already rooted inside this item
        # ("stacked encryption"). Those descendants — and everything under
        # them — are out of scope: they keep their existing keys and their
        # own per-user ItemAccess records. We only encrypt items in the
        # effective scope (this item's descendants minus each inner root's
        # subtree).
        inner_roots = list(
            item.descendants().filter(
                is_encrypted=True,
                encrypted_symmetric_key__isnull=True,
            )
        )
        effective_descendants_qs = item.descendants()
        for inner in inner_roots:
            effective_descendants_qs = effective_descendants_qs.exclude(
                path__descendants=inner.path,
            )

        # Validate: a wrapped key must be provided for every descendant in
        # the effective scope (files AND nested folders). The hierarchical
        # key model stores each descendant's key wrapped by its direct
        # parent folder's key, so /key-chain/ can walk from the user's
        # entry point down to any leaf. This also doubles as an integrity
        # check: if the subtree mutated between frontend discovery and
        # this commit (another user added a file, a folder, etc.), the
        # provided id set won't match the live one and we abort the whole
        # operation so the user can re-discover + retry.
        live_descendant_ids = {
            str(pk) for pk in effective_descendants_qs.values_list("pk", flat=True)
        }
        provided_descendant_ids = set(encrypted_keys_for_descendants.keys())
        if live_descendant_ids != provided_descendant_ids:
            return drf.response.Response(
                {
                    "detail": _(
                        "Folder contents changed during the operation. "
                        "Please retry."
                    ),
                    "code": "subtree_mutated",
                    "missing": sorted(live_descendant_ids - provided_descendant_ids),
                    "extra": sorted(provided_descendant_ids - live_descendant_ids),
                },
                status=drf.status.HTTP_409_CONFLICT,
            )

        file_key_mapping = serializer.validated_data["fileKeyMapping"]

        # Collect old S3 keys for cleanup after commit
        old_s3_keys = []

        # Apply encryption: mark item as encrypted (it's the encryption root)
        item.is_encrypted = True
        item.encrypted_symmetric_key = None  # root has per-user keys, not parent-wrapped
        update_fields = ["is_encrypted", "encrypted_symmetric_key"]
        # Swap filename to point to the new S3 key where encrypted content was uploaded
        # title stays the same (visible name), only the S3 key changes
        if str(item.pk) in file_key_mapping:
            old_s3_keys.append(item.file_key)
            item.filename = file_key_mapping[str(item.pk)]
            update_fields.append("filename")
        item.save(update_fields=update_fields)

        # Apply encryption to descendants in the effective scope only —
        # inner encrypted subtrees keep their existing state untouched.
        for descendant in effective_descendants_qs.iterator():
            descendant.is_encrypted = True
            descendant.encrypted_symmetric_key = encrypted_keys_for_descendants.get(
                str(descendant.pk)
            )
            desc_fields = ["is_encrypted", "encrypted_symmetric_key"]
            if str(descendant.pk) in file_key_mapping:
                old_s3_keys.append(descendant.file_key)
                descendant.filename = file_key_mapping[str(descendant.pk)]
                desc_fields.append("filename")
            descendant.save(update_fields=desc_fields)

        # Store per-user encrypted keys on ItemAccess records that live on
        # THIS item. Keys *must* sit here — not on an ancestor's ItemAccess
        # — because /key-chain/ looks for the user's entry point by walking
        # from the target item upward until it finds an ItemAccess with
        # encrypted_item_symmetric_key_for_user set, and that entry point
        # is expected to be the encryption root (this item). Storing on an
        # ancestor would make decrypt walk through `item`'s own non-root
        # ancestors, which don't have a wrapped key.
        #
        # Drive itself computes inherited access on the fly via ancestor
        # path queries — there is no concrete ItemAccess row on descendants
        # of a shared ancestor. So when encrypting a subfolder, any user
        # who has only inherited access on this item has no row on which
        # to place their wrapped key. We create that row here, carrying
        # over the role they currently hold via inheritance so permissions
        # don't change — the new ItemAccess exists purely to hold the
        # encrypted key material.
        # Per-user fingerprint map — required, must cover the same set
        # of user subs as the wrapped-key map. Stored alongside the
        # wrapped key so clients can later tell which key the file was
        # encrypted for (surfaced in the "key mismatch" panel when
        # decrypt fails on a rotated key).
        fingerprint_per_user = serializer.validated_data[
            "encryptionPublicKeyFingerprintPerUser"
        ]
        fingerprint_subs = set(fingerprint_per_user.keys())
        if fingerprint_subs != provided_user_subs:
            fp_missing = provided_user_subs - fingerprint_subs
            fp_extra = fingerprint_subs - provided_user_subs
            errors = {}
            if fp_missing:
                errors["missing_users"] = list(fp_missing)
            if fp_extra:
                errors["extra_users"] = list(fp_extra)
            return drf.response.Response(
                {
                    "detail": _(
                        "Provided fingerprints do not match the users in "
                        "encryptedSymmetricKeyPerUser."
                    ),
                    **errors,
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        remaining_user_subs = set(encrypted_key_per_user.keys())
        for access in models.ItemAccess.objects.filter(
            item=item, user__isnull=False
        ).select_related("user"):
            user_sub = access.user.sub
            if user_sub in encrypted_key_per_user:
                access.encrypted_item_symmetric_key_for_user = encrypted_key_per_user[
                    user_sub
                ]
                update_fields = ["encrypted_item_symmetric_key_for_user"]
                if user_sub in fingerprint_per_user:
                    access.encryption_public_key_fingerprint = (
                        fingerprint_per_user[user_sub] or None
                    )
                    update_fields.append("encryption_public_key_fingerprint")
                access.save(update_fields=update_fields)
                remaining_user_subs.discard(user_sub)

        if remaining_user_subs:
            users_by_sub = {
                u.sub: u
                for u in models.User.objects.filter(sub__in=remaining_user_subs)
            }
            for user_sub in remaining_user_subs:
                user = users_by_sub.get(user_sub)
                if user is None:
                    continue
                # Inherited role from an ancestor ItemAccess. Defaults to
                # READER if none found (shouldn't happen — the access-set
                # check above already enforced membership).
                role = item.get_role(user) or models.RoleChoices.READER
                models.ItemAccess.objects.create(
                    item=item,
                    user=user,
                    role=role,
                    encrypted_item_symmetric_key_for_user=encrypted_key_per_user[
                        user_sub
                    ],
                    encryption_public_key_fingerprint=(
                        fingerprint_per_user.get(user_sub) or None
                    ),
                )

        # After DB commit: clean up old S3 objects (best-effort)
        def _cleanup_old_s3_keys():
            s3_client = default_storage.connection.meta.client
            bucket = default_storage.bucket_name
            for old_key in old_s3_keys:
                try:
                    s3_client.delete_object(Bucket=bucket, Key=old_key)
                except ClientError:
                    logger.warning("Failed to delete old S3 key: %s", old_key)

        transaction.on_commit(_cleanup_old_s3_keys)

        return drf.response.Response(
            self.get_serializer(item).data,
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(
        detail=True, methods=["patch"], url_path="remove-encryption"
    )
    @transaction.atomic
    def remove_encryption(self, request, *args, **kwargs):
        """Remove encryption from an item or subtree.

        The frontend uploads decrypted file content to new S3 keys, then calls
        this endpoint with a fileKeyMapping. The backend atomically swaps
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
        file_key_mapping = serializer.validated_data["fileKeyMapping"]

        # Stacked encryption: exclude inner encryption roots and their
        # subtrees from the removal scope. Those are independent encrypted
        # trees with their own per-user keys and must stay intact.
        inner_roots = list(
            item.descendants().filter(
                is_encrypted=True,
                encrypted_symmetric_key__isnull=True,
            )
        )
        effective_descendants_qs = item.descendants()
        for inner in inner_roots:
            effective_descendants_qs = effective_descendants_qs.exclude(
                path__descendants=inner.path,
            )

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
                    "detail": _(
                        "Folder contents changed during the operation. "
                        "Please retry."
                    ),
                    "code": "subtree_mutated",
                    "missing": sorted(live_file_ids - provided_ids),
                    "extra": sorted(provided_ids - live_file_ids),
                },
                status=drf.status.HTTP_409_CONFLICT,
            )

        # Collect old S3 keys for cleanup after commit
        old_s3_keys = []

        # Clear encryption on item, swap filename to new S3 key if provided
        update_fields = ["is_encrypted", "encrypted_symmetric_key"]
        if str(item.pk) in file_key_mapping:
            old_s3_keys.append(item.file_key)
            item.filename = file_key_mapping[str(item.pk)]
            update_fields.append("filename")
        item.is_encrypted = False
        item.encrypted_symmetric_key = None
        item.save(update_fields=update_fields)

        # Clear encryption on descendants in the effective scope only —
        # inner encrypted subtrees keep their existing state.
        for descendant in effective_descendants_qs.iterator():
            desc_fields = ["is_encrypted", "encrypted_symmetric_key"]
            descendant.is_encrypted = False
            descendant.encrypted_symmetric_key = None
            if str(descendant.pk) in file_key_mapping:
                old_s3_keys.append(descendant.file_key)
                descendant.filename = file_key_mapping[str(descendant.pk)]
                desc_fields.append("filename")
            descendant.save(update_fields=desc_fields)

        # Clear all per-user encrypted keys on this item's accesses
        models.ItemAccess.objects.filter(item=item).update(
            encrypted_item_symmetric_key_for_user=None,
            encryption_public_key_fingerprint=None,
        )

        # Collect file items in the effective scope for post-commit
        # malware scanning (now that they're plaintext again).
        file_items_to_scan = []
        if item.type == models.ItemTypeChoices.FILE and item.filename:
            file_items_to_scan.append((item.file_key, item.pk))
        for descendant in effective_descendants_qs.iterator():
            if descendant.type == models.ItemTypeChoices.FILE and descendant.filename:
                file_items_to_scan.append((descendant.file_key, descendant.pk))

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

            for file_key, item_id in file_items_to_scan:
                malware_detection.analyse_file(file_key, item_id=item_id)
                mirror_item(models.Item.objects.get(pk=item_id))

        transaction.on_commit(_post_commit)

        return drf.response.Response(
            self.get_serializer(item).data,
            status=drf.status.HTTP_200_OK,
        )

    @drf.decorators.action(detail=True, methods=["get"], url_path="key-chain")
    def key_chain(self, request, *args, **kwargs):
        """Return the decryption key chain from the user's access point down to this item.

        The response contains:
        - The user's encrypted entry-point key (from their ItemAccess)
        - The chain of wrapped keys from entry point down to the target item
        """
        item = self.get_object()

        if not item.is_encrypted:
            return drf.response.Response(
                {"detail": _("Item is not encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        # Walk up ancestors to find the user's access point (the item where they have
        # an ItemAccess with an encrypted key). `ancestors` is ordered shallowest
        # first (root of the tree) so we iterate deepest first to pick the
        # NEAREST ancestor carrying a wrapped key. This matters with stacked
        # encryption roots (e.g. T4 is an encrypted root and so is T4/sub):
        # for a file inside T4/sub, sub is the correct entry point, not T4.
        ancestors = list(item.ancestors().order_by("path"))
        candidate_items_deepest_first = [item] + list(reversed(ancestors))

        accesses_by_item_pk = {
            access.item.pk: access
            for access in models.ItemAccess.objects.filter(
                item__in=candidate_items_deepest_first,
                user=user,
                encrypted_item_symmetric_key_for_user__isnull=False,
            ).select_related("item")
        }
        user_access = None
        for candidate in candidate_items_deepest_first:
            if candidate.pk in accesses_by_item_pk:
                user_access = accesses_by_item_pk[candidate.pk]
                break

        if not user_access:
            # This means the user genuinely has no access to the item
            # (not pending — pending users are detected client-side via
            # `is_pending_encryption_for_user` on the Item serializer, so
            # the frontend skips this call entirely for them). 403 here
            # is a real "forbidden" and the global /403 redirect applies.
            return drf.response.Response(
                {"detail": _("No encryption key found for this user on this item chain.")},
                status=drf.status.HTTP_403_FORBIDDEN,
            )

        entry_point_item = user_access.item

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

        return drf.response.Response(
            {
                "user_access_item_id": str(entry_point_item.pk),
                "encrypted_key_for_user": user_access.encrypted_item_symmetric_key_for_user,
                "chain": chain,
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
        launch_url = compute_wopi_launch_url(wopi_client["url"], get_file_info, language)

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
    @transaction.atomic
    def duplicate(self, request, *args, **kwargs):
        """
        Duplicate an item of type File. The item is duplicated in the folder where the original
        item is.
        The user who duplicates becomes the creator of the duplicate
        """

        item_to_duplicate = self.get_object()
        user = request.user

        parent = item_to_duplicate.parent() if item_to_duplicate.depth > 1 else None

        if parent and parent.get_role(user) == models.RoleChoices.READER:
            # If the user as reader role on the parent folder, then the duplicated
            # item must be created at the user's root
            parent = None

        duplicated_item = models.Item.objects.create_child(
            creator=user,
            link_reach=None if parent else LinkReachChoices.RESTRICTED,
            parent=parent,
            title=item_to_duplicate.title,  # Title uniqueness is managed in the create_child method
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

        serializer = self.get_serializer(duplicated_item)
        return drf.response.Response(serializer.data, status=drf.status.HTTP_201_CREATED)


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

        serializer = self.get_serializer_class()(
            selected_accesses, many=True, context=self.get_serializer_context()
        )
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
            self._raise_if_would_strand_pending_users(
                instance, action="role_match_delete"
            )
            instance.delete()
            return drf.response.Response(status=drf.status.HTTP_204_NO_CONTENT)

        access = serializer.save()

        self._syncronize_descendants_accesses(access)

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

        # Handle encryption: validate encrypted key field.
        #
        # For encrypted items the key is optional: if the invitee has no
        # public key yet (still pending their encryption onboarding) the
        # caller legitimately has nothing to wrap. The access row is then
        # created pending (key column NULL) and can be "accepted" later
        # via PATCH /accesses/{id}/encryption-key/ once the invitee has
        # onboarded. Whether the invitee actually has a public key is a
        # client-side concern — the backend only enforces "key provided ⇒
        # item must be encrypted".
        encrypted_key = serializer.validated_data.get(
            "encrypted_item_symmetric_key_for_user"
        )
        if encrypted_key and not self.item.is_encrypted:
            raise drf.exceptions.ValidationError(
                {
                    "encrypted_item_symmetric_key_for_user": _(
                        "This field can only be provided when the item is encrypted."
                    )
                }
            )
        # Normalise "" → None so the DB row uses NULL consistently and
        # `is_pending_encryption` (which tests IS NULL) is reliable.
        if (
            "encrypted_item_symmetric_key_for_user" in serializer.validated_data
            and not serializer.validated_data["encrypted_item_symmetric_key_for_user"]
        ):
            serializer.validated_data["encrypted_item_symmetric_key_for_user"] = None

        # Block team-based access for encrypted items
        if self.item.is_encrypted and serializer.validated_data.get("team"):
            raise drf.exceptions.ValidationError(
                {
                    "team": _(
                        "Team-based access is not supported for encrypted items."
                    )
                }
            )

        access = serializer.save(item_id=self.kwargs["resource_id"])
        self._syncronize_descendants_accesses(access)
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

    def perform_destroy(self, instance):
        """Delete the item access and capture the event."""
        # Strand prevention: if this item is encrypted, removing the last
        # user who holds a wrapped key while pending users remain would
        # leave the subtree undecryptable by anyone (no one left to
        # "accept" the pending rows). Block it.
        self._raise_if_would_strand_pending_users(
            instance, action="remove"
        )
        access_id = instance.id
        item = instance.item
        role = instance.role
        super().perform_destroy(instance)
        posthog_capture(
            "item_access_deleted",
            self.request.user,
            {
                "id": access_id,
                "role": role,
            },
            item=item,
        )

    @drf.decorators.action(
        detail=True, methods=["patch"], url_path="encryption-key"
    )
    def encryption_key(self, request, *args, **kwargs):
        """Accept a pending collaborator by re-wrapping the subtree's
        symmetric key against their public key.

        This is the "Accept" action: a validated collaborator — someone
        who already holds a wrapped key on the subtree — re-wraps it for
        a user who was added before completing their encryption
        onboarding. The endpoint is strictly pending → validated; it
        does not support reverting. To revoke a user, delete the access.
        """
        access = self.get_object()
        item = access.item

        if not item.is_encrypted:
            return drf.response.Response(
                {"detail": _("Item is not encrypted.")},
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        if access.encrypted_item_symmetric_key_for_user:
            return drf.response.Response(
                {
                    "detail": _(
                        "This access is not pending encryption onboarding. "
                        "Delete the access row instead if you want to revoke it."
                    ),
                    "code": "access_not_pending",
                },
                status=drf.status.HTTP_400_BAD_REQUEST,
            )

        # The caller must currently hold a wrapped key somewhere in the
        # chain from the subtree's encryption root down to `item`. Without
        # that, they cannot have legitimately wrapped the new key
        # themselves — they have no plaintext to wrap from.
        ancestors = list(item.ancestors().order_by("path"))
        candidate_items_deepest_first = [item] + list(reversed(ancestors))
        caller_has_key = models.ItemAccess.objects.filter(
            item__in=candidate_items_deepest_first,
            user=request.user,
            encrypted_item_symmetric_key_for_user__isnull=False,
        ).exists()
        if not caller_has_key:
            return drf.response.Response(
                {
                    "detail": _(
                        "You do not currently hold a decryption key for this "
                        "item, so you cannot accept another user on it."
                    )
                },
                status=drf.status.HTTP_403_FORBIDDEN,
            )

        serializer = serializers.AcceptEncryptionAccessSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        access.encrypted_item_symmetric_key_for_user = (
            serializer.validated_data["encrypted_item_symmetric_key_for_user"]
        )
        access.encryption_public_key_fingerprint = (
            serializer.validated_data["encryption_public_key_fingerprint"]
        )
        access.save(
            update_fields=[
                "encrypted_item_symmetric_key_for_user",
                "encryption_public_key_fingerprint",
            ]
        )

        posthog_capture(
            "item_access_encryption_accepted",
            request.user,
            {"id": access.id},
            item=item,
        )

        output = self.get_serializer(access)
        return drf.response.Response(output.data)

    def _raise_if_would_strand_pending_users(self, instance, action):
        """Reject delete / implicit-delete if it would leave pending users
        with nobody able to accept them.

        The invariant we protect: on an encrypted subtree, if any access
        row is pending (`encrypted_item_symmetric_key_for_user IS NULL`),
        at least one other access row on that same item must still hold
        a wrapped key — otherwise nobody is left with the plaintext key
        to re-wrap for the pending users, and the subtree becomes
        undecryptable by everyone.

        `action` is an opaque label used for logging / testability.
        """
        item = instance.item
        if not item.is_encrypted:
            return
        # Only the encryption root carries per-user wrapped keys; other
        # items in the subtree have their key wrapped by the parent
        # folder. If this access is on a non-root item it can't be the
        # last wrapped-key holder.
        if item.encrypted_symmetric_key is not None:
            return
        # Only meaningful if the access we're about to remove actually
        # holds a wrapped key — removing a pending access never strands
        # anyone further.
        if not instance.encrypted_item_symmetric_key_for_user:
            return

        other_accesses = models.ItemAccess.objects.filter(item=item).exclude(
            pk=instance.pk
        )
        remaining_validated = other_accesses.filter(
            encrypted_item_symmetric_key_for_user__isnull=False,
        ).exclude(encrypted_item_symmetric_key_for_user="").exists()
        has_pending = other_accesses.filter(
            encrypted_item_symmetric_key_for_user__isnull=True,
        ).exists()

        if has_pending and not remaining_validated:
            raise drf.exceptions.ValidationError(
                {
                    "detail": _(
                        "Removing this user would leave pending collaborators "
                        "unable to decrypt the folder. Either wait for them "
                        "to finish their encryption onboarding, or remove "
                        "encryption from the folder first."
                    ),
                    "code": "would_strand_pending_users",
                }
            )

    def _syncronize_descendants_accesses(self, access):
        """
        Syncronize the accesses of the descendants of the item
        by removing accesses with roles lower than the current user's role.
        """
        descendants = self.item.descendants().filter(ancestors_deleted_at__isnull=True)

        condition_filter = db.Q()
        if access.user:
            condition_filter |= db.Q(user=access.user)
        if access.team:
            condition_filter |= db.Q(team=access.team)

        role_priority = models.RoleChoices.get_priority(access.role)

        lower_roles = [
            role
            for role in models.RoleChoices.values
            if models.RoleChoices.get_priority(role) <= role_priority
        ]

        models.ItemAccess.objects.filter(
            condition_filter, item__in=descendants, role__in=lower_roles
        ).delete()


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
        # Block invitations for encrypted items
        if self.item.is_encrypted:
            raise drf.exceptions.ValidationError(
                {
                    "detail": _(
                        "Invitations are not supported for encrypted items. "
                        "Add the user directly with their encryption key."
                    )
                }
            )

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


class ConfigView(drf.views.APIView):
    """API ViewSet for sharing some public settings."""

    permission_classes = [AllowAny]

    def get(self, request):
        """
        GET /api/v1.0/config/
            Return a dictionary of public settings.
        """
        array_settings = [
            "CRISP_WEBSITE_ID",
            "DATA_UPLOAD_MAX_MEMORY_SIZE",
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
            "FRONTEND_HIDE_GAUFRE",
            "FRONTEND_SILENT_LOGIN_ENABLED",
            "FRONTEND_EXTERNAL_HOME_URL",
            "FRONTEND_RELEASE_NOTE_ENABLED",
            "FRONTEND_CSS_URL",
            "FRONTEND_JS_URL",
            "MEDIA_BASE_URL",
            "POSTHOG_KEY",
            "POSTHOG_HOST",
            "LANGUAGES",
            "LANGUAGE_CODE",
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
    serializer_class = serializers.UsageMetricSerializer
    pagination_class = Pagination

    def get_queryset(self):
        """
        Return the queryset applying the filters from the query params.
        """
        queryset = self.queryset

        if self.request.query_params.get("account_id"):
            queryset = queryset.filter(sub=self.request.query_params.get("account_id"))

        return queryset


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
        return drf.response.Response(entitlements)
