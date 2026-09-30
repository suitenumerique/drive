"""View serving the Prometheus metrics."""

from django.http import HttpResponse
from django.views.decorators.http import require_safe

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from core.metrics.collectors import HostnameLabelled, WorkerProcessesCollector


@require_safe
def metrics_view(request):
    """Serve the metrics in the Prometheus text format."""
    registry = CollectorRegistry()
    registry.register(HostnameLabelled(WorkerProcessesCollector()))
    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
