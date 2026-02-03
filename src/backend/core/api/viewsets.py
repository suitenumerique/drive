"""API endpoints"""
# pylint: disable=too-many-lines

import json
import logging
import re
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models as db
from django.db import transaction
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.text import slugify

import posthog
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
from core.tasks.item import process_item_deletion, rename_file
from wopi.services import access as access_service
from wopi.utils import compute_wopi_launch_url, get_wopi_client_config

from . import permissions, serializers, utils
from .filters import ItemFilter, ListItemFilter, SearchItemFilter

logger = logging.getLogger(__name__)

ITEM_FOLDER = "item"
UUID_REGEX = (
    r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
)
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
            self.lookup_url_kwargs[:-1]
            if self.lookup_url_kwargs
            else self.lookup_fields[:-1]
        )

        filter_kwargs = {}
        for index, lookup_url_kwarg in enumerate(lookup_url_kwargs):
            if lookup_url_kwarg not in self.kwargs:
                raise KeyError(
                    f"Expected view {self.__class__.__name__} to be called with a URL "
                    f'keyword argument named "{lookup_url_kwarg}". Fix your URL conf, or '
                    "set the `.lookup_fields` attribute on the view correctly."
                )

            filter_kwargs.update(
                {self.lookup_fields[index]: self.kwargs[lookup_url_kwarg]}
            )

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
                queryset.annotate(
                    distance=RawSQL("levenshtein(email::text, %s::text)", (query,))
                )
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
        return drf.response.Response(
            self.get_serializer(request.user, context=context).data
        )


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
                db.Q(upload_state=models.ItemUploadStateChoices.SUSPICIOUS)
                & ~db.Q(creator=user)
            )

        return queryset.exclude(upload_state=models.ItemUploadStateChoices.SUSPICIOUS)

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
        ancestors_link_definition = self._compute_ancestors_link_definition(
            traced_items
        )
        traced_items_ids = []
        for item in traced_items:
            links = ancestors_link_definition.get(str(item.path[:-1]), [])
            item.ancestors_link_definition = get_equivalent_link_definition(links)
            if item.computed_link_reach != LinkReachChoices.RESTRICTED:
                traced_items_ids.append(item.id)

        # Among all these items remove them that are restricted
        return queryset.filter(
            db.Q(id__in=access_items_ids) | (db.Q(id__in=traced_items_ids))
        )

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
        queryset = queryset.filter(path_list)
        queryset = queryset.filter(ancestors_deleted_at__isnull=True)

        return queryset

    def filter_queryset(self, queryset):
        """Override to apply annotations to generic views."""
        queryset = super().filter_queryset(queryset)
        user = self.request.user
        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_user_roles(user)
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
        if (
            user.is_authenticated
            and not instance.link_traces.filter(user=user).exists()
        ):
            models.LinkTrace.objects.create(item=instance, user=request.user)

        return drf.response.Response(serializer.data)

    def perform_create(self, serializer):
        """Set the current user as creator and owner of the newly created object."""
        obj = models.Item.objects.create_child(
            creator=self.request.user,
            link_reach=LinkReachChoices.RESTRICTED,
            **serializer.validated_data,
        )
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
        if instance.type == models.ItemTypeChoices.FILE:
            title = serializer.validated_data.get("title")
            if title and instance.title != title:
                rename_file.delay(instance.id, title)
        serializer.save()

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

        filterset = ListItemFilter(
            self.request.GET, queryset=queryset, request=self.request
        )
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
        queryset = filterset.filters["is_favorite"].filter(
            queryset, filter_data["is_favorite"]
        )

        # Apply ordering only now that everyting is filtered and annotated
        queryset = filters.OrderingFilter().filter_queryset(
            self.request, queryset, self
        )

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
                detail=can_upload.get(
                    "message", "You do not have permission to upload files."
                )
            )

        s3_client = default_storage.connection.meta.client

        head_response = s3_client.head_object(
            Bucket=default_storage.bucket_name, Key=item.file_key
        )
        file_size = head_response["ContentLength"]

        if file_size > 2048:
            range_response = s3_client.get_object(
                Bucket=default_storage.bucket_name,
                Key=item.file_key,
                Range="bytes=0-2047",
            )
            file_head = range_response["Body"].read()
        else:
            file_head = s3_client.get_object(
                Bucket=default_storage.bucket_name, Key=item.file_key
            )["Body"].read()

        # Use improved MIME type detection combining magic bytes and file extension
        logger.info("upload_ended: detecting mimetype for file: %s", item.file_key)
        mimetype = utils.detect_mimetype(file_head, filename=item.filename)

        if (
            settings.RESTRICT_UPLOAD_FILE_TYPE
            and mimetype not in settings.FILE_MIMETYPE_ALLOWED
        ):
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

        if settings.POSTHOG_KEY:
            posthog.capture(
                "item_uploaded",
                distinct_id=request.user.email,
                properties={
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
        queryset = queryset.annotate(
            is_favorite=db.Value(True, output_field=db.BooleanField())
        )
        queryset = queryset.annotate_user_roles(user)

        filterset = ItemFilter(
            self.request.GET, queryset=queryset, request=self.request
        )
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)

        queryset = filterset.filter_queryset(queryset)

        favorite_items_ids = models.ItemFavorite.objects.filter(user=user).values_list(
            "item_id", flat=True
        )

        queryset = queryset.filter(id__in=favorite_items_ids)

        return self.get_response_for_queryset(
            queryset, with_ancestors_link_definition=True
        )

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
            message = (
                "You do not have permission to move items "
                "as a child to this target item."
            )

        if message:
            raise drf.exceptions.ValidationError(
                {"target_item_id": message}, code="item_move_missing_permission"
            )

        item.move(target_item)

        # If the item is moved to the root and the user does not have an access on the item,
        # create an owner access for the user. Otherwise, the item will be invisible for the user.
        update_fields = []
        if (
            not target_item
            and not models.ItemAccess.objects.filter(item=item, user=user).exists()
        ):
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
                    detail=can_upload.get(
                        "message", "You do not have permission to upload files."
                    )
                )

            child_item = models.Item.objects.create_child(
                creator=request.user,
                parent=item,
                **serializer.validated_data,
            )

            # Set the created instance to the serializer
            serializer.instance = child_item

            headers = self.get_success_headers(serializer.data)
            return drf.response.Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

        # GET: List children
        queryset = (
            item.children().select_related("creator").filter(deleted_at__isnull=True)
        )
        queryset = self._filter_suspicious_items(queryset, request.user)
        queryset = self.filter_queryset(queryset)
        filterset = ItemFilter(request.GET, queryset=queryset)
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)
        queryset = filterset.qs

        # Apply ordering only now that everything is filtered and annotated
        queryset = filters.OrderingFilter().filter_queryset(
            self.request, queryset, self
        )

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
            self.queryset.filter(
                path__ancestors=item.path, ancestors_deleted_at__isnull=True
            )
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

        filterset = ItemFilter(
            self.request.GET, queryset=queryset, request=self.request
        )
        if not filterset.is_valid():
            raise drf.exceptions.ValidationError(filterset.errors)

        queryset = filterset.filter_queryset(queryset)

        queryset = queryset.annotate_is_favorite(user)
        queryset = queryset.annotate_user_roles(user)

        queryset = queryset.order_by("-updated_at")

        return self.get_response_for_queryset(
            queryset, with_ancestors_link_definition=True
        )

    @drf.decorators.action(detail=True, methods=["get"])
    def breadcrumb(self, request, *args, **kwargs):
        """
        List the breadcrumb for an item
        """
        item = self.get_object()

        highest_ancestor = (
            self.queryset.filter(
                path__ancestors=item.path, ancestors_deleted_at__isnull=True
            )
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
        filterset = SearchItemFilter(
            request.GET, queryset=queryset, request=self.request
        )

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
            for parent in models.Item.objects.filter(
                id__in=missing_parent_ids
            ).iterator():
                parents[str(parent.id)] = parent

        # Set parents for each item
        for item in items:
            item.parents = [
                parents[item_id] for item_id in item.path if item_id != str(item.id)
            ]

        return items

    @drf.decorators.action(detail=True, methods=["put"], url_path="link-configuration")
    def link_configuration(self, request, *args, **kwargs):
        """Update link configuration with specific rights (cf get_abilities)."""
        # Check permissions first
        item = self.get_object()
        previous_link_reach = item.link_reach

        # Deserialize and validate the data
        serializer = serializers.LinkItemSerializer(
            item, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        if models.LinkReachChoices.get_priority(
            item.link_reach
        ) >= models.LinkReachChoices.get_priority(previous_link_reach):
            item.descendants().update(link_reach=None)

        return drf.response.Response(serializer.data, status=drf.status.HTTP_200_OK)

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
            # At this point the annotation is_favorite is already made by the
            # queryset.annotate_is_favorite(user) and its value is False.
            # If we want a fresh data we have to make a new queryset, apply the annotation
            # and get the item again.
            # To avoid all of this we directly set item.is_favorite to True.
            item.is_favorite = True
            serializer = self.get_serializer(item)
            return drf.response.Response(
                serializer.data, status=drf.status.HTTP_201_CREATED
            )

        # Handle DELETE method to unmark as favorite
        deleted, _ = models.ItemFavorite.objects.filter(item=item, user=user).delete()
        if deleted:
            # At this point the annotation is_favorite is already made by the
            # queryset.annotate_is_favorite(user) and its value is True.
            # If we want a fresh data we have to make a new queryset, apply the annotation
            # and get the item again.
            # To avoid all of this we directly set item.is_favorite to False.
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
            logger.debug(
                "User '%s' lacks permission for item '%s'", request.user.id, pk
            )
            raise drf.exceptions.PermissionDenied()

        logger.debug(
            "Subrequest authorization successful. Extracted parameters: %s", url_params
        )
        return url_params, user_abilities, request.user.id, item

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
        url_params, _, _, item = self._authorize_subrequest(
            request, MEDIA_STORAGE_URL_PATTERN
        )
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
        launch_url = compute_wopi_launch_url(wopi_client, get_file_info, language)

        return drf.response.Response(
            {
                "access_token": access_token,
                "access_token_ttl": access_token_ttl,
                "launch_url": launch_url,
            },
            status=drf.status.HTTP_200_OK,
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

        accesses_qs = accesses_qs.annotate_user_roles(user).order_by(
            "item__path", "created_at"
        )

        # Track max role and keep only deepest access per target
        max_role_by_target = {}
        deepest_access_by_target = {}

        for access in accesses_qs.iterator():
            target = access.target_key
            previous = max_role_by_target.get(target)
            previous_role = previous["role"] if previous else None

            # Set max_ancestors_role from previous accesses in hierarchy
            access.max_ancestors_role = previous_role
            access.max_ancestors_role_item_id = (
                previous["item_id"] if previous else None
            )

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
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data.get("role")

        # Check if the role is being updated and the new role is not "owner"
        if role and role != models.RoleChoices.OWNER:
            # Check if the access being updated is the last owner access for the resource
            if (
                self.item.is_root
                and instance.role == models.RoleChoices.OWNER
                and self.item.accesses.filter(role=models.RoleChoices.OWNER).count()
                == 1
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

        self._syncronize_descendants_accesses(access)

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
        ancestor_qs = (
            self.item.ancestors() | models.Item.objects.filter(pk=self.item.pk)
        ).filter(ancestors_deleted_at__isnull=True)
        ancestors_roles = models.ItemAccess.objects.filter(
            item__in=ancestor_qs, user=serializer.validated_data.get("user")
        ).values_list("role", flat=True)
        max_ancestors_role = models.RoleChoices.max(*ancestors_roles)

        if models.RoleChoices.get_priority(
            max_ancestors_role
        ) >= models.RoleChoices.get_priority(role):
            raise drf.exceptions.ValidationError(
                {
                    "role": (
                        f"The role {role} you are trying to assign is lower or equal"
                        f" than the max ancestors role {max_ancestors_role}."
                    ),
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
    queryset = (
        models.Invitation.objects.all().select_related("item").order_by("-created_at")
    )
    serializer_class = serializers.InvitationSerializer

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        context = super().get_serializer_context()
        context["resource_id"] = self.kwargs["resource_id"]
        return context

    def get_queryset(self):
        """Return the queryset according to the action."""
        queryset = super().get_queryset()
        queryset = queryset.filter(item=self.kwargs["resource_id"])

        if self.action == "list":
            user = self.request.user
            teams = user.teams

            # Determine which role the logged-in user has in the item
            user_roles_query = (
                models.ItemAccess.objects.filter(
                    db.Q(user=user) | db.Q(team__in=teams),
                    item=self.kwargs["resource_id"],
                )
                .values("item")
                .annotate(roles_array=ArrayAgg("role"))
                .values("roles_array")
            )

            queryset = (
                # The logged-in user should be administrator or owner to see its accesses
                queryset.filter(
                    db.Q(
                        item__accesses__user=user,
                        item__accesses__role__in=PRIVILEGED_ROLES,
                    )
                    | db.Q(
                        item__accesses__team__in=teams,
                        item__accesses__role__in=PRIVILEGED_ROLES,
                    ),
                )
                # Abilities are computed based on logged-in user's role and
                # the user role on each item access
                .annotate(user_roles=db.Subquery(user_roles_query))
                .distinct()
            )
        return queryset

    def perform_create(self, serializer):
        """Save invitation to a item then send an email to the invited user."""
        invitation = serializer.save()

        invitation.item.send_invitation_email(
            invitation.email,
            invitation.role,
            self.request.user,
            self.request.user.language or settings.LANGUAGE_CODE,
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

        cache_key = (
            f"theme_customization_{slugify(settings.THEME_CUSTOMIZATION_FILE_PATH)}"
        )
        theme_customization = cache.get(cache_key, {})
        if theme_customization:
            return theme_customization

        try:
            with open(
                settings.THEME_CUSTOMIZATION_FILE_PATH, "r", encoding="utf-8"
            ) as f:
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
