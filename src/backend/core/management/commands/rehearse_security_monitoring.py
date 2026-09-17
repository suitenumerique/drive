"""Reproduce baseline, attacks, known evasions and delivery without cloud credentials."""

import json
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.services.security_bridge import process_batch
from core.services.security_posthog import DemoDestination, send_demo_batch
from core.services.security_rules import load_rules


def scenarios():
    """Fixed reference workloads: results describe synthetic data, not real-user accuracy."""
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    def events(count, action, step=1, actors=1, **context):
        return [
            {
                "id": str(uuid4()),
                "timestamp": (start + timedelta(seconds=i * step))
                .isoformat()
                .replace("+00:00", "Z"),
                "actor": f"synthetic-account-{i % actors}",
                "action": action,
                "resource": f"synthetic-file-{i % 10}",
                "context": dict(context),
            }
            for i in range(count)
        ]

    baseline = events(160, "file_downloaded", step=180, actors=5, bytes=1000)
    baseline += events(20, "permission_denied", step=1440, actors=5)
    baseline += events(20, "permission_changed", step=1440, actors=5)
    baseline.sort(key=lambda entry: entry["timestamp"])
    self_grant = {"target_actor": "synthetic-account-0", "old_role": "reader", "new_role": "admin"}
    return [
        ("baseline_8_hours", baseline, set(), "normal"),
        ("mass_download", events(120, "file_downloaded", step=0.4), {"mass_download"}, "attack"),
        ("permission_probing", events(10, "permission_denied"), {"permission_probing"}, "attack"),
        (
            "permission_volume",
            events(10, "permission_changed"),
            {"permission_escalation"},
            "attack",
        ),
        (
            "impossible_self_grant",
            events(1, "permission_changed", **self_grant, actor_effective_role="reader"),
            {"permission_escalation"},
            "attack",
        ),
        ("slow_download", events(120, "file_downloaded", step=600), set(), "evasion"),
        ("distributed_download", events(120, "file_downloaded", actors=40), set(), "evasion"),
        (
            "existing_inherited_owner",
            events(1, "permission_changed", **self_grant, actor_effective_role="owner"),
            set(),
            "normal",
        ),
    ]


class CaptureReceiver(BaseHTTPRequestHandler):
    """Local capture protocol stand-in; never redirects or forwards received events."""

    accepted = 0

    def do_POST(self):  # pylint: disable=invalid-name
        """Acknowledge only our synthetic capture events."""
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        valid = self.path == "/batch/" and payload.get("api_key") == "local-rehearsal-only"
        valid = valid and all(
            event.get("event") == "drive_security_alert" for event in payload.get("batch", [])
        )
        if valid:
            type(self).accepted += len(payload["batch"])
        self.send_response(200 if valid else 400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": 1 if valid else 0}).encode())

    def log_message(self, *_args):
        """Keep synthetic payloads out of console diagnostics."""


class Command(BaseCommand):
    """Run repeatable cases against configured rules and a real loopback HTTP receiver."""

    requires_system_checks = []
    help = "Measure synthetic baseline/attack cases and local HTTP delivery; never uses cloud keys."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="/data/security/rehearsals")
        parser.add_argument("--runs", type=int, default=1)

    def handle(self, *args, **options):
        if not 1 <= options["runs"] <= 100:
            raise CommandError("runs must be between 1 and 100")
        root = Path(options["output"]) / str(uuid4())
        root.mkdir(parents=True)
        rules = load_rules(settings.SECURITY_MONITORING_RULES)
        results = []
        CaptureReceiver.accepted = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureReceiver)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        destination = DemoDestination(
            f"http://127.0.0.1:{server.server_port}", "local-rehearsal-only"
        )
        try:
            for run in range(options["runs"]):
                for name, events, expected, kind in scenarios():
                    directory = root / str(run + 1) / name
                    directory.mkdir(parents=True)
                    source = directory / "events.jsonl"
                    source.write_text("".join(json.dumps(event) + "\n" for event in events))
                    outbox = directory / "processed"
                    batch = process_batch(source, outbox, rules, 1000)
                    alerts = [
                        json.loads(line)
                        for path in (outbox / "batches").glob("*.alerts.jsonl")
                        for line in path.read_text().splitlines()
                    ]
                    actual = {alert["rule"] for alert in alerts}
                    sent = send_demo_batch(outbox, destination)
                    repeat = send_demo_batch(outbox, destination)
                    passed = (
                        actual == expected
                        and not batch["rejected"]
                        and sent["sent"] == len(alerts)
                        and repeat["sent"] == 0
                    )
                    results.append(
                        {
                            "run": run + 1,
                            "scenario": name,
                            "kind": kind,
                            "events": len(events),
                            "alerts": len(alerts),
                            "rules": sorted(actual),
                            "passed": passed,
                        }
                    )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        summary = {
            "data": "synthetic; not a production false-positive estimate",
            "runs": options["runs"],
            "successful_runs": sum(
                all(case["passed"] for case in results if case["run"] == run)
                for run in range(1, options["runs"] + 1)
            ),
            "baseline_hours_per_run": 8,
            "baseline_false_alerts": sum(
                case["alerts"] for case in results if case["scenario"] == "baseline_8_hours"
            ),
            "reference_attacks": sum(case["kind"] == "attack" for case in results),
            "reference_attacks_detected": sum(
                case["kind"] == "attack" and bool(case["alerts"]) for case in results
            ),
            "known_evasions": sum(case["kind"] == "evasion" for case in results),
            "known_evasions_missed": sum(
                case["kind"] == "evasion" and not case["alerts"] for case in results
            ),
            "local_http_events_accepted": CaptureReceiver.accepted,
            "output": str(root),
        }
        (root / "report.json").write_text(
            json.dumps({**summary, "cases": results}, indent=2) + "\n"
        )
        self.stdout.write(json.dumps(summary))
        if not all(case["passed"] for case in results):
            raise CommandError(
                "Reference expectations differ from configured rules; inspect report.json"
            )
