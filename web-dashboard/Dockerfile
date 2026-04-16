# ── Stage 1: Build ─────────────────────────────────────────────
FROM node:18-alpine AS builder

WORKDIR /app

# Cài dependencies
COPY package*.json ./
RUN npm install

# Copy source và build
COPY . .
# Lưu ý: VITE_API_URL lúc này là rỗng để Dashboard dùng relative path '/api'
# Relative path sẽ được Nginx proxy sang backend:8000
RUN npm run build

# ── Stage 2: Runtime ───────────────────────────────────────────
FROM nginx:stable-alpine

# Copy file build từ stage builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy cấu hình Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
