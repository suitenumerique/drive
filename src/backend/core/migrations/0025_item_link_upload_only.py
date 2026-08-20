from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0024_alter_item_upload_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="link_upload_only",
            field=models.BooleanField(default=False),
        ),
    ]
