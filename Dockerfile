# BubbleMate - 智能奶茶店客服Agent
# 多阶段构建，优化镜像体积

# 阶段1: 后端构建
FROM python:3.11-slim as backend-builder

WORKDIR /app/backend

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 阶段2: 前端构建
FROM node:20-alpine as frontend-builder

WORKDIR /app/frontend

# 安装依赖
COPY frontend/package*.json ./
RUN npm ci --only=production

# 复制前端代码并构建
COPY frontend/ .
RUN npm run build

# 阶段3: 最终镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制后端
COPY --from=backend-builder /app/backend ./backend
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/package*.json ./frontend/

# 安装Node.js用于运行前端
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 安装前端生产依赖
RUN cd frontend && npm ci --only=production

# 复制数据和脚本
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY README.md .

# 复制启动脚本
COPY start-docker.sh /app/start.sh
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 3000 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令
CMD ["/app/start.sh"]