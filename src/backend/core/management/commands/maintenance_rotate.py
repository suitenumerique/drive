"""Write back the escrow copies the LaSuite maintenance tool re-wrapped for a new key."""

from django.core.management.base import BaseCommand, CommandError

from core.services.maintenance_escrow import ManifestError, rotate


class Command(BaseCommand):
    """Replace each root's escrow copy with its re-wrapped one, in one transaction."""

    help = (
        "Replace the escrow copies of a keys-only export with those the LaSuite "
        "maintenance tool re-wrapped for a new maintenance key, all in one transaction; "
        "a root whose copy changed since the export keeps it."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "folder", help="The tool's rotation output (unzipped), with manifest.ndjson at its root"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Check every root, change nothing"
        )

    def handle(self, *args, **options):
        try:
            summary = rotate(options["folder"], dry_run=options["dry_run"])
        except ManifestError as error:
            raise CommandError(str(error)) from error

        verb = "Would rotate" if options["dry_run"] else "Rotated"

        self.stdout.write(f"{verb} the copies of {len(summary.rotated)} encryption root(s).")

        for root_id, reason in summary.skipped.items():
            self.stdout.write(self.style.WARNING(f"Not rotated: {root_id} ({reason})"))
