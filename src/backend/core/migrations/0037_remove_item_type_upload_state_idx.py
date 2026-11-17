from django.contrib.postgres.operations import RemoveIndexConcurrently
from django.db import migrations


class Migration(migrations.Migration):
    # DROP INDEX CONCURRENTLY cannot run inside a transaction. It avoids locking
    # writes on the item table while the index is dropped.
    # The item counts are no longer reported on /metrics: counting a large item
    # table at every refresh cannot stay fast, and an index on upload_state makes
    # every change of upload state update all the indexes of the table.
    atomic = False

    dependencies = [
        ("core", "0036_business_metrics_indexes"),
    ]

    operations = [
        RemoveIndexConcurrently(
            model_name="item",
            name="item_type_upload_state_idx",
        ),
    ]
