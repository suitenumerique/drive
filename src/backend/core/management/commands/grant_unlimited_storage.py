"""Grant unlimited storage to users already using more than a threshold."""

from django.core.management.base import BaseCommand
from django.db.models import Q, Sum

from core.models import User


class Command(BaseCommand):
    """
    Set storage_limit_override to 0 (unlimited) for every user whose quota
    counted storage exceeds the given threshold. Users with an existing
    override are left untouched so explicit per-user decisions are never
    clobbered.
    """

    help = "Set storage_limit_override=0 (unlimited) for users above a storage threshold"

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold-gb",
            type=float,
            required=True,
            help="Storage threshold in GB, users strictly above it are granted unlimited storage",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report the users that would be updated",
        )

    def handle(self, *args, **options):
        threshold = int(options["threshold_gb"] * 1000**3)

        # Same item filter as CreatorStorageComputeBackend.compute_storage_used
        # so the command agrees with the quota enforcement.
        users = (
            User.objects.filter(storage_limit_override__isnull=True)
            .annotate(
                total_size=Sum(
                    "items_created__size",
                    filter=Q(
                        items_created__hard_deleted_at__isnull=True,
                        items_created__quota_excluded=False,
                    ),
                    default=0,
                )
            )
            .filter(total_size__gt=threshold)
        )

        if options["dry_run"]:
            for email in users.values_list("email", flat=True):
                self.stdout.write(f"[dry-run] Would grant unlimited storage to {email}")
            self.stdout.write(
                f"[dry-run] Would grant unlimited storage to {users.count()} user(s)."
            )
            return

        user_ids = list(users.values_list("id", flat=True))
        count = User.objects.filter(id__in=user_ids).update(storage_limit_override=0)
        # No cache invalidation needed: only the storage used is cached and
        # this command changes the limit, which is read fresh on every call.
        self.stdout.write(f"Granted unlimited storage to {count} user(s).")
