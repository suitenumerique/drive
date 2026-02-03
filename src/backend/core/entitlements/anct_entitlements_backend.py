"""
ANCT Entitlements Backend.
"""

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

import requests
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.entitlements.entitlements_backend import EntitlementsBackend

ENTITLEMENTS_CACHE_TIMEOUT = 60
ENTITLEMENTS_CACHE_KEY_PREFIX = "anct_entitlements_user:"


# pylint: disable=abstract-method
class ANCTEntitlementsParametersSerializer(serializers.Serializer):
    """Parameters for the ANCT entitlements backend."""

    url = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    service_id = serializers.CharField(required=True)
    cache_timeout = serializers.IntegerField(
        required=False, default=ENTITLEMENTS_CACHE_TIMEOUT
    )


class ANCTEntitlementsBackend(EntitlementsBackend):
    """Abstract base class for entitlements backends."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameters = None

    def get_parameters(self):
        """
        Get parameters for the entitlements backend.
        """
        if self.parameters:
            return self.parameters
        serializer = ANCTEntitlementsParametersSerializer(
            data=settings.ENTITLEMENTS_BACKEND_PARAMETERS
        )
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            # Don't expose sensitive configuration details in the response
            # Raise a configuration exception that will result in a 500 error
            # The default serializer exception are serialized in the response.
            raise ImproperlyConfigured(
                "Invalid entitlements backend configuration"
            ) from exc
        self.parameters = serializer.validated_data
        return self.parameters

    def fetch_entitlements(self, user):
        """
        Fetch entitlements for a user.
        """
        parameters = self.get_parameters()
        siret = user.claims.get("siret")
        response = requests.get(
            f"{parameters['url']}",
            params={
                "siret": siret,
                "account_type": "user",
                "account_id": user.sub,
                "service_id": parameters["service_id"],
            },
            headers={"X-Service-Auth": f"Bearer {parameters['token']}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_entitlements(self, user):
        """
        Get entitlements for a user, cached for the given timeout.
        """
        parameters = self.get_parameters()
        cache_key = f"{ENTITLEMENTS_CACHE_KEY_PREFIX}{user.id}"
        entitlements = cache.get(cache_key)
        if entitlements:
            return entitlements
        entitlements = self.fetch_entitlements(user)
        cache.set(cache_key, entitlements, timeout=parameters["cache_timeout"])
        return entitlements

    def can_upload(self, user):
        """
        Check if a user can upload a file.
        """
        entitlements = self.get_entitlements(user)
        return {"result": entitlements.get("entitlements", {}).get("can_upload", False)}

    def can_access(self, user):
        """
        Check if a user can access the app.
        """
        entitlements = self.get_entitlements(user)
        return {"result": entitlements.get("entitlements", {}).get("can_access", False)}
