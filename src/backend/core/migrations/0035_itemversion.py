import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_linktrace_link_unlocked_at"),
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
                ("filename", models.CharField(max_length=255)),
                ("mimetype", models.CharField(blank=True, max_length=255, null=True)),
                ("size", models.BigIntegerField(blank=True, null=True)),
                ("version_number", models.PositiveIntegerField()),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="item_versions_created",
                        to="core.user",
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
                "ordering": ("version_number",),
            },
        ),
        migrations.AddConstraint(
            model_name="itemversion",
            constraint=models.UniqueConstraint(
                fields=("item", "version_number"), name="unique_item_version_number"
            ),
        ),
        migrations.AddConstraint(
            model_name="itemversion",
            constraint=models.CheckConstraint(
                condition=models.Q(("version_number__gt", 0)), name="item_version_number_positive"
            ),
        ),
    ]
