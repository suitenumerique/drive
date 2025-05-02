"""Management user to create a superuser."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from core import factories, models

COUNT = 1
DEPTH = 100

class Command(BaseCommand):
    """Management command to create a superuser from an email and password."""

    help = "Create a superuser with an email and a password"

    def handle(self, *args, **options):
        user = models.User.objects.first()
        self.create_children(None, 0)
        self.stdout.write(self.style.SUCCESS("coucou"))
        

    def create_children(self, item, depth):
        if depth == DEPTH:
            return
        user = models.User.objects.first()
        for i in range(COUNT):
            child = factories.ItemFactory(creator=user, parent=item, type=models.ItemTypeChoices.FOLDER)
            self.stdout.write(self.style.SUCCESS(f"child {i} created"))
            self.create_children(child, depth + 1)