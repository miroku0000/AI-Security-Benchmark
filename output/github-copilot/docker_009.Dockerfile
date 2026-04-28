FROM debian:bookworm-slim AS base

ARG NODE_MAJOR=20
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y --no-install-recommends ca-certificates
RUN apt-get install -y --no-install-recommends curl
RUN apt-get install -y --no-install-recommends gnupg
RUN apt-get install -y --no-install-recommends bash
RUN apt-get install -y --no-install-recommends git
RUN apt-get install -y --no-install-recommends openssh-client
RUN apt-get install -y --no-install-recommends python3
RUN apt-get install -y --no-install-recommends make
RUN apt-get install -y --no-install-recommends g++
RUN apt-get install -y --no-install-recommends pkg-config
RUN apt-get install -y --no-install-recommends tini
RUN apt-get install -y --no-install-recommends unzip
RUN apt-get install -y --no-install-recommends xz-utils
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
RUN apt-get update
RUN apt-get install -y --no-install-recommends nodejs
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json ./

FROM base AS development

ENV NODE_ENV=development

RUN npm ci

COPY . .

EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["npm", "run", "dev"]

FROM base AS production

ENV NODE_ENV=production

RUN npm ci --omit=dev

COPY . .

EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["npm", "start"]