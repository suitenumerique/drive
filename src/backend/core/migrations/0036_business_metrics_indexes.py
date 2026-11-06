from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction. It avoids locking
    # writes on the item and user tables while they are read to build the indexes.
    # They let the Prometheus business metrics count without reading the whole
    # item table (1.5GB for 4M items): 26MB and 1MB to read instead.
    atomic = False

    dependencies = [
        ("core", "0035_normalize_stored_emails"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="item",
            index=models.Index(
                condition=models.Q(("hard_deleted_at__isnull", True)),
                fields=["type", "upload_state"],
                name="item_type_upload_state_idx",
            ),
        ),
        AddIndexConcurrently(
            model_name="user",
            index=models.Index(fields=["is_active"], name="user_is_active_idx"),
        ),
    ]
