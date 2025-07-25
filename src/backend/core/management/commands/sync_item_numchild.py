"""Sync the numchild field of items."""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Item, ItemTypeChoices


class Command(BaseCommand):
    """Sync the numchild field of items."""

    help = "Sync the numchild and numchild_folder fields for all items"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making actual changes",
        )

    def handle(self, *args, **options):
        """Sync the numchild and numchild_folder fields of items."""
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Get all non-deleted items
        items = Item.objects.filter(
            deleted_at__isnull=True,
            ancestors_deleted_at__isnull=True,
        ).order_by("path")

        items_to_update = []
        total_items = items.count()
        updated_count = 0
        processed_count = 0

        self.stdout.write(f"Processing {total_items} items...")

        for item in items:
            processed_count += 1

            # Show progress every 100 items
            if processed_count % 100 == 0:
                self.stdout.write(f"Processed {processed_count}/{total_items} items...")
            # Get all non-deleted children
            children = item.children().filter(
                deleted_at__isnull=True,
                ancestors_deleted_at__isnull=True,
            )

            # Count total children and folder children
            total_children = children.count()
            folder_children = children.filter(type=ItemTypeChoices.FOLDER).count()

            # Check if values need updating
            needs_update = (
                item.numchild != total_children
                or item.numchild_folder != folder_children
            )

            if needs_update:
                if dry_run:
                    self.stdout.write(
                        f"Would update {item.title} (ID: {item.id}): "
                        f"numchild {item.numchild} -> {total_children}, "
                        f"numchild_folder {item.numchild_folder} -> {folder_children}"
                    )
                else:
                    item.numchild = total_children
                    item.numchild_folder = folder_children
                    items_to_update.append(item)

                updated_count += 1

        if not dry_run and items_to_update:
            # Use bulk_update for better performance
            with transaction.atomic():
                Item.objects.bulk_update(
                    items_to_update, ["numchild", "numchild_folder"], batch_size=100
                )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: {updated_count} items would be updated")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully updated {updated_count} items")
            )
