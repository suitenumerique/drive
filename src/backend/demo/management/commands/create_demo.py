"""create_demo management command"""

import logging
import math
import random
import secrets
import time
import uuid
from io import BytesIO

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from faker import Faker

from core import factories, models

from demo import defaults

fake = Faker()

logger = logging.getLogger(__file__)
DEFAULT_PARENT = object()


FILE_TYPE_ITEMS = (
    {
        "title": "Demo text document",
        "filename": "demo-text-document.docx",
        "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    {
        "title": "Demo spreadsheet",
        "filename": "demo-spreadsheet.xlsx",
        "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    {
        "title": "Demo presentation",
        "filename": "demo-presentation.pptx",
        "mimetype": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
    {
        "title": "Demo PDF",
        "filename": "demo-pdf.pdf",
        "mimetype": "application/pdf",
    },
    {
        "title": "Demo image",
        "filename": "demo-image.png",
        "mimetype": "image/png",
    },
    {
        "title": "Demo video",
        "filename": "demo-video.mp4",
        "mimetype": "video/mp4",
    },
    {
        "title": "Demo archive",
        "filename": "demo-archive.zip",
        "mimetype": "application/zip",
    },
    {
        "title": "Demo audio",
        "filename": "demo-audio.mp3",
        "mimetype": "audio/mpeg",
    },
    {
        "title": "Demo other file",
        "filename": "demo-other.bin",
        "mimetype": "application/octet-stream",
    },
)


def get_or_create_demo_user(user_data):
    """Get an existing demo user or create it when absent."""
    email = user_data["email"]
    user, _created = models.User.objects.get_or_create(
        sub=email,
        defaults={
            "admin_email": email,
            "email": email,
            "full_name": user_data["full_name"],
            "short_name": user_data["short_name"],
            "password": make_password("pass"),  # NOSONAR
            "is_superuser": False,
            "is_active": True,
            "is_staff": False,
        },
    )
    update_fields = []
    for field in ["full_name", "short_name"]:
        if not getattr(user, field):
            setattr(user, field, user_data[field])
            update_fields.append(field)

    if update_fields:
        user.save(update_fields=update_fields)

    return user


class Timeit:
    """A utility context manager/method decorator to time execution."""

    total_time = 0

    def __init__(self, stdout, sentence=None):
        """Set the sentence to be displayed for timing information."""
        self.sentence = sentence
        self.start = None
        self.stdout = stdout

    def __call__(self, func):
        """Behavior on call for use as a method decorator."""

        def timeit_wrapper(*args, **kwargs):
            """wrapper to trigger/stop the timer before/after function call."""
            self.__enter__()
            result = func(*args, **kwargs)
            self.__exit__(None, None, None)
            return result

        return timeit_wrapper

    def __enter__(self):
        """Start timer upon entering context manager."""
        self.start = time.perf_counter()
        if self.sentence:
            self.stdout.write(self.sentence, ending=".")

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Stop timer and display result upon leaving context manager."""
        if exc_type is not None:
            raise exc_type(exc_value)
        end = time.perf_counter()
        elapsed_time = end - self.start
        if self.sentence:
            self.stdout.write(f" Took {elapsed_time:g} seconds")

        self.__class__.total_time += elapsed_time
        return elapsed_time


def create_users():
    """Create random users"""
    for user_data in defaults.USERS[: defaults.NB_OBJECTS["users"]]:
        yield get_or_create_demo_user(user_data)


def create_dev_users():
    """Create development users"""
    for dev_user in defaults.DEV_USERS:
        user = get_or_create_demo_user(dev_user)

        create_item(user)
        yield user


def create_item(
    user,
    title=None,
    file_data=None,
    parent=DEFAULT_PARENT,
):
    """Create file item with the given user as creator"""
    file_data = file_data or {}
    content = file_data.get("content") or fake.sentence(nb_words=50).encode()
    if parent is DEFAULT_PARENT:
        parent = factories.ItemFactory(
            creator=user,
            users=[(user, models.RoleChoices.OWNER)],
            type=models.ItemTypeChoices.FOLDER,
        )

    item = factories.ItemFactory(
        type=models.ItemTypeChoices.FILE,
        update_upload_state=models.ItemUploadStateChoices.READY,
        link_reach=models.LinkReachChoices.AUTHENTICATED,
        link_role=models.LinkRoleChoices.READER,
        creator=user,
        users=[(user, models.RoleChoices.OWNER)] if parent is None else None,
        parent=parent,
        title=title or fake.sentence(nb_words=4),
        filename=file_data.get("filename", "content.txt"),
        description=fake.sentence(nb_words=10),
        mimetype=file_data.get("mimetype", "text/plain"),
        size=len(content),
    )

    default_storage.save(item.file_key, BytesIO(content))

    return item


def create_items(users):
    """Create random items and file content for users"""
    for _id in range(defaults.NB_OBJECTS["files"]):
        user = secrets.choice(users)
        yield create_item(user)


def create_file_type_items(user):
    """Create one ready file for each file type category described in issue #597."""
    for file_type_item in FILE_TYPE_ITEMS:
        yield create_item(
            user,
            title=file_type_item["title"],
            file_data={
                "filename": file_type_item["filename"],
                "mimetype": file_type_item["mimetype"],
                "content": f"{file_type_item['title']} fixture".encode(),
            },
            parent=None,
        )


def build_profile_item(owner, parent, **kwargs):
    """Build an unsaved item under parent, or a root item when parent is None."""
    item_id = uuid.uuid4()
    return models.Item(
        id=item_id,
        path=f"{parent.path}.{item_id}" if parent else str(item_id),
        creator=owner,
        link_reach=models.LinkReachChoices.RESTRICTED if parent is None else None,
        **kwargs,
    )


def build_profile_file(rng, owner, parent, number):
    """Build an unsaved ready file with a mimetype and size drawn from production stats."""
    mimetype, extension, _weight, median_size = rng.choices(
        defaults.PROFILE_MIMETYPES,
        weights=[mimetype[2] for mimetype in defaults.PROFILE_MIMETYPES],
    )[0]
    filename = f"file-{number}.{extension}"
    return build_profile_item(
        owner,
        parent,
        title=filename,
        filename=filename,
        type=models.ItemTypeChoices.FILE,
        upload_state=models.ItemUploadStateChoices.READY,
        mimetype=mimetype,
        size=int(rng.lognormvariate(math.log(median_size), 1.5)),
    )


def build_tree(rng, owner, folders, files, depth):
    """Build the unsaved items of a tree and return them with its roots."""
    if not folders:
        roots = [build_profile_file(rng, owner, None, number) for number in range(files)]
        return roots, roots

    # The first folders form a chain reaching the depth, the others hang
    # randomly on folders that leave room for files below them.
    root = build_profile_item(owner, None, title="Folder 0", type=models.ItemTypeChoices.FOLDER)
    tree = [(root, 1)]
    parents = [(root, 1)] if depth > 2 else []
    for number in range(1, folders):
        parent, level = tree[-1] if number < depth - 1 else rng.choice(parents)
        folder = build_profile_item(
            owner, parent, title=f"Folder {number}", type=models.ItemTypeChoices.FOLDER
        )
        tree.append((folder, level + 1))
        if level + 1 < depth - 1:
            parents.append((folder, level + 1))

    tree_folders = [folder for folder, _level in tree]
    tree_files = [
        build_profile_file(
            rng,
            owner,
            tree_folders[depth - 2] if number == 0 else rng.choice(tree_folders),
            number,
        )
        for number in range(files)
    ]
    return tree_folders + tree_files, [root]


def create_profile(name, spec, user=None):
    """Create items following a production profile for the given or a dedicated user."""
    rng = random.Random(name)  # noqa: S311  # seeded for reproducible shapes
    user = user or get_or_create_demo_user(
        {"email": f"{name}@profiles.demo", "full_name": f"Profile {name}", "short_name": name}
    )
    org = get_or_create_demo_user(
        {
            "email": f"org-{name}@profiles.demo",
            "full_name": f"Organization {name}",
            "short_name": f"org-{name}",
        }
    )
    items = []
    accesses = []

    for folders, files, depth in spec["owned"]:
        tree, roots = build_tree(rng, user, folders, files, depth)
        items += tree
        accesses += [
            models.ItemAccess(item=root, user=user, role=models.RoleChoices.OWNER) for root in roots
        ]

    owned_files = [item for item in items if item.type == models.ItemTypeChoices.FILE]
    now = timezone.now()
    for item in rng.sample(owned_files, spec["trash"]):
        item.deleted_at = item.ancestors_deleted_at = now

    for folders, files, depth, role in spec["shared"]:
        tree, roots = build_tree(rng, org, folders, files, depth)
        items += tree
        for root in roots:
            accesses += [
                models.ItemAccess(item=root, user=org, role=models.RoleChoices.OWNER),
                models.ItemAccess(item=root, user=user, role=role),
            ]

    traced, _roots = build_tree(rng, org, 0, spec["link_traces"], 1)
    for item in traced:
        item.link_reach = models.LinkReachChoices.PUBLIC
    items += traced
    accesses += [
        models.ItemAccess(item=item, user=org, role=models.RoleChoices.OWNER) for item in traced
    ]

    models.Item.objects.bulk_create(items, batch_size=5000)
    models.ItemAccess.objects.bulk_create(accesses, batch_size=5000)
    models.LinkTrace.objects.bulk_create(
        [models.LinkTrace(item=item, user=user) for item in traced], batch_size=5000
    )


def create_demo(stdout, *, file_types=False, profiles=(), profile_user=None):
    """
    Create a database with demo data for developers to work in a realistic environment.
    """
    with Timeit(stdout, "Creating users"):
        users = list(create_users())

    with Timeit(stdout, "Creating items"):
        items = list(create_items(users))

    with Timeit(stdout, "Creating development users"):
        dev_users = list(create_dev_users())

    with Timeit(stdout, "Creating item accesses on development users"):
        for user in dev_users:
            create_item(user)

            for item in items:
                factories.UserItemAccessFactory(
                    item=item,
                    user=user,
                    role=models.RoleChoices.READER,
                )

    if file_types:
        with Timeit(stdout, "Creating file type items"):
            list(create_file_type_items(dev_users[0]))

    with Timeit(stdout, "Sharing development users items with demo users"):
        dev_items = models.Item.objects.filter(
            creator__in=dev_users, type=models.ItemTypeChoices.FILE
        ).exclude(accesses__user__in=users)
        for item in dev_items:
            nb_users = secrets.randbelow(len(users)) + 1
            shared_users = fake.random_sample(elements=users, length=nb_users)
            for user in shared_users:
                factories.UserItemAccessFactory(
                    item=item,
                    user=user,
                    role=models.RoleChoices.READER,
                )

            names = ", ".join(user.short_name for user in shared_users)
            item.title = f"{item.title} (shared with {names})"
            item.save(update_fields=["title"])

    user = None
    if profile_user:
        user = models.User.objects.filter(email=profile_user).first()
        if user is None:
            raise CommandError(f"No user found with email {profile_user}")

    for name in profiles:
        with Timeit(stdout, f"Creating profile {name}"):
            create_profile(name, defaults.PROFILES[name], user=user)


class Command(BaseCommand):
    """A management command to create a demo database."""

    help = __doc__

    def add_arguments(self, parser):
        """Add argument to require forcing execution when not in debug mode."""
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="Force command execution despite DEBUG is set to False",
        )
        parser.add_argument(
            "--file_types",
            "--file-types",
            action="store_true",
            default=False,
            help="Create items for several file types",
        )
        parser.add_argument(
            "--profiles",
            nargs="*",
            choices=list(defaults.PROFILES),
            default=None,
            help="Create users with item trees shaped like production profiles (all by default)",
        )
        parser.add_argument(
            "--profile-user",
            default=None,
            help="Email of an existing user to attach the single selected profile to",
        )

    def handle(self, *args, **options):
        """Handling of the management command."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                (
                    "This command is not meant to be used in production environment "
                    "except you know what you are doing, if so use --force parameter"
                )
            )

        # --profiles without values selects every profile
        profiles = options["profiles"]
        if profiles == []:
            profiles = list(defaults.PROFILES)

        if options["profile_user"] and len(profiles or ()) != 1:
            raise CommandError("--profile-user requires exactly one profile in --profiles")

        create_demo(
            self.stdout,
            file_types=options["file_types"],
            profiles=profiles or (),
            profile_user=options["profile_user"],
        )
