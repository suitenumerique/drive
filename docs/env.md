# Environment Variables

This document lists all configurable environment variables for the Drive application, extracted from the Django settings configuration.

## General settings

These variables apply to production and any other deployment.

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `ALLOWED_HOSTS` | List of allowed hosts for the application (used in Production) | `[]` |
| `ALLOW_LOGOUT_GET_METHOD` | Allow logout via GET method | `True` |
| `ALLOW_SHARE_IMPORT_FILE` | Enable batch sharing of an item from an imported contacts file | `False` |
| `API_SDK_EVENT_RELAY_THROTTLE_RATE` | Throttle rate for the SDK event relay endpoint | `200/minute` |
| `API_USERS_LIST_LIMIT` | Maximum number of users returned in API user list | `5` |
| `API_USERS_LIST_THROTTLE_RATE_BURST` | Burst throttle rate for user list API | `30/minute` |
| `API_USERS_LIST_THROTTLE_RATE_SUSTAINED` | Sustained throttle rate for user list API | `180/hour` |
| `AWS_S3_ACCESS_KEY_ID` | AWS S3 access key ID for file storage | `None` |
| `AWS_S3_ENDPOINT_URL` | AWS S3 endpoint URL for file storage | `None` |
| `AWS_S3_DOMAIN_REPLACE` | The S3 domain to used by the frontend application. Used by the docker compose stack. | `None` |
| `AWS_S3_REGION_NAME` | AWS S3 region name for file storage | `None` |
| `AWS_S3_SECRET_ACCESS_KEY` | AWS S3 secret access key for file storage | `None` |
| `AWS_S3_SIGNATURE_VERSION` | AWS S3 signature version | `s3v4` |
| `AWS_S3_UPLOAD_ACL` | ACL applied to uploaded objects, set to `default` for storages that do not support ACLs (e.g. GCS based providers). With `default`, objects get the bucket's default object ACL: make sure it keeps objects private | `private` |
| `AWS_S3_UPLOAD_POLICY_EXPIRATION` | AWS S3 upload policy expiration time in seconds | `86400` (24h) |
| `AWS_STORAGE_BUCKET_NAME` | AWS S3 bucket name for file storage | `drive-media-storage` |
| `CACHES_DEFAULT_KEY_PREFIX` | Key prefix for the default cache | `drive` |
| `CACHES_DEFAULT_TIMEOUT` | Default cache timeout in seconds | `30` |
| `CACHES_SESSION_TIMEOUT` | Session cache timeout in seconds | `30` |
| `CRISP_WEBSITE_ID` | Crisp chat widget website ID | `None` |
| `CSRF_TRUSTED_ORIGINS` | List of trusted origins for CSRF | `[]` |
| `DATA_DIR` | Directory for storing application data | `/data` |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | max upload file size, in bytes | `2147483648` (2 GB) |
| `DATABASE_URL` | Database connection URL (overrides individual DB settings) | `None` |
| `DB_ENGINE` | Database engine | `django.db.backends.postgresql` |
| `DB_HOST` | Database host | `localhost` |
| `DB_NAME` | Database name | `drive` |
| `DB_PASSWORD` | Database password | `pass` |
| `DB_PORT` | Database port | `5432` |
| `DB_USER` | Database user | `dinum` |
| `DJANGO_CELERY_BROKER_TRANSPORT_OPTIONS` | Celery broker transport options | `{}` |
| `DJANGO_CELERY_BROKER_URL` | Celery broker URL for task queue | `redis://redis:6379/0` |
| `DJANGO_CELERY_TASK_ROUTES` | Celery task routing configuration. Use this to route specific tasks to dedicated queues, e.g. `{"core.tasks.item.duplicate_file": {"queue": "duplicate_file"}}` | `{}` |
| `DJANGO_CORS_ALLOW_ALL_ORIGINS` | Allow all origins for CORS | `False` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | List of allowed origins for CORS | `[]` |
| `DJANGO_CORS_ALLOWED_ORIGIN_REGEXES` | List of allowed origin regexes for CORS | `[]` |
| `DJANGO_EMAIL_BACKEND` | Email backend for sending emails | `django.core.mail.backends.smtp.EmailBackend` |
| `DJANGO_EMAIL_BRAND_NAME` | Brand name for email templates | `None` |
| `DJANGO_EMAIL_FROM` | Default sender email address | `from@example.com` |
| `DJANGO_EMAIL_HOST` | SMTP host for email sending | `None` |
| `DJANGO_EMAIL_HOST_PASSWORD` | SMTP password for email sending | `None` |
| `DJANGO_EMAIL_HOST_USER` | SMTP username for email sending | `None` |
| `DJANGO_EMAIL_LOGO_IMG` | Logo image URL for email templates | `None` |
| `DJANGO_EMAIL_PORT` | SMTP port for email sending | `None` |
| `DJANGO_EMAIL_URL_APP` | URL used in emails to link back to the app | `None` |
| `DJANGO_EMAIL_USE_SSL` | Use SSL for SMTP connection | `False` |
| `DJANGO_EMAIL_USE_TLS` | Use TLS for SMTP connection | `False` |
| `DJANGO_LANGUAGE_CODE` | Default language code | `en-us` |
| `DJANGO_LANGUAGES` | Available languages, ordered by priority | See settings.py module |
| `DJANGO_SECRET_KEY` | Django secret key, must be defined in production | `None` |
| `ENTITLEMENTS_BACKEND` | Class of the backend computing user entitlements | `core.entitlements.backends.static.StaticEntitlementsBackend` |
| `ENTITLEMENTS_BACKEND_PARAMETERS` | Parameters passed to the entitlements backend | `{}` |
| `EXTERNAL_API` | Available routes and actions for the external API endpoints | See settings.py module |
| `EXTERNAL_API_AUD_ITEM_ATTRIBUTES` | Extra attributes applied to items created through the external API, keyed by the token audience of the request, e.g. `{"some_audience": {"quota_excluded": true}}` | `{}` |
| `FEATURES_INDEXED_SEARCH` | Enable the search of indexed files through the API | `True` |
| `FILE_EXTENSIONS_ALLOWED` | List of file extension allowed to be uploaded | See in the settings.py file |
| `FILE_MIMETYPE_ALLOWED` | List of file mimetype allowed to be uploaded | See in the setings.py file |
| `FRONTEND_THEME` | Frontend theme configuration | `None` |
| `FRONTEND_MORE_LINK` | URL of the "more" link displayed in the frontend | `None` |
| `FRONTEND_EXTERNAL_HOME_URL` | Frontend external home url to redirect to | `None` |
| `FRONTEND_FEEDBACK_BUTTON_SHOW` | Show feedback button | `False` |
| `FRONTEND_FEEDBACK_BUTTON_IDLE` | Make feedback button idle (e.g. to bind to external library) | `False` |
| `FRONTEND_FEEDBACK_ITEMS` | Dictionary of feedback items with URLs | `{}` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_ENABLED` | Enable feedback messages widget | `False` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL` | API URL for feedback messages widget | `None` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL` | Channel for feedback messages widget | `None` |
| `FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH` | Path for feedback messages widget | `None` |
| `FRONTEND_RELEASE_NOTE_ENABLED` | Enable release notes modal on connexion | `True` |
| `FRONTEND_ENTITLEMENTS_DISCLAIMERS` | Enable entitlements disclaimers with custom params | `{}` |
| `FRONTEND_HELP_MENU_CONFIG` | Dictionary of help menu items with URLs | `{}` |
| `FRONTEND_HIDE_GAUFRE` | Hide the "gaufre" applications menu | `False` |
| `FRONTEND_SILENT_LOGIN_ENABLED` | Enable silent login on frontend | `False` |
| `FRONTEND_STORAGE_GAUGE_INFORMATION_LINK` | Information link displayed next to the storage gauge | `None` |
| `FRONTEND_CSS_URL` | URL of a custom CSS file loaded by the frontend | `None` |
| `FRONTEND_JS_URL` | URL of a custom JS file loaded by the frontend | `None` |
| `ITEM_PREVIEWABLE_MIME_TYPES` | List of mime type prefixes for which a preview is available | `["image/", "video/", "audio/", "application/pdf"]` |
| `INVITATION_VALIDITY_DURATION` | Duration during which an invitation remains valid, in seconds | `604800` (7 days) |
| `LOGIN_REDIRECT_URL` | URL to redirect after successful login | `None` |
| `LOGIN_REDIRECT_URL_FAILURE` | URL to redirect after failed login | `None` |
| `LOGOUT_REDIRECT_URL` | URL to redirect after logout | `None` |
| `LOGGING_LEVEL_LOGGERS_APP` | Logging level for application loggers | `INFO` |
| `LOGGING_LEVEL_LOGGERS_ROOT` | Logging level for root logger | `INFO` |
| `MALWARE_DETECTION_BACKEND` | Class of the backend for malware detection | `lasuite.malware_detection.backends.dummy.DummyBackend` |
| `MALWARE_DETECTION_PARAMETERS` | Parameters passed to the malware detection backend | `{"callback_path": "core.malware_detection.malware_detection_callback"}` |
| `MAX_PAGE_SIZE` | Limit the maximum page size the client may request | `200` |
| `MEDIA_BASE_URL` | Base URL for media files | `None` |
| `METRICS_ENABLED` | Enable the metrics endpoint | `False` |
| `METRICS_USER_CLAIMS_EXPOSED` | List of user claims exposed by the metrics endpoint | `[]` |
| `OIDC_AUTH_REQUEST_EXTRA_PARAMS` | Extra parameters for OIDC auth requests | `{}` |
| `OIDC_ALLOW_DUPLICATE_EMAILS` | Allow multiple users with same email | `False` |
| `OIDC_CREATE_USER` | Automatically create users on OIDC login | `True` |
| `OIDC_FALLBACK_TO_EMAIL_FOR_IDENTIFICATION` | Use email as fallback for user identification | `True` |
| `OIDC_OP_AUTHORIZATION_ENDPOINT` | OIDC provider authorization endpoint | `None` |
| `OIDC_OP_INTROSPECTION_ENDPOINT` | OIDC provider introspection endpoint (resource server) | `None` |
| `OIDC_OP_JWKS_ENDPOINT` | OIDC provider JWKS endpoint | `None` |
| `OIDC_OP_LOGOUT_ENDPOINT` | OIDC provider logout endpoint | `None` |
| `OIDC_OP_TOKEN_ENDPOINT` | OIDC provider token endpoint | `None` |
| `OIDC_OP_URL` | OIDC provider base URL (resource server) | `None` |
| `OIDC_OP_USER_ENDPOINT` | OIDC provider user endpoint | `None` |
| `OIDC_PROXY` | Proxy URL used for OIDC requests | `None` |
| `OIDC_REDIRECT_ALLOWED_HOSTS` | List of allowed hosts for OIDC redirects | `[]` |
| `OIDC_REDIRECT_FIELD_NAME` | Name of the query parameter holding the post-login redirect URL | `returnTo` |
| `OIDC_REDIRECT_REQUIRE_HTTPS` | Require HTTPS for OIDC redirects | `False` |
| `OIDC_RESOURCE_SERVER_ENABLED` | Enable the OIDC resource server (external API) | `False` |
| `OIDC_RP_CLIENT_ID` | OIDC client ID | `drive` |
| `OIDC_RP_CLIENT_SECRET` | OIDC client secret | `None` |
| `OIDC_RP_SCOPES` | OIDC scopes | `openid email` |
| `OIDC_RP_SIGN_ALGO` | OIDC signing algorithm | `RS256` |
| `OIDC_RS_ALLOWED_AUDIENCES` | List of audiences accepted by the resource server | `[]` |
| `OIDC_RS_AUDIENCE_CLAIM` | Token claim holding the audience | `client_id` |
| `OIDC_RS_BACKEND_CLASS` | Class of the resource server backend | `lasuite.oidc_resource_server.backend.ResourceServerBackend` |
| `OIDC_RS_CLIENT_ID` | Resource server client ID | `None` |
| `OIDC_RS_CLIENT_SECRET` | Resource server client secret | `None` |
| `OIDC_RS_ENCRYPTION_ALGO` | Encryption algorithm for introspection responses | `RSA-OAEP` |
| `OIDC_RS_ENCRYPTION_ENCODING` | Encryption encoding for introspection responses | `A256GCM` |
| `OIDC_RS_ENCRYPTION_KEY_TYPE` | Key type used to decrypt introspection responses | `RSA` |
| `OIDC_RS_PRIVATE_KEY_STR` | Private key used to decrypt introspection responses | `None` |
| `OIDC_RS_SCOPES` | Scopes accepted by the resource server | `["openid"]` |
| `OIDC_RS_SIGNING_ALGO` | Signing algorithm for introspection responses | `ES256` |
| `OIDC_PKCE_CODE_CHALLENGE_METHOD` | OIDC PKCE challenge method | `S256` |
| `OIDC_PKCE_CODE_VERIFIER_SIZE` | Length of the OIDC PKCE verifier code | `64` |
| `OIDC_STORE_ACCESS_TOKEN` | Store OIDC access token | `False` |
| `OIDC_STORE_CLAIMS` | List of OIDC claims to store on the user | `[]` |
| `OIDC_STORE_ID_TOKEN` | Store OIDC ID token | `True` |
| `OIDC_STORE_REFRESH_TOKEN` | Store OIDC refresh token | `False` |
| `OIDC_STORE_REFRESH_TOKEN_KEY` | Key for storing OIDC refresh token | `None` |
| `OIDC_TIMEOUT` | Timeout in seconds for OIDC requests | `3` |
| `OIDC_USE_NONCE` | Use nonce for OIDC requests | `True` |
| `OIDC_USE_PKCE` | Use PKCE when interacting with OIDC server | `False` |
| `OIDC_USER_INFO` | List of OIDC user info claims | `[]` |
| `OIDC_USERINFO_FULLNAME_FIELDS` | Fields to use for full name | `["first_name", "last_name"]` |
| `OIDC_USERINFO_SHORTNAME_FIELD` | Field to use for short name | `first_name` |
| `OIDC_VERIFY_SSL` | Verify SSL certificates for OIDC requests | `True` |
| `POSTHOG_HOST` | PostHog analytics host URL | `https://eu.i.posthog.com` |
| `POSTHOG_KEY` | PostHog analytics API key | `None` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `RESTRICT_UPLOAD_FILE_TYPE` | Boolean to enable or not upload restriction based on file type (extension + mimetype) | `True` |
| `S3_TRANSFER_CONFIG_MULTIPART_THRESHOLD` | `multipart_threshold` value for the `TransferConfig` configuration | `8388608` (8MB) |
| `S3_TRANSFER_CONFIG_MULTIPART_CHUNKSIZE` | `multipart_chunksize` value for the `TransferConfig` configuration | `8388608` (8MB) |
| `S3_TRANSFER_CONFIG_MAX_CONCURRENCY` | `max_concurrency` value for the `TransferConfig` configuration | `10` |
| `S3_TRANSFER_CONFIG_USE_THREADS` | `use_threads` value for the `TransfertConfig` configuration | `True` |
| `SDK_CORS_ALLOWED_ORIGINS` | List of allowed origins for the SDK endpoints CORS | `[]` |
| `SDK_RELAY_CACHE_TIMEOUT` | Cache timeout in seconds for SDK relay events | `600` (10 min) |
| `SEARCH_INDEXER_ALLOWED_MIMETYPES` | Indexable files mimetypes | `["text/"]` |
| `SEARCH_INDEXER_CLASS` | Class of the backend for item indexation & search ||
| `SEARCH_INDEXER_BATCH_SIZE` | Size of each batch for indexation of all items | `1000` |
| `SEARCH_INDEXER_COUNTDOWN` | Minimum debounce delay of indexation jobs (in seconds) | 1 |
| `SEARCH_INDEXER_QUERY_URL` | Find application endpoint for search | `None` |
| `SEARCH_INDEXER_SECRET` | Token for indexation queries | `None` |
| `SEARCH_INDEXER_CONTENT_MAX_SIZE` | Maximum size for an indexable file | `2097152` |
| `SEARCH_INDEXER_URL` | Find application endpoint for indexation | `None` |
| `SEARCH_INDEXER_QUERY_LIMIT` | Maximum number of results expected from search endpoint | 50 |
| `SENTRY_DSN` | Sentry DSN for error tracking | `None` |
| `SENTRY_TRACES_SAMPLE_RATE` | Ratio of requests traced for Sentry performance monitoring (0 to 1) | `0.0` |
| `SPECTACULAR_SETTINGS_ENABLE_DJANGO_DEPLOY_CHECK` | Enable Django deploy check in Spectacular | `False` |
| `STORAGE_COMPUTE_BACKEND` | Class of the backend computing users' storage usage | `core.storage.creator_storage_compute_backend.CreatorStorageComputeBackend` |
| `STORAGES_DEFAULT_BACKEND` | Backend for the default (media) file storage | `storages.backends.s3.S3Storage` |
| `STORAGES_STATICFILES_BACKEND` | Backend for static files storage | `whitenoise.storage.CompressedManifestStaticFilesStorage` |
| `THEME_CUSTOMIZATION_CACHE_TIMEOUT` | Cache timeout in seconds for the theme customization file | `86400` (24h) |
| `THEME_CUSTOMIZATION_FILE_PATH` | Path to the theme customization JSON file | `drive/configuration/theme/default.json` in the backend base directory |
| `TRASHBIN_CUTOFF_DAYS` | Number of days before items are automatically removed from trash after their soft deletion | `30` |
| `PURGE_GRACE_DAYS` | Number of days before items and their associated file can be permanently purged from storage and database after the trashbin cutoff period | `7` |
| `USER_OIDC_ESSENTIAL_CLAIMS` | Deprecated, use `OIDC_USER_INFO` instead | `[]` |
| `USER_RECONCILIATION_FORM_URL` | URL of a third-party form for user reconciliation requests, used in the email sent when a request fails | `None` |
| `WOPI_CLIENTS` | List of client name. These client names will be used in the post_setup | [] |
| `WOPI_{CLIENT_NAME}_DISCOVERY_URL` | The discovery url for each client present in the `WOPI_CLIENTS`. if `WOPI_CLIENTS=vendorA` then set `WOPI_VENDORA_DISCOVERY_URL` | |
| `WOPI_EXCLUDED_MIMETYPES` | List of mimetypes excluded when parsing the discovery url | See settings.py module |
| `WOPI_EXCLUDED_EXTENSIONS` | List of extensions excluded when parsing the discovery url | See settings.py module |
| `WOPI_SRC_BASE_URL` | The backend url | None |
| `WOPI_ACCESS_TOKEN_TIMEOUT` | TTL in seconds for the access_token_ttl sent to the WOPI client | `36000` (10H) |
| `WOPI_LOCK_TIMEOUT` | TTL for the lock acquired by a WOPI client | `1800` (30 min) |
| `WOPI_CONVERSION_SOURCE_TOKEN_TIMEOUT` | TTL in seconds for the short-lived token OnlyOffice uses to fetch the source file | `120` |
| `WOPI_ONLYOFFICE_CONVERT_JWT_SECRET` | Shared secret for signing OnlyOffice /converter requests. Required for conversion to work. | `None` |
| `WOPI_ONLYOFFICE_CONVERT_HTTP_CONNECT_TIMEOUT` | Connect timeout in seconds for the /converter request | `5` |
| `WOPI_ONLYOFFICE_CONVERT_HTTP_READ_TIMEOUT` | Read timeout in seconds for the /converter request | `60` |
| `WOPI_ONLYOFFICE_CONVERT_DOWNLOAD_CONNECT_TIMEOUT` | Connect timeout in seconds for downloading the converted file | `5` |
| `WOPI_ONLYOFFICE_CONVERT_DOWNLOAD_READ_TIMEOUT` | Read timeout in seconds for downloading the converted file | `30` |
| `WOPI_DISABLE_CHAT` | Disable chat in the WOPI client interface | `0` |
| `WOPI_CONFIGURATION_CACHE_EXPIRATION` | Cache expiration in seconds for the WOPI clients configuration | `86400` (24h) |
| `WOPI_CONFIGURATION_CRONTAB_MINUTE` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `0` |
| `WOPI_CONFIGURATION_CRONTAB_HOUR` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `3` |
| `WOPI_CONFIGURATION_CRONTAB_DAY_OF_MONTH` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `*` |
| `WOPI_CONFIGURATION_CRONTAB_MONTH_OF_YEAR` | Used to configure the celery beat crontab, See https://docs.celeryq.dev/en/main/reference/celery.schedules.html#celery.schedules.crontab | `*` |

## Development and test settings

These variables only affect development or test environments.

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `DJANGO_CELERY_TASK_ALWAYS_EAGER` | Run Celery tasks synchronously (Test settings only) | `True` |
| `MALWARE_DETECTION_DUMMY_SLEEP` | Delay in seconds for the development `SleepyDummyBackend` safe result | `3` |
