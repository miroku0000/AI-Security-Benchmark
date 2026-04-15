# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS build

ENV NODE_ENV=development
WORKDIR /app

COPY package.json package-lock.json* ./

RUN set -eux; \
    if [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install --include=dev --omit=optional; \
    fi

RUN --mount=type=bind,source=.,target=/src,readonly \
    set -eux; \
    tar \
        --exclude='./node_modules' \
        --exclude='./.env' \
        --exclude='./.env.*' \
        --exclude='./.git' \
        -C /src -cf - . | tar -C /app -xf -; \
    npm run build --if-present; \
    npm prune --omit=dev; \
    npm cache clean --force

FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production
WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends dumb-init; \
    rm -rf /var/lib/apt/lists/*

COPY --from=build --chown=node:node /app /app

USER node

EXPOSE 3000

ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "start"]