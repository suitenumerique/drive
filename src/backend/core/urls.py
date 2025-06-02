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
                re_path(
                    r"^sdk-relay/events/(?P<token>[0-9a-zA-Z-]*)/",
                    viewsets.SDKRelayEventView.as_view(),
                ),
                re_path(
                    r"^sdk-relay/events/",
                    viewsets.SDKRelayEventCreateView.as_view(),
                ),
            ]
        ),
    ),
    path(f"api/{settings.API_VERSION}/config/", viewsets.ConfigView.as_view()),
    # path(r"api/{settings.API_VERSION}/sdk-relay/events/(?P<token>[0-9a-z-]*)/", viewsets.SDKRelayEventView.as_view()),
    # path(r"api/{settings.API_VERSION}/sdk-relay/events/", viewsets.SDKRelayEventCreateView.as_view()),
]
