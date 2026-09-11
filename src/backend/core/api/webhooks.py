"""Webhook endpoints exposed to trusted external services."""

from django.http import Http404

from drf_spectacular.utils import extend_schema
from lasuite.malware_detection import malware_detection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class MalwareScanWebhookView(APIView):
    """Receive a scan verdict pushed by the file-scanner service.

    The scanner POSTs the report to the URL the FileScannerBackend handed it
    at submit time: the record UUID routes the payload and the per-record
    secret in the query string authenticates it. Verdict interpretation,
    secret verification and callback dispatch all live in the backend —
    this view only forwards the parsed payload.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)
    def post(self, request, record_id):
        """Forward the scanner's verdict to the malware detection backend."""
        handler = getattr(malware_detection, "handle_webhook_result", None)
        if handler is None:
            # The active backend (dummy, jcop) has no webhook flow.
            raise Http404
        handler(str(record_id), request.query_params.get("secret", ""), request.data)
        # Always acknowledge with a 2xx (the scanner treats redirects as
        # failures and retries): a bad secret or an unknown record is
        # dropped by the backend, and answering differently would give
        # a probe an oracle while making the scanner retry uselessly.
        return Response(status=status.HTTP_204_NO_CONTENT)
