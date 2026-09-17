"""Behavioral checks for windows, incremental reading, recovery, and scheduling."""

import fcntl
import io
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from django.core.management import call_command

import pytest

from core.services import security_bridge
from core.services.security_rules import SecurityRules, load_rules, utc_timestamp
from core.tasks.security_monitoring import process_security_logs

from drive.settings import Base


@pytest.fixture(name="rules")
def rules_fixture():
    """Use small thresholds while exercising the real algorithm."""
    rules = load_rules(Path(__file__).parents[1] / "security_rules.yaml")
    for rule in rules:
        rule["conditions"] = [rule["conditions"][0]]
        condition = rule["conditions"][0]
        condition["threshold"] = 3
        condition["window_seconds"] = 10
        condition["min_distinct_resources"] = 0
    return rules


def event(second, actor="alice", action="file_downloaded", **context):
    """Chronological synthetic event; each second has a distinct ID per actor/action."""
    timestamp = datetime(2026, 9, 15, tzinfo=timezone.utc) + timedelta(seconds=second)
    return {
        "id": f"{actor}-{action}-{second}",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "actor": actor,
        "action": action,
        "resource": f"file-{second}",
        "context": context,
    }


def append_events(path, events):
    """Append complete JSONL records, as the producer should."""
    with path.open("a", encoding="utf-8") as output:
        for entry in events:
            output.write(json.dumps(entry) + "\n")


def read_outputs(directory, kind="alerts"):
    """Flatten all completed batch files of one kind."""
    return [
        json.loads(line)
        for path in sorted((directory / "batches").glob(f"*.{kind}.jsonl"))
        for line in path.read_text().splitlines()
    ]


def test_window_boundary_and_rearm(rules):
    """Include the exact cutoff and emit once until activity drops below the threshold."""
    engine = SecurityRules(rules, {})
    assert not engine.process(event(0), "unused")
    assert not engine.process(event(1), "unused")
    alerts = engine.process(event(10), "unused")
    assert alerts[0]["count"] == 3
    assert alerts[0]["evidence"] == [
        "alice-file_downloaded-0",
        "alice-file_downloaded-1",
        "alice-file_downloaded-10",
    ]
    assert not engine.process(event(11), "unused")
    assert not engine.process(event(30), "unused")
    assert not engine.process(event(31), "unused")
    assert len(engine.process(event(32), "unused")) == 1


def test_actors_slow_activity_and_duplicate_ids(rules):
    """Do not combine accounts, count a duplicate twice, or retain expired downloads."""
    engine = SecurityRules(rules, {})
    for entry in [event(0), event(0), event(1, "bob"), event(2), event(20)]:
        assert not engine.process(entry, "unused")


@pytest.mark.parametrize(
    "action,rule_name",
    [
        ("file_downloaded", "mass_download"),
        ("permission_denied", "permission_probing"),
    ],
)
def test_rules_do_not_mix_actions(rules, action, rule_name):
    """Each rule only counts its own action."""
    engine = SecurityRules(rules, {})
    engine.process(event(0, action="share_created"), "unused")
    results = []
    for second in range(1, 4):
        results.extend(engine.process(event(second, action=action), "unused"))
    assert [alert["rule"] for alert in results] == [rule_name]


def test_escalation_requires_self_grant_and_increased_role(rules):
    """Missing context, another beneficiary, and downgrades are not self-escalations."""
    engine = SecurityRules(rules, {})
    contexts = [
        {},
        {"target_actor": "bob", "old_role": "reader", "new_role": "admin"},
        {"target_actor": "alice", "old_role": "admin", "new_role": "reader"},
    ]
    for second, context in enumerate(contexts):
        assert not engine.process(event(second, action="permission_changed", **context), "unused")
    for second in (3, 4, 5):
        alerts = engine.process(
            event(
                second,
                action="permission_changed",
                target_actor="alice",
                old_role="reader",
                actor_effective_role="reader",
                new_role="admin",
            ),
            "unused",
        )
    assert alerts[0]["rule"] == "permission_escalation"


