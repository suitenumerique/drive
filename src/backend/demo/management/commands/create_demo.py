# ruff: noqa: S106
"""create_demo management command"""

import logging
import secrets
import time
from io import BytesIO

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from faker import Faker

from core import factories, models

from demo import defaults

fake = Faker()

logger = logging.getLogger(__file__)


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
    for user_id in range(defaults.NB_OBJECTS["users"]):
        email = f"user.test{user_id:d}@example.com"
        yield factories.UserFactory(
            admin_email=email,
            email=email,
            sub=email,
            password="!",
            is_superuser=False,
            is_active=True,
            is_staff=False,
        )


def create_dev_users():
    """Create development users"""
    for dev_user in defaults.DEV_USERS:
        email = dev_user["email"]
        user = factories.UserFactory(
            admin_email=email,
            email=email,
            sub=email,
            password="!",
            is_superuser=False,
            is_active=True,
            is_staff=False,
        )

        create_item(user)
        yield user


def create_item(user):
    """Create file item with the given user as creator"""
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
        parent=parent,
        title=fake.sentence(nb_words=4),
        filename="content.txt",
        description=fake.sentence(nb_words=10),
        mimetype="text/plain",
    )

    default_storage.save(item.file_key, BytesIO(fake.sentence(nb_words=50).encode()))

    return item


def create_items(users):
    """Create random items and file content for users"""
    for _id in range(defaults.NB_OBJECTS["files"]):
        user = secrets.choice(users)
        yield create_item(user)


def create_demo(stdout):
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

    def handle(self, *args, **options):
        """Handling of the management command."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                (
                    "This command is not meant to be used in production environment "
                    "except you know what you are doing, if so use --force parameter"
                )
            )

        create_demo(self.stdout)
