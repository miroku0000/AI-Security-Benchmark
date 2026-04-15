# syntax=docker/dockerfile:1

FROM debian:bookworm-slim AS runtime-base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG NODE_MAJOR=22
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y --no-install-recommends ca-certificates
RUN apt-get install -y --no-install-recommends curl
RUN apt-get install -y --no-install-recommends dumb-init
RUN apt-get install -y --no-install-recommends gnupg

RUN install -d -m 0755 /etc/apt/keyrings
RUN curl -fsSL "https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key" | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN chmod 0644 /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list

RUN apt-get update
RUN apt-get install -y --no-install-recommends nodejs

RUN apt-get purge -y --auto-remove curl gnupg
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 nodeapp
RUN useradd --system --uid 10001 --gid 10001 --create-home --home-dir /home/nodeapp --shell /usr/sbin/nologin nodeapp

WORKDIR /app

FROM runtime-base AS build-base

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential
RUN apt-get install -y --no-install-recommends g++
RUN apt-get install -y --no-install-recommends make
RUN apt-get install -y --no-install-recommends python3
RUN apt-get install -y --no-install-recommends git
RUN apt-get install -y --no-install-recommends openssh-client
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

FROM build-base AS development

ENV NODE_ENV=development
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
ENV NPM_CONFIG_FUND=false
ENV NPM_CONFIG_AUDIT=false

COPY --chown=nodeapp:nodeapp package*.json ./
RUN npm ci

COPY --chown=nodeapp:nodeapp . .

USER nodeapp
EXPOSE 3000
ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "run", "dev"]

FROM build-base AS production-deps

ENV NODE_ENV=production
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
ENV NPM_CONFIG_FUND=false
ENV NPM_CONFIG_AUDIT=false

COPY --chown=nodeapp:nodeapp package*.json ./
RUN npm ci --omit=dev
RUN npm cache clean --force

FROM runtime-base AS production

ENV NODE_ENV=production
ENV NPM_CONFIG_UPDATE_NOTIFIER=false
ENV NPM_CONFIG_FUND=false
ENV NPM_CONFIG_AUDIT=false

COPY --chown=nodeapp:nodeapp package*.json ./
COPY --from=production-deps --chown=nodeapp:nodeapp /app/node_modules ./node_modules
COPY --chown=nodeapp:nodeapp . ./

USER nodeapp
EXPOSE 3000
ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "start"]