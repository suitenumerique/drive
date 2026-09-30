"""Collectors assembled by the metrics view on every scrape."""

import logging
import socket

from prometheus_client import CollectorRegistry
from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.multiprocess import MultiProcessCollector

from drive.celery_app import app as celery_app

logger = logging.getLogger(__name__)

HOSTNAME_LABEL = "hostname"


class CeleryQueueCollector:
    """
    The number of tasks waiting on the default Celery queue, asked to the broker
    when the metrics are scraped.

    The workers have no endpoint of their own, and the queue is what tells that
    they are not keeping up. One queue for the whole deployment: every replica
    reports the same number, which is to be read with max(), never summed.
    """

    def collect(self):
        """Yield the gauge, or nothing when the broker cannot be asked."""
        length = self.queue_length()
        if length is None:
            return
        gauge = GaugeMetricFamily(
            "drive_celery_queue_length",
            "Tasks waiting on the default Celery queue, for the whole deployment "
            "(use max, not sum)",
            labels=["queue"],
        )
        gauge.add_metric([self.queue_name()], length)
        yield gauge

    @staticmethod
    def queue_name():
        """The queue the tasks are sent to: none of them names another one."""
        return celery_app.conf.task_default_queue

    def queue_length(self):
        """Ask the broker, quickly: a scrape must not hang on it."""
        try:
            with celery_app.connection_for_read() as connection:
                if connection.transport.driver_type != "redis":
                    return None
                connection.ensure_connection(max_retries=1, timeout=2)
                channel = connection.default_channel
                queue = self.queue_name()
                # kombu keeps one redis list per priority step
                keys = [
                    f"{queue}{channel.sep}{priority}" if priority else queue
                    for priority in channel.priority_steps
                ]
                return sum(channel.client.llen(key) for key in keys)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            logger.debug("could not read the celery queue length", exc_info=True)
            return None


class WorkerProcessesCollector:
    """
    The metrics of every worker process of this host.

    gunicorn runs several workers and the scrape is answered by one of them: the
    multiprocess collector reads what they all wrote to PROMETHEUS_MULTIPROC_DIR
    and adds it up, instead of reporting the numbers of that worker alone.
    """

    def collect(self):
        """Yield the aggregated metrics."""
        # a registry of its own: the collector registers itself in the one it is given
        yield from MultiProcessCollector(CollectorRegistry()).collect()


class HostnameLabelled:
    """
    The metrics of another collector, labelled with the name of this host.

    The label is for a scraper that goes through a load balancer (an ingress in
    front of several replicas): each scrape is then answered by a different
    replica, and without it their counters would land in the same series.
    """

    def __init__(self, collector):
        self.collector = collector
        self.hostname = socket.gethostname()

    def collect(self):
        """Yield the metrics with the hostname added to every sample."""
        for metric in self.collector.collect():
            labelled = Metric(metric.name, metric.documentation, metric.type)
            for sample in metric.samples:
                labelled.add_sample(
                    sample.name,
                    {**sample.labels, HOSTNAME_LABEL: self.hostname},
                    sample.value,
                    sample.timestamp,
                    sample.exemplar,
                )
            yield labelled
