Creating the Dockerfile now with a cache-friendly npm install flow and the expected port exposure.

The workspace blocked the direct patch, so I’m checking write access and then I’ll finish with the Dockerfile content either in-repo or directly here.

FROM node:20-alpine

WORKDIR /usr/src/app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]