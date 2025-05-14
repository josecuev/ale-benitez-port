# Stage 1: Build con pnpm + Vite
FROM node:18-alpine AS builder
WORKDIR /app

# Habilita corepack + pnpm
RUN corepack enable \
  && corepack prepare pnpm@latest --activate

# Copia definición de deps
COPY ab-frontend/package.json ab-frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copia todo el frontend y ejecuta SOLO vite build
COPY ab-frontend/. ./
RUN pnpm exec vite build

# Stage 2: Nginx sirve la carpeta dist
FROM nginx:stable-alpine
LABEL maintainer="Jose Cuevas <tu-email@ejemplo.com>"

# Tu configuración de nginx
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Archivos estáticos compilados
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
