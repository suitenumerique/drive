"""Focused delivery checks using a real local HTTP receiver, never PostHog Cloud."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command

import pytest

from core.services import security_posthog
from core.services.security_bridge import process_batch
from core.services.security_posthog import DemoDestination, send_demo_batch
from core.services.security_rules import load_rules
from core.tasks.security_monitoring import send_security_alerts


@pytest.fixture(name="receiver")
def receiver_fixture():
    """Record actual HTTP requests and control capture acknowledgements."""
    state = SimpleNamespace(requests=[], status=200, acknowledgement={"status": "Ok"})

    class Handler(BaseHTTPRequestHandler):
        """Minimal local stand-in for the documented batch capture endpoint."""

        def do_POST(self):  # pylint: disable=invalid-name
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append((self.path, payload))
            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            if state.status == 307:
                self.send_header("Location", "/must-not-follow")
            self.end_headers()
            self.wfile.write(json.dumps(state.acknowledgement).encode())

        def log_message(self, *_args):
            """Do not print payloads or test tokens."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.host = f"http://127.0.0.1:{server.server_port}"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture(name="outbox")
def outbox_fixture(tmp_path):
    """Run the real detector so the sender consumes the actual exported contract."""
    root = Path(__file__).parents[1]
    process_batch(
        root / "tests/data/security_monitoring.jsonl",
        tmp_path,
        load_rules(root / "security_rules.yaml"),
        batch_size=160,
    )
    return tmp_path


def test_http_batches_resume_and_leave_drive_client_untouched(outbox, receiver, monkeypatch):
    """A failed request retries identical event identities, then drains bounded batches."""
    destination = DemoDestination(receiver.host, "phc_demo_test_only", batch_size=2)
    clock = [1000]
    monkeypatch.setattr(security_posthog, "time", SimpleNamespace(time=lambda: clock[0]))
    receiver.status = 503
    with mock.patch("posthog.capture", side_effect=AssertionError("Drive client used")):
        assert send_demo_batch(outbox, destination)["status"] == "retry"
        state = json.loads((outbox / "demo-posthog-state.json").read_text())
        assert "offset" not in state
        assert "phc_demo_test_only" not in json.dumps(state)
        assert send_demo_batch(outbox, destination)["status"] == "backoff"
        assert len(receiver.requests) == 1
        clock[0] += 11
        receiver.status = 200
        results = [send_demo_batch(outbox, destination) for _ in range(4)]
        assert [result["sent"] for result in results] == [2, 2, 2, 1]
        assert send_demo_batch(outbox, destination)["status"] == "caught_up"
    assert receiver.requests[0][1] == receiver.requests[1][1]
    accepted = [event for _, payload in receiver.requests[1:] for event in payload["batch"]]
    assert len({event["uuid"] for event in accepted}) == 7
    assert all(path == "/batch/" for path, _ in receiver.requests)
    assert all(event["event"] == "drive_security_alert" for event in accepted)
    assert all(event["properties"]["recommendation"] for event in accepted)
    assert all(event["properties"]["$process_person_profile"] is False for event in accepted)
    with pytest.raises(ValueError, match="destination changed"):
        send_demo_batch(outbox, DemoDestination(receiver.host, "phc_other_project"))


@pytest.mark.parametrize(
    "status,acknowledgement",
    [
        (307, {"status": "Ok"}),
        (200, {"status": 0}),
        (200, {"status": "Unknown"}),
        (200, {"status": "Ok", "quota_limited": ["events"]}),
    ],
)
def test_no_redirect_or_false_acknowledgement(outbox, receiver, status, acknowledgement):
    """Redirects cannot leak the token, and a failed capture never advances the cursor."""
    receiver.status, receiver.acknowledgement = status, acknowledgement
    result = send_demo_batch(outbox, DemoDestination(receiver.host, "phc_test"))
    assert result["status"] == "retry"
    assert len(receiver.requests) == 1
    assert "offset" not in json.loads((outbox / "demo-posthog-state.json").read_text())


@pytest.mark.parametrize("acknowledgement", [1, {"status": 1}])
def test_legacy_capture_acknowledgements(outbox, receiver, acknowledgement):
    """Older numeric success responses still advance the shared cursor once."""
    receiver.acknowledgement = acknowledgement
    destination = DemoDestination(receiver.host, "phc_test")
    assert send_demo_batch(outbox, destination) == {"status": "accepted", "sent": 7}
    assert send_demo_batch(outbox, destination) == {"status": "caught_up", "sent": 0}
    assert len(receiver.requests) == 1


def test_delivery_off_by_default_and_separate_configuration(settings, capsys):
    """Drive's own token alone cannot enable or configure demo delivery."""
    settings.SECURITY_DEMO_POSTHOG_ENABLED = False
    settings.POSTHOG_KEY = "phc_drive_project"
    with mock.patch("requests.post", side_effect=AssertionError("unexpected request")):
        assert send_security_alerts.run()["status"] == "disabled"
        call_command("send_security_alerts")
        assert json.loads(capsys.readouterr().out)["status"] == "disabled"
    settings.SECURITY_DEMO_POSTHOG_KEY = None
    with pytest.raises(ValueError, match="KEY is required"):
        DemoDestination.from_settings(settings)
    settings.SECURITY_DEMO_POSTHOG_KEY = "phc_drive_project"
    with pytest.raises(ValueError, match="must differ"):
        DemoDestination.from_settings(settings)
    with pytest.raises(ValueError, match="HTTPS origin"):
        DemoDestination("http://external.example", "phc_test").endpoint()


def test_manual_and_periodic_delivery_use_same_cursor(outbox, receiver, settings, capsys):
    """The runnable command and scheduled task send each accepted batch only once."""
    settings.SECURITY_DEMO_POSTHOG_ENABLED = True
    settings.SECURITY_DEMO_POSTHOG_KEY = "phc_demo_test_only"
    settings.SECURITY_DEMO_POSTHOG_HOST = receiver.host
    settings.SECURITY_DEMO_POSTHOG_BATCH_SIZE = 3
    settings.SECURITY_MONITORING_WORKDIR = str(outbox)
    call_command("send_security_alerts")
    assert json.loads(capsys.readouterr().out)["sent"] == 3
    assert send_security_alerts.run()["sent"] == 3
    assert send_security_alerts.run()["sent"] == 1
    assert send_security_alerts.run()["sent"] == 0
