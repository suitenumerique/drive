"""API endpoints"""
# pylint: disable=too-many-lines

import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db import models as db
from django.db import transaction
from django.db.models.expressions import RawSQL
from django.db.models.functions import Left, Length

import rest_framework as drf
from django_filters import rest_framework as drf_filters
from rest_framework import filters, status, viewsets
from rest_framework import response as drf_response
from rest_framework.permissions import AllowAny

from core import enums, models

from . import permissions, serializers, utils
from .filters import ItemFilter

logger = logging.getLogger(__name__)

ITEM_FOLDER = "item"
UUID_REGEX = (
    r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}"
)
FILE_EXT_REGEX = r"\.[a-zA-Z]{3,4}"
MEDIA_STORAGE_URL_PATTERN = re.compile(
    f"{settings.MEDIA_URL:s}"
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
    max_page_size = 200
    page_size_query_param = "page_size"


class UserViewSet(
    drf.mixins.UpdateModelMixin, viewsets.GenericViewSet, drf.mixins.ListModelMixin
):
    """User ViewSet"""

    permission_classes = [permissions.IsSelf]
    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer

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
        if item_id := self.request.GET.get("item_id", ""):
            queryset = queryset.exclude(itemaccess__item_id=item_id)

        if not (query := self.request.GET.get("q", "")):
            return queryset

        # For emails, match emails by Levenstein distance to prevent typing errors
        if "@" in query:
            return (
                queryset.annotate(
                    distance=RawSQL("levenshtein(email::text, %s::text)", (query,))
                )
                .filter(distance__lte=3)
                .order_by("distance", "email")
            )

        # Use trigram similarity for non-email-like queries
        # For performance reasons we filter first by similarity, which relies on an
        # index, then only calculate precise similarity scores for sorting purposes
        return (
            queryset.filter(email__trigram_word_similar=query)
            .annotate(similarity=TrigramSimilarity("email", query))
            .filter(similarity__gt=0.2)
            .order_by("-similarity", "email")
        )

    @drf.decorators.action(
        detail=False,
        methods=["get"],
        url_name="me",
        url_path="me",
        permission_classes=[permissions.IsAuthenticated],
    )
    def get_me(self, request):
        """
        Return information on currently logged user
        """
        context = {"request": request}
        return drf.response.Response(
            self.serializer_class(request.user, context=context).data
        )


class ResourceAccessViewsetMixin:
    """Mixin with methods common to all access viewsets."""

    def get_permissions(self):
        """User only needs to be authenticated to list resource accesses"""
        if self.action == "list":
            permission_classes = [permissions.IsAuthenticated]
        else:
            return super().get_permissions()

        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""
        context = super().get_serializer_context()
        context["resource_id"] = self.kwargs["resource_id"]
        return context

    def get_queryset(self):
        """Return the queryset according to the action."""
        queryset = super().get_queryset()
        queryset = queryset.filter(
            **{self.resource_field_name: self.kwargs["resource_id"]}
        )

        if self.action == "list":
            user = self.request.user
            teams = user.teams
            user_roles_query = (
                queryset.filter(
                    db.Q(user=user) | db.Q(team__in=teams),
                    **{self.resource_field_name: self.kwargs["resource_id"]},
                )
                .values(self.resource_field_name)
                .annotate(roles_array=ArrayAgg("role"))
                .values("roles_array")
            )

            # Limit to resource access instances related to a resource THAT also has
            # a resource access
            # instance for the logged-in user (we don't want to list only the resource
            # access instances pointing to the logged-in user)
            queryset = (
                queryset.filter(
                    db.Q(**{f"{self.resource_field_name}__accesses__user": user})
                    | db.Q(
                        **{f"{self.resource_field_name}__accesses__team__in": teams}
                    ),
                    **{self.resource_field_name: self.kwargs["resource_id"]},
                )
                .annotate(user_roles=db.Subquery(user_roles_query))
                .distinct()
            )
        return queryset

    def destroy(self, request, *args, **kwargs):
        """Forbid deleting the last owner access"""
        instance = self.get_object()
        resource = getattr(instance, self.resource_field_name)

        # Check if the access being deleted is the last owner access for the resource
        if (
            instance.role == "owner"
            and resource.accesses.filter(role="owner").count() == 1
        ):
            return drf.response.Response(
                {"detail": "Cannot delete the last owner access for the resource."},
                status=drf.status.HTTP_403_FORBIDDEN,
            )

        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Check that we don't change the role if it leads to losing the last owner."""
        instance = serializer.instance

        # Check if the role is being updated and the new role is not "owner"
        if (
            "role" in self.request.data
            and self.request.data["role"] != models.RoleChoices.OWNER
        ):
            resource = getattr(instance, self.resource_field_name)
            # Check if the access being updated is the last owner access for the resource
            if (
                instance.role == models.RoleChoices.OWNER
                and resource.accesses.filter(role=models.RoleChoices.OWNER).count() == 1
            ):
                message = "Cannot change the role to a non-owner role for the last owner access."
                raise drf.exceptions.PermissionDenied({"detail": message})

        serializer.save()


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
    drf.mixins.ListModelMixin,
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
    2. **user_roles**: Roles the current user has on the item or its ancestors.

    ### Notes:
    - Only the highest ancestor in a item hierarchy is shown in list views.
    - Implements soft delete logic to retain item tree structures.
    """

    filter_backends = [drf_filters.DjangoFilterBackend]
    filterset_class = ItemFilter
    metadata_class = ItemMetadata
    ordering = ["-updated_at"]
    ordering_fields = ["created_at", "updated_at", "title"]
    permission_classes = [
        permissions.ItemAccessPermission,
    ]
    queryset = models.Item.objects.all()
    serializer_class = serializers.ItemSerializer
    list_serializer_class = serializers.ListItemSerializer
    trashbin_serializer_class = serializers.ListItemSerializer
    children_serializer_class = serializers.ListItemSerializer
    create_serializer_class = serializers.CreateItemSerializer

    def annotate_is_favorite(self, queryset):
        """
        Annotate item queryset with the favorite status for the current user.
        """
        user = self.request.user

        if user.is_authenticated:
            favorite_exists_subquery = models.ItemFavorite.objects.filter(
                item_id=db.OuterRef("pk"), user=user
            )
            return queryset.annotate(is_favorite=db.Exists(favorite_exists_subquery))

        return queryset.annotate(is_favorite=db.Value(False))

    def annotate_user_roles(self, queryset):
        """
        Annotate item queryset with the roles of the current user
        on the item or its ancestors.
        """
        user = self.request.user
        output_field = ArrayField(base_field=db.CharField())

        if user.is_authenticated:
            user_roles_subquery = models.ItemAccess.objects.filter(
                db.Q(user=user) | db.Q(team__in=user.teams),
                item__path=Left(db.OuterRef("path"), Length("item__path")),
            ).values_list("role", flat=True)

            return queryset.annotate(
                user_roles=db.Func(
                    user_roles_subquery, function="ARRAY", output_field=output_field
                )
            )

        return queryset.annotate(
            user_roles=db.Value([], output_field=output_field),
        )

    def get_queryset(self):
        """Get queryset performing all annotation and filtering on the item tree structure."""
        user = self.request.user
        queryset = super().get_queryset()

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
        traced_items_ids = models.LinkTrace.objects.filter(user=user).values_list(
            "item_id", flat=True
        )

        return queryset.filter(
            db.Q(id__in=access_items_ids)
            | (
                db.Q(id__in=traced_items_ids)
                & ~db.Q(link_reach=models.LinkReachChoices.RESTRICTED)
            )
        )

    def filter_queryset(self, queryset):
        """Apply annotations and filters sequentially."""
        filterset = ItemFilter(
            self.request.GET, queryset=queryset, request=self.request
        )
        filterset.is_valid()
        filter_data = filterset.form.cleaned_data

        # Filter as early as possible on fields that are available on the model
        for field in ["is_creator_me", "title"]:
            queryset = filterset.filters[field].filter(queryset, filter_data[field])

        queryset = self.annotate_user_roles(queryset)

        if self.action == "list":
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
                is_highest_ancestor_for_user=db.Value(
                    True, output_field=db.BooleanField()
                )
            )

        # Annotate favorite status and filter if applicable as late as possible
        queryset = self.annotate_is_favorite(queryset)
        queryset = filterset.filters["is_favorite"].filter(
            queryset, filter_data["is_favorite"]
        )

        # Apply ordering only now that everyting is filtered and annotated
        return filters.OrderingFilter().filter_queryset(self.request, queryset, self)

    def get_response_for_queryset(self, queryset):
        """Return paginated response for the queryset if requested."""
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            return result

        serializer = self.get_serializer(queryset, many=True)
        return drf.response.Response(serializer.data)

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

    @transaction.atomic
    def perform_create(self, serializer):
        """Set the current user as creator and owner of the newly created object."""
        obj = models.Item.add_root(
            creator=self.request.user,
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

    @drf.decorators.action(detail=True, methods=["post"], url_path="upload-ended")
    def upload_ended(self, request, *args, **kwargs):
        """
        Set an item state to uploaded after a successful upload.
        """

        item = self.get_object()

        if item.type != models.ItemTypeChoices.FILE:
            raise drf.exceptions.ValidationError(
                {"item": "This action is only available for items of type FILE."}
            )

        if item.upload_state != models.ItemUploadStateChoices.PENDING:
            raise drf.exceptions.ValidationError(
                {"item": "This action is only available for items in PENDING state."}
            )

        item.upload_state = models.ItemUploadStateChoices.UPLOADED
        item.save(update_fields=["upload_state"])

        serializer = self.get_serializer(item)
        return drf_response.Response(serializer.data, status=status.HTTP_200_OK)

    @drf.decorators.action(
        detail=False,
        methods=["get"],
    )
    def favorite_list(self, request, *args, **kwargs):
        """Get list of favorite items for the current user."""
        user = request.user

        favorite_items_ids = models.ItemFavorite.objects.filter(user=user).values_list(
            "item_id", flat=True
        )

        queryset = self.get_queryset()
        queryset = queryset.filter(id__in=favorite_items_ids)
        return self.get_response_for_queryset(queryset)

    @drf.decorators.action(
        detail=False,
        methods=["get"],
    )
    def trashbin(self, request, *args, **kwargs):
        """
        Retrieve soft-deleted items for which the current user has the owner role.

        The selected items are those deleted within the cutoff period defined in the
        settings (see TRASHBIN_CUTOFF_DAYS), before they are considered permanently deleted.
        """
        queryset = self.queryset.filter(
            deleted_at__isnull=False,
            deleted_at__gte=models.get_trashbin_cutoff(),
        )
        queryset = self.annotate_user_roles(queryset)
        queryset = queryset.filter(user_roles__contains=[models.RoleChoices.OWNER])

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

        target_item_id = validated_data["target_item_id"]
        try:
            target_item = models.Item.objects.get(
                id=target_item_id, ancestors_deleted_at__isnull=True
            )
        except models.Item.DoesNotExist:
            return drf.response.Response(
                {"target_item_id": "Target parent item does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        position = validated_data["position"]
        message = None

        if position in [
            enums.MoveNodePositionChoices.FIRST_CHILD,
            enums.MoveNodePositionChoices.LAST_CHILD,
        ]:
            if not target_item.get_abilities(user).get("move"):
                message = (
                    "You do not have permission to move items "
                    "as a child to this target item."
                )
        elif not target_item.is_root():
            if not target_item.get_parent().get_abilities(user).get("move"):
                message = (
                    "You do not have permission to move items "
                    "as a sibling of this target item."
                )

        if message:
            return drf.response.Response(
                {"target_item_id": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.move(target_item, pos=position)

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
        ordering=["path"],
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

            with transaction.atomic():
                child_item = item.add_child(
                    creator=request.user,
                    **serializer.validated_data,
                )
                models.ItemAccess.objects.create(
                    item=child_item,
                    user=request.user,
                    role=models.RoleChoices.OWNER,
                )
            # Set the created instance to the serializer
            serializer.instance = child_item

            headers = self.get_success_headers(serializer.data)
            return drf.response.Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )

        # GET: List children
        queryset = item.get_children().filter(deleted_at__isnull=True)
        queryset = self.filter_queryset(queryset)
        queryset = self.annotate_is_favorite(queryset)
        queryset = self.annotate_user_roles(queryset)
        return self.get_response_for_queryset(queryset)

    @drf.decorators.action(detail=True, methods=["put"], url_path="link-configuration")
    def link_configuration(self, request, *args, **kwargs):
        """Update link configuration with specific rights (cf get_abilities)."""
        # Check permissions first
        item = self.get_object()

        # Deserialize and validate the data
        serializer = serializers.LinkItemSerializer(
            item, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

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
            return drf.response.Response(
                {"detail": "item marked as favorite"},
                status=drf.status.HTTP_201_CREATED,
            )

        # Handle DELETE method to unmark as favorite
        deleted, _ = models.ItemFavorite.objects.filter(item=item, user=user).delete()
        if deleted:
            return drf.response.Response(
                {"detail": "item unmarked as favorite"},
                status=drf.status.HTTP_204_NO_CONTENT,
            )
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
        match = pattern.search(parsed_url.path)

        # If the path does not match the pattern, try to extract the parameters from the query
        if not match:
            match = pattern.search(parsed_url.query)

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
        try:
            item = models.Item.objects.get(pk=pk)
        except models.Item.DoesNotExist as exc:
            logger.debug("item with ID '%s' does not exist", pk)
            raise drf.exceptions.PermissionDenied() from exc

        user_abilities = item.get_abilities(request.user)

        if not user_abilities.get(self.action, False):
            logger.debug("User '%s' lacks permission for item '%s'", request.user, pk)
            raise drf.exceptions.PermissionDenied()

        logger.debug(
            "Subrequest authorization successful. Extracted parameters: %s", url_params
        )
        return url_params, user_abilities, request.user.id

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
        url_params, _, _ = self._authorize_subrequest(
            request, MEDIA_STORAGE_URL_PATTERN
        )
        # Generate S3 authorization headers using the extracted URL parameters
        request = utils.generate_s3_authorization_headers(f"{url_params.get('key'):s}")

        return drf.response.Response("authorized", headers=request.headers, status=200)


class ItemAccessViewSet(
    ResourceAccessViewsetMixin,
    drf.mixins.CreateModelMixin,
    drf.mixins.DestroyModelMixin,
    drf.mixins.ListModelMixin,
    drf.mixins.RetrieveModelMixin,
    drf.mixins.UpdateModelMixin,
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
    pagination_class = Pagination
    permission_classes = [permissions.IsAuthenticated, permissions.AccessPermission]
    queryset = models.ItemAccess.objects.select_related("user").all()
    resource_field_name = "item"
    serializer_class = serializers.ItemAccessSerializer

    def perform_create(self, serializer):
        """Add a new access to the item and send an email to the new added user."""
        access = serializer.save()
        language = self.request.headers.get("Content-Language", "en-us")

        access.item.send_invitation_email(
            access.user.email,
            access.role,
            self.request.user,
            language,
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
    permission_classes = [
        permissions.CanCreateInvitationPermission,
        permissions.AccessPermission,
    ]
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
                        item__accesses__role__in=models.PRIVILEGED_ROLES,
                    )
                    | db.Q(
                        item__accesses__team__in=teams,
                        item__accesses__role__in=models.PRIVILEGED_ROLES,
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

        language = self.request.headers.get("Content-Language", "en-us")

        invitation.item.send_invitation_email(
            invitation.email, invitation.role, self.request.user, language
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
            "MEDIA_BASE_URL",
            "POSTHOG_KEY",
            "LANGUAGES",
            "LANGUAGE_CODE",
            "SENTRY_DSN",
        ]
        dict_settings = {}
        for setting in array_settings:
            if hasattr(settings, setting):
                dict_settings[setting] = getattr(settings, setting)

        return drf.response.Response(dict_settings)