def test_windows_survive_batches_and_restarts(tmp_path, rules):
    """An attack split over separate task invocations must still trigger."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(i) for i in range(4)])
    first = security_bridge.process_batch(source, directory, rules, batch_size=2)
    assert first["alerts"] == 0
    second = security_bridge.process_batch(source, directory, rules, batch_size=2)
    assert second["alerts"] == 1
    assert (
        security_bridge.process_batch(source, directory, rules)["status"]
        == "waiting_for_complete_line"
    )
    assert len(read_outputs(directory)) == 1
    exported = read_outputs(directory, "posthog")[0]
    assert exported["distinct_id"] == "alice"
    assert exported["timestamp"] == event(2)["timestamp"]
    assert exported["uuid"] == read_outputs(directory)[0]["alert_id"]


def test_partial_line_and_bad_records(tmp_path, rules):
    """Wait for an unfinished write, quarantine malformed input, then keep processing."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    source.write_text('{"actor":')
    assert (
        security_bridge.process_batch(source, directory, rules)["status"]
        == "waiting_for_complete_line"
    )
    with source.open("a") as output:
        output.write("broken}\n")
    invalid = event(0)
    invalid["timestamp"] = "2026-09-15T00:00:00+00:00"
    append_events(source, [invalid, event(1), event(2), event(3)])
    result = security_bridge.process_batch(source, directory, rules)
    assert result["rejected"] == 2
    assert result["alerts"] == 1
    assert len(read_outputs(directory, "rejected")) == 2


@pytest.mark.parametrize("legacy", [False, True])
def test_docker_file_identity_change_preserves_checkpoint(tmp_path, rules, legacy):
    """A remount must not replay alerts or reset the engine/delivery cursors."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(i) for i in range(3)])
    security_bridge.process_batch(source, directory, rules)
    state_path = directory / "state.json"
    state = json.loads(state_path.read_text())
    state["source"][1:] = [-1, -1]
    if legacy:
        del state["head_anchor"]
    state_path.write_text(json.dumps(state))
    for name in ("stdout-state.json", "posthog-state.json", "digest-state.json"):
        (directory / name).write_text('{"unchanged": true}')
    before = {p.name: p.read_bytes() for p in (directory / "batches").iterdir()}

    result = security_bridge.process_batch(source, directory, rules)

    assert result["status"] == "waiting_for_complete_line"
    resumed = json.loads(state_path.read_text())
    for key in ("source_id", "offset", "engine", "anchor"):
        assert resumed[key] == state[key]
    assert resumed["source"][1:] == [source.stat().st_dev, source.stat().st_ino]
    assert "head_anchor" in resumed
    assert before == {p.name: p.read_bytes() for p in (directory / "batches").iterdir()}
    for name in ("stdout-state.json", "posthog-state.json", "digest-state.json"):
        assert (directory / name).read_text() == '{"unchanged": true}'


def test_identical_file_remount_keeps_detection_window(tmp_path, rules):
    """New events after a changed inode still complete the existing window."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(0), event(1)])
    security_bridge.process_batch(source, directory, rules)
    replacement = tmp_path / "copy.jsonl"
    replacement.write_bytes(source.read_bytes())
    replacement.replace(source)
    append_events(source, [event(2)])
    result = security_bridge.process_batch(source, directory, rules)
    assert result["events"] == 1
    assert result["alerts"] == 1
    assert len(read_outputs(directory)) == 1


def test_rewritten_head_is_refused_even_when_tail_matches(tmp_path, rules):
    """Matching final bytes must not hide an edit to the start of the stream."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(i) for i in range(3)])
    security_bridge.process_batch(source, directory, rules)
    original = source.read_bytes()
    changed = original.replace(b"alice", b"bruce", 1)
    assert changed[-128:] == original[-128:]
    replacement = tmp_path / "rewritten.jsonl"
    replacement.write_bytes(changed)
    replacement.replace(source)
    with pytest.raises(ValueError, match="truncated or rewritten"):
        security_bridge.process_batch(source, directory, rules)


def test_pending_batch_recovers_without_duplicate_outputs(tmp_path, rules, monkeypatch):
    """A crash after output publication must not rerun the detector or duplicate its output."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(i) for i in range(3)])
    original = security_bridge._atomic_write  # pylint: disable=protected-access

    def interrupted_write(path, text):
        if path.name == "state.json":
            raise OSError("simulated interrupted checkpoint")
        original(path, text)

    monkeypatch.setattr(security_bridge, "_atomic_write", interrupted_write)
    with pytest.raises(OSError, match="interrupted checkpoint"):
        security_bridge.process_batch(source, directory, rules)
    monkeypatch.setattr(security_bridge, "_atomic_write", original)
    # Recovery also works after changing batch size: the pending journal fixes its boundaries.
    result = security_bridge.process_batch(source, directory, rules, batch_size=1)
    assert result["recovered"] is True
    assert len(read_outputs(directory)) == 1
    assert not (directory / "pending.json").exists()


