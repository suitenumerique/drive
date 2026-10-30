# Upgrade

All instructions to upgrade this project from one release to the next will be
documented in this file. Upgrades must be run sequentially, meaning you should
not skip minor/major releases while upgrading (fix releases can be skipped).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For most upgrades, you just need to run the django migrations with
the following command inside your docker container:

`python manage.py migrate`

(Note : in your development environment, you can `make migrate`.)

## [Unreleased]

- ⚠️ `FILE_MIMETYPE_ALLOWED` was read from `DJANGO_FILE_MIMETYPE_ALLOWED`:
  rename the variable if you override it.
- ⚠️ `RESTRICT_UPLOAD_FILE_TYPE` is no longer a boolean: replace `True` with
  `allowlist` and `False` with `off`. Any other value stops the startup.
- ⚠️ Emails use a new layout. The product name in their text now comes from
  `DJANGO_EMAIL_APP_NAME` (default `Drive`) instead of the translations: set it
  to keep another name, e.g. `Fichiers`.
- Emails can show more branding, each block being hidden while its setting is
  unset (see [env.md](docs/env.md)): `DJANGO_EMAIL_FONT_REGULAR_URL`,
  `DJANGO_EMAIL_FONT_BOLD_URL`, `DJANGO_EMAIL_GOVERNMENT_LOGO_IMG`,
  `DJANGO_EMAIL_SUITE_LOGO_IMG`, `DJANGO_EMAIL_SUITE_URL`,
  `DJANGO_EMAIL_PRODUCT_ICONS`, `DJANGO_EMAIL_NEWSLETTER_URL`,
  `DJANGO_EMAIL_SUPPORT_URL` and `DJANGO_EMAIL_TERMS_OF_SERVICE_URL`. The
  support and terms of use links default to the ones of
  `FRONTEND_HELP_MENU_CONFIG`.
- The frontend now serves images and the Marianne font for emails under
  `/assets/email/` and `/assets/fonts/`. Deploy it before pointing the settings
  above to them. Fonts are served with `Access-Control-Allow-Origin: *` so that
  webmails can load them: keep this header if a proxy or CDN sits in front.
- `DJANGO_EMAIL_LOGO_IMG` is now shown 250px wide: the
  `/assets/email/logo-lasuite-fichiers.png` image is made for it.
