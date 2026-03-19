FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json package-lock.json ./
COPY apps/frontend/package.json ./apps/frontend/package.json
COPY apps/remotion_renderer/package.json ./apps/remotion_renderer/package.json

RUN npm ci

COPY apps/frontend ./apps/frontend

RUN npm run build --workspace @geek-movie-forge/frontend

FROM nginx:1.29-alpine

COPY infra/docker/nginx/frontend.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/frontend/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
