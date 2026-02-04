"""Management command to prepare the mirroring items history."""

from django.core.management.base import BaseCommand

from core.models import (
    Item,
    ItemTypeChoices,
    ItemUploadStateChoices,
    MirrorItemTask,
    MirrorItemTaskStatusChoices,
)


class Command(BaseCommand):
    """Management command to prepare the mirroring items history."""

    help = (
        "Prepare the mirroring items history by creating a MirrorItemTask for "
        "each item that is a file."
    )

    def handle(self, *args, **options):
        """Prepare the mirroring items history."""

        self.stdout.write(self.style.SUCCESS("Preparing mirroring items history..."))

        items_id = (
            Item.objects.prefetch_related("mirror_tasks")
            .filter(
                type=ItemTypeChoices.FILE,
                upload_state__in=[
                    status[0]
                    for status in ItemUploadStateChoices.choices
                    if status[0] != ItemUploadStateChoices.PENDING
                ],
                mirror_tasks__isnull=True,  # left outer join on mirror_tasks to avoid duplicates
            )
            .values_list("id", flat=True)
        )
        processed_count = 0
        batch = []
        batch_size = 100
        total_items = items_id.count()
        self.stdout.write(f"Processing {total_items} items...")
        for item_id in items_id:
            processed_count += 1
            batch.append(
                MirrorItemTask(
                    item_id=item_id,
                    status=MirrorItemTaskStatusChoices.PENDING,
                )
            )

            if processed_count % batch_size == 0:
                MirrorItemTask.objects.bulk_create(batch, batch_size=batch_size)
                batch = []
                self.stdout.write(f"Processed {processed_count}/{total_items} items...")

        if batch:
            MirrorItemTask.objects.bulk_create(batch, batch_size=len(batch))

        self.stdout.write(
            self.style.SUCCESS(f"Prepared {total_items} mirroring items history.")
        )
