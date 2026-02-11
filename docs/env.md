# Environment Variables

This document lists all configurable environment variables for the Drive application, extracted from the Django settings configuration.


| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `ALLOWED_HOSTS` | List of allowed hosts for the application (used in Production) | `[]` |
| `ALLOW_LOGOUT_GET_METHOD` | Allow logout via GET method | `True` |
| `API_USERS_LIST_LIMIT` | Maximum number of users returned in API user list | `5` |
| `API_USERS_LIST_THROTTLE_RATE_BURST` | Burst throttle rate for user list API | `30/minute` |
| `API_USERS_LIST_THROTTLE_RATE_SUSTAINED` | Sustained throttle rate for user list API | `180/hour` |
| `AWS_S3_ACCESS_KEY_ID` | AWS S3 access key ID for file storage | `None` |
| `AWS_S3_ENDPOINT_URL` | AWS S3 endpoint URL for file storage | `None` |
| `AWS_S3_DOMAIN_REPLACE` | The S3 domain to used by the frontend application. Used by the docker compose stack. | `None` |
| `AWS_S3_REGION_NAME` | AWS S3 region name for file storage | `None` |
| `AWS_S3_SECRET_ACCESS_KEY` | AWS S3 secret access key for file storage | `None` |
| `AWS_S3_UPLOAD_POLICY_EXPIRATION` | AWS S3 upload policy expiration time in seconds | `86400` (24h) |
| `ITEM_UPLOAD_PENDING_TTL_SECONDS` | Pending upload TTL in seconds (after which pending items are treated as expired) | `3600` (1h) |
| `AWS_STORAGE_BUCKET_NAME` | AWS S3 bucket name for file storage | `drive-media-storage` |
| `CACHES_DEFAULT_TIMEOUT` | Default cache timeout in seconds | `30` |
| `CELERY_BROKER_URL` | Celery broker URL for task queue | `redis://redis:6379/0` |
| `CORS_ALLOW_ALL_ORIGINS` | Allow all origins for CORS | `False` |
| `CORS_ALLOWED_ORIGINS` | List of allowed origins for CORS | `[]` |
| `CORS_ALLOWED_ORIGIN_REGEXES` | List of allowed origin regexes for CORS | `[]` |
| `CRISP_WEBSITE_ID` | Crisp chat widget website ID | `None` |
| `CSRF_TRUSTED_ORIGINS` | List of trusted origins for CSRF | `[]` |
| `DATA_DIR` | Directory for storing application data | `/data` |
| `DATABASE_URL` | Database connection URL (overrides individual DB settings) | `None` |
| `DB_ENGINE` | Database engine | `django.db.backends.postgresql` |
| `DB_HOST` | Database host | `localhost` |
| `DB_NAME` | Database name | `drive` |
| `DB_PASSWORD` | Database password | `pass` |
| `DB_PORT` | Database port | `5432` |
| `DB_USER` | Database user | `dinum` |
| `DRIVE_ALLOW_INSECURE_HTTP` | Dev-only override to allow `http://` on public-surface base URLs (only when `DEBUG=True`). | `False` |
| `DRIVE_ALLOWED_HOSTS` | Additional allowed hosts (hostnames only) for redirect safety checks (no wildcards). Canonical host derived from `DRIVE_PUBLIC_URL` is always included when set. | `[]` |
| `DRIVE_ALLOWED_ORIGINS` | Additional allowed origins (scheme://host[:port]) for SDK relay CORS (no wildcards). Canonical origin derived from `DRIVE_PUBLIC_URL` is always included when set. | `[]` |
| `DRIVE_ALLOWED_REDIRECT_URIS` | Additional allowed redirect targets (absolute URIs incl. path) used to derive allowed hosts (no wildcards). Canonical root URI derived from `DRIVE_PUBLIC_URL` is always included when set. | `[]` |
| `DRIVE_PUBLIC_URL` | Canonical public base URL (scheme + host only). Validated and normalized (trailing slash removed). | `None` |
| `EMAIL_BACKEND` | Email backend for sending emails | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_BRAND_NAME` | Brand name for email templates | `None` |
| `EMAIL_FROM` | Default sender email address | `from@example.com` |
| `EMAIL_HOST` | SMTP host for email sending | `None` |
| `EMAIL_HOST_PASSWORD` | SMTP password for email sending | `None` |
| `EMAIL_HOST_USER` | SMTP username for email sending | `None` |
| `EMAIL_LOGO_IMG` | Logo image URL for email templates | `None` |
| `EMAIL_PORT` | SMTP port for email sending | `None` |
| `EMAIL_USE_SSL` | Use SSL for SMTP connection | `False` |
| `EMAIL_USE_TLS` | Use TLS for SMTP connection | `False` |
| `FEATURES_ALPHA` | Enable alpha features | `False` |
| `FEATURES_INDEXED_SEARCH` | Enable the search of indexed files through the API | `True` |
| `FILE_EXTENSIONS_ALLOWED` | List of file extension allowed to be uploaded | See in the settings.py file |
| `FILE_MIMETYPE_ALLOWED` | List of file mimetype allowed to be uploaded | See in the setings.py file |
| `FRONTEND_THEME` | Frontend theme configuration | `None` |
| `FRONTEND_EXTERNAL_HOME_URL` | Frontend external home url to redirect to | `None` |
| `FRONTEND_FEEDBACK_BUTTON_SHOW` | Show feedback button | `False` |
| `FRONTEND_FEEDBACK_BUTTON_IDLE` | Make feedback button idle (e.g. to bind to external library) | `False` |
| `FRONTEND_FEEDBACK_ITEMS` | Dictionary of feedback items with URLs | `{}` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_ENABLED` | Enable feedback messages widget | `False` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL` | API URL for feedback messages widget | `None` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL` | Channel for feedback messages widget | `None` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH` | Path for feedback messages widget | `None` |
| `ITEM_FILE_MAX_SIZE` | Maximum file size for uploads in bytes | `5368709120` (5GB) |
| `LANGUAGE_CODE` | Default language code | `en-us` |
| `LOGIN_REDIRECT_URL` | URL to redirect after successful login | `None` |
| `LOGIN_REDIRECT_URL_FAILURE` | URL to redirect after failed login | `None` |
| `LOGOUT_REDIRECT_URL` | URL to redirect after logout | `None` |
| `LOGGING_LEVEL_LOGGERS_APP` | Logging level for application loggers | `INFO` |
| `LOGGING_LEVEL_LOGGERS_ROOT` | Logging level for root logger | `INFO` |
| `MAX_PAGE_SIZE` | Limit the maximum page size the client may request | `200` |
| `MEDIA_BASE_URL` | Base URL for media files | `None` |
| `OIDC_AUTH_REQUEST_EXTRA_PARAMS` | Extra parameters for OIDC auth requests | `{}` |
| `OIDC_ALLOW_DUPLICATE_EMAILS` | Allow multiple users with same email | `False` |
| `OIDC_CREATE_USER` | Automatically create users on OIDC login | `True` |
| `OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION` | Use email as fallback for user identification | `True` |
| `OIDC_OP_AUTHORIZATION_ENDPOINT` | OIDC provider authorization endpoint | `None` |
| `OIDC_OP_JWKS_ENDPOINT` | OIDC provider JWKS endpoint | `None` |
| `OIDC_OP_LOGOUT_ENDPOINT` | OIDC provider logout endpoint | `None` |
| `OIDC_OP_TOKEN_ENDPOINT` | OIDC provider token endpoint | `None` |
| `OIDC_OP_USER_ENDPOINT` | OIDC provider user endpoint | `None` |
| `OIDC_OP_URL` | OIDC issuer/base URL (discovery reference) | `None` |
| `OIDC_REDIRECT_ALLOWED_HOSTS` | List of allowed hosts for OIDC redirects | `[]` |
| `OIDC_REDIRECT_REQUIRE_HTTPS` | Require HTTPS for OIDC redirects | `False` |
| `OIDC_RP_CLIENT_ID` | OIDC client ID | `drive` |
| `OIDC_RP_CLIENT_SECRET_FILE` | File path to the OIDC client secret (refs-only) | `None` |
| `OIDC_RP_CLIENT_SECRET_ENV` | Env var name holding the OIDC client secret (refs-only) | `None` |
| `OIDC_RP_SCOPES` | OIDC scopes | `openid email` |
| `OIDC_RP_SIGN_ALGO` | OIDC signing algorithm | `RS256` |
| `OIDC_STORE_ACCESS_TOKEN` | Store OIDC access token | `False` |
| `OIDC_STORE_ID_TOKEN` | Store OIDC ID token | `True` |
| `OIDC_STORE_REFRESH_TOKEN` | Store OIDC refresh token | `False` |
| `OIDC_STORE_REFRESH_TOKEN_KEY` | Key for storing OIDC refresh token | `None` |
| `OIDC_USE_NONCE` | Use nonce for OIDC requests | `True` |
| `OIDC_USER_INFO` | List of OIDC user info claims | `[]` |
| `OIDC_USERINFO_FULLNAME_FIELDS` | Fields to use for full name | `["first_name", "last_name"]` |
| `OIDC_USERINFO_SHORTNAME_FIELD` | Field to use for short name | `first_name` |
| `POSTHOG_HOST` | PostHog analytics host URL | `https://eu.i.posthog.com` |
| `POSTHOG_KEY` | PostHog analytics API key | `None` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `RESTRICT_UPLOAD_FILE_TYPE` | Boolean to enable or not upload restriction based on file type (extension + mimetype) | `True` |
| `S3_TRANSFER_CONFIG_MULTIPART_THRESHOLD` | `multipart_threshold` value for the `TransferConfig` configuration | `8388608` (8MB) |
| `S3_TRANSFER_CONFIG_MULTIPART_CHUNKSIZE` | `multipart_chunksize` value for the `TransferConfig` configuration | `8388608` (8MB) |
| `S3_TRANSFER_CONFIG_MAX_CONCURRENCY` | `max_concurrency` value for the `TransferConfig` configuration | `10` |
| `S3_TRANSFER_CONFIG_USE_THREADS` | `use_threads` value for the `TransfertConfig` configuration | `True` |
| `SEARCH_INDEXER_ALLOWED_MIMETYPES` | Indexable files mimetypes | `["text/"]` |
| `SEARCH_INDEXER_CLASS` | Class of the backend for item indexation & search ||
| `SEARCH_INDEXER_BATCH_SIZE` | Size of each batch for indexation of all items | `1000` |
| `SEARCH_INDEXER_COUNTDOWN` | Minimum debounce delay of indexation jobs (in seconds) | 1 |
| `SEARCH_INDEXER_MIMETYPES` | Find application endpoint for search | `None` |
| `SEARCH_INDEXER_QUERY_URL` | Find application endpoint for search | `None` |
| `SEARCH_INDEXER_SECRET` | Token for indexation queries | `None` |
| `SEARCH_INDEXER_CONTENT_MAX_SIZE` | Maximum size for an indexable file | `2097152` |
| `SEARCH_INDEXER_URL` | Find application endpoint for indexation | `None` |
| `SEARCH_INDEXER_QUERY_LIMIT` | Maximum number of results expected from search endpoint | 50 |
| `SENTRY_DSN` | Sentry DSN for error tracking | `None` |
| `SPECTACULAR_SETTINGS_ENABLE_DJANGO_DEPLOY_CHECK` | Enable Django deploy check in Spectacular | `False` |
| `STORAGES_STATICFILES_BACKEND` | Backend for static files storage | `whitenoise.storage.CompressedManifestStaticFilesStorage` |
| `TRASHBIN_CUTOFF_DAYS` | Number of days before items are permanently deleted from trash | `30` |
| `WOPI_CLIENTS` | List of client name. These client names will be used in the post_setup | [] |
| `WOPI_{CLIENT_NAME}_DISCOVERY_URL` | The discovery url for each client present in the `WOPI_CLIENTS`. if `WOPI_CLIENTS=vendorA` then set `WOPI_VENDORA_DISCOVERY_URL` | |
| `WOPI_EXCLUDED_MIMETYPES` | List of mimetypes excluded when parsing the discovery url | See settings.py module |
| `WOPI_EXCLUDED_EXTENSIONS` | List of extensions excluded when parsing the discovery url | See settings.py module |
| `WOPI_SRC_BASE_URL` | The backend url | None |
| `WOPI_ACCESS_TOKEN_TIMEOUT` | TTL in seconds for the access_token_ttl sent to the WOPI client | `36000` (10H) |
| `WOPI_LOCK_TIMEOUT` | TTL for the lock acquired by a WOPI client | `1800` (30 min) |
| `WOPI_DISABLE_CHAT` | Disable chat in the WOPI client interface | `0` |
| `WOPI_CONFIGURATION_CRONTAB_MINUTE` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `0` |
| `WOPI_CONFIGURATION_CRONTAB_HOUR` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `3` |
| `WOPI_CONFIGURATION_CRONTAB_DAY_OF_MONTH` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `*` |
| `WOPI_CONFIGURATION_CRONTAB_MONTH_OF_YEAR` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `*` |

## S3 TransferConfig tuning (backend-mediated transfers)

Drive configures boto3 `TransferConfig` via the `S3_TRANSFER_CONFIG_*` env vars.
These settings primarily affect **backend-mediated** transfers (server-side S3
interactions, and any flows using boto3 `TransferConfig`, e.g. WOPI save flows).

They do **not** affect browser presigned PUT uploads (`EXTERNAL_BROWSER`) unless
multipart upload is explicitly implemented in the browser client.

Notes:

- Values are integers in **bytes**.
- Constraints enforced by `config_preflight`:
  - `S3_TRANSFER_CONFIG_MULTIPART_CHUNKSIZE`: 5MB–5GB
  - `S3_TRANSFER_CONFIG_MULTIPART_THRESHOLD`: 5MB–5TB
  - `S3_TRANSFER_CONFIG_MULTIPART_CHUNKSIZE` must be `<=` threshold
  - `S3_TRANSFER_CONFIG_MAX_CONCURRENCY`: 1–256

## `DRIVE_PUBLIC_URL` examples

Production (HTTPS):

```bash
DRIVE_PUBLIC_URL=https://drive.example.com
```

Development-only HTTP override (requires both `DEBUG=True` and `DRIVE_ALLOW_INSECURE_HTTP=true`):

```bash
DRIVE_PUBLIC_URL=http://localhost:3000
DRIVE_ALLOW_INSECURE_HTTP=true
```

Notes:

- In production posture, public surfaces are **HTTPS-only** (no mixed TLS modes).
- In production posture, `http://` is rejected even if `DRIVE_ALLOW_INSECURE_HTTP=true`.
- The same posture applies to other public-surface base URLs such as `WOPI_SRC_BASE_URL` and any URL-form entries in `OIDC_REDIRECT_ALLOWED_HOSTS`.

## Split allowlists (derived from `DRIVE_PUBLIC_URL`)

When `DRIVE_PUBLIC_URL` is set, Drive always derives and includes canonical defaults:

- Canonical origin: `DRIVE_PUBLIC_URL` (origin form, no trailing slash)
- Canonical host: host (and port if present) extracted from `DRIVE_PUBLIC_URL`
- Canonical redirect URI: `DRIVE_PUBLIC_URL/` (root path)

Operator additions are additive and validated deterministically (no wildcards):

```bash
# Redirect targets (absolute URIs incl. path). Used to derive allowed hosts for OIDC returnTo.
DRIVE_ALLOWED_REDIRECT_URIS=https://extra.example.com/after-login

# Explicit extra hosts for OIDC returnTo validation (hostnames only).
DRIVE_ALLOWED_HOSTS=extra.example.com

# SDK relay CORS origins (origin form only).
DRIVE_ALLOWED_ORIGINS=https://sdk.example.com
```
