#!/bin/bash

# BubbleMate 启动脚本

echo "=========================================="
echo "BubbleMate 智能奶茶店客服Agent"
echo "=========================================="

# 检查Python
if ! command -v python &> /dev/null; then
    echo "错误: 未安装Python"
    exit 1
fi

# 检查pip依赖
echo "检查后端依赖..."
pip install fastapi uvicorn pydantic 2>/dev/null || python -m pip install fastapi uvicorn pydantic

# 检查前端依赖
if [ -d "frontend/node_modules" ]; then
    echo "前端依赖已安装"
else
    echo "安装前端依赖..."
    cd frontend && npm install && cd ..
fi

# 启动后端
echo "启动后端服务..."
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 8 &

# 启动前端
echo "启动前端服务..."
cd frontend && npm run dev &

echo ""
echo "=========================================="
echo "服务已启动:"
echo "  - 前端: http://localhost:3000"
echo "  - 后端: http://localhost:8000"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止服务"

wait