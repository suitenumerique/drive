# Below stages that only output JS/WASM files are run just once for multi-platform build
# to save time (only the nginx stage has specifics)
FROM --platform=$BUILDPLATFORM node:22-alpine AS frontend-deps

WORKDIR /home/frontend/

COPY ./src/frontend/package.json ./package.json
COPY ./src/frontend/yarn.lock ./yarn.lock
COPY ./src/frontend/apps/drive/package.json ./apps/drive/package.json

RUN yarn install --frozen-lockfile

COPY .dockerignore ./.dockerignore
# COPY ./src/frontend/.prettierrc.js ./.prettierrc.js
#COPY ./src/frontend/packages/eslint-config-drive ./packages/eslint-config-drive
COPY ./src/frontend/apps/drive ./apps/drive

### ---- Front-end builder image ----
FROM frontend-deps AS drive

WORKDIR /home/frontend/apps/drive

FROM frontend-deps AS drive-dev

WORKDIR /home/frontend/apps/drive

EXPOSE 3000

RUN yarn build-theme
CMD ["yarn", "dev"]

# ---- OnlyOffice client-side assets (for encryption) ----
FROM --platform=$BUILDPLATFORM alpine:3.24 AS onlyoffice-assets

RUN apk add --no-cache bash curl unzip

COPY ./scripts/install-onlyoffice.sh /build/scripts/install-onlyoffice.sh
RUN bash /build/scripts/install-onlyoffice.sh

# The ingress compresses text on the fly, not these binaries (the 57 MB x2t.wasm first):
# a gzipped copy sits next to each, served by `gzip_static` (conf/default.conf).
RUN find /build/src/frontend/apps/drive/public/onlyoffice -type f -size +1k \
      \( -name '*.wasm' -o -name '*.bin' -o -name '*.ttf' -o -name '*.otf' -o -name '*.dic' -o -name '*.aff' \) \
      -exec gzip -k -6 {} +

# Tilt will rebuild drive target so, we dissociate drive and drive-builder
# to avoid rebuilding the app at every changes.
FROM drive AS drive-builder

WORKDIR /home/frontend/apps/drive

ARG API_ORIGIN
ENV NEXT_PUBLIC_API_ORIGIN=${API_ORIGIN}

RUN yarn build

# ---- Front-end image ----
FROM nginxinc/nginx-unprivileged:alpine3.24 AS frontend-production

# Upgrade system packages to install security updates
USER root
RUN apk update && \
  apk upgrade && \
  rm -rf /var/cache/apk/*

# Un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

COPY --from=drive-builder \
    /home/frontend/apps/drive/out \
    /usr/share/nginx/html

# Straight from the download, not through `next build`, which would reset the files'
# dates: nginx derives the ETag from them, and a new one on every build would make
# every browser download the whole editor again after each deployment.
COPY --from=onlyoffice-assets \
    /build/src/frontend/apps/drive/public/onlyoffice \
    /usr/share/nginx/html/onlyoffice

COPY ./src/frontend/apps/drive/conf/default.conf /etc/nginx/conf.d
COPY ./docker/files/usr/local/bin/entrypoint /usr/local/bin/entrypoint

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]

CMD ["nginx", "-g", "daemon off;"]
