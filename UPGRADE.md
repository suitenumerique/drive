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

## [v0.26.0] - 2026-11-04

- ⚠️ `FILE_MIMETYPE_ALLOWED` was read from `DJANGO_FILE_MIMETYPE_ALLOWED`:
  rename the variable if you override it.
- ⚠️ `RESTRICT_UPLOAD_FILE_TYPE` is no longer a boolean: replace `True` with
  `allowlist` and `False` with `off`. Any other value stops the startup.
- ⚠️ Emails use a new layout. The product name in their text now comes from
  `DJANGO_EMAIL_APP_NAME` (default `Drive`) instead of the translations: set it
  to keep another name, e.g. `Fichiers`.
