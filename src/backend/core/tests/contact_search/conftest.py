"""Fixtures for the contact search tests."""

import json
import time

import httpx
import pytest
from rest_framework.test import APIClient

from core import factories

CONTACTS_URL = "https://contacts.example.org"
SEARCH_PATH = "/external_api/v1.0/search/"
INTERACTIONS_PATH = "/external_api/v1.0/interactions/"
ACCESS_TOKEN = "user-access-token"


class FakeContacts:
    """La Suite Contacts, as an httpx transport recording what Drive sends."""

    def __init__(self):
        self.calls = []
        self._answers = {}

    def answer(self, method, path, **response):
        """How to answer *method* *path* from now on.

        *response* takes ``json_body``, ``status`` (200), ``text`` or ``error``
        (an exception to raise instead of answering).
        """
        self._answers[(method, path)] = (
            response.get("json_body"),
            response.get("status", 200),
            response.get("text"),
            response.get("error"),
        )

    def handle(self, request):
        """Answer a request Drive makes."""
        self.calls.append(request)
        answer = self._answers.get((request.method, request.url.path))
        if answer is None:
            raise httpx.ConnectError("Contacts is not reachable", request=request)
        json_body, status, text, error = answer
        if error is not None:
            raise error
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=json_body)

    @property
    def transport(self):
        """The transport to give the backend."""
        return httpx.MockTransport(self.handle)

    def bodies(self, path):
        """The JSON bodies sent to *path*."""
        return [json.loads(call.content) for call in self.calls if call.url.path == path]


@pytest.fixture(name="contacts")
def contacts_fixture():
    """A fake La Suite Contacts."""
    return FakeContacts()


@pytest.fixture(name="contacts_backend")
def contacts_backend_fixture(settings, contacts):
    """Configure the La Suite Contacts backend, talking to the fake Contacts."""
    settings.LASUITE_CONTACT_SEARCH = {
        "BACKEND": "lasuite.contact_search.backends.lasuite_contacts.LaSuiteContactsBackend",
        "PARAMETERS": {"base_url": CONTACTS_URL, "transport": contacts.transport},
        "FALLBACK": {"BACKEND": "core.contact_search.LocalContactSearchBackend"},
    }
    settings.OIDC_STORE_ACCESS_TOKEN = True
    return contacts


def card(name, *emails, pref=None, kind="individual", uid=None):
    """A JSContact card as Contacts' search returns it."""
    entries = {}
    for index, address in enumerate(emails, start=1):
        entry = {"address": address}
        if pref == index or (pref is None and index == 1):
            entry["pref"] = 1
        entries[f"e{index}"] = entry
    return {
        "@type": "Card",
        "version": "1.0",
        "uid": uid or f"urn:uuid:{name}",
        "kind": kind,
        "name": {"full": name},
        "emails": entries,
    }


def logged_in_client(user, *, access_token=ACCESS_TOKEN, expires_in=3600):
    """A client logged in as *user*, with an OIDC access token in its session."""
    client = APIClient()
    # Logged in through OIDC, like real users: only those sessions refresh.
    client.force_login(user, backend="core.authentication.backends.OIDCAuthenticationBackend")
    session = client.session
    if access_token:
        session["oidc_access_token"] = access_token
    session["oidc_id_token_expiration"] = time.time() + expires_in
    session.save()
    return client


@pytest.fixture(name="user")
def user_fixture():
    """The user searching."""
    return factories.UserFactory(email="alice@example.org")
