"""Test the build information metric."""

from unittest import mock

from prometheus_client import CollectorRegistry, generate_latest

from core.metrics.collectors import BuildInfoCollector, search_indexer_label


def _build_info_line():
    """Return the drive_build_info sample the collector yields."""
    registry = CollectorRegistry()
    registry.register(BuildInfoCollector())

    lines = [
        line
        for line in generate_latest(registry).decode().splitlines()
        if line.startswith("drive_build_info{")
    ]
    assert len(lines) == 1
    return lines[0]


def test_metrics_build_info():
    """The version and the search configuration of the deployment should be exposed."""
    with mock.patch("drive.settings.get_release", return_value="1.2.3"):
        line = _build_info_line()

    assert line.endswith("} 1.0")
    assert 'version="1.2.3"' in line
    assert 'indexed_search="true"' in line
    assert 'search_indexer="FindItemIndexer"' in line
    assert 'environment="' in line


def test_metrics_build_info_without_indexer(settings):
    """An unconfigured indexer should be named, not left out of the labels."""
    settings.SEARCH_INDEXER_CLASS = None

    assert search_indexer_label() == "none"
    assert 'search_indexer="none"' in _build_info_line()


def test_metrics_build_info_labels_are_bounded(settings):
    """Only the class name should be labelled, never the dotted path of the setting."""
    settings.SEARCH_INDEXER_CLASS = "core.services.search_indexers.FindItemIndexer"

    assert search_indexer_label() == "FindItemIndexer"
    assert "core.services" not in _build_info_line()
