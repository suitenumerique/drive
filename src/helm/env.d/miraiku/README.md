# Déploiement Drive sur Scaleway — namespace `miraiku`

Runbook d'installation de La Suite Drive sur le cluster Scaleway `k8s-par-brave-bassi`
(région `fr-par`), namespace `miraiku`, URL `https://mesfichiers.fake-domain.name`.

## Pré-requis

- `kubectl` pointant sur le contexte `admin@k8s-par-brave-bassi`
- `scw` CLI configuré (profil `newprofile`, credentials dans `~/.zshrc` / `~/.config/scw/config.yaml`)
- `helm` 3.x
- Accès au secret `owui-socle-secrets` du namespace `miraiku` (contient `POSTGRES_USER`, `KEYCLOAK_ADMIN_PASSWORD`)
- Ressources déjà présentes dans `miraiku` : `postgres`, `keycloak`, `search-valkey`, ingress-nginx, cert-manager (ClusterIssuer `letsencrypt-prod`)

## Ressources créées par ce déploiement

| Type | Nom | Emplacement |
|---|---|---|
| Bucket S3 | `miraiku-drive-media` | Scaleway fr-par |
| Secret k8s | `drive-db-secrets` | miraiku |
| Secret k8s | `drive-s3-secrets` | miraiku |
| Secret k8s | `drive-app-secrets` | miraiku |
| Base Postgres + user | `drive` / `drive` | postgres pod |
| Client Keycloak | `drive` (confidentiel) | realm `openwebui` |
| Release Helm | `drive` (2 backend + 2 frontend + 3 celery) | miraiku |
| Ingress | drive, drive-admin, drive-media, drive-media-preview | miraiku |

## Étape 1 — Bucket S3

```sh
scw object bucket create name=miraiku-drive-media region=fr-par
```

Les credentials S3 réutilisent `$SCW_ACCESS_KEY` / `$SCW_SECRET_KEY` du `.zshrc` (décision
validée ; une IAM application scope-restreinte serait plus propre si on veut réduire le blast radius).

## Étape 2 — Secrets k8s

```sh
DRIVE_DB_PASS=$(openssl rand -base64 24 | tr -d '=+/' | head -c 32)

kubectl -n miraiku create secret generic drive-db-secrets \
  --from-literal=DB_NAME=drive \
  --from-literal=DB_USER=drive \
  --from-literal=DB_PASSWORD="$DRIVE_DB_PASS"

kubectl -n miraiku create secret generic drive-s3-secrets \
  --from-literal=AWS_S3_ACCESS_KEY_ID="$SCW_ACCESS_KEY" \
  --from-literal=AWS_S3_SECRET_ACCESS_KEY="$SCW_SECRET_KEY"

kubectl -n miraiku create secret generic drive-app-secrets \
  --from-literal=DJANGO_SECRET_KEY="$(openssl rand -base64 48)" \
  --from-literal=OIDC_RP_CLIENT_SECRET="placeholder"   # patché à l'étape 4
```

## Étape 3 — Base Postgres + user

```sh
PG_ADMIN=$(kubectl -n miraiku get secret owui-socle-secrets -o jsonpath='{.data.POSTGRES_USER}' | base64 -d)

kubectl -n miraiku exec -i deploy/postgres -- psql -U "$PG_ADMIN" <<SQL
CREATE USER drive WITH PASSWORD '$DRIVE_DB_PASS';
CREATE DATABASE drive OWNER drive;
SQL
```

Test :
```sh
kubectl -n miraiku exec -i deploy/postgres -- env PGPASSWORD="$DRIVE_DB_PASS" \
  psql -h localhost -U drive -d drive -c '\conninfo'
```

## Étape 4 — Client Keycloak

### 4a — Persistent (repo `owuicore-main`)

Le client est déjà ajouté à `owuicore-main/keycloak/realm-openwebui.k8s.json` (commit
`feat(keycloak): add drive confidential client…`). Pour ré-import complet, le script
`deploy/deploy-k8s.sh` inclut désormais `${DRIVE_HOST}` et `${DRIVE_CLIENT_SECRET}` dans
`RENDER_VARS`.

### 4b — Live via kcadm.sh

```sh
KC_ADMIN_PASS=$(kubectl -n miraiku get secret owui-socle-secrets \
  -o jsonpath='{.data.KEYCLOAK_ADMIN_PASSWORD}' | base64 -d)
DRIVE_CS=$(openssl rand -base64 32 | tr -d '=+/' | head -c 40)

kubectl -n miraiku exec deploy/keycloak -- /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password "$KC_ADMIN_PASS"

kubectl -n miraiku exec deploy/keycloak -- /opt/keycloak/bin/kcadm.sh create clients \
  -r openwebui -s clientId=drive -s enabled=true -s publicClient=false \
  -s 'redirectUris=["https://mesfichiers.fake-domain.name/*"]' \
  -s 'webOrigins=["https://mesfichiers.fake-domain.name"]' \
  -s standardFlowEnabled=true -s directAccessGrantsEnabled=false \
  -s "secret=$DRIVE_CS"

kubectl -n miraiku patch secret drive-app-secrets --type=json \
  -p="[{\"op\":\"replace\",\"path\":\"/data/OIDC_RP_CLIENT_SECRET\",
       \"value\":\"$(printf %s $DRIVE_CS | base64)\"}]"
```

