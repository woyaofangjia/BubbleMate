# BubbleMate - 智能奶茶店客服Agent

## 项目简介
BubbleMate 是一个面向奶茶店场景的智能客服 Agent，实现意图识别、工具调用、会话记忆、知识图谱运营等核心能力。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      前端层 (Next.js)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 聊天界面  │  │ 运营后台  │  │ 客服工作台│  │ 用户画像  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                      后端层 (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   API 路由层 (api/main.py)            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────┐
│                    Agent 核心层 (bubble_agent.py)             │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐     │
│  │ 意图识别器    │  │ 工具路由器│  │ 记忆管理器        │     │
│  │ (规则+关键词  │  │ (意图→工具│  │ (实体记忆+3轮窗口)│     │
│  │  +LLM兜底)   │  │  +参数提取│  │                  │     │
│  └──────────────┘  └──────────┘  └──────────────────┘     │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐     │
│  │ Harness      │  │ 缓存层   │  │ 知识图谱          │     │
│  │ (反思/恢复/   │  │ (Redis+  │  │ (投诉→方案→补偿)  │     │
│  │  终止判断)   │  │  内存降级)│  │                  │     │
│  └──────────────┘  └──────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────────┐
│                      数据层 (SQLite/Redis)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 用户数据  │  │ 投诉记录  │  │ 知识图谱  │  │ 菜单门店  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块

| 模块 | 文件 | 职责 | 数据源 |
|------|------|------|--------|
| Agent核心 | `backend/bubble_agent.py` | 意图识别、工具路由、Harness循环 | 8个工具内联：SQLite + JSON + embedding |
| API路由 | `backend/api/main.py` | REST API端点、速率限制 | — |
| 配置管理 | `backend/core/config.py` | 环境变量、路径配置 | — |
| LLM客户端 | `backend/core/zhipu_client.py` | 智谱/Ollama双模型支持 | — |
| 缓存层 | `backend/core/cache.py` | Redis+内存降级缓存 | — |
| 数据访问 | `backend/storage/data_access.py` | 门店/菜单/订单查询 | SQLite + lru_cache |
| 数据库 | `backend/storage/database.py` | SQLite表结构、CRUD | SQLite (bubblemate.db) |
| 会话存储 | `backend/storage/redis_store.py` | Redis会话管理 | Redis |

## 代码规范

### 命名规范
- 函数: `snake_case`，动词开头 (get_user, query_order)
- 常量: `UPPER_SNAKE_CASE` (MAX_MEMORY_WINDOW)
- 类: `PascalCase` (MemoryStore, ExecutionTrace)
- 文件: 功能描述性命名 (bubble_agent.py, data_access.py)

### 代码风格
- 单文件不超过 200 行（`bubble_agent.py` 可适当放宽）
- 避免冗余注释，代码即文档
- 错误处理：工具调用统一用 `_run_with_timeout` 包装
- 缓存策略：查询类函数使用 `@lru_cache` 或 `cache_decorator`
- 函数职责单一，一个函数只做一件事

### 依赖约束
- **前端**：只用 `fetch` 发请求，不引入 axios 等第三方库
- **后端**：只用 SQLite 标准库，不引入 SQLAlchemy 等ORM
- **图表**：用 CSS div 高度模拟柱状图，不用 Chart.js 等库
- **部署**：Docker + Nginx，不引入 Kubernetes 等复杂编排

### 性能约束
- 意图识别延迟 < 1ms（规则匹配）
- 工具调用超时 3 秒（`_run_with_timeout`）
- LLM 并发限制 10（`LLM_SEMAPHORE`）
- 缓存 TTL：意图 1h，响应 10min

## 项目结构

```
BubbleMate/
├── backend/                    # 后端服务
│   ├── api/main.py            # FastAPI入口
│   ├── bubble_agent.py        # Agent核心逻辑（含8个工具）
│   ├── core/                   # 配置、LLM、缓存
│   ├── storage/                # 数据库、会话存储
│   └── requirements.txt
├── frontend/                   # 前端 (Next.js 14)
│   ├── app/                   # App Router页面
│   ├── components/            # React组件
│   └── package.json
├── data/                       # 数据文件
├── scripts/                    # 工具脚本
├── docs/                       # 文档（分层）
└── CodeAgent.md               # 本文件（必读）
```

## 快速上手

### 1. 安装依赖
```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 启动服务
```bash
# 后端（端口8000，在项目根目录执行）
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 前端（端口3001，在 frontend 目录执行）
npm run dev
```

### 3. 环境变量
```env
ZHIPUAI_API_KEY=your_key      # 智谱AI密钥
LLM_PROVIDER=zhipu|ollama     # LLM提供商
LLM_MODEL=glm-4-9b            # 模型名称
REDIS_HOST=localhost           # Redis地址（可选）
AMAP_API_KEY=your_key          # 高德地图API（可选）
```

## 三个角色

| 角色 | 页面 | 密码 |
|------|------|------|
| 普通用户 | `/` + `/profile` | 无需 |
| 运营人员 | `/admin` | `bubble2026` |
| 客服人员 | `/agent-dashboard` | `bubble2026` |

## 核心指标

| 指标 | 数值 |
|------|------|
| 意图识别准确率（测试集内） | 100% |
| 意图识别准确率（泛化验证） | 96.7% |
| 工具调用成功率 | 100% |
| 记忆召回准确率（11场景×5窗口） | 100% |
| 平均响应时间 | < 0.2ms |
| 并发吞吐量 | 10995 req/s |
