"""URL configuration for the drive project"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path

from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("", include("wopi.urls")),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = (
        urlpatterns
        + staticfiles_urlpatterns()
        + static(settings.MEDIA_URL, item_root=settings.MEDIA_ROOT)
        + debug_toolbar_urls()
    )

# Serve the Prometheus metrics only when they are enabled for this environment.
# Outside of /api/ on purpose, so that the ingress of the application does not
# publish them, and behind a bearer token (core.middleware.PrometheusAuthMiddleware).
if settings.PROMETHEUS_METRICS_ENABLED:
    from core.metrics.views import metrics_view
    from core.middleware import METRICS_PATH

    urlpatterns += [path(METRICS_PATH.lstrip("/"), metrics_view, name="prometheus-metrics")]

if settings.LOAD_E2E_URLS:
    urlpatterns += [path("", include("e2e.urls"))]


if settings.USE_SWAGGER or settings.DEBUG:
    urlpatterns += [
        path(
            f"api/{settings.API_VERSION}/swagger.json",
            SpectacularJSONAPIView.as_view(
                api_version=settings.API_VERSION,
                urlconf="core.urls",
            ),
            name="client-api-schema",
        ),
        path(
            f"api/{settings.API_VERSION}/swagger/",
            SpectacularSwaggerView.as_view(url_name="client-api-schema"),
            name="swagger-ui-schema",
        ),
        re_path(
            f"api/{settings.API_VERSION}/redoc/",
            SpectacularRedocView.as_view(url_name="client-api-schema"),
            name="redoc-schema",
        ),
    ]
