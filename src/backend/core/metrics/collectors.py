"""Collectors assembled by the metrics view on every scrape."""

import socket

from prometheus_client import CollectorRegistry
from prometheus_client.core import Metric
from prometheus_client.multiprocess import MultiProcessCollector

HOSTNAME_LABEL = "hostname"


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
