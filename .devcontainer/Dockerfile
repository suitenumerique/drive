ARG BASE_IMAGE=drive:backend-development
FROM ${BASE_IMAGE}

USER root

# Install tools needed by Zed (basedpyright LSP requires node)
RUN apk add --no-cache nodejs npm bash

# Create a writable home and register the dev user with a valid shell
ARG DEV_UID=1000
RUN mkdir -p /tmp/dev-home && chown ${DEV_UID}:0 /tmp/dev-home \
    && echo "default:x:${DEV_UID}:0:default user:/tmp/dev-home:/bin/sh" >> /etc/passwd

USER default
ENV HOME=/tmp/dev-home
