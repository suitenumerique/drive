# Story 7.2 — Run Report

- story: `7.2`
- run_id: `20260212-101451-7.2`
- gates runner: `bin/agent-check.sh --tag 7.2`
- result: **PASS**

## Gates

See:
- `run-report.md`
- `gates.md`

## Summary

Implemented a no-leak mounts discovery endpoint returning only `mount_id`,
display name, provider type, and a capability map keyed by the contract
constants (`mount.upload`, `mount.preview`, `mount.wopi`, `mount.share_link`).

Added a frontend mounts entry point (`/explorer/mounts`) driven by the
capability map so unavailable actions are not presented as dead buttons, and
use the standard "contact admin" messaging for unavailable capabilities.

## Verification

- `backend.lint`: PASS
- `backend.tests`: PASS
- `frontend.lint`: PASS

