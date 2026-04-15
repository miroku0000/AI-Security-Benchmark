FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ARG NODE_MAJOR=22

RUN apt-get update
RUN apt-get install -y --no-install-recommends ca-certificates
RUN apt-get install -y --no-install-recommends curl
RUN apt-get install -y --no-install-recommends gnupg
RUN apt-get install -y --no-install-recommends dirmngr
RUN apt-get install -y --no-install-recommends apt-transport-https

RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list

RUN apt-get update
RUN apt-get install -y --no-install-recommends nodejs
RUN apt-get install -y --no-install-recommends build-essential
RUN apt-get install -y --no-install-recommends python3
RUN apt-get install -y --no-install-recommends git
RUN apt-get install -y --no-install-recommends bash
RUN apt-get install -y --no-install-recommends openssh-client
RUN apt-get install -y --no-install-recommends tini
RUN apt-get install -y --no-install-recommends procps
RUN apt-get install -y --no-install-recommends iputils-ping
RUN apt-get install -y --no-install-recommends netcat-openbsd
RUN apt-get install -y --no-install-recommends unzip
RUN apt-get install -y --no-install-recommends xz-utils

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS development

ENV NODE_ENV=development

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["npm", "run", "dev"]

FROM base AS build

ENV NODE_ENV=development

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build --if-present
RUN npm prune --omit=dev

FROM base AS production

ENV NODE_ENV=production

COPY --from=build /app /app

EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["npm", "start"]