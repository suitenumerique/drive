"""Process pending mirror tasks in batches."""

from django.core.management.base import BaseCommand

from core.models import MirrorItemTask, MirrorItemTaskStatusChoices
from core.tasks.storage import mirror_file


class Command(BaseCommand):
    """Process pending mirror tasks."""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            action="store",
            dest="batch_size",
            type=int,
            default=100,
            help="Number of tasks to process in each batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        processing_count = MirrorItemTask.objects.filter(
            status=MirrorItemTaskStatusChoices.PROCESSING
        ).count()

        slots_available = batch_size - processing_count

        if slots_available <= 0:
            self.stdout.write(
                f"No slots available for pending tasks "
                f"({processing_count} tasks already processing)"
            )
            return

        pending_tasks = MirrorItemTask.objects.filter(
            status=MirrorItemTaskStatusChoices.PENDING, retries=0
        )[:slots_available]

        count_tasks = 0
        for task in pending_tasks:
            mirror_file.delay(task.id)
            count_tasks += 1

        self.stdout.write(
            f"Enqueued {count_tasks} pending mirror tasks for processing "
            f"({processing_count} already processing)"
        )
