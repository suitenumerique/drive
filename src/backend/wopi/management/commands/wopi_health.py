"""Management command to emit WOPI enablement + health state (no-leak)."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand

from wopi.services.health import get_wopi_health


class Command(BaseCommand):
    """Emit WOPI health state as JSON."""

    help = "Emit WOPI enablement + health state as deterministic JSON (no-leak)."

    def handle(self, *args: Any, **options: Any) -> None:
        health = get_wopi_health()
        payload = health.to_dict()
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))

        ok = bool(payload.get("healthy", False) or payload.get("state") == "disabled")
        if not ok:
            raise SystemExit(1)

