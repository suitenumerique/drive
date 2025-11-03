"""API filters for drive' core application."""

from django.db.models import Exists, OuterRef, Q, TextChoices
from django.utils.translation import gettext_lazy as _

import django_filters

from core import models


class ItemFilter(django_filters.FilterSet):
    """
    Custom filter for filtering items.
    """

    title = django_filters.CharFilter(
        field_name="title", lookup_expr="unaccent__icontains", label=_("Title")
    )

    class Meta:
        model = models.Item
        fields = ["title", "type"]


class ScopeChoices(TextChoices):
    """Choices for the scope filter."""

    ALL = "all", _("All")
    DELETED = "deleted", _("Deleted")
    NOT_DELETED = "not_deleted", _("Not deleted")


class WorkspacesChoices(TextChoices):
    """Choices for the workspace filter."""

    PUBLIC = "public", _("Public")
    SHARED = "shared", _("Shared")


class SearchItemFilter(ItemFilter):
    """Filter class dedicated to the Item viewset search method."""

    workspace = django_filters.UUIDFilter(
        method="filter_workspace", label=_("Workspace")
    )

    type = django_filters.ChoiceFilter(
        field_name="type",
        label=_("Type"),
        choices=models.ItemTypeChoices.choices + [("workspace", _("Workspace"))],
        method="filter_type",
    )

    scope = django_filters.MultipleChoiceFilter(
        field_name="scopes",
        label=_("Scopes"),
        choices=ScopeChoices.choices,
        initial="not_deleted",
        method="filter_scope",
    )

    class Meta:
        model = models.Item
        fields = ["title", "type", "workspace"]

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, data=None, *args, **kwargs):
        """Use initial values as defaults."""
        # if filterset is bound, use initial values as defaults
        if data is not None:
            # get a mutable copy of the QueryDict
            data = data.copy()

            # pylint: disable=no-member
            for name, f in self.base_filters.items():
                initial = f.extra.get("initial")

                # filter param is either missing or empty, use initial as default
                if not data.get(name) and initial:
                    data[name] = initial

        super().__init__(data, *args, **kwargs)

    # pylint: disable=unused-argument
    def filter_workspace(self, queryset, name, value):
        """
        This filter do nothing, it returns directly the queryset.
        It is used by the viewset directly to filter the ItemAccess queryset.
        """
        return queryset

    def filter_type(self, queryset, name, value):
        """
        Filter items based on their type.
        """
        if value == "workspace":
            return queryset.filter(path__depth=1, type=models.ItemTypeChoices.FOLDER)
        if value == "folder":
            return queryset.filter(
                path__depth__gt=1, type=models.ItemTypeChoices.FOLDER
            )
        if value == "file":
            return queryset.filter(type=models.ItemTypeChoices.FILE)
        return queryset

    def filter_scope(self, queryset, name, value):
        """Filter items based on their scopes."""
        to_filter = Q()
        if ScopeChoices.ALL in value:
            return queryset
        if ScopeChoices.DELETED in value:
            to_filter |= Q(ancestors_deleted_at__isnull=False)
        if ScopeChoices.NOT_DELETED in value:
            to_filter |= Q(deleted_at__isnull=True, ancestors_deleted_at__isnull=True)

        return queryset.filter(to_filter)


class ListItemFilter(ItemFilter):
    """Filter class dedicated to the Item viewset list method."""

    is_creator_me = django_filters.BooleanFilter(
        method="filter_is_creator_me", label=_("Creator is me")
    )
    is_favorite = django_filters.BooleanFilter(
        method="filter_is_favorite", label=_("Favorite")
    )

    workspaces = django_filters.ChoiceFilter(
        label=_("Workspaces"),
        choices=WorkspacesChoices.choices,
        method="filter_workspaces",
    )

    class Meta:
        model = models.Item
        fields = ["is_creator_me", "is_favorite", "title", "type"]

    # pylint: disable=unused-argument
    def filter_is_creator_me(self, queryset, name, value):
        """
        Filter items based on the `creator` being the current user.

        Example:
            - /api/v1.0/items/?is_creator_me=true
                → Filters items created by the logged-in user
            - /api/v1.0/items/?is_creator_me=false
                → Filters items created by other users
        """
        user = self.request.user

        if not user.is_authenticated:
            return queryset

        if value:
            return queryset.filter(creator=user)

        return queryset.exclude(creator=user)

    # pylint: disable=unused-argument
    def filter_is_favorite(self, queryset, name, value):
        """
        Filter items based on whether they are marked as favorite by the current user.

        Example:
            - /api/v1.0/items/?is_favorite=true
                → Filters items marked as favorite by the logged-in user
            - /api/v1.0/items/?is_favorite=false
                → Filters items not marked as favorite by the logged-in user
        """
        user = self.request.user

        if not user.is_authenticated:
            return queryset

        return queryset.filter(is_favorite=bool(value))

    def filter_workspaces(self, queryset, name, value):
        """Filter items based on their workspace."""
        user = self.request.user

        if not user.is_authenticated or not value:
            return queryset

        item_access_queryset = models.ItemAccess.objects.filter(
            Q(user=user) | Q(team__in=user.teams),
            item__path__ancestors=OuterRef("path"),
        )

        if value == WorkspacesChoices.PUBLIC:
            return queryset.filter(link_reach=models.LinkReachChoices.PUBLIC).filter(
                ~Q(Exists(item_access_queryset))
            )
        if value == WorkspacesChoices.SHARED:
            return queryset.filter(Exists(item_access_queryset))

        return queryset
