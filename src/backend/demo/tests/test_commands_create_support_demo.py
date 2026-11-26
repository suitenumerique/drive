"""Test the `create_support_demo` management command"""

import re

from django.contrib.admin.models import LogEntry
from django.core.management import call_command

import pytest

from core import models

pytestmark = pytest.mark.django_db


def test_commands_create_support_demo():
    """The command should create the support accounts, the scenario and its history."""
    call_command("create_support_demo", force=True)

    groups = dict(
        models.User.objects.filter(is_staff=True).values_list("admin_email", "groups__name")
    )
    assert groups == {
        "support1@drive.world": "Support read-only",
        "support2@drive.world": "Support operations",
    }
    assert models.User.objects.get(admin_email="support1@drive.world").check_password("pass")
    camille = models.User.objects.get(email="camille.martin@academie.example")
    assert models.Item.objects.get(
        title="Notes de service", type=models.ItemTypeChoices.FOLDER
    ).is_restricted
    assert models.Item.objects.get(title="Budget 2026.xlsx").parent().title == "Archives"
    assert models.Invitation.objects.filter(issuer=camille).exists()
    history = {}
    for entry in LogEntry.objects.order_by("id"):
        message = re.sub(r" \([0-9a-f-]{36}\)", "", entry.change_message)
        history.setdefault(entry.object_repr, []).append((entry.user.short_name, message))
    assert history == {
        "Budget 2026.xlsx": [
            ("Louis", "Moved from Projets pédagogiques to Sorties scolaires."),
            ("Camille", "Moved from Sorties scolaires to Archives."),
        ],
        "Sorties scolaires": [
            ("Camille", "Moved from Projets pédagogiques to Archives."),
            ("Camille", "Moved from Archives to Projets pédagogiques."),
            ("Camille", "Restricted."),
            ("Camille", "Restriction lifted."),
        ],
        "Ancien planning.docx": [
            ("Camille", "Moved to the trash."),
            ("Camille", "Restored from the trash."),
        ],
        "Brouillon.docx": [
            ("Camille", "Moved to the trash."),
            ("Camille", "Deleted from the trash."),
        ],
        "Conseil de classe": [
            ("Sophie", "Moved to the trash."),
            ("Sophie", "Restored from the trash."),
        ],
        "Compte rendu.odt": [("Sophie", "Moved from Conseil de classe to the root.")],
        "Notes de service": [("Camille", "Restricted.")],
    }


def test_commands_create_support_demo_twice():
    """Running the command again should not create the scenario twice."""
    call_command("create_support_demo", force=True)
    call_command("create_support_demo", force=True)

    assert models.Item.objects.filter(title="Projets pédagogiques").count() == 1
    assert models.User.objects.filter(email="support1@drive.world").count() == 1


def test_commands_create_support_demo_production_settings(settings):
    """The command should call the API on an environment with the production settings."""
    settings.ALLOWED_HOSTS = ["drive.example"]
    settings.SECURE_SSL_REDIRECT = True

    call_command("create_support_demo", force=True)

    assert models.Item.objects.get(title="Budget 2026.xlsx").parent().title == "Archives"
