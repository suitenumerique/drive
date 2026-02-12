"""URL configuration for the core app."""

from django.conf import settings
from django.urls import include, path, re_path

from lasuite.oidc_login.urls import urlpatterns as oidc_urls
from rest_framework.routers import DefaultRouter

from core.api import viewsets
from core.external_api import viewsets as external_api_viewsets

# - Main endpoints
router = DefaultRouter()
router.register("items", viewsets.ItemViewSet, basename="items")
router.register("mounts", viewsets.MountViewSet, basename="mounts")
router.register("share-links", viewsets.ShareLinkViewSet, basename="share_links")
router.register("users", viewsets.UserViewSet, basename="users")

# - Routes nested under a item
item_related_router = DefaultRouter()
item_related_router.register(
    "accesses",
    viewsets.ItemAccessViewSet,
    basename="item_accesses",
)
item_related_router.register(
    "invitations",
    viewsets.InvitationViewset,
    basename="invitations",
)

sdk_relay_router = DefaultRouter()
sdk_relay_router.register(
    "sdk-relay/events",
    viewsets.SDKRelayEventViewset,
    basename="sdk_relay_events",
)

entitlements_router = DefaultRouter()
entitlements_router.register(
    "entitlements",
    viewsets.EntitlementsViewset,
    basename="entitlements",
)

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/",
        include(
            [
                *router.urls,
                *oidc_urls,
                re_path(
                    r"^items/(?P<resource_id>[0-9a-z-]*)/",
                    include(item_related_router.urls),
                ),
                *sdk_relay_router.urls,
                *entitlements_router.urls,
            ]
        ),
    ),
    path(f"api/{settings.API_VERSION}/config/", viewsets.ConfigView.as_view()),
]


if settings.OIDC_RESOURCE_SERVER_ENABLED:
    # - Resource server routes
    external_api_router = DefaultRouter()
    items_access_config = settings.EXTERNAL_API.get("items", {})
    items_enabled = bool(items_access_config.get("enabled", False))
    if items_enabled:
        external_api_router.register(
            "items",
            external_api_viewsets.ResourceServerItemViewSet,
            basename="resource_server_items",
        )

    users_access_config = settings.EXTERNAL_API.get("users", {})
    if users_access_config.get("enabled", False):
        external_api_router.register(
            "users",
            external_api_viewsets.ResourceServerUserViewSet,
            basename="resource_server_users",
        )

    external_api_urls = [*external_api_router.urls]

    if items_enabled:
        # - Resource server nested routes under items
        external_api_item_related_router = DefaultRouter()
        item_access_config = settings.EXTERNAL_API.get("item_access", {})
        if item_access_config.get("enabled", False):
            external_api_item_related_router.register(
                "accesses",
                external_api_viewsets.ResourceServerItemAccessViewSet,
                basename="resource_server_item_accesses",
            )

        item_invitation_config = settings.EXTERNAL_API.get("item_invitation", {})
        if item_invitation_config.get("enabled", False):
            external_api_item_related_router.register(
                "invitations",
                external_api_viewsets.ResourceServerInvitationViewSet,
                basename="resource_server_invitations",
            )

        if external_api_item_related_router.urls:
            external_api_urls.append(
                re_path(
                    r"^items/(?P<resource_id>[0-9a-z-]*)/",
                    include(external_api_item_related_router.urls),
                )
            )

    if external_api_urls:
        urlpatterns.append(
            path(
                f"external_api/{settings.API_VERSION}/",
                include(external_api_urls),
            )
        )

if settings.METRICS_ENABLED:
    usage_metrics_router = DefaultRouter()
    usage_metrics_router.register(
        "usage",
        viewsets.UsageMetricViewset,
        basename="usage_metrics",
    )
    urlpatterns.append(
        path(
            f"external_api/{settings.API_VERSION}/metrics/",
            include(usage_metrics_router.urls),
        )
    )
