"""Measure query performance in a disposable PostgreSQL database."""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections, transaction
from django.test.utils import override_settings

from core.services.benchmark import PROFILES, Benchmark


@contextmanager
def temporary_database():
    """Create only a fresh database; restore the connection and drop it on exit."""
    if connection.vendor != "postgresql" or len(list(connections)) != 1:
        raise CommandError("benchmark requires a single PostgreSQL database configuration")
    if connection.in_atomic_block:
        raise CommandError("benchmark cannot run inside an existing transaction")
    original_name = connection.settings_dict["NAME"]
    temporary_name = f"drive_bench_{uuid.uuid4().hex}"
    created = False
    connection.close()
    try:
        # Django's maintenance connection does not connect to the benchmark DB.
        with connection._nodb_cursor() as cursor:  # pylint: disable=protected-access  # noqa: SLF001
            cursor.execute(f"CREATE DATABASE {connection.ops.quote_name(temporary_name)}")
        created = True
        connection.settings_dict["NAME"] = temporary_name
        yield temporary_name
    finally:
        connection.close()
        connection.settings_dict["NAME"] = original_name
        if created:
            with connection._nodb_cursor() as cursor:  # pylint: disable=protected-access  # noqa: SLF001
                cursor.execute(f"DROP DATABASE {connection.ops.quote_name(temporary_name)}")


class Command(BaseCommand):
    """Run API and SQL measurements without populating the configured database."""

    help = "Run query benchmarks in a temporary database (requires CREATE DATABASE permission)"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=("pghero", "historical"), default="pghero")
        parser.add_argument("--profile", choices=(*PROFILES, "large"), default="smoke")
        parser.add_argument("--reps", type=int, help="Repetitions per scenario, minimum 2")
        parser.add_argument("--restrictions", action="store_true")
        parser.add_argument("--output", type=Path, help="New JSON output path; never overwritten")
        parser.add_argument("--commit", help="Git SHA, if the repository is not mounted")

    def handle(self, *args, **options):
        if options["reps"] is not None and options["reps"] < 2:
            raise CommandError("--reps must be at least 2")
        output = options["output"] or Path("bench_results") / (
            f"bench_{options['mode']}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
        )
        if output.exists():
            raise CommandError(f"Output already exists: {output}")
        runner = Benchmark(
            mode=options["mode"],
            profile=options["profile"],
            reps=options["reps"],
            restrictions=options["restrictions"],
            output=output,
            commit=options["commit"],
        )
        # Keep requests local and disable external search, email and entitlement services.
        # Roll back the workload to discard on_commit background jobs, like pytest did.
        with (
            override_settings(
                ALLOWED_HOSTS=["testserver"],
                SECURE_SSL_REDIRECT=False,
                CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
                SESSION_CACHE_ALIAS="default",
                EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                SEARCH_INDEXER_CLASS=None,
                FEATURES_INDEXED_SEARCH=True,
                ENTITLEMENTS_BACKEND="core.entitlements.backends.static.StaticEntitlementsBackend",
                ENTITLEMENTS_BACKEND_PARAMETERS={},
            ),
            temporary_database() as database_name,
        ):
            self.stdout.write(f"Temporary database: {database_name}")
            call_command("migrate", interactive=False, verbosity=0)
            with transaction.atomic():
                result = runner.run()
                transaction.set_rollback(True)
        for name, stats in result["scenarios"].items():
            duration = stats["api"]["median_ms"] if "api" in stats else stats["ms_median"]
            self.stdout.write(f"{name}: {duration:.3f} ms")
        self.stdout.write(f"Results: {output}")
