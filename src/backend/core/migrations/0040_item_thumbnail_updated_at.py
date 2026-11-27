from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_item_created_at_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='thumbnail_updated_at',
            field=models.DateTimeField(blank=True, help_text='When the current thumbnail was rendered, null when there is none.', null=True),
        ),
    ]
