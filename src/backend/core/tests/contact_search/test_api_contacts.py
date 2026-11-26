"""GET /api/v1.0/contacts/: the contacts the share modal suggests."""

import pytest
from rest_framework.test import APIClient

from core import factories

from .conftest import ACCESS_TOKEN, INTERACTIONS_PATH, SEARCH_PATH, card, logged_in_client

pytestmark = pytest.mark.django_db

URL = "/api/v1.0/contacts/"


# Local backend (default)


def test_drive_users_are_suggested_by_default(user):
    """Without configuration, Drive's users matched on their email."""
    john = factories.UserFactory(email="john.doe@example.org", full_name="John Doe")

    response = logged_in_client(user, access_token=None).get(URL, {"q": "john.doe@example.org"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "kind": "user",
            "id": str(john.id),
            "email": "john.doe@example.org",
            "full_name": "John Doe",
            "short_name": john.short_name or "",
        }
    ]


def test_short_queries_find_nobody_by_default(user):
    """The local search keeps its 5 characters minimum."""
    factories.UserFactory(email="john.doe@example.org")

    assert logged_in_client(user).get(URL, {"q": "john"}).json() == []


def test_anonymous_users_are_refused():
    """Only for logged-in users."""
    assert APIClient().get(URL, {"q": "john.doe@example.org"}).status_code == 401


# La Suite Contacts backend


@pytest.mark.usefixtures("contacts_backend")
def test_contacts_come_back_as_users_and_invitations(user, contacts):
    """Drive users keep their id; other addresses use their email as id."""
    felix = factories.UserFactory(email="felix@example.org", full_name="Félix Marchand")
    contacts.answer(
        "GET",
        SEARCH_PATH,
        json_body={
            "results": [card("Félix", "felix@example.org"), card("Marie", "marie@example.org")]
        },
    )

    response = logged_in_client(user).get(URL, {"q": "m"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "kind": "user",
            "id": str(felix.id),
            "email": "felix@example.org",
            "full_name": "Félix Marchand",
            "short_name": felix.short_name or "",
        },
        # The share modal sends an invitation for a contact whose id is its email.
        {
            "kind": "user",
            "id": "marie@example.org",
            "email": "marie@example.org",
            "full_name": "Marie",
            "short_name": "",
        },
    ]
    assert contacts.calls[0].headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"


@pytest.mark.usefixtures("contacts_backend")
def test_one_letter_is_enough_with_contacts(user, contacts):
    """Contacts only searches the user's own book: short queries are fine."""
    contacts.answer("GET", SEARCH_PATH, json_body={"results": []})

    assert logged_in_client(user).get(URL, {"q": "m"}).status_code == 200
    assert len(contacts.calls) == 1


@pytest.mark.usefixtures("contacts_backend")
def test_an_empty_query_answers_nothing(user, contacts):
    """No query, no call."""
    assert logged_in_client(user).get(URL, {"q": ""}).json() == []
    assert not contacts.calls


@pytest.mark.usefixtures("contacts_backend")
def test_contacts_down_falls_back_to_drive_users(user, contacts):
    """When Contacts fails, the share modal still finds Drive's users."""
    john = factories.UserFactory(email="john.doe@example.org")
    contacts.answer("GET", SEARCH_PATH, status=503, json_body={})

    response = logged_in_client(user).get(URL, {"q": "john.doe@example.org"})

    assert [found["id"] for found in response.json()] == [str(john.id)]


@pytest.mark.usefixtures("contacts_backend")
def test_without_fallback_contacts_down_answers_nothing(user, contacts, settings):
    """The dummy backend as fallback makes an outage visible instead."""
    settings.LASUITE_CONTACT_SEARCH = {
        **settings.LASUITE_CONTACT_SEARCH,
        "FALLBACK": {"BACKEND": "lasuite.contact_search.backends.dummy.DummyContactSearchBackend"},
    }
    factories.UserFactory(email="john.doe@example.org")
    contacts.answer("GET", SEARCH_PATH, status=503, json_body={})

    assert logged_in_client(user).get(URL, {"q": "john.doe@example.org"}).json() == []


@pytest.mark.usefixtures("contacts_backend")
def test_without_token_in_session_it_falls_back(user, contacts):
    """No stored token: Drive's users, and Contacts isn't called."""
    john = factories.UserFactory(email="john.doe@example.org")

    response = logged_in_client(user, access_token=None).get(URL, {"q": "john.doe@example.org"})

    assert not contacts.calls
    assert [found["id"] for found in response.json()] == [str(john.id)]


