# Django drive

# ---- base image to inherit from ----
FROM python:3.13.9-alpine AS base

# Upgrade pip to its latest release to speed up dependencies installation
# We must do taht to avoid having an outdated pip version with security issues
RUN python -m pip install --upgrade pip

# Upgrade system packages to install security updates
RUN apk update && \
  apk upgrade && \
  apk add git

# ---- Back-end builder image ----
FROM base AS back-builder


ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image;
ENV UV_PYTHON_DOWNLOADS=0

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /uvx /bin/

WORKDIR /app


RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=src/backend/uv.lock,target=uv.lock \
  --mount=type=bind,source=src/backend/pyproject.toml,target=pyproject.toml \
  uv sync --locked --no-install-project --no-dev
COPY src/backend /app
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-dev

# ---- mails ----
FROM node:20 AS mail-builder

COPY ./src/mail /mail/app

WORKDIR /mail/app

RUN yarn install --frozen-lockfile && \
  yarn build

# ---- static link collector ----
FROM base AS link-collector
ARG DRIVE_STATIC_ROOT=/data/static

# Install libmagic, pango & rdfind
RUN apk add \
  libmagic \
  pango \
  rdfind

WORKDIR /app

# Copy the application from the builder
COPY --from=back-builder /app /app

ENV PATH="/app/.venv/bin:$PATH"


# collectstatic
RUN DJANGO_CONFIGURATION=Build \
  python manage.py collectstatic --noinput

# Replace duplicated file by a symlink to decrease the overall size of the
# final image
RUN rdfind -makesymlinks true -followsymlinks true -makeresultsfile false ${DRIVE_STATIC_ROOT}

# ---- Core application image ----
FROM base AS core

ENV PYTHONUNBUFFERED=1

# Install required system libs
RUN apk add \
  cairo \
  file \
  font-noto \
  font-noto-emoji \
  gettext \
  gdk-pixbuf \
  libffi-dev \
  pandoc \
  pango \
  shared-mime-info

RUN wget https://raw.githubusercontent.com/suitenumerique/django-lasuite/refs/heads/main/assets/conf/mime.types -O /etc/mime.types

# Copy entrypoint
COPY ./docker/files/usr/local/bin/entrypoint /usr/local/bin/entrypoint

# Give the "root" group the same permissions as the "root" user on /etc/passwd
# to allow a user belonging to the root group to add new users; typically the
# docker user (see entrypoint).
RUN chmod g=u /etc/passwd

# Copy the application from the builder
COPY --from=back-builder /app /app

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

# Generate compiled translation messages
RUN DJANGO_CONFIGURATION=Build \
  python manage.py compilemessages --ignore=".venv/**/*"


# We wrap commands run in this container by the following entrypoint that
# creates a user on-the-fly with the container user ID (see USER) and root group
# ID.
ENTRYPOINT [ "/usr/local/bin/entrypoint" ]

# ---- Development image ----
FROM core AS backend-development

# Switch back to the root user to install development dependencies
USER root:root

# Install psql
RUN apk add postgresql-client

# Install development dependencies
RUN --mount=from=ghcr.io/astral-sh/uv:0.9.10,source=/uv,target=/bin/uv \
  uv sync --all-extras --locked

# Restore the un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

# Target database host (e.g. database engine following docker compose services
# name) & port
ENV DB_HOST=postgresql \
  DB_PORT=5432

# Run django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- Production image ----
FROM core AS backend-production

ARG DRIVE_STATIC_ROOT=/data/static

# Remove git, we don't need it in the production image
RUN apk del git

# Gunicorn
RUN mkdir -p /usr/local/etc/gunicorn
COPY docker/files/usr/local/etc/gunicorn/drive.py /usr/local/etc/gunicorn/drive.py

# Un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

# Copy statics
COPY --from=link-collector ${DRIVE_STATIC_ROOT} ${DRIVE_STATIC_ROOT}

# Copy mails
COPY --from=mail-builder /mail/backend/core/templates/mail /app/core/templates/mail


# The default command runs gunicorn WSGI server in drive's main module
CMD ["gunicorn", "-c", "/usr/local/etc/gunicorn/drive.py", "drive.wsgi:application"]
