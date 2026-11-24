"""create_support_demo management command."""

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings

from rest_framework.test import APIClient

from core import factories, models

# Same users as the Keycloak realm and demo.defaults.DEV_USERS, with an admin login
SUPPORT_USERS = {
    "support1": ("Support Read", "Support read-only"),
    "support2": ("Support Operations", "Support operations"),
}
DOMAIN = "academie.example"


def _make_support_user(username, full_name, group):
    """Create or update a staff user of the support group, with the realm password."""
    email = f"{username}@drive.world"
    user = models.User.objects.filter(email=email).first() or models.User(
        email=email, sub=email, full_name=full_name, short_name="Support"
    )
    user.admin_email = email
    user.is_staff = True
    user.set_password("pass")
    user.save()
    user.groups.set([Group.objects.get(name=group)])
    return user


def _make_user(name):
    """Create a user of the scenario from its full name, or reuse an existing one."""
    email = f"{name.lower().replace(' ', '.')}@{DOMAIN}"
    if user := models.User.objects.filter(email=email).first():
        return user
    return factories.UserFactory(email=email, sub=email, full_name=name, short_name=name.split()[0])


def _folder(title, creator, **kwargs):
    """Create a folder."""
    return factories.ItemFactory(
        title=title, type=models.ItemTypeChoices.FOLDER, creator=creator, **kwargs
    )


def _file(title, creator, parent):
    """Create a ready file of 2.4 MB, without content in the storage."""
    return factories.ItemFactory(
        title=title,
        type=models.ItemTypeChoices.FILE,
        creator=creator,
        parent=parent,
        filename=title,
        mimetype="application/octet-stream",
        size=2_400_000,
        update_upload_state=models.ItemUploadStateChoices.READY,
    )


def _api(stdout, user, method, url, data=None):
    """Call the API as the user, so its history is written as the app writes it."""
    client = APIClient()
    client.force_authenticate(user)
    # The client sends the testserver host, refused by the production settings
    with override_settings(ALLOWED_HOSTS=["testserver"]):
        response = getattr(client, method)(url, data, format="json", secure=True)
    stdout.write(f"  {user.full_name}: {method.upper()} {url} -> {response.status_code}")
    if response.status_code >= 300:
        raise CommandError(f"The API refused the call: {response.content!r}")


def create_scenario(stdout):
    """Create the users, items, invitation and history of the scenario."""
    camille, louis, sophie = (
        _make_user(name) for name in ("Camille Martin", "Louis Bernard", "Sophie Leroy")
    )
    if models.Item.objects.filter(creator=camille).exists():
        stdout.write(f"The items of {camille} already exist, nothing created.")
        return
    camille.storage_limit_override = 20 * 1000**3
    camille.save()

    stdout.write("Creating the items.")
    projects = _folder(
        "Projets pédagogiques",
        camille,
        users=[(camille, "owner"), (louis, "administrator")],
        link_reach=models.LinkReachChoices.RESTRICTED,
    )
    trips = _folder("Sorties scolaires", camille, parent=projects)
    _file("Autorisation parentale.pdf", camille, trips)
    notes = _folder("Notes de service", camille, parent=projects)
    factories.UserItemAccessFactory(item=notes, user=sophie, role="administrator")
    budget = _file("Budget 2026.xlsx", camille, projects)
    planning = _file("Ancien planning.docx", camille, projects)
    draft = _file("Brouillon.docx", camille, projects)
    archives = _folder(
        "Archives",
        camille,
        users=[(camille, "owner")],
        link_reach=models.LinkReachChoices.PUBLIC,
        link_role=models.LinkRoleChoices.READER,
    )
    _file("Bilan 2025.pdf", louis, archives)
    council = _folder("Conseil de classe", sophie, users=[(sophie, "owner"), (camille, "reader")])
    report = _file("Compte rendu.odt", sophie, council)
    models.Invitation.objects.create(
        email=f"nouvelle.collegue@{DOMAIN}", item=projects, role="editor", issuer=camille
    )

    stdout.write("Acting through the API to fill the history.")
    items = "/api/v1.0/items"
    _api(stdout, louis, "post", f"{items}/{budget.pk}/move/", {"target_item_id": trips.pk})
    _api(stdout, camille, "post", f"{items}/{budget.pk}/move/", {"target_item_id": archives.pk})
    _api(stdout, camille, "post", f"{items}/{trips.pk}/move/", {"target_item_id": archives.pk})
    _api(stdout, camille, "post", f"{items}/{trips.pk}/move/", {"target_item_id": projects.pk})
    _api(stdout, camille, "delete", f"{items}/{planning.pk}/")
    _api(stdout, camille, "post", f"{items}/{planning.pk}/restore/")
    _api(stdout, camille, "delete", f"{items}/{draft.pk}/")
    _api(stdout, camille, "delete", f"{items}/{draft.pk}/hard-delete/")
    _api(stdout, sophie, "delete", f"{items}/{council.pk}/")
    _api(stdout, sophie, "post", f"{items}/{council.pk}/restore/")
    _api(stdout, sophie, "post", f"{items}/{report.pk}/move/")
    _api(stdout, camille, "post", f"{items}/{trips.pk}/restrict/")
    _api(stdout, camille, "delete", f"{items}/{trips.pk}/restrict/")
    _api(stdout, camille, "post", f"{items}/{notes.pk}/restrict/")


def create_support_demo(stdout):
    """Create the support accounts and a scenario to try the admin with."""
    for username, (full_name, group) in SUPPORT_USERS.items():
        _make_support_user(username, full_name, group)
        stdout.write(f"{username}@drive.world / pass: staff in {group}")
    with transaction.atomic():
        create_scenario(stdout)

    stdout.write("\nLog in on http://localhost:8071/admin/ with a support account, then:")
    stdout.write(f"  - Users: search {DOMAIN}, open Camille Martin, follow her accesses.")
    stdout.write("  - Items: open 'Projets pédagogiques' (link, tree, invitation).")
    stdout.write(
        "  - History of 'Budget 2026.xlsx', 'Sorties scolaires', 'Ancien planning.docx',"
        " 'Brouillon.docx', 'Conseil de classe', 'Compte rendu.odt', 'Notes de service'."
    )
    stdout.write("  - With support2: transfer Camille Martin's contents to Louis Bernard.")


class Command(BaseCommand):
    """Create support accounts and data to try the admin used by the support."""

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

    def handle(self, *args, **options):
        """Handle the management command."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "This command is not meant to be used in production environment "
                "except you know what you are doing, if so use --force parameter"
            )

        create_support_demo(self.stdout)
