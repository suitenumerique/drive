"""Export the encrypted trees for a batch recovery with the LaSuite maintenance tool."""

from django.core.management.base import BaseCommand, CommandError

from core.services.maintenance_escrow import export, key_id_from_fingerprint


class Command(BaseCommand):
    """Write manifest.ndjson and the encrypted files of every encryption root into a folder."""

    help = (
        "Export the encrypted trees (or those escrowed for one maintenance key) into a "
        "folder the LaSuite maintenance tool decrypts on an isolated computer, or with "
        "--keys-only their escrow copies, which the tool re-wraps for a new maintenance key."
    )

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True, help="Folder to write the export into")
        parser.add_argument(
            "--fingerprint",
            help=(
                "Only the trees escrowed for this maintenance key: its fingerprint, the "
                "40 digits the tool shows and the encryption server logs at startup "
                "(spaces allowed)"
            ),
        )
        parser.add_argument(
            "--keys-only",
            action="store_true",
            help=(
                "Only the escrow copy of each encryption root, no descendant and no file: "
                "what the tool re-wraps when the maintenance key is replaced"
            ),
        )

    def handle(self, *args, **options):
        try:
            summary = export(
                options["output"],
                key_id=options["fingerprint"] and key_id_from_fingerprint(options["fingerprint"]),
                keys_only=options["keys_only"],
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        if options["keys_only"]:
            self.stdout.write(f"Exported the copies of {summary.trees} encryption root(s).")
        else:
            self.stdout.write(
                f"Exported {summary.trees} tree(s): {summary.items} item(s), "
                f"{summary.files} file(s)."
            )

        if summary.missing_objects:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(summary.missing_objects)} file(s) missing from the object storage, "
                    "their trees will stay encrypted: " + ", ".join(summary.missing_objects[:10])
                )
            )
        if summary.without_copy:
            self.stdout.write(
                self.style.WARNING(
                    f"{summary.without_copy} tree(s) have no maintenance copy and cannot "
                    "be recovered this way (created before the escrow, or before their "
                    "owner's domain was covered)."
                )
            )
