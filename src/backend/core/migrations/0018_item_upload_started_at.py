"""Add upload_started_at to items for pending TTL tracking."""

from __future__ import annotations

from django.db import migrations, models


def backfill_upload_started_at(apps, schema_editor):
    Item = apps.get_model("core", "Item")
    # Best-effort backfill: use created_at for existing file records.
    Item.objects.filter(type="file", upload_started_at__isnull=True).update(
        upload_started_at=models.F("created_at")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_alter_user_short_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="upload_started_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Timestamp used to compute pending upload TTL. Set when a file "
                    "enters PENDING state and refreshed when a pending upload is "
                    "re-initiated."
                ),
                null=True,
            ),
        ),
        migrations.RunPython(backfill_upload_started_at, migrations.RunPython.noop),
    ]

