"""Urls of the WOPI app."""

from django.conf import settings
from django.urls import include, path

from wopi.routers import WopiRouter
from wopi.viewsets import MountWopiViewSet, WopiViewSet

router = WopiRouter()
router.register("files", WopiViewSet, basename="files")
router.register("mount-files", MountWopiViewSet, basename="mount-files")

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/wopi/",
        include(
            [
                *router.urls,
            ]
        ),
    ),
]
