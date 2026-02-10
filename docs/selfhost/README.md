# Self-host (v1) — Docker-first

This folder is the entry point for **v1 self-hosting** documentation.

## Scope (v1)

- **Baseline:** single-machine Docker / Docker Compose.
- **Reverse proxy:** bring your own (proxy-agnostic contract).
- **Kubernetes/Helm:** existing files remain **reference-only, as-is** (no v1 hardening
  guarantees and no new v1 gates for K8s).

## Where to start

- `docs/selfhost/edge-contract.md` — proxy-agnostic `/media` edge contract
- `docs/selfhost/smoke-checklist.md` — deterministic smoke checklist (operator-run)

## Storage backend (compose baseline)

The Docker Compose baseline uses an **S3-compatible object storage**.
In this repo, the compose baseline is **SeaweedFS S3 gateway** (see `compose.yaml`).

