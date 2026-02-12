"""Merge core migrations after upstream sync.

This resolves a parallel migration branch introduced by:
- 0018_item_upload_started_at
- 0019_user_last_release_note_seen (via 0018_mirroritemtask)
"""

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_item_upload_started_at"),
        ("core", "0019_user_last_release_note_seen"),
    ]

    operations: list[migrations.Operation] = []

