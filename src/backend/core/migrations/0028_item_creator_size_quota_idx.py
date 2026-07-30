from django.contrib.postgres.operations import AddIndexConcurrently, RemoveIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    # CREATE/DROP INDEX CONCURRENTLY cannot run inside a transaction. It avoids
    # locking writes on the item table while the index is being built. The new
    # index is added before the old one is removed so the storage used
    # aggregation never loses index support during the deployment.
    atomic = False

    dependencies = [
        ('core', '0027_item_quota_excluded'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='item',
            index=models.Index(condition=models.Q(('hard_deleted_at__isnull', True), ('quota_excluded', False)), fields=['creator'], include=('size',), name='item_creator_size_quota_idx'),
        ),
        RemoveIndexConcurrently(
            model_name='item',
            name='item_creator_size_not_hdel_idx',
        ),
    ]
