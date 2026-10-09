import core.models
from core.utils.migrations import AddIndexConcurrentlyIfMissing
from django.db import migrations, models


class Migration(migrations.Migration):

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction. It avoids locking
    # writes on the item table while the index is being built (about 20 seconds and
    # 900MB for 4M items).
    atomic = False

    dependencies = [
        ('core', '0030_item_add_restriction_target'),
    ]

    operations = [
        # Queries read the whole item table until this index is valid, so on large
        # databases it is created by hand before the release is deployed.
        AddIndexConcurrentlyIfMissing(
            model_name='item',
            index=models.Index(core.models.ParentPath(models.F('path')), name='item_parent_path_idx'),
        ),
    ]
