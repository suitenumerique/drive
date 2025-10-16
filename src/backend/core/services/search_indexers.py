"""Document search index management utilities and indexers"""

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import cache

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.db.models import Subquery
from django.utils.module_loading import import_string

import requests

from core import models

logger = logging.getLogger(__name__)


@cache
def get_file_indexer():
    """Returns an instance of indexer service if enabled and properly configured."""
    classpath = settings.SEARCH_INDEXER_CLASS

    # For this usecase an empty indexer class is not an issue but a feature.
    if not classpath:
        logger.info("Item indexer is not configured (see SEARCH_INDEXER_CLASS)")
        return None

    try:
        indexer_class = import_string(settings.SEARCH_INDEXER_CLASS)
        return indexer_class()
    except ImportError as err:
        logger.error("SEARCH_INDEXER_CLASS setting is not valid : %s", err)
    except ImproperlyConfigured as err:
        logger.error("Item indexer is not properly configured : %s", err)

    return None


def get_ancestor_to_descendants_map(items):
    """
    Given a list of items, return a mapping of ancestor_path -> set of descendant_paths.

    Each path is assumed to use materialized path format with fixed-length segments.

    Args:
        items (list of Item): List of items.

    Returns:
        dict[str, set[str]]: Mapping from ancestor path to its descendant paths (including itself).
    """
    ancestor_map = defaultdict(set)

    for item in items:
        path = str(item.path)
        ancestors = path.split(".")
        for i in range(1, len(ancestors) + 1):
            ancestor = ".".join(ancestors[:i])
            ancestor_map[ancestor].add(path)

    return ancestor_map


def get_batch_accesses_by_users_and_teams(items):
    """
    Get accesses related to a list of document paths,
    grouped by users and teams, including all ancestor paths.
    """
    ancestor_map = get_ancestor_to_descendants_map(items)
    access_qs = models.ItemAccess.objects.filter(
        item__path__in=list(ancestor_map.keys())
    ).values("item__path", "user__sub", "team")

    access_by_document_path = defaultdict(lambda: {"users": set(), "teams": set()})

    for access in access_qs:
        ancestor_path = str(access["item__path"])
        user_sub = access["user__sub"]
        team = access["team"]

        for descendant_path in ancestor_map.get(ancestor_path, []):
            if user_sub:
                access_by_document_path[descendant_path]["users"].add(str(user_sub))
            if team:
                access_by_document_path[descendant_path]["teams"].add(team)

    return dict(access_by_document_path)


def get_visited_items_ids_of(queryset, user):
    """
    Returns the ids of the documents that have a linktrace to the user and NOT owned.
    It will be use to limit the opensearch responses to the public documents already
    "visited" by the user.
    """
    if isinstance(user, AnonymousUser):
        return []

    qs = models.LinkTrace.objects.filter(user=user)

    docs = (
        queryset.exclude(accesses__user=user)
        .filter(
            deleted_at__isnull=True,
            ancestors_deleted_at__isnull=True,
        )
        .filter(pk__in=Subquery(qs.values("item_id")))
        .order_by("pk")
        .distinct("pk")
    )

    return [str(id) for id in docs.values_list("pk", flat=True)]


