FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
COPY deploy/frontend-entrypoint.sh /usr/local/bin/frontend-entrypoint
RUN chmod 755 /usr/local/bin/frontend-entrypoint

EXPOSE 5173
CMD ["frontend-entrypoint"]
