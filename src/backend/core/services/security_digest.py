"""Optional bounded email digest with a cursor separate from analysis and PostHog."""

import fcntl
import hashlib
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email


def send_digest(workdir, recipients, limit=100):
    """Acknowledge only after SMTP success; failures leave the pending batch untouched."""
    recipients = sorted(set(recipients))
    if not recipients or not 1 <= limit <= 1000:
        raise ValueError("Digest recipients and a limit between 1 and 1000 are required")
    for recipient in recipients:
        validate_email(recipient)
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    with (root / "digest.lock").open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "sent": 0}
        cursor = root / "digest-state.json"
        state = json.loads(cursor.read_text()) if cursor.exists() else {}
        fingerprint = hashlib.sha256(json.dumps(recipients).encode()).hexdigest()
        if state.get("recipients", fingerprint) != fingerprint:
            raise ValueError("Digest recipients changed; use a fresh workdir for deliberate replay")
        alerts, position = _pending(root, state, limit)
        if not alerts:
            return {"status": "caught_up", "sent": 0}
        body = "Drive security alerts\n\n" + "\n\n".join(
            f"[{alert['severity']}] {alert['rule']} — {alert['detected_at']}\n"
            f"Account: {alert['actor']['id']}\n"
            f"{alert['explanation']}\nRecommended action: {alert['recommendation']}\n"
            f"Alert ID: {alert['alert_id']}"
            for alert in alerts
        )
        sent = send_mail(
            f"Drive security: {len(alerts)} alert(s)", body, settings.EMAIL_FROM, recipients
        )
        if sent != 1:
            raise OSError("Digest was not accepted by the mail backend")
        temporary = cursor.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump({**position, "recipients": fingerprint}, output)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(cursor)
        return {"status": "sent", "sent": len(alerts)}


def _pending(root, state, limit):
    """Read immutable alert batches while refusing lost/truncated checkpoint files."""
    previous = state.get("file", "")
    if previous and not (root / "batches" / previous).is_file():
        raise ValueError("Digest checkpoint file is missing")
    alerts = []
    position = {"file": previous, "offset": state.get("offset", 0)}
    for path in sorted((root / "batches").glob("*.alerts.jsonl")):
        if path.name < previous:
            continue
        offset = state.get("offset", 0) if path.name == previous else 0
        if offset > path.stat().st_size:
            raise ValueError("Digest checkpoint file was truncated")
        with path.open("rb") as source:
            source.seek(offset)
            while len(alerts) < limit:
                line = source.readline(1024 * 1024 + 1)
                if not line:
                    break
                if len(line) > 1024 * 1024 or not line.endswith(b"\n"):
                    raise ValueError("Digest alert is oversized or incomplete")
                alerts.append(json.loads(line))
                position = {"file": path.name, "offset": source.tell()}
        if len(alerts) == limit:
            break
    return alerts, position
