# Upgrade

All instructions to upgrade this project from one release to the next will be
documented in this file. Upgrades must be run sequentially, meaning you should
not skip minor/major releases while upgrading (fix releases can be skipped).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For most upgrades, you just need to run the django migrations with
the following command inside your docker container:

`python manage.py migrate`

(Note : in your development environment, you can `make migrate`.)

## [Unreleased]

- ⚠️ The media proxy must forward three new headers from the `media-auth`
  subrequest response: `X-Storage-Path` (the signed object-storage path the
  proxy must target, via a variable in `proxy_pass`), `X-Content-Type` and
  `X-Content-Disposition`. In the Helm chart, add them to the ingress
  `auth-response-headers` of the `/media/` locations. The nginx configs shipped
  in `docker/files/` are already updated. Without this, files stored under
  content-addressed keys cannot be served.
- Files are now stored under content-addressed keys (`blobs/<sha256>`).
  Existing objects keep their historical `item/<uuid>/<filename>` key (double
  reading, no data migration needed upfront); migrate them in the background
  with `python manage.py migrate_items_to_blobs --limit=1000` (repeat in batches,
  or schedule it with `MIGRATE_ITEMS_TO_BLOBS_SCHEDULE` and celery beat). New
  uploads are content-addressed only when the client sends `upload_hash` at
  creation; until the frontend sends it, uploads keep the historical flow.
- ⚠️ Add a lifecycle rule on the media bucket to expire objects under `tmp/`
  (abandoned content-addressed uploads), e.g. after 1 day.
- Optional settings: `BLOB_UNREFERENCED_GRACE_HOURS` (default `168` = 7 days,
  grace period before an unreferenced blob object is deleted),
  `GC_UNREFERENCED_BLOBS_SCHEDULE` (celery beat schedule for the
  `gc_unreferenced_blobs` garbage collector),
  `UPLOAD_CHALLENGE_THRESHOLD_BYTES` (default `1048576` = 1 MiB, above which an
  upload with an announced hash requires a possession challenge),
  `UPLOAD_CHALLENGE_RANGE_BYTES` (default `65536` = 64 KiB),
  `UPLOAD_CHALLENGE_TTL_SECONDS` (default `300`).
- Item versions are exposed at `/api/v1.0/items/<id>/versions/` (list, restore,
  delete) and served through `/media/item/<id>/versions/<version_id>/<name>`.
  They require an explicit access on the item, never a share link.

## [v0.26.0] - 2026-11-04

- ⚠️ `FILE_MIMETYPE_ALLOWED` was read from `DJANGO_FILE_MIMETYPE_ALLOWED`:
  rename the variable if you override it.
- ⚠️ `RESTRICT_UPLOAD_FILE_TYPE` is no longer a boolean: replace `True` with
  `allowlist` and `False` with `off`. Any other value stops the startup.
- ⚠️ Emails use a new layout. The product name in their text now comes from
  `DJANGO_EMAIL_APP_NAME` (default `Drive`) instead of the translations: set it
  to keep another name, e.g. `Fichiers`.
