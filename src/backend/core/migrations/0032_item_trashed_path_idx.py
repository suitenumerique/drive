from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction. It avoids locking
    # writes on the item table while it is read to build the index. The index only
    # holds the soft-deleted items (about 5MB for 28k of them among 4M items).
    atomic = False

    dependencies = [
        ('core', '0031_item_parent_path_idx'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='item',
            index=models.Index(condition=models.Q(('deleted_at__isnull', False)), fields=['path'], name='item_trashed_path_idx'),
        ),
    ]
