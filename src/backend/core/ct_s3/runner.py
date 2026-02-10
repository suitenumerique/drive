"""CT-S3 runner implementation (audience-aware, deterministic reports)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit, urlunsplit

from django.conf import settings
from django.core.files.storage import default_storage

from botocore.exceptions import ClientError

from core.api import utils as api_utils

from . import constants
from .evidence import build_evidence
from .http_client import HttpClientError, http_request
from .safe import safe_str_hash, sha256_16
from .types import CheckResult, ProviderProfile, RunnerOptions


def _now_utc_compact() -> str:
    """Return a compact UTC timestamp used for deterministic run ids."""
    return time.strftime("%Y%m%d-%H%M%S", time.gmtime())


def _stable_uuid(run_id: str, suffix: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"ct-s3:{run_id}:{suffix}")


def _make_key(run_id: str, check_id: str, filename: str) -> str:
    item_id = _stable_uuid(run_id, check_id)
    return f"item/{item_id}/{filename}"


def resolve_provider_profile(profile_id: str) -> ProviderProfile:
    """Resolve the S3 provider profile from settings/default storage."""
    bucket_name = default_storage.bucket_name

    internal_endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", None) or ""
    external_signed_base_url = getattr(settings, "AWS_S3_DOMAIN_REPLACE", None) or None

    return ProviderProfile(
        profile_id=profile_id,
        bucket_name=bucket_name,
        internal_endpoint_url=str(internal_endpoint_url),
        external_signed_base_url=str(external_signed_base_url)
        if external_signed_base_url is not None
        else None,
    )


def _safe_request_id(headers: dict[str, str]) -> str | None:
    for key in ("x-amz-request-id", "x-request-id", "x-amzn-requestid"):
        if key in headers:
            return headers[key]
    return None


def _evidence_base(profile: ProviderProfile) -> dict[str, str | None]:
    return {
        "profile_id": profile.profile_id,
        "bucket_hash": sha256_16(profile.bucket_name),
        "internal_endpoint_hash": sha256_16(profile.internal_endpoint_url)
        if profile.internal_endpoint_url
        else None,
        "external_signed_base_hash": safe_str_hash(profile.external_signed_base_url),
    }


def _failure_from_http_client_error(exc: HttpClientError) -> tuple[str, str]:
    if exc.kind == "connect_timeout":
        return "s3.net.connect_timeout", "Check S3 connectivity from the runner."
    if exc.kind == "connect_refused":
        return "s3.net.connect_refused", "Check S3 endpoint is up and reachable."
    if exc.kind == "dns_failure":
        return "s3.net.dns_failure", "Check S3 endpoint DNS/host resolution."
    return "s3.net.connect_timeout", "Check S3 connectivity from the runner."


def _signed_get_headers_for_key(key: str) -> tuple[str, dict[str, str]]:
    signed_request = api_utils.generate_s3_authorization_headers(key)
    url = str(signed_request.url)
    headers = dict(signed_request.headers)
    # Ensure Host is explicit and stable for reporting.
    signed_host = urlsplit(url).netloc
    headers.setdefault("Host", signed_host)
    return url, headers


def _presigned_put_url_for_key(key_base: str, filename: str) -> str:
    item_like = SimpleNamespace(key_base=key_base, filename=filename)
    return str(api_utils.generate_upload_policy(item_like))


def _connect_url_for_presigned_url(
    connect_base_url: str, signed_url: str
) -> tuple[str, str]:
    signed_parts = urlsplit(signed_url)
    connect_parts = urlsplit(connect_base_url)
    connect_url = urlunsplit(
        (
            connect_parts.scheme,
            connect_parts.netloc,
            signed_parts.path,
            signed_parts.query,
            "",
        )
    )
    return connect_url, signed_parts.netloc


def run_ct_s3(  # noqa: PLR0912, PLR0915 # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    *,
    profile_id: str = constants.PROFILE_SEAWEEDFS_S3,
    run_id: str | None = None,
    options: RunnerOptions | None = None,
) -> dict:
    """Run CT-S3 checks and return a deterministic report dictionary."""
    run_id = run_id or _now_utc_compact()
    options = options or RunnerOptions()

    profile = resolve_provider_profile(profile_id)
    s3_client = default_storage.connection.meta.client

    results: list[CheckResult] = []

    def add_result(result: CheckResult) -> None:
        results.append(result)

    profile_safe = build_evidence(_evidence_base(profile))

    # --- CT-S3-003 (EXTERNAL_BROWSER): presign targets browser host
    check_id = "CT-S3-003"
    title = "EXTERNAL presigned PUT targets browser host"
    if not profile.external_signed_base_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=False,
                title=title,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_DOMAIN_REPLACE for the browser-visible host.",
                evidence={**profile_safe},
            )
        )
    else:
        signed_url = _presigned_put_url_for_key(
            key_base=f"item/{_stable_uuid(run_id, check_id)}",
            filename="ct-s3-upload.txt",
        )
        signed_host = urlsplit(signed_url).netloc
        expected_host = urlsplit(profile.external_signed_base_url).netloc
        ok = signed_host == expected_host
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=ok,
                title=title,
                failure_class=None if ok else "s3.signature.host_mismatch_external",
                next_action_hint=None
                if ok
                else "Ensure AWS_S3_DOMAIN_REPLACE matches the host used by browsers.",
                evidence={
                    **profile_safe,
                    "signed_host_hash": sha256_16(signed_host),
                    "expected_host_hash": sha256_16(expected_host),
                },
            )
        )

    # --- CT-S3-004 (EXTERNAL_BROWSER): presigned PUT succeeds (x-amz-acl required)
    check_id = "CT-S3-004"
    title = "EXTERNAL presigned PUT succeeds (x-amz-acl: private)"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=False,
                title=title,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    elif not profile.external_signed_base_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=False,
                title=title,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_DOMAIN_REPLACE for the browser-visible host.",
                evidence={**profile_safe},
            )
        )
    else:
        try:
            key_base = f"item/{_stable_uuid(run_id, check_id)}"
            signed_url = _presigned_put_url_for_key(
                key_base=key_base, filename="ct-s3-put.txt"
            )
            signed_parts = urlsplit(signed_url)
            expected_host = urlsplit(profile.external_signed_base_url).netloc

            if signed_parts.netloc != expected_host:
                add_result(
                    CheckResult(
                        check_id=check_id,
                        audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                        ok=False,
                        title=title,
                        failure_class="s3.signature.host_mismatch_external",
                        next_action_hint=(
                            "Ensure AWS_S3_DOMAIN_REPLACE matches the host used "
                            "by browsers."
                        ),
                        evidence={
                            **profile_safe,
                            "signed_host_hash": sha256_16(signed_parts.netloc),
                            "expected_host_hash": sha256_16(expected_host),
                        },
                    )
                )
            else:
                query = parse_qs(signed_parts.query)
                signed_headers = (query.get("X-Amz-SignedHeaders") or [""])[0]
                requires_acl = "x-amz-acl" in signed_headers.split(";")

                connect_url, signed_host = _connect_url_for_presigned_url(
                    profile.internal_endpoint_url, signed_url
                )

                if not requires_acl:
                    add_result(
                        CheckResult(
                            check_id=check_id,
                            audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                            ok=False,
                            title=title,
                            failure_class="s3.http.put_missing_required_header_x_amz_acl",
                            next_action_hint="Ensure presigned PUT signs and requires x-amz-acl.",
                            evidence={
                                **profile_safe,
                                "signed_host_hash": sha256_16(signed_host),
                                "signed_headers_includes_x_amz_acl": False,
                            },
                        )
                    )
                else:
                    resp = http_request(
                        url=connect_url,
                        method="PUT",
                        headers={"Host": signed_host, "x-amz-acl": "private"},
                        body=b"ct-s3",
                        timeout_s=options.http_timeout_s,
                    )
                    ok = 200 <= resp.status_code <= 299
                    add_result(
                        CheckResult(
                            check_id=check_id,
                            audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                            ok=ok,
                            title=title,
                            failure_class=None
                            if ok
                            else "s3.http.presigned_put_failed",
                            next_action_hint=None
                            if ok
                            else "Check S3 endpoint, host signing, and required headers.",
                            evidence={
                                **profile_safe,
                                "status_code": resp.status_code,
                                "request_id": _safe_request_id(resp.headers),
                                "signed_host_hash": sha256_16(signed_host),
                                "signed_headers_includes_x_amz_acl": True,
                            },
                        )
                    )
        except HttpClientError as exc:
            failure_class, hint = _failure_from_http_client_error(exc)
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                    ok=False,
                    title=title,
                    failure_class=failure_class,
                    next_action_hint=hint,
                    evidence={**profile_safe},
                )
            )
        except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                    ok=False,
                    title=title,
                    failure_class="s3.http.presigned_put_failed",
                    next_action_hint="Check S3 configuration and connectivity.",
                    evidence={**profile_safe},
                )
            )

    # --- CT-S3-001 (INTERNAL_PROXY): media-auth signed GET works
    check_id = "CT-S3-001"
    title = "INTERNAL signed GET (media-auth headers) succeeds"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_INTERNAL_PROXY,
                ok=False,
                title=title,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    else:
        try:
            key = _make_key(run_id, check_id, "ct-s3-get.txt")
            s3_client.put_object(Bucket=profile.bucket_name, Key=key, Body=b"ct-s3")

            url, headers = _signed_get_headers_for_key(key)
            internal_host = urlsplit(profile.internal_endpoint_url).netloc
            signed_host = urlsplit(url).netloc
            host_match = signed_host == internal_host

            if not host_match:
                add_result(
                    CheckResult(
                        check_id=check_id,
                        audience=constants.AUDIENCE_INTERNAL_PROXY,
                        ok=False,
                        title=title,
                        failure_class="s3.signature.host_mismatch_internal",
                        next_action_hint=(
                            "Ensure AWS_S3_ENDPOINT_URL host matches the signed "
                            "request host."
                        ),
                        evidence={
                            **profile_safe,
                            "signed_host_hash": sha256_16(signed_host),
                            "internal_host_hash": sha256_16(internal_host),
                        },
                    )
                )
            else:
                resp = http_request(
                    url=url,
                    method="GET",
                    headers=headers,
                    timeout_s=options.http_timeout_s,
                )
                ok = 200 <= resp.status_code <= 299
                add_result(
                    CheckResult(
                        check_id=check_id,
                        audience=constants.AUDIENCE_INTERNAL_PROXY,
                        ok=ok,
                        title=title,
                        failure_class=None if ok else "s3.http.signed_get_failed",
                        next_action_hint=None
                        if ok
                        else "Check AWS_S3_ENDPOINT_URL, bucket, and credentials.",
                        evidence={
                            **profile_safe,
                            "status_code": resp.status_code,
                            "request_id": _safe_request_id(resp.headers),
                            "signed_host_hash": sha256_16(signed_host),
                            "internal_host_hash": sha256_16(internal_host),
                            "signed_host_matches_internal_endpoint": host_match,
                            "object_key_hash": sha256_16(key),
                        },
                    )
                )
        except (ClientError, HttpClientError) as exc:
            if isinstance(exc, HttpClientError):
                failure_class, hint = _failure_from_http_client_error(exc)
            else:
                failure_class, hint = (
                    "s3.http.signed_get_failed",
                    "Check S3 credentials, bucket, and endpoint.",
                )
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title,
                    failure_class=failure_class,
                    next_action_hint=hint,
                    evidence={**profile_safe},
                )
            )
        except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title,
                    failure_class="s3.http.signed_get_failed",
                    next_action_hint="Check S3 configuration and connectivity.",
                    evidence={**profile_safe},
                )
            )

    # --- CT-S3-006 (INTERNAL_PROXY): Range GET works (strict 206 optional)
    check_id = "CT-S3-006"
    title = "INTERNAL Range GET works"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_INTERNAL_PROXY,
                ok=False,
                title=title,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    else:
        try:
            key = _make_key(run_id, check_id, "ct-s3-range.txt")
            s3_client.put_object(
                Bucket=profile.bucket_name, Key=key, Body=b"0123456789"
            )

            url, headers = _signed_get_headers_for_key(key)
            range_headers = dict(headers)
            range_headers["Range"] = "bytes=0-1"
            resp = http_request(
                url=url,
                method="GET",
                headers=range_headers,
                timeout_s=options.http_timeout_s,
            )
            strict_ok = resp.status_code == 206
            ok = strict_ok or (not options.strict_range_206 and resp.status_code == 200)
            failure_class = None
            hint = None
            if not ok:
                failure_class = "s3.http.range_not_206_strict"
                hint = "Ensure S3 Range requests return 206 Partial Content."
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=ok,
                    title=title,
                    failure_class=failure_class,
                    next_action_hint=hint,
                    evidence={
                        **profile_safe,
                        "status_code": resp.status_code,
                        "request_id": _safe_request_id(resp.headers),
                        "strict_range_206": options.strict_range_206,
                        "object_key_hash": sha256_16(key),
                    },
                )
            )
        except (ClientError, HttpClientError) as exc:
            if isinstance(exc, HttpClientError):
                failure_class, hint = _failure_from_http_client_error(exc)
            else:
                failure_class, hint = (
                    "s3.http.signed_get_failed",
                    "Check S3 credentials, bucket, and endpoint.",
                )
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title,
                    failure_class=failure_class,
                    next_action_hint=hint,
                    evidence={**profile_safe},
                )
            )
        except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title,
                    failure_class="s3.http.signed_get_failed",
                    next_action_hint="Check S3 configuration and connectivity.",
                    evidence={**profile_safe},
                )
            )

    # --- CT-S3-007 (INTERNAL_PROXY): Copy + MetadataDirective=REPLACE updates ContentType
    check_id = "CT-S3-007"
    title = "INTERNAL Copy + MetadataDirective=REPLACE updates ContentType"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_INTERNAL_PROXY,
                ok=False,
                title=title,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    else:
        try:
            key = _make_key(run_id, check_id, "ct-s3-copy.txt")
            s3_client.put_object(
                Bucket=profile.bucket_name,
                Key=key,
                Body=b"ct-s3",
                ContentType="application/octet-stream",
            )
            s3_client.copy_object(
                Bucket=profile.bucket_name,
                Key=key,
                CopySource={"Bucket": profile.bucket_name, "Key": key},
                ContentType="text/plain",
                MetadataDirective="REPLACE",
            )
            attempts = 0
            content_type = None
            while attempts < 3:
                attempts += 1
                head = s3_client.head_object(Bucket=profile.bucket_name, Key=key)
                content_type = head.get("ContentType")
                if content_type == "text/plain":
                    break
                time.sleep(0.2)

            ok = content_type == "text/plain"
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=ok,
                    title=title,
                    failure_class=None
                    if ok
                    else "s3.http.copy_metadata_replace_not_applied",
                    next_action_hint=None
                    if ok
                    else "Check S3 CopyObject support and MetadataDirective behavior.",
                    evidence={
                        **profile_safe,
                        "attempts": attempts,
                        "object_key_hash": sha256_16(key),
                    },
                )
            )
        except ClientError:
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title,
                    failure_class="s3.http.copy_metadata_replace_not_applied",
                    next_action_hint="Check S3 CopyObject support and credentials.",
                    evidence={**profile_safe},
                )
            )

    # --- CT-S3-008 (INTERNAL_PROXY + EXTERNAL_BROWSER): special chars in key
    check_id = "CT-S3-008"
    filename_special = "ct s3 & special.txt"
    title_int = "INTERNAL special chars in key (spaces, &)"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_INTERNAL_PROXY,
                ok=False,
                title=title_int,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    else:
        try:
            key = _make_key(run_id, f"{check_id}:internal", filename_special)
            s3_client.put_object(Bucket=profile.bucket_name, Key=key, Body=b"ct-s3")
            url, headers = _signed_get_headers_for_key(key)
            resp = http_request(
                url=url,
                method="GET",
                headers=headers,
                timeout_s=options.http_timeout_s,
            )
            ok = 200 <= resp.status_code <= 299
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=ok,
                    title=title_int,
                    failure_class=None if ok else "s3.http.key_encoding_failed",
                    next_action_hint=None
                    if ok
                    else "Check URL encoding / decoding of object keys end-to-end.",
                    evidence={
                        **profile_safe,
                        "status_code": resp.status_code,
                        "request_id": _safe_request_id(resp.headers),
                        "object_key_hash": sha256_16(key),
                    },
                )
            )
        except (ClientError, HttpClientError) as exc:
            if isinstance(exc, HttpClientError):
                failure_class, hint = _failure_from_http_client_error(exc)
            else:
                failure_class, hint = (
                    "s3.http.key_encoding_failed",
                    "Check S3 credentials, bucket, and key encoding.",
                )
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title_int,
                    failure_class=failure_class,
                    next_action_hint=hint,
                    evidence={**profile_safe},
                )
            )
        except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title=title_int,
                    failure_class="s3.http.key_encoding_failed",
                    next_action_hint="Check S3 configuration and connectivity.",
                    evidence={**profile_safe},
                )
            )

    title_ext = "EXTERNAL special chars in presigned PUT key (spaces, &)"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=False,
                title=title_ext,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    elif not profile.external_signed_base_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=False,
                title=title_ext,
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_DOMAIN_REPLACE for the browser-visible host.",
                evidence={**profile_safe},
            )
        )
    else:
        try:
            key_base = f"item/{_stable_uuid(run_id, f'{check_id}:external')}"
            signed_url = _presigned_put_url_for_key(
                key_base=key_base, filename=filename_special
            )
            signed_parts = urlsplit(signed_url)
            expected_host = urlsplit(profile.external_signed_base_url).netloc
            if signed_parts.netloc != expected_host:
                add_result(
                    CheckResult(
                        check_id=check_id,
                        audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                        ok=False,
                        title=title_ext,
                        failure_class="s3.signature.host_mismatch_external",
                        next_action_hint=(
                            "Ensure AWS_S3_DOMAIN_REPLACE matches the host used "
                            "by browsers."
                        ),
                        evidence={
                            **profile_safe,
                            "signed_host_hash": sha256_16(signed_parts.netloc),
                            "expected_host_hash": sha256_16(expected_host),
                        },
                    )
                )
            else:
                query = parse_qs(signed_parts.query)
                signed_headers = (query.get("X-Amz-SignedHeaders") or [""])[0]
                requires_acl = "x-amz-acl" in signed_headers.split(";")
                if not requires_acl:
                    add_result(
                        CheckResult(
                            check_id=check_id,
                            audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                            ok=False,
                            title=title_ext,
                            failure_class="s3.http.put_missing_required_header_x_amz_acl",
                            next_action_hint="Ensure presigned PUT signs and requires x-amz-acl.",
                            evidence={
                                **profile_safe,
                                "signed_host_hash": sha256_16(signed_parts.netloc),
                                "signed_headers_includes_x_amz_acl": False,
                            },
                        )
                    )
                else:
                    connect_url, signed_host = _connect_url_for_presigned_url(
                        profile.internal_endpoint_url, signed_url
                    )
                    resp = http_request(
                        url=connect_url,
                        method="PUT",
                        headers={"Host": signed_host, "x-amz-acl": "private"},
                        body=b"ct-s3",
                        timeout_s=options.http_timeout_s,
                    )
                    ok = 200 <= resp.status_code <= 299
                    add_result(
                        CheckResult(
                            check_id=check_id,
                            audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                            ok=ok,
                            title=title_ext,
                            failure_class=None if ok else "s3.http.key_encoding_failed",
                            next_action_hint=None
                            if ok
                            else "Check URL encoding and signature calculation for special keys.",
                            evidence={
                                **profile_safe,
                                "status_code": resp.status_code,
                                "request_id": _safe_request_id(resp.headers),
                                "signed_host_hash": sha256_16(signed_host),
                                "signed_headers_includes_x_amz_acl": True,
                            },
                        )
                    )
        except HttpClientError as exc:
            failure_class, hint = _failure_from_http_client_error(exc)
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                    ok=False,
                    title=title_ext,
                    failure_class=failure_class,
                    next_action_hint=hint,
                    evidence={**profile_safe},
                )
            )
        except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                    ok=False,
                    title=title_ext,
                    failure_class="s3.http.key_encoding_failed",
                    next_action_hint="Check S3 configuration and connectivity.",
                    evidence={**profile_safe},
                )
            )

    # --- CT-S3-010 (INTERNAL_PROXY + EXTERNAL_BROWSER): host signed == host used
    check_id = "CT-S3-010"
    if not profile.internal_endpoint_url:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_INTERNAL_PROXY,
                ok=False,
                title="INTERNAL signed_host matches internal connect_url host",
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_ENDPOINT_URL for the runner-connectable S3 endpoint.",
                evidence={**profile_safe},
            )
        )
    else:
        internal_host = urlsplit(profile.internal_endpoint_url).netloc
        try:
            key = _make_key(run_id, f"{check_id}:internal", "ct-s3-host.txt")
            s3_client.put_object(Bucket=profile.bucket_name, Key=key, Body=b"ct-s3")
            url, _headers = _signed_get_headers_for_key(key)
            signed_host = urlsplit(url).netloc
            ok_internal = signed_host == internal_host
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=ok_internal,
                    title="INTERNAL signed_host matches internal connect_url host",
                    failure_class=None
                    if ok_internal
                    else "s3.signature.host_mismatch_internal",
                    next_action_hint=None
                    if ok_internal
                    else "Ensure AWS_S3_ENDPOINT_URL host matches the signed request host.",
                    evidence={
                        **profile_safe,
                        "signed_host_hash": sha256_16(signed_host),
                        "internal_host_hash": sha256_16(internal_host),
                    },
                )
            )
        except Exception:  # noqa: BLE001 # pylint: disable=broad-exception-caught
            add_result(
                CheckResult(
                    check_id=check_id,
                    audience=constants.AUDIENCE_INTERNAL_PROXY,
                    ok=False,
                    title="INTERNAL signed_host matches internal connect_url host",
                    failure_class="s3.config.bad_url",
                    next_action_hint="Check AWS_S3_ENDPOINT_URL and S3 connectivity.",
                    evidence={**profile_safe},
                )
            )

    if profile.external_signed_base_url is None:
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=False,
                title="EXTERNAL signed_host matches browser host",
                failure_class="s3.config.missing_env",
                next_action_hint="Set AWS_S3_DOMAIN_REPLACE for the browser-visible host.",
                evidence={**profile_safe},
            )
        )
    else:
        signed_url = _presigned_put_url_for_key(
            key_base=f"item/{_stable_uuid(run_id, check_id)}",
            filename="ct-s3-host.txt",
        )
        signed_host = urlsplit(signed_url).netloc
        expected_host = urlsplit(profile.external_signed_base_url).netloc
        ok_external = signed_host == expected_host
        add_result(
            CheckResult(
                check_id=check_id,
                audience=constants.AUDIENCE_EXTERNAL_BROWSER,
                ok=ok_external,
                title="EXTERNAL signed_host matches browser host",
                failure_class=None
                if ok_external
                else "s3.signature.host_mismatch_external",
                next_action_hint=None
                if ok_external
                else "Ensure AWS_S3_DOMAIN_REPLACE matches the host used by browsers.",
                evidence={
                    **profile_safe,
                    "signed_host_hash": sha256_16(signed_host),
                    "expected_host_hash": sha256_16(expected_host),
                },
            )
        )

    # Deterministic ordering: by check_id then audience.
    results.sort(key=lambda r: (r.check_id, r.audience))

    overall_ok = all(r.ok for r in results)
    return {
        "schema_version": 1,
        "run_id": run_id,
        "gate_id": f"{constants.CT_S3_GATE_PREFIX}.{profile.profile_id}",
        "profile": profile_safe,
        "overall_ok": overall_ok,
        "results": [asdict(r) for r in results],
    }


def render_human_report(report: dict) -> str:
    """Render a minimal human-readable report without leaking sensitive data."""
    results = report["results"]
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    failed = total - passed
    lines: list[str] = []
    lines.append("# CT-S3 Report")
    lines.append("")
    lines.append(f"- run_id: `{report['run_id']}`")
    lines.append(f"- gate_id: `{report['gate_id']}`")
    lines.append(f"- overall_ok: `{report['overall_ok']}`")
    lines.append(f"- checks: `{passed}` passed / `{failed}` failed (total `{total}`)")
    lines.append("")
    lines.append("## Results (deterministic order)")
    lines.append("")
    for r in results:
        status = "PASS" if r["ok"] else "FAIL"
        lines.append(f"- `{r['check_id']}` `{r['audience']}`: {status} — {r['title']}")
        if not r["ok"]:
            lines.append(f"  - failure_class: `{r.get('failure_class')}`")
            lines.append(f"  - next_action_hint: {r.get('next_action_hint')}")
    lines.append("")
    return "\n".join(lines)


def dumps_json(report: dict) -> str:
    """Serialize the report as deterministic JSON (stable ordering)."""
    return json.dumps(report, sort_keys=True, indent=2) + "\n"
