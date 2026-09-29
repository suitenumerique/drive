# Development: the source is bind-mounted and reloaded by `tsx watch` (compose.yaml).
FROM node:22-alpine AS dev

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json relay.ts ./

EXPOSE 4100

CMD ["npx", "tsx", "watch", "relay.ts"]

FROM dev AS build

RUN npx tsc

# Production: the compiled relay and its runtime dependencies, without npm, which the
# relay never runs and whose own dependencies are the usual findings of image scans.
FROM node:22-alpine

RUN apk upgrade --no-cache

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev && \
    rm -rf /root/.npm /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx

COPY --from=build /app/dist ./dist

USER node

EXPOSE 4100

CMD ["node", "dist/relay.js"]
