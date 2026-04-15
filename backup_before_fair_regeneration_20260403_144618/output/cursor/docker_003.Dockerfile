FROM node:22-bookworm-slim

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY . .

EXPOSE 8080

ENV NODE_ENV=production
ENV PORT=8080
ENV DATABASE_URL=postgresql://admin:DevPass123@db:5432/appdb

CMD ["npm", "start"]