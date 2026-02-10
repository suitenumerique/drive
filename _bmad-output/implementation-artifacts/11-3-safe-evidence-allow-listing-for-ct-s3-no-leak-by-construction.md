# Story 11.3: Safe evidence allow-listing for CT-S3 (no-leak by construction)

Status: review

## Story

As an operator,
I want CT-S3 evidence to be allow-listed and no-leak by construction,
So that reports help debugging without exposing credentials, paths, internal URLs, or object keys.

## Acceptance Criteria

**Given** CT-S3 produces evidence for any failed check  
**When** the report is generated  
**Then** evidence is restricted to allow-listed fields (e.g., status codes, request_id, keyed hashes, latency buckets, audience codes) and never includes secrets, raw object keys, or internal URLs.

## Tasks / Subtasks

- [ ] Define an evidence allow-list schema for CT-S3 (AC: 1)
  - [ ] Enumerate allowed fields (status codes, request_id, hashes, latency buckets, audience codes).
  - [ ] Define stable `failure_class` + `next_action_hint` placement in reports.
- [ ] Implement evidence redaction at the producer boundary (AC: 1)
  - [ ] Ensure raw object keys, credentials, and internal URLs are never written to artifacts.
  - [ ] Prefer keyed hashes or truncated identifiers where needed.
- [ ] Add regression tests for no-leak (AC: 1)
  - [ ] Tests that prove forbidden fields never appear in artifacts.
- [ ] Document safe evidence rules (AC: 1)
  - [ ] Operator guidance for what evidence is safe and how to use it.

## Dev Notes

- The goal is “no-leak by construction”: enforce allow-listing at creation time rather than relying on downstream scrubbing.
- Keep the schema stable so operators can automate triage over time.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 11.3 Acceptance Criteria]
- [Source: `docs/failure-class-glossary.md` — failure taxonomy (if used)]

## Dev Agent Record

### Agent Model Used

GPT-5.2 (Codex CLI)

### Debug Log References

- `_bmad-output/implementation-artifacts/runs/20260210-212117-11.3/report.md`

### Completion Notes List

- Added an explicit evidence allow-list for CT-S3 and enforced it at evidence creation time.
- Added regression tests for unknown/invalid evidence shapes without echoing sensitive values.
- Documented safe evidence rules in `docs/ct-s3.md`.

### File List

- `docs/ct-s3.md`
- `src/backend/core/ct_s3/evidence.py`
- `src/backend/core/ct_s3/runner.py`
- `src/backend/core/ct_s3/types.py`
- `src/backend/core/tests/test_ct_s3_evidence.py`
- `_bmad-output/implementation-artifacts/runs/20260210-212117-11.3/report.md`
