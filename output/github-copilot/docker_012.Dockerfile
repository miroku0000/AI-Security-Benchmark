I found there isn't an existing React app or Dockerfile in the repo, so I'm creating a straightforward generic Dockerfile at the repo root that builds a typical React app and serves the built `build/` directory.

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install && npm install -g serve

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]