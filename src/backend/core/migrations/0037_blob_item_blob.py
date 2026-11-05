# Hand-written for the content-addressed storage work (ignored/docs-x-drive/brief_hash.md),
# in the exact shape `makemigrations` would generate.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0036_business_metrics_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="Blob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="primary key for the record as UUID",
                        primary_key=True,
                        serialize=False,
                        verbose_name="id",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="date and time at which a record was created",
                        verbose_name="created on",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="date and time at which a record was last updated",
                        verbose_name="updated on",
                    ),
                ),
                ("hash", models.CharField(max_length=64, unique=True, verbose_name="hash")),
                ("size", models.BigIntegerField(verbose_name="size")),
                (
                    "upload_state",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("pending", "Pending"),
                            ("duplicating", "Duplicating"),
                            ("converting", "Converting"),
                            ("analyzing", "Analyzing"),
                            ("suspicious", "Suspicious"),
                            ("file_too_large_to_analyze", "File too large to analyze"),
                            ("ready", "Ready"),
                        ],
                        max_length=25,
                        null=True,
                        verbose_name="upload state",
                    ),
                ),
                (
                    "malware_detection_info",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Malware detection info when the analysis status is unsafe.",
                        null=True,
                    ),
                ),
                (
                    "unreferenced_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the blob lost its last reference, for the garbage collector.",
                        null=True,
                        verbose_name="unreferenced at",
                    ),
                ),
            ],
            options={
                "verbose_name": "Blob",
                "verbose_name_plural": "Blobs",
                "db_table": "drive_blob",
                "indexes": [
                    models.Index(
                        condition=models.Q(("unreferenced_at__isnull", False)),
                        fields=["unreferenced_at"],
                        name="blob_unreferenced_at_idx",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="item",
            name="blob",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="core.blob",
            ),
        ),
    ]