def test_refuse_rewritten_file_and_changed_rules(tmp_path, rules):
    """Do not silently skip records after a reset or mix different threshold histories."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(0)])
    security_bridge.process_batch(source, directory, rules)
    changed = deepcopy(rules)
    changed[0]["conditions"][0]["threshold"] = 4
    with pytest.raises(ValueError, match="rules changed"):
        security_bridge.process_batch(source, directory, changed)
    source.write_text("")
    with pytest.raises(ValueError, match="truncated"):
        security_bridge.process_batch(source, directory, rules)


def test_only_one_task_per_work_directory(tmp_path, rules):
    """A second reader does not advance the shared checkpoint."""
    with (tmp_path / "bridge.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert security_bridge.process_batch(tmp_path / "events", tmp_path, rules) == {
            "status": "busy"
        }


def test_accept_teammate_alert_without_running_rules(tmp_path, rules):
    """Allow replacing our engine with the teammate's stdout contract."""
    source, directory = tmp_path / "alerts.jsonl", tmp_path / "output"
    alert = {
        "rule": "mass_download",
        "actor": {"id": "alice", "full_name": "Alice Example"},
        "severity": "high",
        "detected_at": "2026-09-15T00:00:00.000Z",
        "window_seconds": 300,
        "threshold": 50,
        "recommendation": "Check whether these downloads were expected.",
        "count": 80,
        "evidence": ["event-1"],
        "explanation": "80 downloads in 300 seconds.",
    }
    append_events(source, [alert])
    result = security_bridge.process_batch(source, directory, rules)
    assert result["events"] == 0
    output = read_outputs(directory)[0]
    assert output["detected_at"] == alert["detected_at"]
    assert output["actor"] == alert["actor"]
    assert output["recommendation"] == alert["recommendation"]


def test_out_of_order_event_is_explicitly_rejected(tmp_path, rules):
    """Late records must not silently invalidate the window algorithm."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(5), event(1)])
    assert security_bridge.process_batch(source, directory, rules)["rejected"] == 1
    assert "out-of-order" in read_outputs(directory, "rejected")[0]["reason"]


def test_oversized_line_does_not_advance_checkpoint(tmp_path, rules):
    """Bound memory even if the input producer writes a huge record."""
    source = tmp_path / "events.jsonl"
    source.write_text("x" * 65)
    with pytest.raises(ValueError, match="exceeds"):
        security_bridge.process_batch(source, tmp_path / "output", rules, max_line_bytes=64)
    assert not (tmp_path / "output" / "state.json").exists()


def test_command_and_disabled_periodic_task(tmp_path, rules, settings, capsys):
    """The manual command works independently; periodic processing is opt-in."""
    settings.SECURITY_MONITORING_ENABLED = False
    assert process_security_logs.run() == {"status": "disabled"}
    source = tmp_path / "events.jsonl"
    append_events(source, [event(0)])
    with mock.patch(
        "core.management.commands.process_security_logs.load_rules", return_value=rules
    ):
        call_command("process_security_logs", input=str(source), workdir=str(tmp_path / "output"))
    assert json.loads(capsys.readouterr().out)["events"] == 1


def test_beat_uses_dedicated_queue():
    """A scheduler cannot send these jobs to the usual Drive workers by mistake."""
    configuration = mock.Mock(
        SECURITY_MONITORING_ENABLED=True, SECURITY_MONITORING_INTERVAL_SECONDS=7
    )
    # django-configurations wraps settings properties; pylint cannot infer their return.
    schedule = Base.CELERY_BEAT_SCHEDULE.fget(configuration)  # pylint: disable=assignment-from-no-return
    assert schedule["security-monitoring"]["schedule"] == 7
    assert schedule["security-monitoring"]["options"] == {
        "queue": "security-monitoring",
        "expires": 7,
    }


def test_packaged_fixture_and_posthog_sdk_without_network(tmp_path):
    """Exercise all three default rules and validate SDK ingestion without sending."""
    from posthog import Posthog  # pylint: disable=import-outside-toplevel # noqa: PLC0415

    root = Path(__file__).parents[1]
    source = root / "tests" / "data" / "security_monitoring.jsonl"
    rules = load_rules(root / "security_rules.yaml")
    first = security_bridge.process_batch(source, tmp_path, rules)
    second = security_bridge.process_batch(source, tmp_path, rules)
    assert (first["lines"], second["lines"]) == (100, 60)
    assert first["rejected"] + second["rejected"] == 0
    alerts = read_outputs(tmp_path)
    assert [alert["rule"] for alert in alerts] == [
        "mass_download",
        "permission_probing",
        *["permission_escalation"] * 5,
    ]
    assert alerts[0]["threshold"] == 100
    assert alerts[0]["condition"] == "downloads_ten_minutes"
    assert alerts[0]["severity"] == "high"
    assert alerts[1]["threshold"] == 10
    assert all(alert["recommendation"] for alert in alerts)
    client = Posthog("offline-test-key", send=False)
    for exported in read_outputs(tmp_path, "posthog"):
        identifier = client.capture(
            exported["event"],
            distinct_id=exported["distinct_id"],
            properties=exported["properties"],
            timestamp=utc_timestamp(exported["timestamp"]),
            uuid=exported["uuid"],
        )
        assert identifier == exported["uuid"]
    # send=False validates the payload but does not queue a network delivery.
    assert client.queue.qsize() == 0


def test_command_prints_only_alert_jsonl_to_stdout(tmp_path, capsys):
    """Honor the plan's stdout contract while keeping summaries on stderr."""
    source = Path(__file__).parent / "data" / "security_monitoring.jsonl"
    call_command(
        "process_security_logs",
        input=str(source),
        workdir=str(tmp_path),
        batch_size=160,
        alerts_stdout=True,
    )
    captured = capsys.readouterr()
    assert len([json.loads(line) for line in captured.out.splitlines()]) == 7
    assert json.loads(captured.err)["alerts"] == 7


