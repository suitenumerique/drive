"""Normalize stored emails to ASCII lowercase, so identity lookups can match them exactly."""

import string

from django.db import migrations

_ASCII_LOWERCASE_TABLE = str.maketrans(
    string.ascii_uppercase,
    string.ascii_lowercase,
)


def normalize_email(email):
    """Strip an email and lowercase its ASCII letters only."""
    if not email:
        return email
    return email.strip().translate(_ASCII_LOWERCASE_TABLE)


def delete_duplicate_invitations(apps):
    """Keep the most recent invitation of each item and normalized email."""
    invitation_model = apps.get_model("core", "Invitation")
    seen = set()
    duplicate_ids = []
    for invitation_id, item_id, email in invitation_model.objects.order_by(
        "-created_at"
    ).values_list("id", "item_id", "email"):
        key = (item_id, normalize_email(email))
        if key in seen:
            duplicate_ids.append(invitation_id)
        seen.add(key)
    invitation_model.objects.filter(id__in=duplicate_ids).delete()


def forwards(apps, schema_editor):
    """ASCII-lowercase the emails stored on users and invitations."""
    delete_duplicate_invitations(apps)

    batch_size = 500
    for model_name in ("User", "Invitation"):
        model = apps.get_model("core", model_name)
        to_update = []
        for obj in model.objects.iterator():
            normalized = normalize_email(obj.email)
            if normalized != obj.email:
                obj.email = normalized
                to_update.append(obj)
        if to_update:
            model.objects.bulk_update(to_update, ["email"], batch_size=batch_size)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0034_linktrace_link_unlocked_at"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
