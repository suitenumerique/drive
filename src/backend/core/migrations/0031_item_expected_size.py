from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0030_item_add_restriction_target")]

    operations = [
        migrations.AddField(
            model_name="item",
            name="expected_size",
            field=models.PositiveBigIntegerField(
                blank=True,
                null=True,
                help_text="Bytes reserved before issuing the upload authorization.",
            ),
        ),
    ]
