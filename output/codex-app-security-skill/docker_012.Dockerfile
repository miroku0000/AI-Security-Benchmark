FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build \
    && if [ -d build ]; then mv build /tmp/app-build; \
    elif [ -d dist ]; then mv dist /tmp/app-build; \
    else echo "Expected npm run build to produce either ./build or ./dist" >&2; exit 1; \
    fi

FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY --from=build /tmp/app-build/ /usr/share/nginx/html/

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]