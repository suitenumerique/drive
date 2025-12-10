"""Task configuring WOPI using discovery url."""

from base64 import b64decode

from django.conf import settings
from django.core.cache import cache

import requests
from celery import Celery
from celery.schedules import crontab
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from defusedxml.ElementTree import fromstring

from drive.celery_app import app as celery_app

WOPI_CONFIGURATION_CACHE_KEY = "wopi_configuration"
WOPI_DEFAULT_CONFIGURATION = {
    "mimetypes": {},
    "extensions": {},
}


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    """Setup periodic tasks."""
    sender.add_periodic_task(
        crontab(minute="0"),
        configure_wopi_clients.s(),
        name="configure_wopi_clients_every_hour",
        serializer="json",
    )


@celery_app.task
def configure_wopi_clients():
    """Configure wopi clients from discovery url."""
    cache.delete(WOPI_CONFIGURATION_CACHE_KEY)

    for client in settings.WOPI_CLIENTS:
        _configure_wopi_client_from_discovery(
            client, settings.WOPI_CLIENTS_CONFIGURATION[client]["discovery_url"]
        )


def build_rsa_public_key(modulus, exponent):
    """Build RSA public key from modulus and exponent."""
    mod = int(b64decode(modulus).hex(), 16)
    exp = int(b64decode(exponent).hex(), 16)

    rsa_public_key = RSAPublicNumbers(exp, mod).public_key()

    return rsa_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _configure_wopi_client_from_discovery(client, discovery_url):
    """Configure wopi client from discovery url."""

    response = requests.get(discovery_url, timeout=30)

    if not response.ok:
        raise RuntimeError(
            f"status code {response.status_code} return by discovery url for "
            f"wopi client {client} is invalid"
        )

    wopi_configuration = cache.get(
        WOPI_CONFIGURATION_CACHE_KEY,
        default=WOPI_DEFAULT_CONFIGURATION,
    )

    root = fromstring(response.content)

    # Find the net-zone element
    net_zone = root.find(".//net-zone")
    if net_zone is None:
        raise RuntimeError(
            f"net-zone element not found in discovery url for wopi client {client}"
        )

    proof_key_node = root.find(".//proof-key")
    proof_keys = {}

    if proof_key_node is not None:
        # build current and old public key
        current_public_key = build_rsa_public_key(
            proof_key_node.get("modulus"), proof_key_node.get("exponent")
        )
        old_public_key = build_rsa_public_key(
            proof_key_node.get("oldmodulus"), proof_key_node.get("oldexponent")
        )

        proof_keys = {
            "public_key": current_public_key,
            "old_public_key": old_public_key,
        }

    wopi_configuration[client] = {
        "proof_keys": proof_keys,
    }

    # Iterate through all app elements
    for app in net_zone.findall(".//app"):
        app_name = app.get("name")
        if app_name is None:
            continue

        for action in app.findall("action"):
            if action.get("name") != "edit":
                continue

            # configure using mimetype
            if action.get("ext") == "":
                mimetype = app.get("name")

                if mimetype in settings.WOPI_EXCLUDED_MIMETYPES:
                    continue

                wopi_configuration["mimetypes"][mimetype] = {
                    "launch_url": action.get("urlsrc"),
                    "client": client,
                }

            else:
                extension = action.get("ext")

                if extension in settings.WOPI_EXCLUDED_EXTENSIONS:
                    continue

                wopi_configuration["extensions"][extension] = {
                    "launch_url": action.get("urlsrc"),
                    "client": client,
                }

    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        wopi_configuration,
        timeout=settings.WOPI_CONFIGURATION_CACHE_EXPIRATION,
    )
