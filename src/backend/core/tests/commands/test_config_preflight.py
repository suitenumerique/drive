"""Tests for deterministic config_preflight output and validations."""

from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.test.utils import override_settings

# pylint: disable=missing-function-docstring


def _run_preflight() -> tuple[int, dict]:
    output = StringIO()
    try:
        call_command("config_preflight", stdout=output)
        code = 0
    except SystemExit as exc:
        code = int(getattr(exc, "code", 1) or 1)
    return code, json.loads(output.getvalue())


def test_config_preflight_requires_endpoint_url(monkeypatch):
    monkeypatch.delenv("AWS_S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_S3_DOMAIN_REPLACE", raising=False)

    code, payload = _run_preflight()

    assert code == 1
    assert payload["ok"] is False
    assert payload["errors"][0]["field"] == "AWS_S3_ENDPOINT_URL"
    assert payload["errors"][0]["failure_class"] == "config.s3.endpoint_url.missing"
    assert isinstance(payload["errors"][0]["next_action_hint"], str)
    assert payload["errors"][0]["next_action_hint"]


def test_config_preflight_rejects_endpoint_url_with_userinfo(monkeypatch):
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "http://user:pass@example.com")
    monkeypatch.delenv("AWS_S3_DOMAIN_REPLACE", raising=False)

    code, payload = _run_preflight()

    assert code == 1
    assert payload["errors"][0]["field"] == "AWS_S3_ENDPOINT_URL"
    assert payload["errors"][0]["failure_class"] == "config.s3.endpoint_url.invalid"


def test_config_preflight_rejects_domain_replace_http_in_https_only_posture(
    monkeypatch,
):
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "http://seaweedfs-s3:8333")
    monkeypatch.setenv("AWS_S3_DOMAIN_REPLACE", "http://public.example.com")

    with override_settings(
        SECURE_SSL_REDIRECT=True,
        DEBUG=False,
        DRIVE_ALLOW_INSECURE_HTTP=True,
    ):
        code, payload = _run_preflight()

    assert code == 1
    assert payload["errors"][0]["field"] == "AWS_S3_DOMAIN_REPLACE"
    assert (
        payload["errors"][0]["failure_class"]
        == "config.s3.domain_replace.https_required"
    )


def test_config_preflight_errors_are_sorted_by_field(monkeypatch):
    monkeypatch.delenv("AWS_S3_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_S3_DOMAIN_REPLACE", "not-a-url")

    code, payload = _run_preflight()

    assert code == 1
    fields = [err["field"] for err in payload["errors"]]
    assert fields == sorted(fields)


def test_config_preflight_manual_checks_are_deterministic(monkeypatch):
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", "http://seaweedfs-s3:8333")
    monkeypatch.delenv("AWS_S3_DOMAIN_REPLACE", raising=False)

    code, payload = _run_preflight()

    assert code == 0
    assert payload["ok"] is True
    assert [c["id"] for c in payload["manual_checks"]] == [
        "edge.media.contract",
        "edge.media.signed_host_invariants",
    ]
