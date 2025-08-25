
from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from demo import viewsets


user_auth_router = DefaultRouter()
user_auth_router.register(
    "user-auth",
    viewsets.UserAuthViewSet,
    basename="user-auth",
)

urlpatterns = [
    path(
        f"api/{settings.API_VERSION}/demo/",
        include(
            [
                *user_auth_router.urls,
            ]
        ),
    ),
]