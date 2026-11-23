from django.db import migrations


class Migration(migrations.Migration):
    # VALIDATE CONSTRAINT scans the item table under a SHARE UPDATE EXCLUSIVE lock,
    # which lets reads and writes go on. It runs apart from 0040 so the ACCESS
    # EXCLUSIVE lock taken there to add the constraint is already released.

    dependencies = [
        ("core", "0040_item_link_url"),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "drive_item" VALIDATE CONSTRAINT "check_link_url_only_on_links"',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
