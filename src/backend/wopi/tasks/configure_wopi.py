"""Task configuring WOPI using discovery url."""

from django.conf import settings
from django.core.cache import cache

import requests
from celery import Celery
from celery.schedules import crontab
from defusedxml.ElementTree import fromstring

from drive.celery_app import app as celery_app

WOPI_CONFIGURATION_CACHE_KEY = "wopi_configuration"
WOPI_DEFAULT_CONFIGURATION = {
    "mimetypes": {},
    "extensions": {},
}


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    """Setup periodic tasks."""
    sender.add_periodic_task(
        crontab(
            minute=settings.WOPI_CONFIGURATION_CRONTAB_MINUTE,
            hour=settings.WOPI_CONFIGURATION_CRONTAB_HOUR,
            day_of_month=settings.WOPI_CONFIGURATION_CRONTAB_DAY_OF_MONTH,
            month_of_year=settings.WOPI_CONFIGURATION_CRONTAB_MONTH_OF_YEAR,
        ),
        configure_wopi_clients.s(),
        name="configure_wopi_clients",
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
                    "url": action.get("urlsrc"),
                    "client": client,
                }

            else:
                extension = action.get("ext")

                if extension in settings.WOPI_EXCLUDED_EXTENSIONS:
                    continue

                wopi_configuration["extensions"][extension] = {
                    "url": action.get("urlsrc"),
                    "client": client,
                }

    cache.set(
        WOPI_CONFIGURATION_CACHE_KEY,
        wopi_configuration,
        timeout=settings.WOPI_CONFIGURATION_CACHE_EXPIRATION,
    )
