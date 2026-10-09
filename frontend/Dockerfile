# syntax=docker/dockerfile:1
# -------------------------------------------------------------
# Stage 1: Build the Vite / React production bundle
# -------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests first to leverage Docker layer caching
COPY package.json package-lock.json* ./

# Install project dependencies
RUN npm install

# Copy application source code (excluding files defined in .dockerignore)
COPY . .

# Build-time environment arguments (configurable via docker-compose)
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_API_URL=http://backend:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_URL=${VITE_API_URL}

# Compile TypeScript and build production assets
RUN npm run build

# -------------------------------------------------------------
# Stage 2: Serve static assets via lightweight Nginx
# -------------------------------------------------------------
FROM nginx:alpine

# Remove default static files and configuration
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration (SPA routing and backend:8000 proxying)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled production bundle from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
