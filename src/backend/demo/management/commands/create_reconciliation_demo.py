# ruff: noqa: S107
"""create_reconciliation_demo management command."""

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import factories, models

DEFAULT_OUTPUT = "demo/reconciliation_demo.csv"
# Active user = the demo dev user, which exists in the Keycloak realm so it can
# be used to log in on the frontend and check the merged content.
ACTIVE_EMAIL = "drive@drive.world"
INACTIVE_EMAIL = "inactive.recon@example.com"
SOURCE_ID = "recon-demo"


def _make_user(email, password="!"):
    """Create a user identified by the given email, or reuse an existing one."""
    if user := models.User.objects.filter(sub=email).first():
        return user

    return factories.UserFactory(
        admin_email=email,
        email=email,
        sub=email,
        password=password,
        is_superuser=False,
        is_active=True,
        is_staff=False,
    )


def _create_file(parent, creator, title):
    """Create a ready-to-use file item inside the given parent folder."""
    return factories.ItemFactory(
        parent=parent,
        title=title,
        type=models.ItemTypeChoices.FILE,
        creator=creator,
        filename=f"{title}.txt",
        mimetype="text/plain",
        update_upload_state=models.ItemUploadStateChoices.READY,
    )


def create_reconciliation_demo(stdout, output_path, checked):
    """Seed two accounts (active/inactive) plus content, and write the import CSV."""
    active = _make_user(ACTIVE_EMAIL)
    inactive = _make_user(INACTIVE_EMAIL)

    # Pre-existing content of the active user: visible before and after the merge.
    factories.ItemFactory(
        title="Déjà visible (compte actif)",
        type=models.ItemTypeChoices.FOLDER,
        creator=active,
        users=[(active, models.RoleChoices.OWNER)],
    )

    # Workspace owned by the inactive user: invisible to the active user before the
    # merge, fully visible after (its OWNER access and the creator of every item are
    # transferred). Exercises the ItemAccess and Item.creator transfers on a tree.
    workspace = factories.ItemFactory(
        title="À transférer — dossier (créé par l'inactif)",
        type=models.ItemTypeChoices.FOLDER,
        creator=inactive,
        users=[(inactive, models.RoleChoices.OWNER)],
        favorited_by=[inactive],
    )
    _create_file(workspace, inactive, "À transférer — fichier")
    _create_file(workspace, inactive, "À transférer — fichier 2")
    subfolder = factories.ItemFactory(
        parent=workspace,
        title="À transférer — sous-dossier",
        type=models.ItemTypeChoices.FOLDER,
        creator=inactive,
    )
    _create_file(subfolder, inactive, "À transférer — fichier imbriqué")

    # Folder shared with both users with different roles: after the merge the active
    # user keeps the highest role (admin). Favorited by both -> favorite de-dup.
    factories.ItemFactory(
        title="Rôle à fusionner (reader → admin)",
        type=models.ItemTypeChoices.FOLDER,
        creator=active,
        users=[
            (active, models.RoleChoices.READER),
            (inactive, models.RoleChoices.ADMIN),
        ],
        favorited_by=[active, inactive],
    )

    # Link-shared item the inactive user opened without a role: the link trace is
    # transferred so it stays in the active user's recently-viewed items.
    factories.ItemFactory(
        title="Trace de lien à transférer",
        type=models.ItemTypeChoices.FOLDER,
        creator=active,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        link_traces=[inactive],
    )

    # Invitation issued by the inactive user -> issuer reassigned to the active user.
    factories.InvitationFactory(issuer=inactive, item=workspace, email="collegue@example.com")

    # Write the CSV expected by the admin import
    fieldnames = ["active_email", "inactive_email", "id"]
    row = {
        "active_email": ACTIVE_EMAIL,
        "inactive_email": INACTIVE_EMAIL,
        "id": SOURCE_ID,
    }
    if checked:
        fieldnames += ["active_email_checked", "inactive_email_checked"]
        row["active_email_checked"] = "1"
        row["inactive_email_checked"] = "1"

    path = Path(output_path).resolve()
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    stdout.write("\nReconciliation demo data created:")
    stdout.write(f"  active (kept):        {ACTIVE_EMAIL}")
    stdout.write(f"  inactive (merged in): {INACTIVE_EMAIL}")
    stdout.write(f"\nCSV written to: {path}")
    stdout.write("(on the host, under src/backend/demo/ unless --output was changed)\n")
    stdout.write("Next steps:")
    stdout.write("  1. Admin > Core > User reconciliation CSV imports > Add, upload the CSV.")
    if checked:
        stdout.write("  2. Emails are pre-checked: skip the confirmation step.")
    else:
        stdout.write(
            "  2. Open the two confirmation links from mailcatcher (http://localhost:1081)."
        )
    stdout.write(
        "  3. Admin > Core > User reconciliations > select rows > "
        "'Process selected user reconciliations'."
    )
    stdout.write(f"\nLog in on the frontend as {ACTIVE_EMAIL} (via Keycloak):")
    stdout.write("  - before: 'Déjà visible (compte actif)' and 'Rôle à fusionner' (reader).")
    stdout.write(
        "  - after:  the 'À transférer' folder and its files appear, and the role "
        "on 'Rôle à fusionner' becomes admin."
    )


class Command(BaseCommand):
    """Create demo data and a CSV to test user reconciliation through the admin."""

    help = __doc__

    def add_arguments(self, parser):
        """Add the command arguments."""
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="Force command execution despite DEBUG is set to False",
        )
        parser.add_argument(
            "-o",
            "--output",
            default=DEFAULT_OUTPUT,
            help=f"Path of the generated CSV file (default: {DEFAULT_OUTPUT})",
        )
        parser.add_argument(
            "--checked",
            action="store_true",
            default=False,
            help="Pre-check both emails in the CSV to skip the confirmation step",
        )

    def handle(self, *args, **options):
        """Handle the management command."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "This command is not meant to be used in production environment "
                "except you know what you are doing, if so use --force parameter"
            )

        create_reconciliation_demo(self.stdout, options["output"], options["checked"])
