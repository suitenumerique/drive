"""Configurable per-actor windows with JSON-serializable detection state."""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import yaml

SEVERITIES = {"low", "medium", "high", "critical"}
ROLE_ORDER = {None: 0, "reader": 1, "editor": 2, "admin": 3, "owner": 4}
TEMPLATE_VALUES = {
    "count": 1,
    "window_seconds": 1,
    "threshold": 1,
    "distinct_resources": 1,
    "min_distinct_resources": 1,
    "observed_value": 1,
    "actor": "account",
    "action": "action",
}


def utc_timestamp(value):
    """Require the team's UTC ISO 8601 format, including the final Z."""
    if not isinstance(value, str) or not value.endswith("Z") or "T" not in value:
        raise ValueError("timestamp must be an ISO 8601 UTC string ending in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return parsed


def _integer(value, field, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")


def _template(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty template")
    try:
        value.format(**TEMPLATE_VALUES)
    except (KeyError, ValueError, IndexError, AttributeError) as error:
        raise ValueError(f"invalid {field} template: {error}") from error


def load_rules(path):
    """Load named rules; new counting rules require YAML only, no Python registry."""
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rules = config.get("rules") if isinstance(config, dict) else None
    if not isinstance(rules, list) or not rules:
        raise ValueError("configuration must contain a non-empty rules list")
    names = set()
    for rule in rules:
        if not isinstance(rule, dict) or not re.fullmatch(
            r"[a-z][a-z0-9_]*", str(rule.get("name", ""))
        ):
            raise ValueError("rule name must use lowercase letters, numbers and underscores")
        if rule["name"] in names:
            raise ValueError("duplicate rule name")
        names.add(rule["name"])
        if not isinstance(rule.get("action"), str) or not rule["action"].strip():
            raise ValueError("action must be a non-empty string")
        if rule.get("severity") not in SEVERITIES:
            raise ValueError("unknown severity")
        _template(rule.get("recommendation"), "recommendation")
        excluded = rule.get("exclude_actors", [])
        if not isinstance(excluded, list) or any(not isinstance(actor, str) for actor in excluded):
            raise ValueError("exclude_actors must be a list of identifiers")
        _environment_overrides(rule)
        _validate_conditions(rule)
    return rules


def _environment_overrides(rule):
    """Allow explicit YAML opt-in to integer environment overrides only."""
    conditions = rule.get("conditions")
    if not isinstance(conditions, list):
        return  # The schema validator reports malformed conditions.
    for condition in conditions:
        if not isinstance(condition, dict):
            continue  # The schema validator reports malformed conditions below.
        for field in ("threshold", "window_seconds", "min_distinct_resources"):
            name = condition.get(f"{field}_env")
            if name is None:
                continue
            if not isinstance(name, str) or not re.fullmatch(r"SECURITY_[A-Z0-9_]+", name):
                raise ValueError("rule overrides must name a SECURITY_ environment variable")
            if name in os.environ:
                try:
                    condition[field] = int(os.environ[name])
                except ValueError:
                    raise ValueError(f"{name} must be an integer") from None


def _validate_conditions(rule):
    """Validate the predicates and templates before reading any source records."""
    conditions = rule.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("each rule needs a non-empty conditions list")
    identifiers = set()
    for condition in conditions:
        if not isinstance(condition, dict) or not re.fullmatch(
            r"[a-z][a-z0-9_]*", str(condition.get("id", ""))
        ):
            raise ValueError("condition needs a lowercase id")
        if condition["id"] in identifiers:
            raise ValueError("duplicate condition id")
        identifiers.add(condition["id"])
        _integer(condition.get("threshold"), "threshold")
        _integer(condition.get("window_seconds"), "window_seconds", minimum=0)
        _integer(condition.get("min_distinct_resources", 0), "min_distinct_resources", minimum=0)
        if condition.get("metric", "count") not in ("count", "bytes"):
            raise ValueError("metric must be count or bytes")
        if condition.get("severity", rule["severity"]) not in SEVERITIES:
            raise ValueError("unknown condition severity")
        roles = condition.get("self_grant_roles")
        if roles is not None and (
            not isinstance(roles, list)
            or not roles
            or any(role not in ("reader", "editor", "admin", "owner") for role in roles)
        ):
            raise ValueError("self_grant_roles must list known target roles")
        _template(condition.get("explanation"), "explanation")
        if "recommendation" in condition:
            _template(condition["recommendation"], "recommendation")


def validate_event(event):
    """Require who/when/what; validate optional enrichment before changing state."""
    if not isinstance(event, dict):
        raise ValueError("each line must be a JSON object")
    utc_timestamp(event.get("timestamp"))
    for field in ("actor", "action"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("id", "resource"):
        if field in event and (not isinstance(event[field], str) or not event[field].strip()):
            raise ValueError(f"{field} must be a non-empty string when provided")
    context = event.get("context", {})
    if not isinstance(context, dict):
        raise ValueError("context must be an object")
    if "bytes" in context:
        _integer(context["bytes"], "context.bytes", minimum=0)
    name = context.get("actor_full_name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise ValueError("context.actor_full_name must be a non-empty string or null")


def is_self_escalation(event, roles):
    """Only count evidenced self-grants, never infer them from a permission change."""
    context = event.get("context", {})
    old_role, new_role = context.get("old_role"), context.get("new_role")
    effective = context.get("actor_effective_role")
    return (
        context.get("target_actor") == event["actor"]
        and "old_role" in context
        and isinstance(old_role, (str, type(None)))
        and isinstance(new_role, str)
        and old_role in ROLE_ORDER
        and new_role in roles
        and ROLE_ORDER[new_role] > ROLE_ORDER[old_role]
        and "actor_effective_role" in context
        and isinstance(effective, (str, type(None)))
        and effective in ROLE_ORDER
        and ROLE_ORDER[new_role] > ROLE_ORDER[effective]
    )


class SecurityRules:
    """Track each condition independently; alert on crossing, not on every event.

    All matching events in the window are kept so distinct-item and byte totals
    remain exact. Memory depends on traffic within the largest configured window.
    A zero-second window evaluates each event separately (immediate detection).
    """

    def __init__(self, rules, state):
        self.rules = rules
        self.state = state
        fingerprint = hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()
        if state.get("rules_hash") not in (None, fingerprint):
            raise ValueError("rules changed: use a new work directory to replay/calibrate")
        state["rules_hash"] = fingerprint
        state.setdefault("windows", {})
        state.setdefault("seen", {})

    def process(self, event, fallback_id):
        """Return alerts for one chronological event and update resumable state."""
        validate_event(event)
        now = utc_timestamp(event["timestamp"])
        horizon = max(c["window_seconds"] for r in self.rules for c in r["conditions"])
        oldest = now - timedelta(seconds=max(1, horizon))
        self.state["seen"] = {
            key: ts for key, ts in self.state["seen"].items() if utc_timestamp(ts) >= oldest
        }
        event_id = event.get("id", fallback_id)
        if event_id in self.state["seen"]:
            return []
        last = self.state.get("last_timestamp")
        if last and now < utc_timestamp(last):
            raise ValueError("out-of-order event: chronological input is required")
        self.state["last_timestamp"] = event["timestamp"]
        self.state["seen"][event_id] = event["timestamp"]
        alerts = []
        for rule in self.rules:
            for condition in rule["conditions"]:
                alert = self._condition(event, event_id, rule, condition)
                if alert:
                    alerts.append(alert)
        return alerts

    @staticmethod
    def _statistics(entries, condition):
        resources = len({entry[2] for entry in entries if entry[2] is not None})
        metric = condition.get("metric", "count")
        value = sum(entry[3] or 0 for entry in entries) if metric == "bytes" else len(entries)
        reached = value >= condition["threshold"] and resources >= condition.get(
            "min_distinct_resources", 0
        )
        return value, resources, reached

    def _condition(self, event, event_id, rule, condition):
        now = utc_timestamp(event["timestamp"])
        key = f"{rule['name']}:{condition['id']}"
        accounts = self.state["windows"].setdefault(key, {})
        seconds = condition["window_seconds"]
        cutoff = now - timedelta(seconds=seconds)
        matches = event["action"] == rule["action"] and event["actor"] not in rule.get(
            "exclude_actors", []
        )
        roles = condition.get("self_grant_roles")
        matches = matches and (roles is None or is_self_escalation(event, roles))
        for actor in list(accounts):
            window = accounts[actor]
            window["events"] = [
                e for e in window["events"] if seconds and utc_timestamp(e[0]) >= cutoff
            ]
            if not window["events"]:
                del accounts[actor]
            elif not (matches and actor == event["actor"]):
                window["active"] = (
                    window["active"] and self._statistics(window["events"], condition)[2]
                )
        if not matches:
            return None
        window = accounts.setdefault(event["actor"], {"events": [], "active": False})
        window["events"].append(
            [
                event["timestamp"],
                event_id,
                event.get("resource"),
                event.get("context", {}).get("bytes"),
            ]
        )
        reached = self._statistics(window["events"], condition)[2]
        alert = (
            self._alert(event, event_id, rule, condition, window["events"])
            if reached and not window["active"]
            else None
        )
        window["active"] = reached
        return alert

    @staticmethod
    def _alert(event, event_id, rule, condition, entries):
        context = event.get("context", {})
        value, resources, _ = SecurityRules._statistics(entries, condition)
        substitutions = {
            "count": len(entries),
            "window_seconds": condition["window_seconds"],
            "threshold": condition["threshold"],
            "distinct_resources": resources,
            "min_distinct_resources": condition.get("min_distinct_resources", 0),
            "observed_value": value,
            "actor": context.get("actor_full_name") or event["actor"],
            "action": rule["action"],
        }
        return {
            "alert_id": str(
                uuid5(NAMESPACE_URL, f"drive:{rule['name']}:{condition['id']}:{event_id}")
            ),
            "rule": rule["name"],
            "condition": condition["id"],
            "severity": condition.get("severity", rule["severity"]),
            "detected_at": event["timestamp"],
            "window_seconds": condition["window_seconds"],
            "count": len(entries),
            "threshold": condition["threshold"],
            "actor": {"id": event["actor"], "full_name": context.get("actor_full_name")},
            "explanation": condition["explanation"].format(**substitutions),
            "recommendation": condition.get("recommendation", rule["recommendation"]).format(
                **substitutions
            ),
            "evidence": [entry[1] for entry in entries[:50]],
            "evidence_truncated": len(entries) > 50,
            "metric": condition.get("metric", "count"),
            "observed_value": value,
            "distinct_resources": resources,
            "bytes_complete": all(entry[3] is not None for entry in entries),
        }
