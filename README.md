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
│   │   ├── intent_recognizer_v2.py  # 意图识别（规则+关键词+LLM兜底）
│   │   ├── react_agent_v2.py        # ReAct Agent核心循环
│   │   ├── memory_manager_v2.py     # 滑动窗口记忆管理 + 用户偏好提取
│   │   ├── tool_router.py           # 意图→工具路由 + 参数提取
│   │   ├── keywords.py              # 统一关键词定义（共享配置）
│   │   ├── human_in_loop.py         # 人工介入机制（置信度计算）
│   │   └── __init__.py
│   ├── tools/
│   │   ├── bubble_tools.py          # MCP工具实现（5个工具）
│   │   └── __init__.py
│   ├── api/
│   │   └── main.py                  # FastAPI入口
│   ├── core/
│   │   ├── config.py                # 配置管理
│   │   └── zhipu_client.py          # 智谱AI客户端
│   └── requirements.txt
│
├── frontend/                   # 前端界面
│   ├── app/
│   │   ├── page.tsx                # 主页面
│   │   ├── layout.tsx              # 根布局
│   │   ├── api/                    # API路由代理
│   │   ├── experiment-report/      # 实验报告页面
│   │   ├── eval-report/            # 评估报告页面
│   │   └── human-support/          # 人工客服页面
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
│   ├── qa_pairs.json               # 问答对(21条)
│   ├── menu_data.json              # 菜单数据
│   ├── orders_mock.json            # 订单模拟数据
│   ├── test_cases.json             # 测试用例(18条)
│   └── eval_report.json            # 评估报告
│
├── scripts/                    # 工具脚本
│   ├── crawler.py                  # 高德地图POI爬虫
│   ├── crawler_mall.py             # 商场爬虫
│   ├── merge_data.py               # 数据合并
│   ├── analyze_reviews.py          # 差评分析
│   ├── test_agent.py               # Agent测试
│   └── bubble_eval_runner.py       # 评估脚本
│
├── docs/                       # 文档
│   ├── 30天执行计划.md
│   ├── 技术架构设计.md
│   └── KEY_DESIGN_DECISIONS.md
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

## 实验结果

### 📊 核心指标

| 指标 | 结果 | 说明 |
|------|------|------|
| 意图识别准确率 | **37.0%** | 200条测试集（含40条对抗样本） |
| 分层评测 | Easy 50% / Medium 33% / Hard 10% | 三层难度分布 |
| 对抗样本通过率 | **10.0%** | 40条（讽刺、指代、模糊表达） |
| 工具调用成功率 | **100.0%** | 9个异常场景全部正确处理 |
| 记忆窗口最优配置 | **5轮** | 平衡记忆保留与响应速度 |
| Baseline（纯LLM） | **45.0%** | Zero-shot直接回复 |

### 📈 可视化实验报告
访问地址：`http://localhost:3001/experiment-report`

### 🔬 实验1：意图识别准确率

- 测试集：200条分层测试用例（Easy 100 + Medium 60 + Hard 40）
- 准确率：37.0%（74/200）
- 覆盖意图：15+种（complaint_taste, complaint_quantity, query_recommend, query_order等）

### 🔬 实验2：对比基线（纯LLM vs 完整Agent）

- **Baseline**: 纯LLM Zero-shot → 45.0%准确率
- **完整Agent**: 规则+关键词+工具调用 → 37.0%准确率（含Hard样本）
- **Easy+Medium**: 45%（与LLM相当）
- **说明**: 当前Agent在Hard对抗样本上表现差，但在确定性任务上与LLM相当

### 🔬 实验3：工具调用异常处理

9个异常场景全部正确处理：
- 参数缺失 → 自动反问
- 正常调用 → 返回结果
- 业务错误 → 引导用户

### 🔬 实验4：记忆窗口对比

| 窗口大小 | 消息数 | 有摘要 | 记住实体 | 首Token延迟影响 |
|---------|--------|--------|----------|----------------|
| 3轮 | 4 | ✓ | ✓ | 无明显影响 |
| **5轮** | **6** | **✓** | **✓** | **无明显影响（推荐）** |
| 10轮 | 6 | ✗ | ✓ | 延迟增加约200ms |

**结论**: 5轮为最优选择（覆盖典型场景+触发摘要压缩）

### 🔬 实验5：分层评测（Easy/Medium/Hard）

| 难度 | 样本数 | 准确率 | 特征 |
|------|--------|--------|------|
| 😊 Easy | 100（50%） | 50.0% | 直接表达、单一意图 |
| 😐 Medium | 60（30%） | 33.3% | 复合意图、上下文依赖 |
| 😰 Hard | 40（20%） | 10.0% | 对抗样本、讽刺、指代不明 |

### 🔬 实验6：对抗样本分析

| 对抗类型 | 通过数/总数 | 通过率 |
|---------|-----------|--------|
| 讽刺语气（"呵呵"） | 0/8 | 0% |
| 指代不明（"那个"） | 0/12 | 0% |
| 历史对比 | 4/4 | 100% |
| 模糊表达 | 0/4 | 0% |

**核心短板**: 讽刺语气识别和指代消解是主要问题

### 🎯 Bad Case 根因分析

| 错误输入 | 预测 | 期望 | 根因 | 改进方向 |
|---------|------|------|------|----------|
| "呵呵，你们这服务绝了" | general | complaint_sarcasm | 讽刺语气未识别 | 增加"呵呵"、"绝了"关键词 |
| "那个" | general | unclear | 指代不明 | 增加指代消解逻辑 |
| "退款" | query_refund | complaint_refund | 意图边界模糊 | 优化退款意图分类 |
| "上次买的幽兰拿铁这次怎么没了" | query_order | query_menu | 上下文依赖 | 增加历史对比识别 |

### ⚠️ 实验局限性说明

> 本次实验受限于项目周期，测试集为200条对抗样本集。评测结果揭示：
> - **Easy样本（50%）**：规则匹配表现良好
> - **Hard样本（10%）**：对抗样本（讽刺、指代）是核心短板
> - **优化空间**：增加讽刺识别和指代消解是下一步重点
>
> 完整评测需引入**人工盲测（A/B Test）**和**在线反馈闭环（用户纠偏率）**进行联合评估。

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
python backend/agent/intent_recognizer_v2.py

# 工具测试
python backend/tools/bubble_tools.py

# 记忆管理测试
python backend/agent/memory_manager_v2.py

# 评估测试（18条测试用例）
python scripts/bubble_eval_runner.py

# 分层评测（200条测试集）
python scripts/stratified_eval.py

# 纯LLM Baseline测试
python scripts/llm_baseline_test.py

# 生成训练数据（200条）
python scripts/generate_training_data.py

# 生成测试数据（200条）
python scripts/generate_test_data.py
```