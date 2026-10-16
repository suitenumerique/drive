"""Test the settings wiring of the Prometheus metrics."""

import os

import pytest

from drive.settings import Base

AUTH_MIDDLEWARE = "core.middleware.PrometheusAuthMiddleware"
BEFORE_MIDDLEWARE = "django_prometheus.middleware.PrometheusBeforeMiddleware"
AFTER_MIDDLEWARE = "django_prometheus.middleware.PrometheusAfterMiddleware"


def _settings_class(**attributes):
    """Settings with lists of their own: the setup edits them in place."""

    class MetricsSettings(Base):
        """Fake settings with the metrics enabled."""

        PROMETHEUS_METRICS_ENABLED = True
        PROMETHEUS_API_KEY = "key"
        PROMETHEUS_METRICS_SSL_REDIRECT_EXEMPT = False
        PROMETHEUS_DB_METRICS_ENABLED = True
        PROMETHEUS_MULTIPROC_DIR = None
        INSTALLED_APPS = ["core"]
        MIDDLEWARE = ["django.middleware.security.SecurityMiddleware"]
        SECURE_REDIRECT_EXEMPT = ["^__lbheartbeat__"]
        DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql"}}

    for name, value in attributes.items():
        setattr(MetricsSettings, name, value)
    return MetricsSettings


@pytest.fixture(autouse=True)
def restore_environment(monkeypatch):
    """The setup exports PROMETHEUS_MULTIPROC_DIR: give it back afterwards."""
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", "")


def test_prometheus_metrics_disabled_by_default():
    """The metrics should be opt-in."""
    assert Base.PROMETHEUS_METRICS_ENABLED is False


@pytest.mark.parametrize("api_key", [None, ""])
def test_prometheus_metrics_refused_without_api_key(api_key):
    """The application should refuse to start with the metrics on and no key."""
    settings_class = _settings_class(PROMETHEUS_API_KEY=api_key)

    with pytest.raises(ValueError, match="requires PROMETHEUS_API_KEY"):
        settings_class.setup_prometheus_metrics()


def test_prometheus_metrics_setup(tmp_path):
    """The setup should install the app, the middlewares, the database engine and the dir."""
    directory = tmp_path / "metrics"
    settings_class = _settings_class(PROMETHEUS_MULTIPROC_DIR=str(directory))

    settings_class.setup_prometheus_metrics()
    # a second call should not install anything twice
    settings_class.setup_prometheus_metrics()

    assert settings_class.INSTALLED_APPS == ["core", "django_prometheus"]
    assert settings_class.MIDDLEWARE == [
        AUTH_MIDDLEWARE,
        BEFORE_MIDDLEWARE,
        "django.middleware.security.SecurityMiddleware",
        AFTER_MIDDLEWARE,
    ]
    assert (
        settings_class.DATABASES["default"]["ENGINE"] == "django_prometheus.db.backends.postgresql"
    )
    assert settings_class.SECURE_REDIRECT_EXEMPT == ["^__lbheartbeat__"]
    assert directory.is_dir()
    assert os.environ["PROMETHEUS_MULTIPROC_DIR"] == str(directory)


def test_prometheus_metrics_setup_options(tmp_path):
    """The database engine should be left alone and the ssl exemption added on demand."""
    settings_class = _settings_class(
        PROMETHEUS_MULTIPROC_DIR=str(tmp_path),
        PROMETHEUS_DB_METRICS_ENABLED=False,
        PROMETHEUS_METRICS_SSL_REDIRECT_EXEMPT=True,
    )

    settings_class.setup_prometheus_metrics()
    settings_class.setup_prometheus_metrics()

    assert settings_class.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert settings_class.SECURE_REDIRECT_EXEMPT == ["^__lbheartbeat__", "^metrics$"]


def test_prometheus_metrics_custom_database_engine_left_alone(tmp_path):
    """Only the stock postgresql engine should be swapped for the instrumented one."""
    settings_class = _settings_class(
        PROMETHEUS_MULTIPROC_DIR=str(tmp_path),
        DATABASES={"default": {"ENGINE": "custom.backend"}},
    )

    settings_class.setup_prometheus_metrics()

    assert settings_class.DATABASES["default"]["ENGINE"] == "custom.backend"


def test_prometheus_metrics_refuses_a_symlinked_directory(tmp_path):
    """A link to somewhere else should not be used to share the metrics of the workers."""
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    settings_class = _settings_class(PROMETHEUS_MULTIPROC_DIR=str(link))

    with pytest.raises(ValueError, match="must be a directory owned by"):
        settings_class.setup_prometheus_metrics()
