from django.db import migrations

from django.contrib.postgres.operations import UnaccentExtension


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_user_language'),
    ]

    operations = [
        UnaccentExtension(),
    ]
