"""
SalesAgent Frontend Dockerfile
- 多阶段构建：Node 22 build → Nginx serve
- 输出静态资源到 /usr/share/nginx/html
- 配合 docker-compose 用 nginx 反代 /api 到后端
"""
# 阶段 1：构建
FROM node:22-alpine AS builder
WORKDIR /app

# 国内镜像加速
RUN npm config set registry https://registry.npmmirror.com

COPY package*.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# Vite 读 .env.production
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# 阶段 2：Nginx
FROM nginx:1.27-alpine

# 拷入构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 自定义 nginx 配置（让 /api 反代到 backend 容器）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q -O- http://localhost/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
