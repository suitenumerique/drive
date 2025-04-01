FROM node:20-alpine AS frontend-deps

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

CMD [ "yarn", "dev"]

# Tilt will rebuild drive target so, we dissociate drive and drive-builder 
# to avoid rebuilding the app at every changes.
FROM drive AS drive-builder

WORKDIR /home/frontend/apps/drive

ARG API_ORIGIN
ENV NEXT_PUBLIC_API_ORIGIN=${API_ORIGIN}

ARG S3_DOMAIN_REPLACE
ENV NEXT_PUBLIC_S3_DOMAIN_REPLACE=${S3_DOMAIN_REPLACE}

RUN yarn build --no-lint

# ---- Front-end image ----
FROM nginxinc/nginx-unprivileged:1.26-alpine AS frontend-production

# Un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

COPY --from=drive-builder \
    /home/frontend/apps/drive/out \
    /usr/share/nginx/html

COPY ./src/frontend/apps/drive/conf/default.conf /etc/nginx/conf.d
COPY ./docker/files/usr/local/bin/entrypoint /usr/local/bin/entrypoint

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]

CMD ["nginx", "-g", "daemon off;"]
