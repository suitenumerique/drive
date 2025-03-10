"""WOPI viewsets module."""

import logging
import re
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models as db
from django.db import transaction
from django.db.models.expressions import RawSQL

import magic
import rest_framework as drf
from rest_framework import filters, status, viewsets
from rest_framework import response as drf_response
from rest_framework.permissions import AllowAny

from core import enums, models

from . import permissions, serializers, utils
from .filters import ItemFilter, ListItemFilter

logger = logging.getLogger(__name__)


class WOPIViewSet(viewsets.GenericViewSet):
    """
    WOPI ViewSet
    """

    permission_classes = [AllowAny]
