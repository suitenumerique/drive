"""Convert paths of items to uuid format."""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Item, ItemTypeChoices


class Command(BaseCommand):
    """Convert paths of items to uuid format."""

    help = "Convert paths of items to uuid format"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making actual changes",
        )

    def handle(self, *args, **options):
        """Convert paths of items to uuid format."""
        dry_run = options["dry_run"]

        items = Item.objects.all().filter(path__match="*.000000*.*").extra(
            select={'path_depth': 'nlevel(path)'},
            order_by=['-path_depth']
        )
        count = items.count()

        self.stdout.write(
            self.style.SUCCESS(f"DRY RUN: {count} items would be updated")
        )

        for item in items:
            self.stdout.write(f"{item.path}, {item.deleted_at}")
            path_parts = str(item.path).split(".")
            new_path_parts = []
            parts_processed = []
            for part in path_parts:
                parts_processed.append(part)
                if len(part) == 7:
                    # new_path_parts.append("NEW")
                    ancestor = Item.objects.get(path=".".join(parts_processed))
                    if not ancestor:
                        self.stdout.write(f"Ancestor not found: {parts_processed}")
                        break
                    new_path_parts.append(str(ancestor.id))
                else:
                    new_path_parts.append(part)
            new_path = ".".join(new_path_parts)
            self.stdout.write(f"-> {new_path}")
            item.path = new_path
        
        if not dry_run: 
            self.stdout.write(self.style.SUCCESS("Saving items..."))
            for item in items:
                item.save()
            

