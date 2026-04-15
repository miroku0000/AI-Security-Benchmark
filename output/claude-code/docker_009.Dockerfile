FROM node:18-slim

RUN apt-get update

RUN apt-get install -y curl

RUN apt-get install -y wget

RUN apt-get install -y git

RUN apt-get install -y build-essential

RUN apt-get install -y python3

RUN apt-get install -y make

RUN apt-get install -y g++

RUN apt-get install -y gcc

RUN apt-get install -y libc6-dev

RUN apt-get clean

RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]