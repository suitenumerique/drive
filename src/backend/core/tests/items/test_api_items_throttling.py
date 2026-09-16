"""
Tests for items API endpoint in drive's core app: creation throttling
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from core import factories, models

pytestmark = pytest.mark.django_db

BURST_RATE_LIMIT = 3


@pytest.fixture(name="throttle_rates")
def fixture_throttle_rates(settings):
    """
    Apply low creation rates for the duration of a test.

    The rates live in a nested dictionary that the settings fixture cannot roll
    back, so they are restored here: leaking them would throttle every other test
    creating items.
    """
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    original_rates = rates.copy()

    def _apply(burst=f"{BURST_RATE_LIMIT:d}/minute", sustained="1000/hour"):
        rates["item_create_burst"] = burst
        rates["item_create_sustained"] = sustained

    yield _apply

    rates.clear()
    rates.update(original_rates)


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "my folder", "type": models.ItemTypeChoices.FOLDER},
        {"filename": "my file.txt", "type": models.ItemTypeChoices.FILE, "size": 8},
    ],
)
def test_api_items_throttling_create(throttle_rates, payload):
    """
    Creating items at the root should be throttled whatever the item type: only
    files are bounded by the upload entitlement, folders are not bounded at all.
    """
    throttle_rates()

    client = APIClient()
    client.force_login(factories.UserFactory())

    for _i in range(BURST_RATE_LIMIT):
        response = client.post("/api/v1.0/items/", payload, format="json")
        assert response.status_code == 201

    response = client.post("/api/v1.0/items/", payload, format="json")

    assert response.status_code == 429
    assert response.json()["errors"][0]["code"] == "throttled"
    assert models.Item.objects.count() == BURST_RATE_LIMIT


def test_api_items_throttling_children_create(throttle_rates):
    """Creating children should be throttled as well, the route does not matter."""
    throttle_rates()

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, models.RoleChoices.OWNER)]
    )
    url = f"/api/v1.0/items/{parent.id!s}/children/"
    payload = {"title": "my folder", "type": models.ItemTypeChoices.FOLDER}

    for _i in range(BURST_RATE_LIMIT):
        response = client.post(url, payload, format="json")
        assert response.status_code == 201

    response = client.post(url, payload, format="json")

    assert response.status_code == 429
    assert parent.children().count() == BURST_RATE_LIMIT


def test_api_items_throttling_create_and_children_share_one_budget(throttle_rates):
    """
    The creation routes should count against the same budget, or a client could
    multiply its allowance by alternating between them.
    """
    throttle_rates()

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, models.RoleChoices.OWNER)]
    )
    payload = {"title": "my folder", "type": models.ItemTypeChoices.FOLDER}

    for _i in range(2):
        response = client.post("/api/v1.0/items/", payload, format="json")
        assert response.status_code == 201

    response = client.post(f"/api/v1.0/items/{parent.id!s}/children/", payload, format="json")
    assert response.status_code == 201

    response = client.post(f"/api/v1.0/items/{parent.id!s}/children/", payload, format="json")

    assert response.status_code == 429


def test_api_items_throttling_duplicate(throttle_rates):
    """Duplicating an item creates a new one, so it should be throttled too."""
    throttle_rates()

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="text/plain",
        filename="myfile.txt",
        users=[(user, models.RoleChoices.OWNER)],
    )
    url = f"/api/v1.0/items/{item.id!s}/duplicate/"

    with mock.patch("core.tasks.item.duplicate_file.delay"):
        for _i in range(BURST_RATE_LIMIT):
            response = client.post(url)
            assert response.status_code == 201

        response = client.post(url)

    assert response.status_code == 429


def test_api_items_throttling_sustained_rate(throttle_rates):
    """The sustained rate should cap the long run, even under the burst rate."""
    throttle_rates(burst="1000/minute", sustained=f"{BURST_RATE_LIMIT:d}/hour")

    client = APIClient()
    client.force_login(factories.UserFactory())
    payload = {"title": "my folder", "type": models.ItemTypeChoices.FOLDER}

    for _i in range(BURST_RATE_LIMIT):
        response = client.post("/api/v1.0/items/", payload, format="json")
        assert response.status_code == 201

    response = client.post("/api/v1.0/items/", payload, format="json")

    assert response.status_code == 429


def test_api_items_throttling_children_list_not_throttled(throttle_rates):
    """Listing children shares its action with the creation route but reads only."""
    throttle_rates()

    user = factories.UserFactory()
    client = APIClient()
    client.force_login(user)

    parent = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(user, models.RoleChoices.OWNER)]
    )
    url = f"/api/v1.0/items/{parent.id!s}/children/"

    for _i in range(BURST_RATE_LIMIT + 1):
        response = client.get(url)
        assert response.status_code == 200


def test_api_items_throttling_is_per_user(throttle_rates):
    """One user exhausting their budget should not throttle anybody else."""
    throttle_rates()

    client = APIClient()
    client.force_login(factories.UserFactory())
    payload = {"title": "my folder", "type": models.ItemTypeChoices.FOLDER}

    for _i in range(BURST_RATE_LIMIT):
        assert client.post("/api/v1.0/items/", payload, format="json").status_code == 201

    assert client.post("/api/v1.0/items/", payload, format="json").status_code == 429

    client.force_login(factories.UserFactory())

    response = client.post("/api/v1.0/items/", payload, format="json")

    assert response.status_code == 201
