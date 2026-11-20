"""Drive's own contact search: its active users, matched on their email.

Who the share modal suggests is django-lasuite's contact search
(lasuite.contact_search, settings.LASUITE_CONTACT_SEARCH). This backend is
the default, and the fallback when La Suite Contacts can't answer.
"""

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.expressions import RawSQL

from lasuite.contact_search.backends import USER, ContactResult
from lasuite.contact_search.backends.base import BaseContactSearchBackend

from core import models

# Shorter queries would let anyone list the instance's users.
LOCAL_MIN_QUERY_LENGTH = 5


def filter_users(queryset, query, limit):
    """Users of *queryset* whose email matches *query*, best first.

    An email-like query (with "@") matches by Levenshtein distance, to
    forgive typos; any other query by trigram similarity on the email.
    """
    if "@" in query:
        return (
            queryset.annotate(distance=RawSQL("levenshtein(email::text, %s::text)", (query,)))
            .filter(distance__lte=3)
            .order_by("distance", "email")[:limit]
        )

    # For performance reasons we filter first by similarity, which relies on an
    # index, then only calculate precise similarity scores for sorting purposes
    return (
        queryset.filter(email__trigram_word_similar=query)
        .annotate(similarity=TrigramSimilarity("email", query))
        .filter(similarity__gt=0.2)
        .order_by("-similarity", "email")[:limit]
    )


class LocalContactSearchBackend(BaseContactSearchBackend):
    """Drive's active users, matched on their email."""

    min_query_length = LOCAL_MIN_QUERY_LENGTH

    def search(self, user, query, *, limit=None, access_token=None):
        """Search Drive's active users by email."""
        if len(query) < self.min_query_length:
            return []
        users = filter_users(
            models.User.objects.filter(is_active=True),
            query,
            limit or settings.API_USERS_LIST_LIMIT,
        )
        return [
            ContactResult(kind=USER, email=found.email, name=found.full_name or "", user=found)
            for found in users
        ]
