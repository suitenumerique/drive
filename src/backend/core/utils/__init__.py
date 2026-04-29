"""Module for common utils in the project."""

from functools import cache

from django.conf import settings
from django.contrib.sites.models import Site


@cache
def get_url_app():
    """Return the base url of the application"""

    return settings.URL_APP or Site.objects.get_current().domain
