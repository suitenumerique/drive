# Accessing the app from the local network (e.g. iPhone)

This guide explains how to make the development services reachable from other devices on your WiFi network (e.g. testing on a phone).

## 1. Find your local IP

```bash
ipconfig getifaddr en0
```

This returns something like `192.168.1.91`. Replace this IP in all steps below with your own.

## 2. Update the Dex client (redirect URIs) and issuer

Dex only accepts exact redirect URIs. In `docker/auth/dex.yaml`, add the backend
callback for your IP to the `drive` client, and update the issuer so the URLs
Dex advertises are reachable from your device:

```yaml
issuer: http://<YOUR_IP>:8083/dex   # was http://localhost:8083/dex

staticClients:
  - id: drive
    redirectURIs:
      - http://localhost:8071/api/v1.0/callback/
      - http://<YOUR_IP>:8071/api/v1.0/callback/
```

## 3. Update the nginx silent-login redirect

In `docker/files/development/etc/nginx/conf.d/default.conf`, the `location = /dex/auth`
block redirects `prompt=none` requests back to the backend callback. Point it to
your IP as well:

```nginx
return 302 http://<YOUR_IP>:8071/api/v1.0/callback/?error=login_required&state=$arg_state;
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
OIDC_OP_URL=http://<YOUR_IP>:8083/dex
OIDC_OP_AUTHORIZATION_ENDPOINT=http://<YOUR_IP>:8083/dex/auth
LOGIN_REDIRECT_URL=http://<YOUR_IP>:3000
LOGIN_REDIRECT_URL_FAILURE=http://<YOUR_IP>:3000
LOGOUT_REDIRECT_URL=http://<YOUR_IP>:3000
OIDC_REDIRECT_ALLOWED_HOSTS="localhost:8083,localhost:3000,<YOUR_IP>:3000"
CSRF_TRUSTED_ORIGINS=http://<YOUR_IP>:3000,http://<YOUR_IP>:8071
MEDIA_BASE_URL=http://<YOUR_IP>:8083
```

**Note**: The token, userinfo, and JWKS endpoints (`OIDC_OP_TOKEN_ENDPOINT`, `OIDC_OP_USER_ENDPOINT`, `OIDC_OP_JWKS_ENDPOINT`) are called server-side (backend container → Dex container). Since they communicate over the Docker network, they don't need to be updated.

## 6. Restart the services

```bash
docker compose down
docker compose up -d
```

Dex starts in a few seconds. You can check with:

```bash
docker compose logs -f dex
```

Look for `listening on 0.0.0.0:5556` in the logs.

## 7. Access from your device

On your phone (connected to the same WiFi), open:

```
http://<YOUR_IP>:3000
```

## Reverting

To go back to localhost-only, revert the changes in `compose.yaml`, `docker/auth/dex.yaml`, the nginx dev config, `src/frontend/apps/drive/.env.development`, and `env.d/development/common.local`, then restart the services.