class BaseItemIndexer(ABC):
    """
    Base class for item indexers.

    Handles batching and access resolution. Subclasses must implement both
    `serialize_item()` and `push()` to define backend-specific behavior.
    """

    def __init__(self, batch_size=None, max_upload_size=None):
        """
        Initialize the indexer.

        Args:
            batch_size (int, optional): Number of documents per batch.
                Defaults to settings.SEARCH_INDEXER_BATCH_SIZE.
        """
        self.batch_size = batch_size or settings.SEARCH_INDEXER_BATCH_SIZE
        self.max_upload_size = (
            max_upload_size or settings.SEARCH_INDEXER_UPLOAD_MAX_SIZE
        )
        self.indexer_url = settings.SEARCH_INDEXER_URL
        self.indexer_secret = settings.SEARCH_INDEXER_SECRET
        self.search_url = settings.SEARCH_INDEXER_QUERY_URL
        self.allowed_mimetypes = settings.SEARCH_INDEXER_ALLOWED_MIMETYPES

        if not self.indexer_url:
            raise ImproperlyConfigured(
                "SEARCH_INDEXER_URL must be set in Django settings."
            )

        if not self.indexer_secret:
            raise ImproperlyConfigured(
                "SEARCH_INDEXER_SECRET must be set in Django settings."
            )

        if not self.search_url:
            raise ImproperlyConfigured(
                "SEARCH_INDEXER_QUERY_URL must be set in Django settings."
            )

        if not self.allowed_mimetypes:
            raise ImproperlyConfigured(
                "SEARCH_INDEXER_ALLOWED_MIMETYPES must be set in Django settings."
            )

    def index(self):
        """
        Fetch documents in batches, serialize them, and push to the search backend.
        """
        last_id = None
        count = 0
        queryset = models.Item.objects.filter(
            main_workspace=False,
        ).order_by("id")

        while True:
            if last_id is not None:
                items_batch = list(queryset.filter(id__gt=last_id)[: self.batch_size])
            else:
                items_batch = list(queryset[: self.batch_size])

            if not items_batch:
                break

            last_id = items_batch[-1].id
            accesses_by_item_path = get_batch_accesses_by_users_and_teams(items_batch)
            serialize = self.serialize_item

            serialized_batch = [
                serialize(item, accesses_by_item_path) for item in items_batch
            ]

            self.push(serialized_batch)
            count += len(serialized_batch)

        return count

    @abstractmethod
    def serialize_item(self, item, accesses) -> dict:
        """
        Convert a Item instance to a JSON-serializable format for indexing.

        Must be implemented by subclasses.
        """

    @abstractmethod
    def push(self, data):
        """
        Push a batch of serialized documents to the backend.

        Must be implemented by subclasses.
        """

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def search(self, text, token, visited=(), page=1, page_size=50):
        """
        Search for documents in Find app.
        Ensure the same default ordering as "Docs" list : -updated_at

        Returns ids of the documents

        Args:
            text (str): Text search content.
            token (str): OIDC Authentication token.
            visited (list, optional):
                List of ids of active public documents with LinkTrace
                Defaults to settings.SEARCH_INDEXER_BATCH_SIZE.
            page (int, optional):
                The page number to retrieve.
                Defaults to 1 if not specified.
            page_size (int, optional):
                The number of results to return per page.
                Defaults to 50 if not specified.
        """
        response = self.search_query(
            data={
                "q": text,
                "visited": visited,
                "services": ["drive"],
                "page_number": page,
                "page_size": page_size,
                "order_by": "updated_at",
                "order_direction": "desc",
            },
            token=token,
        )

        return [d["_id"] for d in response]

    @abstractmethod
    def search_query(self, data, token) -> dict:
        """
        Retrieve items from indexation database.

        Must be implemented by subclasses.
        """


class SearchIndexer(BaseItemIndexer):
    """
    File indexer that pushes text content from files to La Suite Find app.
    """

    def to_text(self, item):
        """
        Convert a file content into an indexable text.
        """
        mimetype = item.mimetype or ""

        if mimetype.startswith("text/"):
            return default_storage.open(item.file_key, "rb").read().decode()

        raise SuspiciousFileOperation(f"Unrecognized mimetype {mimetype}")

    def has_text(self, item):
        """
        Return True if the file mimetype can be converted into text for indexation
        """
        mimetype = item.mimetype or ""

        return (
            item.upload_state == models.ItemUploadStateChoices.READY
            and item.type == models.ItemTypeChoices.FILE
            and mimetype
            and any(mimetype.startswith(allowed) for allowed in self.allowed_mimetypes)
        )

    def serialize_item(self, item, accesses):
        """
        Convert a Document to the JSON format expected by La Suite Find.

        Args:
            document (Document): The document instance.
            accesses (dict): Mapping of document ID to user/team access.

        Returns:
            dict: A JSON-serializable dictionary.
        """
        doc_path = str(item.path)
        is_deleted = bool(item.ancestors_deleted_at or item.deleted_at)
        content = self.to_text(item) if not is_deleted and self.has_text(item) else ""

        return {
            "id": str(item.id),
            "title": item.title or "",
            "mimetype": item.mimetype or "",
            "description": item.description or "",
            "content": content,
            "depth": item.depth,
            "path": str(item.path),
            "numchild": item.children().count(),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "users": list(accesses.get(doc_path, {}).get("users", set())),
            "groups": list(accesses.get(doc_path, {}).get("teams", set())),
            "reach": item.link_reach,
            "size": item.size,
            "is_active": not is_deleted,
        }

    def search_query(self, data, token) -> requests.Response:
        """
        Retrieve documents from the Find app API.

        Args:
            data (dict): search data
            token (str): OICD token

        Returns:
            dict: A JSON-serializable dictionary.
        """
        response = requests.post(
            self.search_url,
            json=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def push(self, data):
        """
        Push a batch of documents to the Find backend.

        Args:
            data (list): List of document dictionaries.
        """
        response = requests.post(
            self.indexer_url,
            json=data,
            headers={"Authorization": f"Bearer {self.indexer_secret}"},
            timeout=10,
        )
        response.raise_for_status()
