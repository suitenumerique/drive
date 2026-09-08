from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def drop_index(name, table):
    """Drop the index without locking the table, and recreate it on rollback."""
    return migrations.RunSQL(
        sql=f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON "{table}" ("user_id")',
    )


class Migration(migrations.Migration):

    # The unique constraints on (user, item) already cover lookups by user, the
    # single column indexes are redundant. DROP INDEX CONCURRENTLY cannot run
    # inside a transaction and does not lock writes on these active tables.
    atomic = False

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0030_item_add_restriction_target"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="itemfavorite",
                    name="user",
                    field=models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorite_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                migrations.AlterField(
                    model_name="linktrace",
                    name="user",
                    field=models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="link_traces",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            database_operations=[
                drop_index("drive_item_favorite_user_id_f4a0b235", "drive_item_favorite"),
                drop_index("drive_link_trace_user_id_852fee0b", "drive_link_trace"),
            ],
        ),
    ]
