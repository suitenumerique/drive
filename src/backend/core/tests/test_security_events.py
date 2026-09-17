"""Check the real API producer contract and its connection to the rules engine."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import transaction

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient, APIRequestFactory

from core import factories, models
from core.api import exception_handler
from core.monitoring_utils import audit_access_change, log_audit_event
from core.services.security_bridge import process_batch
from core.services.security_rules import load_rules, validate_event


@pytest.fixture(name="audit_path")
def audit_path_fixture(settings, tmp_path):
    """Use the real logging handler with an isolated output file."""
    settings.SECURITY_AUDIT_ENABLED = True
    settings.SECURITY_AUDIT_PATH = str(tmp_path / "input" / "events.jsonl")
    return Path(settings.SECURITY_AUDIT_PATH)


def read_events(path):
    """Read complete JSON objects without tolerating log prefixes."""
    return [json.loads(line) for line in path.read_text().splitlines()]


def make_request():
    """Build a request with a fictitious attributable account, without a database."""
    request = APIRequestFactory().get(
        "/api/v1.0/items/example/",
        HTTP_X_REQUEST_ID="demo-request",
        HTTP_X_FORWARDED_FOR="untrusted-forwarded-value",
    )
    request.user = SimpleNamespace(pk=uuid4(), is_authenticated=True, full_name="Demo User")
    return request


def test_event_contract_and_disabled_collection(audit_path, settings):
    """Canonical UTC events include enrichment; disabled collection writes nothing."""
    request = make_request()
    settings.SECURITY_AUDIT_ENABLED = False
    log_audit_event("file_downloaded", request=request, resource_id="file", bytes=42)
    assert not audit_path.parent.exists()
    settings.SECURITY_AUDIT_ENABLED = True
    log_audit_event("file_downloaded", request=request, resource_id="file", bytes=42)
    entry = read_events(audit_path)[0]
    validate_event(entry)
    assert entry["timestamp"].endswith("Z")
    assert entry["actor"] == str(request.user.pk)
    assert entry["resource"] == "file"
    assert entry["context"]["bytes"] == 42
    assert entry["context"]["actor_full_name"] == "Demo User"
    assert entry["context"]["request_id"] == "demo-request"
    assert entry["context"]["ip"] == "127.0.0.1"
    assert "criticality" not in entry


def test_anonymous_requests_are_not_merged_into_one_actor(audit_path):
    """These per-account rules cannot attribute anonymous activity to a real account."""
    request = make_request()
    request.user = SimpleNamespace(is_authenticated=False)
    log_audit_event("permission_denied", request=request)
    assert not audit_path.exists()


@pytest.mark.parametrize("exception", [PermissionDenied(), DjangoPermissionDenied()])
def test_permission_denied_uses_response_and_nested_resource(audit_path, exception):
    """Both Django and DRF denials preserve the item's ID rather than an access-row ID."""
    request = make_request()
    view = SimpleNamespace(kwargs={"resource_id": "file", "pk": "access"})
    response = exception_handler(exception, {"request": request, "view": view})
    assert response.status_code == 403
    entry = read_events(audit_path)[0]
    validate_event(entry)
    assert entry["resource"] == "file"
    assert entry["action"] == "permission_denied"


def test_validation_errors_are_not_permission_denials(audit_path):
    """A bad request must not increment probing counters."""
    response = exception_handler(ValidationError("invalid"), {"request": make_request()})
    assert response.status_code == 400
    assert not audit_path.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "reason",
    ["user_quota_exceeded", "user_override_quota_exceeded", "organization_quota_exceeded"],
)
def test_quota_denials_do_not_produce_security_events(audit_path, reason):
    """An actual API upload refusal remains a 403 without feeding probing counters."""
    client = APIClient()
    client.force_authenticate(factories.UserFactory())
    with mock.patch("core.api.viewsets.get_entitlements_backend") as backend:
        backend.return_value.can_upload.return_value = {"result": False, "reason": reason}
        response = client.post(
            "/api/v1.0/items/", {"type": models.ItemTypeChoices.FILE, "filename": "demo.txt"}
        )
    assert response.status_code == 403
    assert response.json()["errors"][0]["code"] == reason
    assert not audit_path.exists()
    assert not models.Item.objects.exists()


def test_disk_failure_preserves_response_and_reports_gap(audit_path, caplog):
    """A failed audit write reports a diagnostic without breaking the API or dumping data."""
    audit_path.mkdir(parents=True)
    response = exception_handler(PermissionDenied(), {"request": make_request()})
    assert response.status_code == 403
    assert "Security audit write failed" in caplog.text
    assert "Demo User" not in caplog.text


