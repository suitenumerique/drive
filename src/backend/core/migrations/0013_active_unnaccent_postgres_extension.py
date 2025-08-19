from django.db import migrations

from django.contrib.postgres.operations import UnaccentExtension


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_item_malware_detection_info'),
    ]

    operations = [
        UnaccentExtension(),
    ]
