"""Opt-in demo delivery, independent from Drive's global PostHog client.

Only analyzed outbox events leave this module. Delivery state is separate from
analysis and stdout cursors; no token, response body or payload is logged.
"""

import fcntl
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import requests

from core.services.security_rules import utc_timestamp

MAX_EVENT_BYTES = 1024 * 1024
MAX_BATCH_BYTES = 5 * 1024 * 1024


class DeliveryError(Exception):
    """A sanitized delivery failure whose batch must remain pending."""


@dataclass(frozen=True)
class DemoDestination:
    """Explicit destination; never falls back to POSTHOG_KEY or POSTHOG_HOST."""

    host: str
    key: str = field(repr=False)
    batch_size: int = 100
    timeout_seconds: int = 10

    @classmethod
    def from_settings(cls, settings):
        """Read only demo settings and guard against reusing Drive's project token."""
        key = settings.SECURITY_DEMO_POSTHOG_KEY
        if not key or not isinstance(key, str) or not key.strip():
            raise ValueError("SECURITY_DEMO_POSTHOG_KEY is required when demo sending is enabled")
        if key.strip() == str(settings.POSTHOG_KEY or "").strip():
            raise ValueError("demo PostHog key must differ from Drive's POSTHOG_KEY")
        return cls(
            host=settings.SECURITY_DEMO_POSTHOG_HOST,
            key=key.strip(),
            batch_size=settings.SECURITY_DEMO_POSTHOG_BATCH_SIZE,
            timeout_seconds=settings.SECURITY_DEMO_POSTHOG_TIMEOUT_SECONDS,
        )

    def endpoint(self):
        """Require an explicit ingestion origin; plain HTTP is local-test only."""
        parsed = urlsplit(self.host)
        local_http = parsed.scheme == "http" and parsed.hostname in (
            "127.0.0.1",
            "::1",
            "localhost",
        )
        invalid_origin = not parsed.hostname or (parsed.scheme != "https" and not local_http)
        extra_url_parts = any((parsed.username, parsed.password, parsed.query, parsed.fragment))
        if invalid_origin or extra_url_parts or parsed.path not in ("", "/"):
            raise ValueError("demo host must be an HTTPS origin (HTTP allowed on loopback only)")
        if not self.key or not 1 <= self.batch_size <= 1000 or not 1 <= self.timeout_seconds <= 60:
            raise ValueError("demo key, batch size (1..1000) and timeout (1..60) are required")
        return self.host.rstrip("/") + "/batch/"


def _save(path, state):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(state, output, allow_nan=False)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def _capture_event(value):
    """Validate required fields locally: some invalid events receive HTTP 200."""
    if not isinstance(value, dict) or value.get("event") != "drive_security_alert":
        raise ValueError("demo outbox accepts only drive_security_alert events")
    actor = value.get("distinct_id")
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 200:
        raise ValueError("PostHog distinct_id must contain 1..200 characters")
    utc_timestamp(value.get("timestamp"))
    UUID(value.get("uuid", ""))
    properties = value.get("properties")
    if not isinstance(properties, dict) or not properties.get("rule"):
        raise ValueError("demo event must contain an analyzed alert")
    # No person updates/aliases: this demo is an event stream in a separate project.
    properties = {key: item for key, item in properties.items() if not key.startswith("$")}
    properties.update({"$process_person_profile": False, "security_demo": True})
    return {
        **{key: value[key] for key in ("event", "distinct_id", "timestamp", "uuid")},
        "properties": properties,
    }


def _pending(directory, state, limit):
    """Read bounded event records without acknowledging them before HTTP success."""
    files = sorted((directory / "batches").glob("*.posthog.jsonl"))
    previous = state.get("file", "")
    if previous and not (directory / "batches" / previous).is_file():
        raise ValueError("delivery cursor file is missing; restore it before sending")
    events, total = [], 0
    position = {"file": previous, "offset": state.get("offset", 0)}
    for path in files:
        if path.name < previous:
            continue
        offset = state.get("offset", 0) if path.name == previous else 0
        if path.stat().st_size < offset:
            raise ValueError("delivery outbox was truncated")
        with path.open("rb") as source:
            source.seek(offset)
            while True:
                if len(events) >= limit:
                    return events, position
                line = source.readline(MAX_EVENT_BYTES + 1)
                if not line:
                    position = {"file": path.name, "offset": source.tell()}
                    break
                if len(line) > MAX_EVENT_BYTES or not line.endswith(b"\n"):
                    raise ValueError("outbox event is oversized or incomplete")
                event = _capture_event(json.loads(line))
                size = len(json.dumps(event, ensure_ascii=False, allow_nan=False).encode("utf-8"))
                if events and total + size > MAX_BATCH_BYTES:
                    return events, position
                events.append(event)
                total += size
                position = {"file": path.name, "offset": source.tell()}
    return events, position


def _post(destination, events):
    """Send synchronously so the local cursor only moves after capture acknowledgement."""
    payload = json.dumps(
        {"api_key": destination.key, "batch": events}, ensure_ascii=False, allow_nan=False
    )
    try:
        with requests.post(
            destination.endpoint(),
            data=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=(min(5, destination.timeout_seconds), destination.timeout_seconds),
            allow_redirects=False,
        ) as response:
            if not 200 <= response.status_code < 300:
                raise DeliveryError(f"PostHog HTTP {response.status_code}; batch retained")
            try:
                acknowledgement = response.json()
            except ValueError:
                raise DeliveryError("PostHog acknowledgement is not JSON; batch retained") from None
            if acknowledgement != 1 and not (
                isinstance(acknowledgement, dict) and acknowledgement.get("status") == 1
            ):
                raise DeliveryError("PostHog did not acknowledge capture; batch retained")
    except requests.RequestException:
        raise DeliveryError("PostHog connection failed; batch retained") from None


def send_demo_batch(directory, destination):
    """Deliver at most one batch, with persistent retry state and destination binding."""
    endpoint = destination.endpoint()
    binding = hashlib.sha256(f"{endpoint}\n{destination.key}".encode()).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cursor = directory / "demo-posthog-state.json"
    with (directory / "demo-posthog.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "sent": 0}
        state = json.loads(cursor.read_text()) if cursor.exists() else {"destination": binding}
        if state.get("destination") != binding:
            raise ValueError(
                "demo destination changed: use a new work directory for the new project"
            )
        if time.time() < state.get("retry_at", 0):
            return {"status": "backoff", "sent": 0}
        events, position = _pending(directory, state, destination.batch_size)
        if not events:
            _save(cursor, {**state, **position})
            return {"status": "caught_up", "sent": 0}
        # Bind the cursor before transmission, even if the first attempt is interrupted.
        _save(cursor, state)
        try:
            _post(destination, events)
        except DeliveryError as error:
            failures = min(state.get("failures", 0) + 1, 6)
            delay = min(300, 10 * (2 ** (failures - 1)))
            _save(cursor, {**state, "failures": failures, "retry_at": time.time() + delay})
            return {"status": "retry", "sent": 0, "retry_seconds": delay, "error": str(error)}
        _save(cursor, {"destination": binding, **position, "failures": 0, "retry_at": 0})
        return {"status": "accepted", "sent": len(events)}