@pytest.mark.usefixtures("contacts_backend")
def test_an_expired_token_without_refresh_token_falls_back(user, contacts):
    """An expired token that can't be refreshed doesn't log the user out."""
    john = factories.UserFactory(email="john.doe@example.org")

    response = logged_in_client(user, expires_in=-60).get(URL, {"q": "john.doe@example.org"})

    assert not contacts.calls
    assert response.status_code == 200
    assert [found["id"] for found in response.json()] == [str(john.id)]


@pytest.mark.usefixtures("contacts_backend")
def test_people_already_in_the_item_are_left_out(user, contacts):
    """item_id leaves out the Drive users who already have an access."""
    felix = factories.UserFactory(email="felix@example.org")
    item = factories.ItemFactory()
    factories.UserItemAccessFactory(item=item, user=felix)
    contacts.answer(
        "GET",
        SEARCH_PATH,
        json_body={
            "results": [card("Félix", "felix@example.org"), card("Marie", "marie@example.org")]
        },
    )

    response = logged_in_client(user).get(URL, {"q": "m", "item_id": str(item.id)})

    assert [found["email"] for found in response.json()] == ["marie@example.org"]


@pytest.mark.usefixtures("contacts_backend")
def test_the_users_endpoint_keeps_the_local_search(user, contacts):
    """GET /users/ is unchanged: it never calls Contacts."""
    john = factories.UserFactory(email="john.doe@example.org")

    response = logged_in_client(user).get("/api/v1.0/users/", {"q": "john.doe@example.org"})

    assert [found["id"] for found in response.json()] == [str(john.id)]
    assert not contacts.calls


# Groups

GROUP_ID = "02e230b4-4179-4da5-ac17-22c55ea5da02"
MEMBERS_PATH = f"/external_api/v1.0/groups/{GROUP_ID}/members/"
MEMBERS_URL = f"{URL}groups/{GROUP_ID}/members/"


@pytest.mark.usefixtures("contacts_backend")
def test_groups_are_suggested_with_their_member_count(user, contacts):
    """A group comes back with its own shape."""
    found = card(
        "Conseil municipal", "conseil@example.org", kind="group", uid=f"urn:uuid:{GROUP_ID}"
    )
    found["numerique.gouv.fr:membersCount"] = 8
    contacts.answer("GET", SEARCH_PATH, json_body={"results": [found]})

    response = logged_in_client(user).get(URL, {"q": "con"})

    assert response.json() == [
        {
            "kind": "group",
            "id": GROUP_ID,
            "name": "Conseil municipal",
            "email": "conseil@example.org",
            "members_count": 8,
        }
    ]


@pytest.mark.usefixtures("contacts_backend")
def test_group_members_are_listed_and_the_group_reported(
    user, contacts, django_capture_on_commit_callbacks
):
    """Listing members for a share reports the group as picked."""
    felix = factories.UserFactory(email="felix@example.org", full_name="Félix")
    contacts.answer(
        "GET",
        MEMBERS_PATH,
        json_body={
            "next": None,
            "results": [card("Félix", "felix@example.org"), card("Marie", "marie@example.org")],
        },
    )
    contacts.answer("POST", INTERACTIONS_PATH, status=204)

    with django_capture_on_commit_callbacks(execute=True):
        response = logged_in_client(user).get(MEMBERS_URL)

    assert response.status_code == 200
    assert [(member["kind"], member["id"]) for member in response.json()] == [
        ("user", str(felix.id)),
        ("user", "marie@example.org"),
    ]
    assert contacts.bodies(INTERACTIONS_PATH) == [
        {"kind": "share", "items": [{"uid": f"urn:uuid:{GROUP_ID}"}]}
    ]


def test_the_local_backend_has_no_groups(user):
    """Drive alone has no groups to list."""
    assert logged_in_client(user).get(MEMBERS_URL).status_code == 404


@pytest.mark.usefixtures("contacts_backend")
def test_a_malformed_group_id_is_not_found(user, contacts):
    """Only group ids reach Contacts."""
    response = logged_in_client(user).get(
        f"{URL}groups/not-a-uuid-at-all-not-a-uuid-at-all/members/"
    )

    assert response.status_code == 404
    assert not contacts.calls


@pytest.mark.usefixtures("contacts_backend")
def test_members_unavailable_answers_503(user, contacts):
    """No fallback for a group: the share modal tells the user to retry."""
    contacts.answer("GET", MEMBERS_PATH, status=503, json_body={})
    client = logged_in_client(user)
    # A 5xx is reported to Sentry through got_request_exception, which the
    # test client would re-raise instead of returning the response.
    client.raise_request_exception = False

    assert client.get(MEMBERS_URL).status_code == 503


def test_anonymous_users_cant_list_members():
    """Only for logged-in users."""
    assert APIClient().get(MEMBERS_URL).status_code == 401
