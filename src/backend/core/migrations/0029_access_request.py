import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_item_creator_size_quota_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessRequest",
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
                        editable=False,
                        verbose_name="created on",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="updated on",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("refused", "Refused"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField(blank=True)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_requests",
                        to="core.item",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_requests",
                        to="core.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Access request",
                "verbose_name_plural": "Access requests",
                "db_table": "drive_access_request",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="accessrequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "pending")),
                fields=("item", "requester"),
                name="unique_pending_access_request",
                violation_error_message=(
                    "You already requested access to this item and your request is pending."
                ),
            ),
        ),
    ]
