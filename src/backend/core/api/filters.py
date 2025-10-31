"""API filters for drive' core application."""

from django.db.models import Q, TextChoices
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

    link_reach = django_filters.ChoiceFilter(
        field_name="link_reach",
        label=_("Link Reach"),
        choices=models.LinkReachChoices.choices,
        method="filter_link_reach",
    )

    class Meta:
        model = models.Item
        fields = ["title", "type", "workspace", "link_reach"]

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
            to_filter |= Q(deleted_at__isnull=False)
        if ScopeChoices.NOT_DELETED in value:
            to_filter |= Q(deleted_at__isnull=True)

        return queryset.filter(to_filter)

    # pylint: disable=unused-argument
    def filter_link_reach(self, queryset, name, value):
        """
        Filter items based on their link_reach, excluding main workspaces.
        
        Example:
            - /api/v1.0/items/search/?link_reach=public
                → Filters items with public link reach (excluding main workspaces)
        """
        if value:
            return queryset.filter(link_reach=value).exclude(main_workspace=True)
        return queryset


class ListItemFilter(ItemFilter):
    """Filter class dedicated to the Item viewset list method."""

    is_creator_me = django_filters.BooleanFilter(
        method="filter_is_creator_me", label=_("Creator is me")
    )
    is_favorite = django_filters.BooleanFilter(
        method="filter_is_favorite", label=_("Favorite")
    )
    link_reach = django_filters.ChoiceFilter(
        field_name="link_reach",
        label=_("Link Reach"),
        choices=models.LinkReachChoices.choices,
        method="filter_link_reach",
    )

    class Meta:
        model = models.Item
        fields = ["is_creator_me", "is_favorite", "title", "type", "link_reach"]

    # pylint: disable=unused-argument
    def filter_link_reach(self, queryset, name, value):
        """
        Filter items based on their link_reach, excluding main workspaces.
        
        Example:
            - /api/v1.0/items/?link_reach=public
                → Filters items with public link reach (excluding main workspaces)
        """
        if value:
            return queryset.filter(link_reach=value).exclude(main_workspace=True)
        return queryset

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
