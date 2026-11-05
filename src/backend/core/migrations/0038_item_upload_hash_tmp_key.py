# Hand-written for the content-addressed storage work (ignored/docs-x-drive/brief_hash.md),
# in the exact shape `makemigrations` would generate.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_blob_item_blob"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="upload_hash",
            field=models.CharField(
                blank=True,
                help_text="SHA-256 hash of the content announced by the client at creation.",
                max_length=64,
                null=True,
                verbose_name="upload hash",
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="upload_tmp_key",
            field=models.CharField(
                blank=True,
                help_text="Temporary storage key the upload policy targets when a hash was announced.",
                max_length=255,
                null=True,
                verbose_name="upload temporary key",
            ),
        ),
    ]
