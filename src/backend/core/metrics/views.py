"""View serving the Prometheus metrics."""

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_safe

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from core.metrics.business import DriveBusinessCollector
from core.metrics.collectors import (
    CeleryQueueCollector,
    HostnameLabelled,
    WorkerProcessesCollector,
)


@require_safe
def metrics_view(request):
    """Serve the metrics in the Prometheus text format."""
    registry = CollectorRegistry()
    registry.register(HostnameLabelled(WorkerProcessesCollector()))
    if settings.PROMETHEUS_CELERY_QUEUE_METRICS_ENABLED:
        registry.register(HostnameLabelled(CeleryQueueCollector()))
    if settings.PROMETHEUS_BUSINESS_METRICS_ENABLED:
        registry.register(HostnameLabelled(DriveBusinessCollector()))
    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
