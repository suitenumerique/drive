# Accessing the app from the local network (e.g. iPhone)

This guide explains how to make the development services reachable from other devices on your WiFi network (e.g. testing on a phone).

## 1. Find your local IP

```bash
ipconfig getifaddr en0
```

This returns something like `192.168.1.91`. Replace this IP in all steps below with your own.

## 2. Update Keycloak realm (redirect URIs)

In `docker/auth/realm.json`, find the `drive` client's `redirectUris` and `webOrigins` arrays and add your IP:

```json
"redirectUris": [
  "http://localhost:8070/*",
  "http://localhost:8071/*",
  "http://localhost:3200/*",
  "http://localhost:8088/*",
  "http://localhost:3000/*",
  "http://<YOUR_IP>:8071/*"
],
"webOrigins": [
  "http://localhost:3200",
  "http://localhost:8088",
  "http://localhost:8070",
  "http://localhost:3000",
  "http://<YOUR_IP>:3000"
],
```

**Important**: Keycloak imports `realm.json` only on first startup. If the database already exists, you must either:
- Delete the Keycloak database and recreate both services:
  ```bash
  docker compose down -v kc_postgresql keycloak
  docker compose up -d kc_postgresql keycloak
  ```
- Or add the URIs manually via the Keycloak admin console at `http://<YOUR_IP>:8083/admin/` (admin / admin) → **Clients → drive → Valid redirect URIs**

## 3. Update Keycloak hostname

In `compose.yaml`, update the Keycloak `--hostname` flag:

```yaml
keycloak:
  command:
    - start-dev
    - --features=preview
    - --import-realm
    - --proxy=edge
    - --hostname=http://<YOUR_IP>:8083   # was http://localhost:8083
    - --hostname-strict=false
```

## 4. Update the frontend API origin

In `compose.yaml`, update the `API_ORIGIN` build arg for `frontend-dev`:

```yaml
frontend-dev:
  build:
    args:
      API_ORIGIN: "http://<YOUR_IP>:8071"   # was http://localhost:8071
```

In `src/frontend/apps/drive/.env.development`, override the environment variables:

```env
NEXT_PUBLIC_S3_DOMAIN_REPLACE=http://<YOUR_IP>:9000
NEXT_PUBLIC_API_ORIGIN=http://<YOUR_IP>:8071
```

## 5. Update the backend OIDC settings

In `env.d/development/common.local`, add or update:

```env
OIDC_OP_URL=http://<YOUR_IP>:8083/realms/drive
OIDC_OP_AUTHORIZATION_ENDPOINT=http://<YOUR_IP>:8083/realms/drive/protocol/openid-connect/auth
LOGIN_REDIRECT_URL=http://<YOUR_IP>:3000
LOGIN_REDIRECT_URL_FAILURE=http://<YOUR_IP>:3000
LOGOUT_REDIRECT_URL=http://<YOUR_IP>:3000
OIDC_REDIRECT_ALLOWED_HOSTS="localhost:8083,localhost:3000,<YOUR_IP>:3000"
CSRF_TRUSTED_ORIGINS=http://<YOUR_IP>:3000,http://<YOUR_IP>:8071
MEDIA_BASE_URL=http://<YOUR_IP>:8083
```

**Note**: The token, userinfo, and JWKS endpoints (`OIDC_OP_TOKEN_ENDPOINT`, `OIDC_OP_USER_ENDPOINT`, `OIDC_OP_JWKS_ENDPOINT`) are called server-side (backend container → Keycloak container). Since they communicate over the Docker network, they don't need to be updated.

## 6. Restart the services

```bash
docker compose down
docker compose up -d
```

Wait for Keycloak to fully start (it can take a minute). You can check with:

```bash
docker compose logs -f keycloak
```

Look for `Listening on: http://0.0.0.0:8080` in the logs.

## 7. Access from your device

On your phone (connected to the same WiFi), open:

```
http://<YOUR_IP>:3000
```

## Reverting

To go back to localhost-only, revert the changes in `compose.yaml`, `docker/auth/realm.json`, `src/frontend/apps/drive/.env.development`, and `env.d/development/common.local`, then restart the services.
