# Integration smoke — 20260213-103855-integration-smoke

- start_utc: 2026-02-13T10:38:55Z
- cwd: /root/Apoze/drive
- git_head: d2240ad66dab7261456c9cd46eda4a8a03c45543
- docker_compose: Docker Compose version v5.0.2

## skill.drive-gates-runner.preflight

- cmd: bin/agent-check.sh --preflight --gate no_leak.scan_bmad_output

- result: PASS

## docker.compose.down.remove-orphans

- cmd: docker compose down --remove-orphans

- result: PASS

## docker.compose.up

- cmd: docker compose up -d

- result: PASS

## docker.compose.ps

- cmd: docker compose ps

- result: PASS

### output (redacted)

```
NAME                       IMAGE                              COMMAND                  SERVICE            CREATED          STATUS                    PORTS
drive-app-dev-1            drive:backend-development          "/usr/local/bin/entr…"   app-dev            29 seconds ago   Up Less than a second     0.0.0.0:8071->8000/tcp, [::]:8071->8000/tcp
drive-celery-dev-1         drive:backend-development          "/usr/local/bin/entr…"   celery-dev         35 seconds ago   Up 26 seconds             
drive-collabora-1          collabora/code:latest              "/start-collabora-on…"   collabora          35 seconds ago   Up 26 seconds (healthy)   0.0.0.0:9980->9980/tcp, [::]:9980->9980/tcp
drive-kc_postgresql-1      postgres:14.3                      "docker-entrypoint.s…"   kc_postgresql      35 seconds ago   Up 26 seconds (healthy)   0.0.0.0:6433->5432/tcp, [::]:6433->5432/tcp
drive-keycloak-1           quay.io/keycloak/keycloak:26.3.2   "/opt/keycloak/bin/k…"   keycloak           33 seconds ago   Up 25 seconds             8443/tcp, 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp, 9000/tcp
drive-mailcatcher-1        sj26/mailcatcher:latest            "mailcatcher --foreg…"   mailcatcher        35 seconds ago   Up 26 seconds             1025/tcp, 0.0.0.0:1081->1080/tcp, [::]:1081->1080/tcp
drive-minio-1              minio/minio                        "minio server --cons…"   minio              2 days ago       Up 2 days (healthy)       0.0.0.0:9100->9000/tcp, [::]:9100->9000/tcp, 0.0.0.0:9101->9001/tcp, [::]:9101->9001/tcp
drive-nginx-1              nginx:1.25                         "/docker-entrypoint.…"   nginx              26 seconds ago   Up Less than a second     80/tcp, 0.0.0.0:8083->8083/tcp, [::]:8083->8083/tcp
drive-onlyoffice-1         onlyoffice/documentserver-de       "/app/ds/run-documen…"   onlyoffice         35 seconds ago   Up 26 seconds (healthy)   443/tcp, 0.0.0.0:9981->80/tcp, [::]:9981->80/tcp
drive-postgresql-1         postgres:16                        "docker-entrypoint.s…"   postgresql         34 seconds ago   Up 26 seconds (healthy)   0.0.0.0:6434->5432/tcp, [::]:6434->5432/tcp
drive-redis-1              redis:5                            "docker-entrypoint.s…"   redis              35 seconds ago   Up 26 seconds             0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
drive-seaweedfs-filer-1    chrislusf/seaweedfs:latest         "/entrypoint.sh file…"   seaweedfs-filer    33 seconds ago   Up 25 seconds             7333/tcp, 8080/tcp, 8333/tcp, 8888/tcp, 9333/tcp, 18080/tcp, 18888/tcp, 19333/tcp
drive-seaweedfs-master-1   chrislusf/seaweedfs:latest         "/entrypoint.sh mast…"   seaweedfs-master   35 seconds ago   Up 26 seconds             7333/tcp, 8080/tcp, 8333/tcp, 8888/tcp, 9333/tcp, 18080/tcp, 18888/tcp, 19333/tcp
drive-seaweedfs-s3-1       chrislusf/seaweedfs:latest         "/entrypoint.sh s3 -…"   seaweedfs-s3       33 seconds ago   Up 25 seconds (healthy)   7333/tcp, 8080/tcp, 8888/tcp, 9333/tcp, 18080/tcp, 18888/tcp, 19333/tcp, 0.0.0.0:9000->8333/tcp, [::]:9000->8333/tcp
drive-seaweedfs-volume-1   chrislusf/seaweedfs:latest         "/entrypoint.sh volu…"   seaweedfs-volume   33 seconds ago   Up 26 seconds             7333/tcp, 8080/tcp, 8333/tcp, 8888/tcp, 9333/tcp, 18080/tcp, 18888/tcp, 19333/tcp
```

## preflight.config

- cmd: docker compose run --rm --no-deps app-dev python manage.py config_preflight

- result: PASS

## seaweedfs.up

- cmd: docker compose up -d seaweedfs-s3 createbuckets

- result: PASS

## seaweedfs.s3.signed-put

- cmd: docker run --rm --network drive_default --entrypoint /bin/sh minio/mc -c 'mc alias set drive http://seaweedfs-s3:8333 drive <REDACTED_PASSWORD> >/dev/null && echo hello >/tmp/hello.txt && mc cp /tmp/hello.txt drive/drive-media-storage/hello.txt && mc stat drive/drive-media-storage/hello.txt && mc version enable drive/drive-media-storage'

- result: PASS

## wopi.health

- cmd: docker compose run --rm --no-deps app-dev python manage.py wopi_health
- result: FAIL (exit=1)

### tail (redacted)
```
 Container drive-app-dev-run-a9ecc5e81cc6 Creating 
 Container drive-app-dev-run-a9ecc5e81cc6 Created 
🐳(entrypoint) creating user running in the container...
🐳(entrypoint) running your command: python manage.py wopi_health
System check identified some issues:

WARNINGS:
?: (dockerflow.health.W001) Unapplied migration core.0018_item_upload_started_at
?: (dockerflow.health.W001) Unapplied migration core.0018_mirroritemtask
?: (dockerflow.health.W001) Unapplied migration core.0019_user_last_release_note_seen
?: (dockerflow.health.W001) Unapplied migration core.0020_merge_0018_item_upload_started_at_0019_user_last_release_note_seen
?: (dockerflow.health.W001) Unapplied migration core.0021_mount_share_link
{
  "enabled": true,
  "evidence": {
    "cached": false,
    "cached_extensions_count": 0,
    "cached_mimetypes_count": 0,
    "drive_public_url_host_sha256_16": null,
    "s3_backend_available": true,
    "s3_bucket_versioning_ok": true,
    "s3_bucket_versioning_status": "Enabled",
    "wopi_clients_count": 2,
    "wopi_src_base_url_host_sha256_16": "d32c79a800ad0c25"
  },
  "failure_class": "wopi.config.discovery.not_configured",
  "healthy": false,
  "next_action_hint": "Run WOPI discovery configuration (celery beat) or trigger it manually with `python manage.py trigger_wopi_configuration`.",
  "state": "enabled_unhealthy"
}

```

- end_utc: 2026-02-13T10:39:53Z

## No-leak scan

See: _bmad-output/implementation-artifacts/runs/20260213-103855-integration-smoke/no-leak.scan.txt
