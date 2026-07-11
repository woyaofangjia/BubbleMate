#!/bin/bash

# BubbleMate Docker启动脚本

echo "========================================"
echo "  BubbleMate 智能奶茶店客服Agent"
echo "  启动服务..."
echo "========================================"

# 启动Redis（如果未运行）
if ! redis-cli ping > /dev/null 2>&1; then
    echo "正在启动Redis..."
    redis-server --daemonize yes
fi

# 启动后端服务
echo "正在启动后端服务 (端口: 8000)..."
cd /app/backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 8 &
BACKEND_PID=$!

# 等待后端启动
sleep 5

# 启动前端服务
echo "正在启动前端服务 (端口: 3000)..."
cd /app/frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "  服务启动完成!"
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8000"
echo "========================================"

# 等待进程
wait $BACKEND_PID $FRONTEND_PID