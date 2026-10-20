"""Import a batch recovery decrypted by the LaSuite maintenance tool."""

from django.core.management.base import BaseCommand, CommandError

from core.services.maintenance_escrow import ManifestError, import_export


class Command(BaseCommand):
    """Switch the trees of a decrypted copy back to plaintext."""

    help = (
        "Put back in plaintext the trees of an export the LaSuite maintenance tool "
        "decrypted, one tree per transaction; trees edited since the export, or with "
        "an item that could not be decrypted, stay encrypted."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "folder", help="The decrypted copy (unzipped), with manifest.ndjson at its root"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Check every tree, change nothing"
        )

    def handle(self, *args, **options):
        try:
            summary = import_export(options["folder"], dry_run=options["dry_run"])
        except ManifestError as error:
            raise CommandError(str(error)) from error

        verb = "Would switch" if options["dry_run"] else "Switched"

        self.stdout.write(f"{verb} {len(summary.switched)} tree(s) to plaintext.")

        for root_id, reason in summary.skipped.items():
            self.stdout.write(self.style.WARNING(f"Kept encrypted: {root_id} ({reason})"))
