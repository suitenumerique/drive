from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction. It avoids locking
    # writes on the item table while it is read to build the index.
    atomic = False

    dependencies = [
        ("core", "0038_item_source"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="item",
            index=models.Index(fields=["created_at"], name="item_created_at_idx"),
        ),
    ]
