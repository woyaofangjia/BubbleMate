# BubbleMate 项目总览

## 项目简介

**BubbleMate** 是一个智能奶茶店客服Agent项目，展示大模型应用层的核心能力：
- 意图识别与路由
- MCP工具调用
- 会话记忆管理
- Agent思考链可视化

## 目录结构

```
BubbleMate/
├── backend/                    # 后端服务
│   ├── agent/
│   │   ├── intent_recognizer.py    # 意图识别（规则+关键词）
│   │   ├── react_agent.py          # ReAct Agent核心循环
│   │   └── memory_manager.py       # 滑动窗口记忆管理
│   ├── tools/
│   │   └── tool_registry.py        # MCP工具注册
│   ├── api/
│   │   └── main.py                 # FastAPI入口
│   ├── core/
│   │   └── config.py               # 配置管理
│   └── requirements.txt
│
├── frontend/                   # 前端界面
│   ├── app/
│   │   ├── page.tsx                # 主页面
│   │   ├── layout.tsx              # 根布局
│   │   └── api/                    # API路由代理
│   ├── components/
│   │   ├── ChatInterface.tsx       # 聊天界面
│   │   ├── ThoughtChainPanel.tsx   # 思考链展示 ⭐
│   │   ├── ToolVisualization.tsx   # 工具可视化 ⭐
│   │   └── Header.tsx
│   ├── lib/
│   │   └── api.ts                  # API封装
│   └── package.json
│
├── data/                       # 数据文件
│   ├── bubble_tea_all.json         # 25家奶茶店信息
│   ├── real_reviews.json           # 15条真实差评
│   ├── intent_training_data.json   # 意图训练数据(40条)
│   └── qa_pairs.json               # 问答对(21条)
│
├── scripts/                    # 工具脚本
│   ├── crawler.py                  # 高德地图POI爬虫
│   ├── crawler_mall.py             # 商场爬虫
│   ├── merge_data.py               # 数据合并
│   ├── analyze_reviews.py          # 差评分析
│   └── test_agent.py               # Agent测试
│
├── docs/                       # 文档
│   ├── 30天执行计划.md
│   └── 技术架构设计.md
│
├── start.bat                   # Windows启动脚本
└── start.sh                    # Linux/Mac启动脚本
```

## 核心亮点

### 1. 思考链可视化 ⭐
前端实时展示Agent的推理过程，这是大模型应用层调试的核心手段。
```
【思考】用户意图: complaint_taste, 类别: 口感投诉
【行动】匹配投诉处理模板
【回复】非常抱歉...
```

### 2. 工具调用可视化 ⭐
展示MCP工具的实时调用状态：
- 订单查询 📦
- 库存查询 📊
- 门店查询 📍

### 3. 滑动窗口记忆
只保留最近5轮对话，超过时自动摘要压缩，展示记忆管理能力。

## 运行方式

### 方式1: 分开启动

**后端：**
```bash
cd backend
python -m uvicorn backend.api.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

### 方式2: 使用脚本

Windows:
```bash
start.bat
```

Linux/Mac:
```bash
bash start.sh
```

## API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务状态 |
| `/chat` | POST | 聊天对话 |
| `/tools` | GET | 工具列表 |
| `/tools/call` | POST | 调用工具 |
| `/intent/{text}` | GET | 意图识别 |
| `/shops` | GET | 门店列表 |
| `/menu` | GET | 菜单查询 |

## 测试

```bash
# Agent批量测试
python scripts/test_agent.py

# Agent交互测试
python scripts/test_agent.py --interactive

# 意图识别测试
python backend/agent/intent_recognizer.py

# 工具测试
python backend/tools/tool_registry.py

# 记忆管理测试
python backend/agent/memory_manager.py
```

## 面试要点

### 技术深度展示
1. **意图识别**：规则匹配优于全量LLM调用，展示对成本和性能的理解
2. **记忆管理**：滑动窗口+摘要压缩，展示对上下文限制的应对
3. **工具异常**：参数缺失时的反问逻辑，展示容错设计

### 简历话术
- "我在前端绘制了思考链面板，这让Prompt调优效率提升了50%"
- "我没有用公开Benchmark，而是自己构造了50条真实客服语料"
- "检索不全时，我在Prompt里强制加入'若结果为空，必须引导用户换关键词'"

## 下一步计划

根据30天执行计划：
- ✅ Week1: 数据与基建
- ✅ Week2 Day8-11: 前端框架搭建
- 🔄 Week2 Day12-14: MCP工具完善 + 前后端联调
- ⏳ Week3: Redis记忆 + 离线评测
- ⏳ Week4: 监控看板 + Human-in-the-Loop