"""Test the Prometheus metrics endpoint."""

import socket

from django.urls import resolve

import pytest
from prometheus_client import REGISTRY, Counter, values
from rest_framework.test import APIClient

from core.tests.utils.urls import reload_urls

from drive.settings import Production

pytestmark = pytest.mark.django_db

API_KEY = "test-prometheus-api-key"
AUTH_MIDDLEWARE = "core.middleware.PrometheusAuthMiddleware"
BEFORE_MIDDLEWARE = "django_prometheus.middleware.PrometheusBeforeMiddleware"
AFTER_MIDDLEWARE = "django_prometheus.middleware.PrometheusAfterMiddleware"


@pytest.fixture(name="metrics_enabled")
def metrics_enabled_fixture(settings, monkeypatch, tmp_path):
    """Configure the application the way PROMETHEUS_METRICS_ENABLED does at startup."""
    settings.PROMETHEUS_METRICS_ENABLED = True
    settings.PROMETHEUS_API_KEY = API_KEY
    settings.MIDDLEWARE = [
        AUTH_MIDDLEWARE,
        BEFORE_MIDDLEWARE,
        *settings.MIDDLEWARE,
        AFTER_MIDDLEWARE,
    ]
    # what a worker started with PROMETHEUS_MULTIPROC_DIR does on its own:
    # write the values to that directory instead of keeping them in memory
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setattr(values, "ValueClass", values.MultiProcessValue())
    # the route only exists when the metrics are enabled at import time
    reload_urls()
    yield
    settings.PROMETHEUS_METRICS_ENABLED = False
    reload_urls()


def _get_metrics(**headers):
    return APIClient().get("/metrics", **headers)


@pytest.mark.parametrize("path", ["/metrics", "/metrics/", "/prometheus/metrics"])
def test_api_metrics_disabled_by_default(path):
    """Nothing should be served unless the metrics are enabled, key or not."""
    response = APIClient().get(path, HTTP_AUTHORIZATION=f"Bearer {API_KEY}")

    assert response.status_code == 404


@pytest.mark.usefixtures("metrics_enabled")
@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "Bearer",
        "Bearer ",
        "Bearer wrong-key",
        f"Bearer {API_KEY} ",
        f"bearer {API_KEY}",
        f"Token {API_KEY}",
        f"Api-Key {API_KEY}",
        API_KEY,
        "Bearer clé-non-ascii",
    ],
)
def test_api_metrics_requires_the_api_key(authorization):
    """Anything but the exact bearer token should be refused, before any other work."""
    headers = {} if authorization is None else {"HTTP_AUTHORIZATION": authorization}

    response = _get_metrics(**headers)

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == 'Bearer realm="metrics"'
    assert response.content == b"Unauthorized"
    assert not response.cookies


@pytest.mark.usefixtures("metrics_enabled")
@pytest.mark.parametrize("api_key", [None, ""])
@pytest.mark.parametrize("authorization", ["Bearer ", "Bearer None", "Bearer"])
def test_api_metrics_fails_closed_without_api_key(settings, api_key, authorization):
    """With no key configured nothing should be served, whatever is presented."""
    settings.PROMETHEUS_API_KEY = api_key

    response = _get_metrics(HTTP_AUTHORIZATION=authorization)

    assert response.status_code == 401


@pytest.mark.usefixtures("metrics_enabled")
def test_api_metrics_served_with_the_api_key():
    """
    The right key should get what every worker wrote to the shared directory, labelled
    with the name of the host, and the call should not create a session.
    """
    counter = Counter("drive_metrics_test", "A counter written by a worker.", registry=None)
    counter.inc(3)

    response = _get_metrics(HTTP_AUTHORIZATION=f"Bearer {API_KEY}")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert (
        f'drive_metrics_test_total{{hostname="{socket.gethostname()}"}} 3.0'
        in response.content.decode()
    )
    assert not response.cookies


@pytest.mark.usefixtures("metrics_enabled")
def test_api_metrics_redirected_to_https_by_default(settings):
    """
    Where the application is reached directly, a scrape over plain http should be sent
    to https like everything else: the bearer token must not travel in clear.
    """
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_REDIRECT_EXEMPT = Production.SECURE_REDIRECT_EXEMPT

    response = _get_metrics(HTTP_AUTHORIZATION=f"Bearer {API_KEY}")

    assert response.status_code == 301
    assert response["Location"] == "https://testserver/metrics"


@pytest.mark.usefixtures("metrics_enabled")
def test_api_metrics_exempt_from_the_ssl_redirect(settings):
    """
    With PROMETHEUS_METRICS_SSL_REDIRECT_EXEMPT, a Prometheus reaching the pods over
    plain http should be served, and every other path still sent to https.
    """
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_REDIRECT_EXEMPT = [*Production.SECURE_REDIRECT_EXEMPT, "^metrics$"]

    response = _get_metrics(HTTP_AUTHORIZATION=f"Bearer {API_KEY}")
    assert response.status_code == 200

    response = APIClient().get("/api/v1.0/config/")
    assert response.status_code == 301


@pytest.mark.usefixtures("metrics_enabled")
def test_api_metrics_is_read_only():
    """Only GET and HEAD should be answered."""
    response = APIClient().post("/metrics", HTTP_AUTHORIZATION=f"Bearer {API_KEY}")

    assert response.status_code == 405


@pytest.mark.usefixtures("metrics_enabled")
@pytest.mark.parametrize(
    "path",
    ["/api/v1.0/metrics", "/api/v1.0/metrics/", "/api/v1.0/prometheus/metrics"],
)
def test_api_metrics_not_served_under_the_api(path):
    """The ingress publishes /api/: the metrics should not be found under it."""
    response = APIClient().get(path, HTTP_AUTHORIZATION=f"Bearer {API_KEY}")

    assert response.status_code == 404


@pytest.mark.usefixtures("metrics_enabled")
def test_api_metrics_other_routes_need_no_api_key():
    """The key should only be asked for on the metrics endpoint."""
    assert APIClient().get("/api/v1.0/config/").status_code == 200


def test_api_metrics_requests_are_labelled_by_view(settings):
    """A request should be counted under the name of its view, never under its path."""
    settings.MIDDLEWARE = [BEFORE_MIDDLEWARE, AFTER_MIDDLEWARE]
    path = "/api/v1.0/config/"
    labels = {"status": "200", "view": resolve(path).view_name, "method": "GET"}
    metric = "django_http_responses_total_by_status_view_method_total"
    before = REGISTRY.get_sample_value(metric, labels) or 0

    response = APIClient().get(path)

    assert response.status_code == 200
    assert REGISTRY.get_sample_value(metric, labels) == before + 1
    assert not any(
        path in value
        for family in REGISTRY.collect()
        for sample in family.samples
        for value in sample.labels.values()
    )
