"""Opt-in security events with request attribution and commit-aware publication."""

import fcntl
import json
import logging
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import transaction

logger = logging.getLogger("monitoring_audit")
diagnostics = logging.getLogger(__name__)


class AuditJSONLHandler(logging.Handler):
    """Append plain JSONL on a shared local filesystem, without rotating under readers."""

    def emit(self, record):
        """Serialize writers and timestamp inside the lock to preserve event order."""
        if not settings.SECURITY_AUDIT_ENABLED:
            return
        try:
            path = Path(settings.SECURITY_AUDIT_PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as output:
                fcntl.flock(output.fileno(), fcntl.LOCK_EX)
                event = dict(record.msg)
                event["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                output.write(json.dumps(event, ensure_ascii=True, allow_nan=False) + "\n")
                output.flush()
        except (OSError, TypeError, ValueError) as error:
            # Keep Drive available, but never silently hide a missing audit trail.
            # Do not print identities, the payload, request headers or exception text.
            diagnostics.error("Security audit write failed (%s)", type(error).__name__)


def log_audit_event(action, *, request, resource_id=None, on_commit=False, **context):
    """Emit who/when/what; the rules engine alone assigns alert severity.

    Anonymous requests have no attributable account and are deliberately excluded
    from these per-account rules, rather than grouped into one invented actor.
    """
    if not settings.SECURITY_AUDIT_ENABLED:
        return
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False) or user.pk is None:
        return

    metadata = request.META
    request_id = getattr(request, "security_request_id", None)
    if request_id is None:
        request_id = metadata.get("HTTP_X_REQUEST_ID") or str(uuid4())
        request.security_request_id = request_id[:128]
    context.update(
        {
            "request_id": request_id[:128],
            # REMOTE_ADDR is the peer address; do not trust arbitrary forwarded headers.
            "ip": metadata.get("REMOTE_ADDR"),
            "user_agent": metadata.get("HTTP_USER_AGENT", "")[:512],
            "actor_full_name": getattr(user, "full_name", None) or None,
        }
    )
    event = {
        "id": str(uuid4()),
        "actor": str(user.pk),
        "action": action,
        "context": context,
    }
    if resource_id is not None:
        event["resource"] = str(resource_id)
    if on_commit:
        transaction.on_commit(partial(logger.info, event))
    else:
        logger.info(event)


def audit_actor_role(item, request):
    """Snapshot effective rights before mutation, with no extra lookup when disabled."""
    return item.get_role(request.user) if settings.SECURITY_AUDIT_ENABLED else None


def audit_access_change(request, item, *, effective_role, old_role, new_role, **context):
    """Record one explicit access operation, excluding internal descendant cleanup."""
    created = context.pop("created", False)
    context.setdefault("target_kind", "team" if context.get("target_team") else "user")
    for field in ("target_actor", "target_team"):
        if context.get(field) is not None:
            context[field] = str(context[field])
    roles = {"administrator": "admin"}
    context.update(
        old_role=roles.get(old_role, old_role),
        new_role=roles.get(new_role, new_role),
        actor_effective_role=roles.get(effective_role, effective_role),
    )
    log_audit_event(
        "permission_changed", request=request, resource_id=item.pk, on_commit=True, **context
    )
    if created:
        log_audit_event(
            "share_created", request=request, resource_id=item.pk, on_commit=True, **context
        )
