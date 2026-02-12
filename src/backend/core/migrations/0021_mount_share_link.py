"""Add MountShareLink mapping table for mount virtual entry share links."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_merge_0018_item_upload_started_at_0019_user_last_release_note_seen"),
    ]

    operations = [
        migrations.CreateModel(
            name="MountShareLink",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        serialize=False,
                        default=uuid.uuid4,
                        editable=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, editable=False),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, editable=False),
                ),
                ("token", models.CharField(max_length=128, unique=True)),
                ("mount_id", models.CharField(db_index=True, max_length=64)),
                ("normalized_path", models.TextField()),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mount_share_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "drive_mount_share_link",
            },
        ),
        migrations.AddConstraint(
            model_name="mountsharelink",
            constraint=models.UniqueConstraint(
                fields=("mount_id", "normalized_path"),
                name="mount_share_link_mount_id_path_unique",
            ),
        ),
    ]
