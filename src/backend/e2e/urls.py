"""URL configuration for the e2e app."""

from django.conf import settings
from django.urls import include, path

from rest_framework.routers import DefaultRouter

from e2e import viewsets

user_auth_router = DefaultRouter()
user_auth_router.register(
    "user-auth",
    viewsets.UserAuthViewSet,
    basename="user-auth",
)

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/e2e/",
        include(
            [
                *user_auth_router.urls,
            ]
        ),
    ),
]
