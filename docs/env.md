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
| `FRONTEND_THEME` | Frontend theme configuration | `None` |
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
| `OIDC_REDIRECT_ALLOWED_HOSTS` | List of allowed hosts for OIDC redirects | `[]` |
| `OIDC_REDIRECT_REQUIRE_HTTPS` | Require HTTPS for OIDC redirects | `False` |
| `OIDC_RP_CLIENT_ID` | OIDC client ID | `drive` |
| `OIDC_RP_CLIENT_SECRET` | OIDC client secret | `None` |
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
| `SENTRY_DSN` | Sentry DSN for error tracking | `None` |
| `SPECTACULAR_SETTINGS_ENABLE_DJANGO_DEPLOY_CHECK` | Enable Django deploy check in Spectacular | `False` |
| `STORAGES_STATICFILES_BACKEND` | Backend for static files storage | `whitenoise.storage.CompressedManifestStaticFilesStorage` |
| `TRASHBIN_CUTOFF_DAYS` | Number of days before items are permanently deleted from trash | `30` |
