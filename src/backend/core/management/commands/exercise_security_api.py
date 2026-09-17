"""Exercise a local Drive API and object storage with isolated demonstration accounts."""

import json
import time
from importlib import import_module
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpRequest
from django.middleware.csrf import get_token

import requests

from core import models

CONTENT = b"security demonstration\n"


class Command(BaseCommand):
    """A local-only HTTP exercise; no new authentication bypass is exposed by the API."""

    requires_system_checks = []
    help = (
        "Create local demo records, exercise real HTTP routes/storage and wait for Celery alerts."
    )

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://app-dev:8000")
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, **options):
        base = options["base_url"].rstrip("/")
        parsed = urlsplit(base)
        local = parsed.scheme == "http" and parsed.hostname in ("app-dev", "127.0.0.1", "localhost")
        if (
            not local
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise CommandError("Use a local HTTP API origin")
        storage = urlsplit(settings.AWS_S3_ENDPOINT_URL or "")
        if (
            not settings.DEBUG
            or settings.POSTHOG_KEY
            or storage.hostname not in ("minio", "localhost", "127.0.0.1")
        ):
            raise CommandError(
                "Requires local development storage and disabled Drive product analytics"
            )
        if settings.EMAIL_HOST != "mailcatcher":
            raise CommandError(
                "Requires Mailcatcher; this command must not send invitations externally"
            )
        if not 1 <= options["timeout"] <= 300:
            raise CommandError("timeout must be between 1 and 300 seconds")

        run_id = str(uuid4())
        users = [
            models.User.objects.create(
                sub=f"security-demo-{run_id}-{index}",
                email=f"security-demo-{run_id}-{index}@example.invalid",
                full_name=f"Security demo {index}",
                password=make_password(None),
            )
            for index in range(3)
        ]
        actor, recipient, other_owner = users
        files = []
        for owner in (actor, other_owner):
            for index in range(5):
                item = models.Item.objects.create_child(
                    title=f"Security demo {run_id} {index}",
                    filename="security-demo.txt",
                    type=models.ItemTypeChoices.FILE,
                    creator=owner,
                )
                models.ItemAccess.objects.create(
                    item=item, user=owner, role=models.RoleChoices.OWNER
                )
                default_storage.save(item.file_key, ContentFile(CONTENT))
                models.Item.objects.filter(pk=item.pk).update(
                    size=len(CONTENT), upload_state=models.ItemUploadStateChoices.READY
                )
                files.append(item)

        session = import_module(settings.SESSION_ENGINE).SessionStore()
        session[SESSION_KEY] = str(actor.pk)
        session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
        session[HASH_SESSION_KEY] = actor.get_session_auth_hash()
        session.set_expiry(300)
        session.save()
        csrf_request = HttpRequest()
        csrf_token = get_token(csrf_request)
        try:
            with requests.Session() as http:
                http.max_redirects = 0
                http.cookies.set(settings.SESSION_COOKIE_NAME, session.session_key)
                http.cookies.set(settings.CSRF_COOKIE_NAME, csrf_request.META["CSRF_COOKIE"])
                http.headers.update({"Host": "localhost", "X-CSRFToken": csrf_token})
                self._exercise(http, base, files, recipient)
            alerts = self._wait_for_alerts(str(actor.pk), options["timeout"])
            report = {
                "run_id": run_id,
                "actor": str(actor.pk),
                "requests": {"downloads": 100, "denials": 10, "permission_changes": 10},
                "stored_content_verified": True,
                "rules": sorted({alert["rule"] for alert in alerts}),
                "alert_ids": [alert["alert_id"] for alert in alerts],
                "demo_user_ids": [str(user.pk) for user in users],
                "demo_item_ids": [str(item.pk) for item in files],
                "note": "Local demonstration records are retained for inspection; no cloud receipt claimed.",
            }
            directory = Path(settings.SECURITY_MONITORING_WORKDIR) / "http-exercises"
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{run_id}.json").write_text(json.dumps(report, indent=2) + "\n")
            self.stdout.write(json.dumps(report))
        finally:
            session.delete()

    def _exercise(self, http, base, files, recipient):
        """Read actual S3 objects; mutate only accesses belonging to the new demo items."""
        for index in range(100):
            item = files[index % 5]
            response = http.get(
                f"{base}/api/v1.0/items/media-auth/",
                headers={"X-Original-URL": f"/media/{item.file_key}", "X-Original-Method": "GET"},
                timeout=10,
            )
            self._check(response, 200)
            headers = {
                key: response.headers[key]
                for key in ("Authorization", "X-Amz-Date", "X-Amz-Content-SHA256")
            }
            url = f"{settings.AWS_S3_ENDPOINT_URL}/{default_storage.bucket_name}/{quote(item.file_key)}"
            with requests.get(url, headers=headers, timeout=10) as downloaded:
                self._check(downloaded, 200)
                if downloaded.content != CONTENT:
                    raise CommandError("Downloaded content differs from the demo file")
        for index in range(10):
            item = files[5 + index % 5]
            response = http.get(
                f"{base}/api/v1.0/items/{item.pk}/download/", timeout=10, allow_redirects=False
            )
            self._check(response, 403)
        for item in files[:5]:
            url = f"{base}/api/v1.0/items/{item.pk}/accesses/"
            response = http.post(
                url, json={"user_id": str(recipient.pk), "role": "reader"}, timeout=10
            )
            self._check(response, 201)
            access_id = response.json()["id"]
            self._check(http.patch(f"{url}{access_id}/", json={"role": "editor"}, timeout=10), 200)

    @staticmethod
    def _check(response, status):
        if response.status_code != status:
            raise CommandError(
                f"Local HTTP exercise expected {status}, received {response.status_code}"
            )

    @staticmethod
    def _wait_for_alerts(actor, timeout):
        """Use the real scheduled worker; do not invoke the detector from this command."""
        deadline = time.monotonic() + timeout
        expected = {"mass_download", "permission_probing", "permission_escalation"}
        while time.monotonic() < deadline:
            alerts = [
                json.loads(line)
                for path in (Path(settings.SECURITY_MONITORING_WORKDIR) / "batches").glob(
                    "*.alerts.jsonl"
                )
                for line in path.read_text().splitlines()
            ]
            alerts = [alert for alert in alerts if alert["actor"]["id"] == actor]
            if expected <= {alert["rule"] for alert in alerts}:
                return alerts
            time.sleep(1)
        raise CommandError(
            "Timed out waiting for three rule families; check worker, Beat, paths and thresholds"
        )
