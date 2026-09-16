"""Validate independent digest checkpoints and SMTP failure recovery."""

from pathlib import Path
from unittest import mock

import pytest

from core.services.security_bridge import process_batch
from core.services.security_digest import send_digest
from core.services.security_rules import load_rules
from core.tasks.security_monitoring import send_security_digest


@pytest.fixture(name="digest_outbox")
def digest_outbox_fixture(tmp_path):
    """Use the same real alert output as the other delivery channel."""
    root = Path(__file__).parents[1]
    process_batch(
        root / "tests/data/security_monitoring.jsonl",
        tmp_path,
        load_rules(root / "security_rules.yaml"),
        160,
    )
    return tmp_path


def test_digest_failure_retry_and_no_repeat(digest_outbox, mailoutbox):
    """Failure retains the batch; successful sends advance without repeating accepted alerts."""
    with mock.patch("core.services.security_digest.send_mail", side_effect=OSError("offline")):
        with pytest.raises(OSError):
            send_digest(digest_outbox, ["security@example.invalid"], limit=2)
    assert not (digest_outbox / "digest-state.json").exists()
    assert send_digest(digest_outbox, ["security@example.invalid"], limit=2)["sent"] == 2
    assert send_digest(digest_outbox, ["security@example.invalid"])["sent"] == 5
    assert send_digest(digest_outbox, ["security@example.invalid"])["sent"] == 0
    assert len(mailoutbox) == 2
    assert "Recommended action:" in mailoutbox[0].body
    assert not (digest_outbox / "demo-posthog-state.json").exists()
    with pytest.raises(ValueError, match="recipients changed"):
        send_digest(digest_outbox, ["different@example.invalid"])


def test_digest_disabled_by_default(settings):
    """Periodic email requires explicit enablement and recipients."""
    settings.SECURITY_DIGEST_ENABLED = False
    with mock.patch("core.tasks.security_monitoring.send_digest") as sender:
        assert send_security_digest()["status"] == "disabled"
        sender.assert_not_called()
