@echo off
REM BubbleMate Windows启动脚本

echo ==========================================
echo BubbleMate 智能奶茶店客服Agent
echo ==========================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装Python
    exit /b 1
)

REM 安装后端依赖
echo 检查后端依赖...
python -m pip install fastapi uvicorn pydantic >nul 2>&1

REM 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装Node.js
    echo 请访问 https://nodejs.org 安装Node.js
    exit /b 1
)

REM 安装前端依赖
if not exist "frontend\node_modules" (
    echo 安装前端依赖...
    cd frontend
    npm install
    cd ..
)

echo.
echo ==========================================
echo 启动说明:
echo   1. 后端: cd backend && python -m uvicorn backend.api.main:app --reload
echo   2. 前端: cd frontend && npm run dev
echo ==========================================
echo.
echo 或运行以下命令同时启动:
echo   start cmd /k "cd backend && python -m uvicorn backend.api.main:app --reload"
echo   start cmd /k "cd frontend && npm run dev"
echo.

pause