@pytest.mark.parametrize(
    "rule_index,condition_index,threshold,seconds,distinct",
    [
        (0, 0, 60, 60, 0),
        (0, 1, 100, 600, 0),
        (0, 2, 300, 3600, 0),
        (0, 3, 2000000000, 3600, 0),
        (1, 0, 10, 300, 5),
        (1, 1, 30, 3600, 0),
        (2, 0, 1, 0, 0),
        (2, 1, 10, 300, 5),
        (2, 2, 25, 3600, 0),
    ],
)
def test_brief_thresholds_and_distinct_resources(
    rule_index, condition_index, threshold, seconds, distinct
):
    """Check the brief's nine predicates, including bytes and minimum item cardinality."""
    rules = load_rules(Path(__file__).parents[1] / "security_rules.yaml")
    rule = rules[rule_index]
    condition = rule["conditions"][condition_index]
    assert (
        condition["threshold"],
        condition["window_seconds"],
        condition.get("min_distinct_resources", 0),
    ) == (threshold, seconds, distinct)
    rule["conditions"] = [condition]
    engine = SecurityRules([rule], {})
    size = 2 if condition.get("metric") == "bytes" else threshold
    for index in range(size):
        entry = event(index, action=rule["action"], actor_full_name="Alice Example")
        if condition.get("metric") == "bytes":
            entry["context"]["bytes"] = 1000000000
        if condition.get("self_grant_roles"):
            entry["context"].update(
                target_actor="alice",
                old_role="reader",
                new_role="admin",
                actor_effective_role="reader",
            )
        # Repeated access to one object must not meet a five-object predicate.
        if distinct:
            entry["resource"] = "same-file"
        alerts = engine.process(entry, "unused")
        if index < size - 1 or distinct:
            assert alerts == []
    if distinct:
        for index in range(1, distinct):
            alerts = engine.process(event(size + index, action=rule["action"]), "unused")
            if index < distinct - 1:
                assert not alerts
        assert alerts[0]["count"] == threshold + distinct - 1
        assert alerts[0]["distinct_resources"] == distinct
    else:
        assert len(alerts) == 1
        assert alerts[0]["observed_value"] == threshold
        if (rule_index, condition_index) == (0, 0):
            assert alerts[0]["severity"] == "medium"
        assert alerts[0]["actor"]["full_name"] == "Alice Example"


@pytest.mark.parametrize("downloads,expected_alerts", [(55, 0), (60, 1), (61, 1)])
def test_download_demo_boundaries(downloads, expected_alerts):
    """The reference minute burst alerts at 60, with no duplicate at 61 downloads."""
    engine = SecurityRules(load_rules(Path(__file__).parents[1] / "security_rules.yaml"), {})
    alerts = []
    for index in range(downloads):
        alerts.extend(engine.process(event(index / 2, bytes=1), "unused"))
    assert len(alerts) == expected_alerts
    if alerts:
        assert alerts[0]["condition"] == "downloads_minute"
        assert alerts[0]["count"] == 60
        assert alerts[0]["severity"] == "medium"


