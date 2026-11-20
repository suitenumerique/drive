"""Test the metrics facade the application code emits through."""

import importlib
import sys
from unittest import mock

from prometheus_client import CollectorRegistry

from core.metrics import events


def test_metrics_events_noop_when_disabled(settings):
    """With the metrics off, the factories should return an object recording nothing."""
    settings.PROMETHEUS_METRICS_ENABLED = False

    metric = events.counter("drive_events_noop_total", "A counter nobody counts.")

    assert metric is events.NOOP
    assert metric.labels(kind="a").inc() is None
    assert metric.observe(1.5) is None
    assert metric.set(2) is None
    assert metric.set_to_current_time() is None


def test_metrics_events_do_not_import_prometheus_client_when_disabled(settings):
    """Nothing should load prometheus_client while the metrics are disabled."""
    settings.PROMETHEUS_METRICS_ENABLED = False

    # importing a module set to None in sys.modules raises ImportError
    with mock.patch.dict(sys.modules, {"prometheus_client": None}):
        module = importlib.reload(events)

        assert module.counter("drive_events_unloaded_total", "A counter.") is module.NOOP
        assert module.histogram("drive_events_unloaded", "A histogram.") is module.NOOP
        assert module.gauge("drive_events_unloaded_gauge", "A gauge.") is module.NOOP


def test_metrics_events_counter_recorded(settings):
    """With the metrics on, a counter should record what it is given, per label."""
    settings.PROMETHEUS_METRICS_ENABLED = True
    registry = CollectorRegistry()

    metric = events.counter(
        "drive_events_counter_total", "A counter the tests count.", ["kind"], registry=registry
    )
    metric.labels(kind="first").inc()
    metric.labels(kind="first").inc(2)
    metric.labels(kind="second").inc()

    assert registry.get_sample_value("drive_events_counter_total", {"kind": "first"}) == 3
    assert registry.get_sample_value("drive_events_counter_total", {"kind": "second"}) == 1


def test_metrics_events_histogram_recorded(settings):
    """A histogram should observe into the buckets it was given, not the default ones."""
    settings.PROMETHEUS_METRICS_ENABLED = True
    registry = CollectorRegistry()

    metric = events.histogram(
        "drive_events_items",
        "A number of items.",
        ["scope"],
        buckets=[1, 10],
        registry=registry,
    )
    metric.labels(scope="subtree").observe(5)

    labels = {"scope": "subtree"}
    assert registry.get_sample_value("drive_events_items_count", labels) == 1
    assert registry.get_sample_value("drive_events_items_sum", labels) == 5
    assert registry.get_sample_value("drive_events_items_bucket", {**labels, "le": "1.0"}) == 0
    assert registry.get_sample_value("drive_events_items_bucket", {**labels, "le": "10.0"}) == 1


def test_metrics_events_gauge_recorded(settings):
    """A gauge should hold the last value it was set to."""
    settings.PROMETHEUS_METRICS_ENABLED = True
    registry = CollectorRegistry()

    metric = events.gauge("drive_events_gauge", "A gauge.", registry=registry)
    metric.set(7)

    assert registry.get_sample_value("drive_events_gauge") == 7
