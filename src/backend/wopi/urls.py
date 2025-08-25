"""Urls of the WOPI app."""

from django.conf import settings
from django.urls import include, path

from wopi.routers import WopiRouter
from wopi.viewsets import WopiViewSet

router = WopiRouter()
router.register("files", WopiViewSet, basename="files")

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
