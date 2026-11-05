# Hand-written for the content-addressed storage work (ignored/docs-x-drive/brief_hash.md),
# in the exact shape `makemigrations` would generate.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_item_upload_hash_tmp_key"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemVersion",
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
                ("filename", models.CharField(blank=True, max_length=255, null=True)),
                ("mimetype", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="item_versions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "blob",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="versions",
                        to="core.blob",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="core.item",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item version",
                "verbose_name_plural": "Item versions",
                "db_table": "drive_item_version",
                "ordering": ("-created_at",),
            },
        ),
    ]
