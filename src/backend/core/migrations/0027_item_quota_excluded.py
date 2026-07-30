from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_item_item_creator_size_not_hdel_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='quota_excluded',
            field=models.BooleanField(default=False, help_text="Exclude this item from its creator's storage quota computation."),
        ),
    ]
