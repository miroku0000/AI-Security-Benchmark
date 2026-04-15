FROM node:20-alpine

WORKDIR /app

ARG NPM_REGISTRY_URL
ARG NODE_ENV=production

ENV NODE_ENV=${NODE_ENV}

COPY . .

RUN if [ -n "$NPM_REGISTRY_URL" ]; then npm config set registry "$NPM_REGISTRY_URL"; fi \
 && if [ ! -d node_modules ]; then npm install; fi \
 && npm cache clean --force

EXPOSE 3000

CMD ["npm", "start"]