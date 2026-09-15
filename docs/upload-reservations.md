# Upload reservations

Direct file uploads require `expected_size` (an integer number of bytes, including
zero) when creating an item, at the root or in a folder:

```json
{"type": "file", "filename": "example.txt", "expected_size": 12}
```

The server rejects files exceeding `DATA_UPLOAD_MAX_MEMORY_SIZE`. It then creates
the item with its reservation inside a transaction and calls the existing
`can_upload(user)`. A refusal rolls back creation and returns the backend's error
before any upload authorization is returned. `expected_size` is stored as the
reservation; `size` remains null until the server measures the uploaded object.
Storage usage includes `COALESCE(size, expected_size)`, so finalization does not
double-count the file. Outstanding uploads consume quota even without an
`upload-ended` call.

The returned `policy` remains a presigned PUT URL. Its SigV4 signature binds the
`Content-Length` header to the reserved size. Send the raw file, not a multipart
form. Browsers compute Content-Length automatically for the File body. Clients
must also send the ACL header when it was signed, as before. A signature without
Content-Length is rejected by Drive rather than returned to the client.

Finalization verifies that the actual size exactly matches the reservation and
still enforces the maximum file size. An admitted upload can finalize even if
the quota becomes full afterward; it does not need a second reservation. Repeating completion for a reserved file
already analyzing or ready returns its current state without starting another
analysis.

## Quota backends

Item creation and the subsequent `can_upload(user)` check share a database
transaction. A refusal or provider error rolls back the item and its reservation.
The existing usage and entitlement caches are used normally, with their existing
invalidation on committed item changes. Admission has no additional quota lock.

Quota enforcement is eventually consistent: a cached permission or concurrent
creations can temporarily authorize usage beyond the quota. New checks account
for persisted reservations once usage is refreshed. This is not a strict bound
on the total bytes authorized in a concurrent burst, and this change adds no
rate limiting.

The local backend keeps its existing threshold: fresh usage at or above the
limit is refused. Cached usage may allow an admission until invalidation or
expiry. Configured unlimited accounts remain unlimited, subject to the per-file
maximum. A refused creation leaves no persisted reservation; any usage cached
while checking that transaction can remain stale until invalidation or expiry.

DeployCenter's cached decision is reused when available. On a cache miss, its
existing metrics payload includes current account and organization usage,
including the item created in this transaction. Drive uses the returned decision
and refusal reason without interpreting or predicting quota limits. Subsequent
fresh requests send corrected metrics after a rollback.

Custom quota backends continue to implement `can_upload(user)` with their existing
cache behavior. The static backend remains authoritative for its configured
upload permission.

## Rollout and scope

Apply migration `0031_item_expected_size` before starting the updated backend.
Deploy updated clients together with the backend: uploads without an expected
size are rejected. Server-generated file templates do not accept this field.
Existing files retain their measured size. Existing pending items are not given
an invented reservation and cannot receive a new unbounded authorization.

Before production rollout, inventory legacy pending uploads and allow for
previously issued upload authorizations and transfers already in flight.

This change covers admission and size enforcement. Reliable abandoned-upload
purging, safe release of reservations after cancellation/deletion, prevention of
URL replay, and object-version retention are separate follow-up work. In
particular, the existing hard-delete accounting and cleanup behavior are not a
bound on physical bucket usage. Do not consider the full orphan-storage report
resolved by this change alone.

## Provider validation

Backend tests cover cache reuse and refresh, rollback on refusal or provider
error, completion after quota exhaustion, invalid sizes, signature requirements
and DeployCenter decisions on both cache hits and misses. `upload-quota.spec.ts` exercises
the real frontend, API and MinIO with a dedicated account limited to 1024 bytes.
The E2E environment uses the local quota backend for these checks.

Repeat provider checks on S3NS and Scaleway before deployment: correct length,
one byte too large, missing/changed Content-Length, empty files, ACL and CORS,
and the bucket's versioning/retention settings. Provider validation is distinct
from testing that the URL contains the signed header.