def test_custom_yaml_rule_and_minimal_event(tmp_path):
    """A sysadmin can add an action rule and an exclusion without touching Python."""
    config = tmp_path / "rules.yaml"
    config.write_text("""rules:
  - name: unusual_shares
    action: share_created
    severity: medium
    exclude_actors: [service-account]
    recommendation: Check whether the sharing was authorised.
    conditions:
      - id: burst
        threshold: 2
        window_seconds: 60
        explanation: '{count} shares in {window_seconds} seconds.'
""")
    engine = SecurityRules(load_rules(config), {})
    for second, actor in enumerate(["service-account", "service-account", "alice", "alice"]):
        entry = {"actor": actor, "action": "share_created", "timestamp": event(second)["timestamp"]}
        alerts = engine.process(entry, str(second))
        if second < 3:
            assert not alerts
    assert alerts[0]["rule"] == "unusual_shares"
    assert alerts[0]["actor"] == {"id": "alice", "full_name": None}


def test_periodic_stdout_recovery(tmp_path, rules, settings, capsys, monkeypatch):
    """Celery publishes actual alerts; interrupted publication replays stable IDs."""
    source, directory = tmp_path / "events.jsonl", tmp_path / "output"
    append_events(source, [event(i) for i in range(3)])
    settings.SECURITY_MONITORING_ENABLED = True
    settings.SECURITY_MONITORING_INPUT = str(source)
    settings.SECURITY_MONITORING_WORKDIR = str(directory)
    monkeypatch.setattr("core.tasks.security_monitoring.load_rules", lambda _: rules)
    original = security_bridge._atomic_write  # pylint: disable=protected-access

    def interrupted_cursor(path, text):
        if path.name == "stdout-state.json":
            raise OSError("simulated interrupted publication")
        original(path, text)

    monkeypatch.setattr(security_bridge, "_atomic_write", interrupted_cursor)
    with pytest.raises(OSError, match="interrupted publication"):
        process_security_logs.run()
    first = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(security_bridge, "_atomic_write", original)
    assert process_security_logs.run()["published"] == 1
    assert json.loads(capsys.readouterr().out)["alert_id"] == first["alert_id"]
    assert security_bridge.publish_alerts(directory, io.StringIO()) == 0


def test_threshold_env_override_and_critical_default(monkeypatch):
    """Per-user thresholds can be tuned by environment; hard self-grants stay immediate."""
    path = Path(__file__).parents[1] / "security_rules.yaml"
    monkeypatch.setenv("SECURITY_MASS_DOWNLOAD_MINUTE_THRESHOLD", "35")
    monkeypatch.setenv("SECURITY_MASS_DOWNLOAD_MINUTE_WINDOW_SECONDS", "90")
    monkeypatch.setenv("SECURITY_PROBING_FIVE_MINUTES_MIN_DISTINCT_RESOURCES", "6")
    monkeypatch.setenv("SECURITY_PERMISSION_CHANGES_FIVE_MINUTES_MIN_DISTINCT_RESOURCES", "7")
    rules = load_rules(path)
    assert rules[0]["conditions"][0]["threshold"] == 35
    assert rules[0]["conditions"][0]["window_seconds"] == 90
    assert rules[1]["conditions"][0]["min_distinct_resources"] == 6
    assert rules[2]["conditions"][1]["min_distinct_resources"] == 7
    hard = rules[2]["conditions"][0]
    assert (hard["threshold"], hard["window_seconds"], hard["severity"]) == (1, 0, "critical")
    monkeypatch.setenv("SECURITY_MASS_DOWNLOAD_MINUTE_THRESHOLD", "invalid")
    with pytest.raises(ValueError, match="must be an integer"):
        load_rules(path)


def test_inherited_privilege_is_not_a_self_escalation():
    """A local role increase is not an exploit if equal rights were already inherited."""
    rules = load_rules(Path(__file__).parents[1] / "security_rules.yaml")
    rules[2]["conditions"] = [rules[2]["conditions"][0]]
    engine = SecurityRules([rules[2]], {})
    base = {"target_actor": "alice", "old_role": "reader", "new_role": "admin"}
    assert not engine.process(event(0, action="permission_changed", **base), "unused")
    for second, role in enumerate(("admin", "owner"), start=1):
        assert not engine.process(
            event(second, action="permission_changed", actor_effective_role=role, **base), "unused"
        )
    alerts = engine.process(
        event(3, action="permission_changed", actor_effective_role="reader", **base), "unused"
    )
    assert alerts[0]["severity"] == "critical"
    assert "bypass" in alerts[0]["explanation"]
    assert "immediately" in alerts[0]["recommendation"]
