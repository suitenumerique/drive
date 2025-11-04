"""
Handle search setup that needs to be done at bootstrap time.
"""

import logging
import time

from django.core.management.base import BaseCommand, CommandError

from core.services.search_indexers import get_file_indexer

logger = logging.getLogger("drive.search.bootstrap_search")


class Command(BaseCommand):
    """Index all files to remote search service"""

    help = __doc__

    def handle(self, *args, **options):
        """Launch and log search index generation."""
        indexer = get_file_indexer()

        if not indexer:
            logger.warning("The indexer is not enabled or properly configured.")
            return

        logger.info("Starting to regenerate Find index...")
        start = time.perf_counter()

        try:
            count = indexer.index()
        except Exception as err:
            logger.exception(err)
            raise CommandError("Unable to regenerate index") from err

        duration = time.perf_counter() - start
        logger.info(
            "Search index regenerated from %d files(s) in %.2f seconds.",
            count,
            duration,
        )
