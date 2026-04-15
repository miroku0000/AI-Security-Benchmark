FROM node:lts-bookworm-slim

ENV NODE_ENV=production \
    PORT=3000

WORKDIR /usr/src/app

COPY --chown=node:node package*.json ./

USER node

RUN npm install --omit=dev && npm cache clean --force

COPY --chown=node:node . .

EXPOSE 3000

CMD ["npm", "start"]