"""
Handle search setup that needs to be done at bootstrap time.
"""

import time

from django.core.management.base import BaseCommand, CommandError

import structlog

from core.services.search_indexers import get_file_indexer

logger = structlog.get_logger("drive.search.bootstrap_search")


class Command(BaseCommand):
    """Index all files to remote search service"""

    help = __doc__

    def add_arguments(self, parser):
        """Add argument to require forcing execution when not in debug mode."""
        parser.add_argument(
            "--batch-size",
            action="store",
            dest="batch_size",
            type=int,
            default=50,
            help="Indexation query batch size",
        )

    def handle(self, *args, **options):
        """Launch and log search index generation."""
        indexer = get_file_indexer()

        if not indexer:
            logger.warning("search_index_disabled")
            return

        logger.info("search_index_started")
        start = time.perf_counter()

        try:
            count = indexer.index(batch_size=options["batch_size"])
        except Exception as err:
            logger.exception("search_index_failed", error=str(err))
            raise CommandError("Unable to regenerate index") from err

        logger.info(
            "search_index_finished",
            count=count,
            duration_ms=round((time.perf_counter() - start) * 1000),
        )
