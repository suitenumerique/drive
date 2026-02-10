"""Minimal HTTP client for CT-S3 (std-lib only)."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HttpResponse:
    """A minimal response view, suitable for safe evidence extraction."""

    status_code: int
    headers: dict[str, str]
    body_len: int


class HttpClientError(Exception):
    """Base class for CT-S3 HTTP transport errors."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def http_request(
    *,
    url: str,
    method: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout_s: float = 10.0,
) -> HttpResponse:
    """
    Perform an HTTP request without leaking sensitive URLs in raised errors.

    Returns a best-effort response with status + headers. For non-2xx HTTP
    status, the response is still returned (no exception).
    """
    request_headers = dict(headers or {})
    req = urllib.request.Request(url, data=body, method=method)
    for key, value in request_headers.items():
        req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            # Read a small amount to ensure the request fully completes, but do
            # not risk large reads in case of unexpected responses.
            read_bytes = resp.read(1024)
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return HttpResponse(
                status_code=int(resp.status),
                headers=resp_headers,
                body_len=len(read_bytes),
            )
    except urllib.error.HTTPError as exc:
        resp_headers = {k.lower(): v for k, v in exc.headers.items()}
        return HttpResponse(
            status_code=int(exc.code),
            headers=resp_headers,
            body_len=0,
        )
    except urllib.error.URLError as exc:
        reason: Any = getattr(exc, "reason", None)
        if isinstance(reason, socket.gaierror):
            raise HttpClientError("dns_failure") from None
        if isinstance(reason, TimeoutError):
            raise HttpClientError("connect_timeout") from None
        if isinstance(reason, ConnectionRefusedError):
            raise HttpClientError("connect_refused") from None
        raise HttpClientError("url_error") from None
    except TimeoutError:
        raise HttpClientError("connect_timeout") from None
