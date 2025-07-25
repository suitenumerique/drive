"""URL configuration for the core app."""

from django.conf import settings
from django.urls import include, path, re_path

from lasuite.oidc_login.urls import urlpatterns as oidc_urls
from rest_framework.routers import DefaultRouter

from core.api import viewsets

# - Main endpoints
router = DefaultRouter()
router.register("items", viewsets.ItemViewSet, basename="items")
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
            ]
        ),
    ),
    path(f"api/{settings.API_VERSION}/config/", viewsets.ConfigView.as_view()),
]
