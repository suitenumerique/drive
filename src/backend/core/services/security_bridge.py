"""Bounded JSONL processing with restart-safe state and local PostHog exports.

No network calls are made here. A single local/shared POSIX directory owns the
checkpoint, lock, pending batch, engine state, and immutable batch filenames.
"""

import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from core.services.security_rules import SEVERITIES, SecurityRules, utc_timestamp


def _actor(actor):
    """Normalize an identified actor without inventing a display name."""
    if (
        not isinstance(actor, dict)
        or not isinstance(actor.get("id"), str)
        or not actor["id"].strip()
    ):
        raise ValueError("actor must be an object with a non-empty id")
    name = actor.get("full_name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise ValueError("actor.full_name must be a non-empty string or null")
    return {"id": actor["id"], "full_name": name}


def normalize_alert(value, fallback_id):
    """Accept the team's alert contract, including custom YAML rule names."""
    if not isinstance(value, dict):
        raise ValueError("alert must be an object")
    for key in ("rule", "explanation", "recommendation"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    actor = _actor(value.get("actor"))
    if value.get("severity") not in SEVERITIES:
        raise ValueError("severity must be low, medium, high, or critical")
    for field, minimum in (("count", 1), ("threshold", 1), ("window_seconds", 0)):
        number = value.get(field)
        if not isinstance(number, int) or isinstance(number, bool) or number < minimum:
            raise ValueError(f"{field} must be an integer >= {minimum}")
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        raise ValueError("evidence must be a list of event identifiers")
    utc_timestamp(value.get("detected_at"))
    identity = value.get("alert_id", fallback_id)
    if not isinstance(identity, str) or not identity:
        raise ValueError("alert_id must be a non-empty string")
    try:
        identity = str(UUID(identity))
    except ValueError:
        identity = str(uuid5(NAMESPACE_URL, f"drive-alert:{identity}"))
    alert = {
        key: value[key]
        for key in (
            "rule",
            "severity",
            "detected_at",
            "window_seconds",
            "count",
            "threshold",
            "evidence",
            "explanation",
            "recommendation",
        )
    }
    for key in (
        "condition",
        "metric",
        "observed_value",
        "distinct_resources",
        "bytes_complete",
        "evidence_truncated",
    ):
        if key in value:
            alert[key] = value[key]
    alert.update(alert_id=identity, actor=actor)
    return alert


def posthog_event(alert):
    """Return one optional capture-event export, excluding project credentials."""
    return {
        "event": "drive_security_alert",
        "distinct_id": alert["actor"]["id"],
        "timestamp": alert["detected_at"],
        "uuid": alert["alert_id"],
        "properties": dict(alert),
    }


def _atomic_write(path, text):
    """Publish a complete file; never expose a half-written JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        output.write(text)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _finish_batch(directory, pending):
    """Publish outputs before advancing the checkpoint; replay a pending journal safely."""
    for kind in ("alerts", "posthog", "rejected"):
        _atomic_write(
            directory / "batches" / f"{pending['name']}.{kind}.jsonl",
            "".join(_json(record) + "\n" for record in pending[kind]),
        )
    _atomic_write(directory / "state.json", _json(pending["state"]))
    (directory / "pending.json").unlink()
    return pending["result"]


def _anchor(source, offset):
    source.seek(max(0, offset - 128))
    return hashlib.sha256(source.read(min(128, offset))).hexdigest()


def _initial_state(input_path, source):
    stat = os.fstat(source.fileno())
    return {
        "version": 1,
        "source": [str(input_path.resolve()), stat.st_dev, stat.st_ino],
        "source_id": str(uuid4()),
        "offset": 0,
        "anchor": _anchor(source, 0),
        "engine": {},
    }


def _read_batch(source, state, engine, batch_size, max_line_bytes):
    """Process complete lines only; bad records are quarantined without blocking the rest."""
    start = state["offset"]
    source.seek(start)
    result = {"status": "processed", "lines": 0, "events": 0, "alerts": 0, "rejected": 0}
    alerts, rejected = [], []
    for _ in range(batch_size):
        offset = source.tell()
        line = source.readline(max_line_bytes + 1)
        if len(line) > max_line_bytes:
            raise ValueError(f"line at byte {offset} exceeds max_line_bytes")
        if not line.endswith(b"\n"):
            break
        result["lines"] += 1
        fallback_id = str(uuid5(UUID(state["source_id"]), str(offset)))
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("each line must be a JSON object")
            if "action" in record and "rule" in record:
                raise ValueError("line must be an event OR an alert, not both")
            if "action" in record:
                detected = engine.process(record, fallback_id)
                result["events"] += 1
            else:
                detected = [record]
            alerts.extend(normalize_alert(item, fallback_id) for item in detected)
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            rejected.append(
                {
                    "offset": offset,
                    "reason": str(error),
                    "raw": line.decode("utf-8", errors="replace").rstrip("\n"),
                }
            )
        state["offset"] = source.tell()
    state["anchor"] = _anchor(source, state["offset"])
    result.update(alerts=len(alerts), rejected=len(rejected))
    result["batch"] = f"{state['source_id']}-{start:016d}-{state['offset']:016d}"
    return {
        "name": result["batch"],
        "state": state,
        "alerts": alerts,
        "posthog": [posthog_event(alert) for alert in alerts],
        "rejected": rejected,
        "result": result,
    }


def process_batch(input_path, directory, rules, batch_size=100, max_line_bytes=65536):
    """Process at most batch_size records; callers may schedule this periodically.

    File replacement/truncation is intentionally refused: use a fresh directory
    for a new source or changed rules. All workers must share this same directory.
    """
    if batch_size < 1 or max_line_bytes < 1:
        raise ValueError("batch_size and max_line_bytes must be positive")
    directory, input_path = Path(directory), Path(input_path)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "bridge.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy"}
        pending_path = directory / "pending.json"
        if pending_path.exists():
            result = _finish_batch(directory, json.loads(pending_path.read_text(encoding="utf-8")))
            return {**result, "recovered": True}
        if not input_path.exists():
            return {"status": "waiting_for_input"}
        state_path = directory / "state.json"
        with input_path.open("rb") as source:
            current = _initial_state(input_path, source)
            state = (
                json.loads(state_path.read_text(encoding="utf-8"))
                if state_path.exists()
                else current
            )
            if state.get("version") != 1 or state["source"] != current["source"]:
                raise ValueError(
                    "input replaced: use a fresh work directory after draining the old file"
                )
            if (
                os.fstat(source.fileno()).st_size < state["offset"]
                or _anchor(source, state["offset"]) != state["anchor"]
            ):
                raise ValueError("input truncated or rewritten: use a fresh work directory")
            engine = SecurityRules(rules, state["engine"])
            pending = _read_batch(source, state, engine, batch_size, max_line_bytes)
        if not pending["result"]["lines"]:
            return {"status": "waiting_for_complete_line"}
        # Save everything needed to finish, including the engine's windows, before
        # publishing outputs. A killed worker can resume without running rules twice.
        _atomic_write(pending_path, _json(pending))
        return _finish_batch(directory, pending)


def publish_alerts(directory, stream=None):
    """Flush pending alert batches to stdout, then advance an independent cursor.

    A crash after flush may repeat an alert, but never acknowledges it beforehand.
    Collectors should deduplicate by alert_id. This is local handoff, not a remote
    collector acknowledgement or a guarantee of external log retention.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stream = sys.stdout if stream is None else stream
    with (directory / "stdout.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        cursor = directory / "stdout-state.json"
        last = (
            json.loads(cursor.read_text(encoding="utf-8"))["last_batch"] if cursor.exists() else ""
        )
        published = 0
        for path in sorted((directory / "batches").glob("*.alerts.jsonl")):
            if path.name <= last:
                continue
            payload = path.read_text(encoding="utf-8")
            stream.write(payload)
            stream.flush()
            _atomic_write(cursor, _json({"last_batch": path.name}))
            published += len(payload.splitlines())
        return published
