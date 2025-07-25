#!/usr/bin/env bash

set -euo pipefail

mkdir -p /tmp/pgdump
cd /tmp/pgdump

RESTIC_VERSION=0.18.0
curl -fsSL --remote-name-all "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" \
  "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/SHA256SUMS" \
  "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/SHA256SUMS.asc"

curl -fsSLo - https://restic.net/gpg-key-alex.asc | gpg --import
gpg --verify SHA256SUMS.asc SHA256SUMS
grep _linux_amd64.bz2 SHA256SUMS | sha256sum -c
bzip2 -d restic_${RESTIC_VERSION}_linux_amd64.bz2
mv restic_${RESTIC_VERSION}_linux_amd64 restic
chmod +x ./restic

# Download postgresql client binaries
dbclient-fetcher pgsql

# Actually dump and upload to scaleway s3
FILENAME="${APP}_pgdump.sql"

pg_dump --clean --if-exists --format c --dbname "${SCALINGO_POSTGRESQL_URL}" --no-owner --no-privileges --no-comments --exclude-schema 'information_schema' --exclude-schema '^pg_*' --file "${FILENAME}"

export AWS_ACCESS_KEY_ID=${BACKUP_PGSQL_S3_KEY}
export AWS_SECRET_ACCESS_KEY=${BACKUP_PGSQL_S3_SECRET}
export RESTIC_PASSWORD=${BACKUP_PGSQL_ENCRYPTION_PASS}
export RESTIC_REPOSITORY=s3:${BACKUP_PGSQL_S3_REPOSITORY}/${APP}

./restic snapshots -q || ./restic init

./restic backup ${FILENAME}
./restic forget --keep-daily 30
