"""API filters for drive' core application."""

from django.db.models import Q, TextChoices
from django.utils.translation import gettext_lazy as _

import django_filters
from rest_framework.filters import OrderingFilter

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


class ItemOrdering(OrderingFilter):
    """Ordering filter dedicated to the ItemViewset"""

    extra_ordering = ["-updated_at"]

    def get_ordering(self, request, queryset, view):
        """Add the extra_ordering to the current ordering if not already present."""
        current_ordering = super().get_ordering(request, queryset, view)

        if not current_ordering:
            # If no ordering present, do not continue and return the current value
            # given by the parent call.
            return current_ordering

        current_fields = {field.lstrip("-") for field in current_ordering}

        for ordering in self.extra_ordering:
            if ordering.lstrip("-") not in current_fields:
                current_ordering.append(ordering)

        return current_ordering


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

    workspace = django_filters.UUIDFilter(method="filter_workspace", label=_("Workspace"))

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
    is_favorite = django_filters.BooleanFilter(method="filter_is_favorite", label=_("Favorite"))

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


class UsageMetricAccountTypeChoices(TextChoices):
    """Choices for the usage metrics `account_type` query param."""

    USER = "user", _("User")
    ORGANIZATION = "organization", _("Organization")


class UsageMetricAccountIdKeyChoices(TextChoices):
    """Allowed keys for filtering users by account id in the usage metrics endpoint."""

    SUB = "sub", _("Sub")
    EMAIL = "email", _("Email")


class BaseUsageMetricFilter(django_filters.FilterSet):
    """Shared `account_id_key`/`account_id_value` handling for usage metrics filters.

    Subclasses declare their own `account_id_key` filter (with the right validation
    rules and `required` flag) and override `ACCOUNT_ID_LOOKUP` to point at the field
    path used to filter the queryset.
    """

    ACCOUNT_ID_LOOKUP = "{key}"

    account_id_value = django_filters.CharFilter(method="filter_noop")

    # pylint: disable=unused-argument
    def filter_account_id_key(self, queryset, name, value):
        """Apply the account_id_key/account_id_value pair as a single filter."""
        account_id_value = self.data.get("account_id_value")
        if not account_id_value:
            return queryset
        lookup = self.ACCOUNT_ID_LOOKUP.format(key=value)
        return queryset.filter(**{lookup: account_id_value})

    # pylint: disable=unused-argument
    def filter_noop(self, queryset, name, value):
        """No-op: `account_id_value` is consumed by `filter_account_id`."""
        return queryset


class UsageMetricFilter(BaseUsageMetricFilter):
    """Filter for the usage metrics endpoint (user listing)."""

    account_id_key = django_filters.ChoiceFilter(
        choices=UsageMetricAccountIdKeyChoices.choices,
        method="filter_account_id_key",
    )
    account_email = django_filters.CharFilter(field_name="email")


class OrganizationUsageMetricFilter(BaseUsageMetricFilter):
    """Filter for the organization variant of the usage metrics endpoint.

    Both `account_id_key` and `account_id_value` are required, the key is an
    arbitrary OIDC claim name, and the lookup goes through the User's `claims`
    JSON field.
    """

    ACCOUNT_ID_LOOKUP = "claims__{key}"

    account_id_key = django_filters.CharFilter(method="filter_account_id_key", required=True)
    account_id_value = django_filters.CharFilter(method="filter_noop", required=True)
