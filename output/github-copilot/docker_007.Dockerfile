I checked the repo layout first: it doesn't contain a Node.js app or a `package.json`, so I’m creating a standard production Dockerfile shape rather than wiring to an app-specific entrypoint. I’m also avoiding baking `.env` and host `node_modules` into the image.

The repo’s own ignore rules already treat `.env` as a secret, so I’m wiring a production Docker build that installs dependencies in-image instead of embedding local secrets or host `node_modules`.

File writes are blocked in this environment, so I’m delivering the complete Dockerfile content directly instead of modifying the repo.FROM node:20-alpine AS base

WORKDIR /app

ENV NODE_ENV=production

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

EXPOSE 3000

CMD ["npm", "start"]