@pytest.mark.django_db
def test_api_events_reach_alert_and_posthog_exports(audit_path, tmp_path, monkeypatch):
    """Actual API calls produce JSONL, two alert families, and capture-ready exports."""
    monkeypatch.setenv("SECURITY_MASS_DOWNLOAD_MINUTE_THRESHOLD", "3")
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, models.RoleChoices.OWNER)],
        size=64,
    )
    assert client.get(f"/api/v1.0/items/{item.pk}/download/").status_code == 302
    assert not audit_path.exists()  # Do not count the redirect and the media request twice.
    for _ in range(3):
        response = client.get(
            "/api/v1.0/items/media-auth/",
            HTTP_X_ORIGINAL_URL=f"/media/{item.file_key}",
            HTTP_X_ORIGINAL_METHOD="GET",
        )
        assert response.status_code == 200
        assert "Authorization" in response

    # Denied media URLs have no view kwargs: retain the resource parsed before rejection.
    for _ in range(5):
        denied = factories.ItemFactory(link_reach="restricted")
        for _ in range(2):
            response = client.get(
                "/api/v1.0/items/media-auth/",
                HTTP_X_ORIGINAL_URL=f"/media/item/{denied.pk}/unavailable.txt",
            )
            assert response.status_code == 403

    events = read_events(audit_path)
    assert len(events) == 13
    assert len({entry["id"] for entry in events}) == 13
    for entry in events:
        validate_event(entry)
        assert entry["actor"] == str(user.pk)
    assert events[0]["context"]["bytes"] == 64
    assert len({entry["resource"] for entry in events[3:]}) == 5
    rules = load_rules(Path(__file__).parents[1] / "security_rules.yaml")
    workdir = tmp_path / "processed"
    result = process_batch(audit_path, workdir, rules, 100, 65536)
    assert result["events"] == 13
    assert result["alerts"] == 2
    assert result["rejected"] == 0
    captures = [
        entry
        for path in (workdir / "batches").glob("*.posthog.jsonl")
        for entry in read_events(path)
    ]
    assert {entry["properties"]["rule"] for entry in captures} == {
        "mass_download",
        "permission_probing",
    }
    assert all(entry["event"] == "drive_security_alert" for entry in captures)


@pytest.mark.django_db
@pytest.mark.parametrize("preview,method", [(True, "GET"), (False, "HEAD")])
def test_preview_and_head_are_not_downloads(audit_path, preview, method):
    """Thumbnail reads and metadata checks must not create download alerts."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        mimetype="image/png",
        users=[(user, models.RoleChoices.OWNER)],
    )
    prefix = "preview/" if preview else ""
    response = client.get(
        "/api/v1.0/items/media-auth/",
        HTTP_X_ORIGINAL_URL=f"/media/{prefix}{item.file_key}",
        HTTP_X_ORIGINAL_METHOD=method,
    )
    assert response.status_code == 200
    assert not audit_path.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("size,range_header", [(None, ""), (64, "bytes=0-9")])
def test_unknown_or_partial_size_is_not_counted_as_full_bytes(audit_path, size, range_header):
    """Keep download counts without inventing byte totals for unknown or partial transfers."""
    user = factories.UserFactory()
    client = APIClient()
    client.force_authenticate(user)
    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        users=[(user, models.RoleChoices.OWNER)],
        size=size,
    )
    response = client.get(
        "/api/v1.0/items/media-auth/",
        HTTP_X_ORIGINAL_URL=f"/media/{item.file_key}",
        HTTP_RANGE=range_header,
    )
    assert response.status_code == 200
    entry = read_events(audit_path)[0]
    validate_event(entry)
    assert entry["action"] == "file_downloaded"
    assert "bytes" not in entry["context"]


@pytest.mark.django_db
def test_permission_lifecycle_and_noop(audit_path, django_capture_on_commit_callbacks):
    """Grants, changes and revocations retain actor/target and pre-mutation rights."""
    owner, target = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(users=[(owner, "owner")])
    client = APIClient()
    client.force_authenticate(owner)
    url = f"/api/v1.0/items/{item.pk}/accesses/"
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(url, {"user_id": str(target.pk), "role": "reader"}, format="json")
    assert response.status_code == 201
    access_url = f"{url}{response.json()['id']}/"
    with django_capture_on_commit_callbacks(execute=True):
        assert client.patch(access_url, {"role": "editor"}, format="json").status_code == 200
        assert client.patch(access_url, {"role": "editor"}, format="json").status_code == 200
        assert client.delete(access_url).status_code == 204
    events = read_events(audit_path)
    assert [event["action"] for event in events] == [
        "permission_changed",
        "share_created",
        "permission_changed",
        "permission_changed",
    ]
    assert [event["context"]["new_role"] for event in events] == [
        "reader",
        "reader",
        "editor",
        None,
    ]
    assert events[0]["context"]["old_role"] is None
    assert events[-1]["context"]["old_role"] == "editor"
    for event in events:
        validate_event(event)
        assert event["actor"] == str(owner.pk)
        assert event["context"]["target_actor"] == str(target.pk)
        assert event["context"]["actor_effective_role"] == "owner"


@pytest.mark.django_db
def test_permission_rollback_has_no_event(audit_path, django_capture_on_commit_callbacks):
    """Aborted transactions discard queued publication rather than producing false incidents."""
    request = make_request()
    with django_capture_on_commit_callbacks(execute=True):
        with transaction.atomic():
            audit_access_change(
                request,
                SimpleNamespace(pk="file"),
                effective_role="owner",
                old_role="reader",
                new_role="editor",
                target_actor="beneficiary",
            )
            transaction.set_rollback(True)
    assert not audit_path.exists()


@pytest.mark.django_db
def test_administrator_role_is_normalized(audit_path, django_capture_on_commit_callbacks):
    """Drive's administrator label becomes admin without inventing a privilege increase."""
    request = make_request()
    with django_capture_on_commit_callbacks(execute=True):
        audit_access_change(
            request,
            SimpleNamespace(pk="file"),
            effective_role="administrator",
            old_role="reader",
            new_role="administrator",
            target_actor=request.user.pk,
        )
    context = read_events(audit_path)[0]["context"]
    assert context["actor_effective_role"] == "admin"
    assert context["new_role"] == "admin"


