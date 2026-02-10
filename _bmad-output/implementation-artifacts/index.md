# Implementation artifacts

Implementation-phase artifacts: execution notes, sprint status, and run reports.

## Key documents

- [Sprint status](sprint-status.yaml)
- [Sprint status (template)](sprint-status.template.yaml)

## Work items / implementation notes

- [1-1 canonical DRIVE_PUBLIC_URL validation](1-1-canonical-drive-public-url-validation-and-deterministic-derivations.md)
- [1-2 separate allowlists for redirect URIs vs origins/hosts](1-2-separate-allowlists-for-redirect-uris-vs-origins-hosts-derived-from-drive-public-url.md)
- [2-1 docker-first edge contract documentation + configuration validation + smoke checks](2-1-docker-first-edge-contract-documentation-configuration-validation-smoke-checks.md)
- [2-2 nginx reference edge configuration for /media auth_request + SigV4 propagation](2-2-nginx-reference-edge-configuration-dev-prod-aligned-for-media-auth-request-sigv4-propagation.md)
- [2-3 TLS posture for public surfaces](2-3-tls-posture-for-public-surfaces-prod-https-only-dev-override-explicit-no-mixed-modes.md)
- [2-4 docker-first backup/restore runbook + post-restore smoke checklist](2-4-docker-first-backup-restore-runbook-deterministic-post-restore-smoke-checklist.md)
- [2-5 docker-first upgrade/rollback runbook + post-action smoke checklist](2-5-docker-first-upgrade-rollback-runbook-deterministic-post-action-smoke-checklist.md)
- [11-1 CT-S3 runner (audience-aware) + deterministic reports](11-1-drive-integrated-ct-s3-runner-with-explicit-audience-model-and-deterministic-reports.md)
- [11-2 SeaweedFS baseline profile + repeatable checks + runbook alignment](11-2-encode-seaweedfs-as-the-blocking-baseline-profile-repeatable-checks-runbook-alignment.md)
- [11-3 CT-S3 safe evidence allow-listing (no-leak)](11-3-safe-evidence-allow-listing-for-ct-s3-no-leak-by-construction.md)
- [12-1 gates runner (stable gate_id + deterministic artifacts)](12-1-gates-runner-executes-stable-gate-ids-and-writes-deterministic-artifacts.md)
- [12-2 standardize failure_class + next_action_hint](12-2-standardize-failure-class-next-action-hint-across-gates-and-operator-facing-artifacts.md)
- [12-4 wire CT-S3 + no-leak scanning into CI; dependency automation policy](12-4-wire-ct-s3-and-no-leak-scanning-into-ci-with-strict-scope-enforce-dependency-automation-policy.md)

## Runs

- Pointer to latest run folder: [latest.txt](latest.txt)
- [Deterministic gates runner runs](runs/index.md)
- [Orchestrator runs](orchestrator-runs/index.md)

## Navigation

- Up: [_bmad-output index](../index.md)