Vérifier :
```sh
curl -sS https://mysso.fake-domain.name/realms/openwebui/.well-known/openid-configuration | jq .issuer
kubectl -n miraiku exec deploy/keycloak -- /opt/keycloak/bin/kcadm.sh \
  get clients -r openwebui -q clientId=drive --fields clientId,enabled,redirectUris
```

## Étape 5 — Déploiement Helm

```sh
cd /Users/etiquet/Documents/GitHub/drive

# Test statique
helm lint src/helm/drive -f src/helm/env.d/miraiku/values.drive.yaml.gotmpl
helm template drive src/helm/drive -n miraiku \
  -f src/helm/env.d/miraiku/values.drive.yaml.gotmpl | \
  kubectl apply --dry-run=client -f -

# Apply
helm upgrade --install drive src/helm/drive -n miraiku \
  -f src/helm/env.d/miraiku/values.drive.yaml.gotmpl --wait --timeout 10m
```

## Vérifications end-to-end

```sh
# 1. Rollouts
kubectl -n miraiku rollout status deploy/drive-backend
kubectl -n miraiku rollout status deploy/drive-frontend

# 2. Ingress + TLS
kubectl -n miraiku get ingress -l app.kubernetes.io/instance=drive
kubectl -n miraiku get certificate mesfichiers-tls       # READY=True

# 3. Endpoints publics
curl -sI https://mesfichiers.fake-domain.name/              # 200 (frontend)
curl -sI https://mesfichiers.fake-domain.name/api/v1.0/config/   # 200 (API)

# 4. Healthchecks internes (via kube-probe, via logs)
kubectl -n miraiku logs deploy/drive-backend | grep -E 'heartbeat|lbheartbeat'  # 200

# 5. S3 depuis le pod
POD=$(kubectl -n miraiku get pod -l app.kubernetes.io/component=backend \
  -o jsonpath='{.items[0].metadata.name}')
kubectl -n miraiku exec "$POD" -- python -c "
from django.conf import settings; import boto3
s3 = boto3.client('s3', endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    region_name=settings.AWS_S3_REGION_NAME,
    aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY)
print(s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME)['ResponseMetadata']['HTTPStatusCode'])
"
# → 200

# 6. SSO roundtrip (navigateur)
# Ouvrir https://mesfichiers.fake-domain.name → "Se connecter" → login Keycloak → retour authentifié
```

## Gotchas rencontrés

1. **Admission webhook ingress-nginx** rejette les annotations
   `nginx.ingress.kubernetes.io/configuration-snippet` (snippet directives désactivées
   sur ce cluster). Override avec `... : null` dans les values pour que Helm les retire
   du merge avec les defaults du chart.
2. **Jobs `configureWopi` et `createsuperuser`** n'ont pas de flag `enabled` dans le
   chart — on les remplace par des no-ops (`/bin/sh -c echo ...`) pour qu'ils se
   terminent proprement sans déps externes.
3. **Le worker Celery `malware-detection`** est retiré de `celeryWorkers` (pas de
   backend antivirus déployé dans `miraiku`). Les routes Celery sont aussi ajustées
   pour ne router que vers `mirror`.
4. **Connexion base** : `DB_HOST=postgres.miraiku.svc.cluster.local` (service cluster),
   pas l'IP du pod. Idem pour Redis via `search-valkey`.
5. **Bases Redis séparées** : drive utilise `/3` (cache) et `/4` (celery broker) sur
   `search-valkey` pour éviter les collisions avec openwebui/mymirai.

## Rollback

```sh
# Rollback à une révision Helm précédente
helm rollback drive -n miraiku <REV>

# Ou uninstall complet
helm uninstall drive -n miraiku

# Restauration du mock précédent (si backup présent)
kubectl apply -f /tmp/drive-mock-backup-*.yaml
```

## Destruction complète

```sh
helm uninstall drive -n miraiku
kubectl -n miraiku delete secret drive-db-secrets drive-s3-secrets drive-app-secrets
kubectl -n miraiku exec deploy/postgres -- psql -U "$PG_ADMIN" \
  -c "DROP DATABASE drive; DROP USER drive;"
kubectl -n miraiku exec deploy/keycloak -- /opt/keycloak/bin/kcadm.sh \
  delete clients/$(kubectl -n miraiku exec deploy/keycloak -- /opt/keycloak/bin/kcadm.sh \
  get clients -r openwebui -q clientId=drive --fields id --format csv --noquotes) \
  -r openwebui
scw object bucket delete name=miraiku-drive-media force=true   # uniquement si vide
```
