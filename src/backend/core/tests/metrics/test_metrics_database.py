"""Test the metrics of the psycopg pool."""

from unittest import mock

from prometheus_client import REGISTRY

from core.metrics.database import record_database_pool

STATS = {
    "pool_size": 4,
    "pool_available": 3,
    "requests_waiting": 1,
    "requests_num": 10,
    "requests_queued": 2,
    "requests_wait_ms": 1500,
    "requests_errors": 1,
    "connections_num": 5,
    "connections_errors": 0,
}


def _value(name, alias="default"):
    return REGISTRY.get_sample_value(name, {"alias": alias}) or 0


def _connections(options):
    connection = mock.Mock()
    connection.settings_dict = {"OPTIONS": options}
    connection.pool.pop_stats.return_value = STATS
    return {"default": connection}


def test_metrics_database_pool_recorded():
    """The gauges should be set and the counters incremented with what the pool popped."""
    requests_before = _value("drive_db_pool_requests_total")
    wait_before = _value("drive_db_pool_requests_wait_seconds_total")

    with mock.patch("core.metrics.database.connections", _connections({"pool": {"min_size": 1}})):
        record_database_pool()

    assert _value("drive_db_pool_size") == 4
    assert _value("drive_db_pool_available") == 3
    assert _value("drive_db_pool_requests_waiting") == 1
    assert _value("drive_db_pool_requests_total") == requests_before + 10
    assert _value("drive_db_pool_requests_wait_seconds_total") == wait_before + 1.5


def test_metrics_database_pool_ignored_without_pool():
    """A connection without a pool should not be asked for stats."""
    connections = _connections({})

    with mock.patch("core.metrics.database.connections", connections):
        record_database_pool()

    connections["default"].pool.pop_stats.assert_not_called()


def test_metrics_database_pool_errors_never_fail():
    """A pool that cannot give its stats should be skipped silently."""
    connections = _connections({"pool": {"min_size": 1}})
    connections["default"].pool.pop_stats.side_effect = RuntimeError("closed")

    with mock.patch("core.metrics.database.connections", connections):
        record_database_pool()
