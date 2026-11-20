"""Metrics that the application emits.

The factories return a no-op metric when PROMETHEUS_METRICS_ENABLED is false.
Therefore no module outside `core.metrics` imports prometheus_client, and a call
site has no condition.
"""

from __future__ import annotations

from django.conf import settings


class NoopMetric:
    """Stand-in for a metric of prometheus_client. It accepts every call."""

    def labels(self, *args, **kwargs):  # pylint: disable=unused-argument
        """Return self. The labels are dropped."""
        return self

    def inc(self, amount=1):  # pylint: disable=unused-argument
        """Drop an increment."""

    def dec(self, amount=1):  # pylint: disable=unused-argument
        """Drop a decrement."""

    def observe(self, amount):  # pylint: disable=unused-argument
        """Drop an observation."""

    def set(self, value):  # pylint: disable=unused-argument
        """Drop a value."""

    def set_to_current_time(self):
        """Drop a timestamp."""


NOOP = NoopMetric()


def counter(name, documentation, labels=(), registry=None):
    """Return a counter, or a no-op when the metrics are disabled."""
    if not settings.PROMETHEUS_METRICS_ENABLED:
        return NOOP

    # imported here, prometheus_client must not be loaded when the metrics are off
    from prometheus_client import REGISTRY, Counter  # noqa: PLC0415

    return Counter(
        name,
        documentation,
        labels,
        registry=REGISTRY if registry is None else registry,
    )


def histogram(name, documentation, labels=(), buckets=None, registry=None):
    """Return a histogram, or a no-op when the metrics are disabled."""
    if not settings.PROMETHEUS_METRICS_ENABLED:
        return NOOP

    # imported here, prometheus_client must not be loaded when the metrics are off
    from prometheus_client import REGISTRY, Histogram  # noqa: PLC0415

    arguments = {} if buckets is None else {"buckets": buckets}
    return Histogram(
        name,
        documentation,
        labels,
        registry=REGISTRY if registry is None else registry,
        **arguments,
    )


def gauge(name, documentation, labels=(), multiprocess_mode="livesum", registry=None):
    """Return a gauge, or a no-op when the metrics are disabled.

    `livesum` by default: the workers of gunicorn add their last values up.
    """
    if not settings.PROMETHEUS_METRICS_ENABLED:
        return NOOP

    # imported here, prometheus_client must not be loaded when the metrics are off
    from prometheus_client import REGISTRY, Gauge  # noqa: PLC0415

    return Gauge(
        name,
        documentation,
        labels,
        multiprocess_mode=multiprocess_mode,
        registry=REGISTRY if registry is None else registry,
    )
