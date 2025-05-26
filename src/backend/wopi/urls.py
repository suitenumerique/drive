"""Urls of the WOPI app."""

from django.conf import settings
from django.urls import include, path

from rest_framework.routers import DefaultRouter

from wopi.viewsets import WopiViewSet

router = DefaultRouter()
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