@pytest.mark.django_db
def test_batch_link_and_invitation_shares(audit_path, settings, django_capture_on_commit_callbacks):
    """Each successful share emits once; skipped rows and repeated link settings emit nothing."""
    settings.ALLOW_SHARE_IMPORT_FILE = True
    owner, target = factories.UserFactory.create_batch(2)
    item = factories.ItemFactory(users=[(owner, "owner")])
    client = APIClient()
    client.force_authenticate(owner)
    rows = {
        "rows": [
            {"email": target.email, "role": "reader"},
            {"email": "pending@example.invalid", "role": "reader"},
        ]
    }
    with django_capture_on_commit_callbacks(execute=True):
        for _ in range(2):
            assert (
                client.post(
                    f"/api/v1.0/items/{item.pk}/batch-share/", rows, format="json"
                ).status_code
                == 200
            )
        for _ in range(2):
            assert (
                client.put(
                    f"/api/v1.0/items/{item.pk}/link-configuration/",
                    {"link_reach": "public", "link_role": "reader"},
                    format="json",
                ).status_code
                == 200
            )
        assert (
            client.post(
                f"/api/v1.0/items/{item.pk}/invitations/",
                {"email": "invitation@example.invalid", "role": "reader"},
                format="json",
            ).status_code
            == 201
        )
    events = read_events(audit_path)
    assert sum(event["action"] == "share_created" for event in events) == 4
    assert sum(event["action"] == "permission_changed" for event in events) == 2
    assert "pending@example.invalid" not in audit_path.read_text()


@pytest.mark.django_db
def test_team_and_inherited_access_changes(audit_path, django_capture_on_commit_callbacks):
    """Team grants have no invented user target; restoring inheritance remains a change."""
    owner, target = factories.UserFactory.create_batch(2)
    root = factories.ItemFactory(
        type=models.ItemTypeChoices.FOLDER, users=[(owner, "owner"), (target, "reader")]
    )
    item = factories.ItemFactory(parent=root)
    access = factories.UserItemAccessFactory(item=item, user=target, role="editor")
    client = APIClient()
    client.force_authenticate(owner)
    with django_capture_on_commit_callbacks(execute=True):
        response = client.patch(
            f"/api/v1.0/items/{item.pk}/accesses/{access.pk}/", {"role": "reader"}, format="json"
        )
        assert response.status_code == 204
        response = client.post(
            f"/api/v1.0/items/{root.pk}/accesses/",
            {"team": "audit-test-team", "role": "reader"},
            format="json",
        )
        assert response.status_code == 201
    events = read_events(audit_path)
    assert events[0]["context"]["operation"] == "restore_inheritance"
    assert events[0]["context"]["actor_effective_role"] == "owner"
    assert events[1]["context"]["target_actor"] is None
    assert events[1]["context"]["target_team"] == "audit-test-team"
