# BubbleMate

智能奶茶店客服Agent项目，展示大模型应用层的核心能力：意图识别、工具调用、会话记忆、用户画像、知识图谱运营。

## 项目结构

```
BubbleMate/
├── backend/                    # 后端服务
│   ├── api/
│   │   └── main.py             # FastAPI入口 + API端点
│   ├── core/
│   │   ├── config.py           # 配置管理
│   │   └── zhipu_client.py     # 智谱AI客户端
│   ├── storage/
│   │   ├── database.py         # SQLite数据库管理
│   │   └── memory_store.py     # 存储接口封装
│   ├── tools/
│   │   └── __init__.py
│   ├── bubble_agent.py         # Agent核心逻辑（单文件）
│   └── requirements.txt
│
├── frontend/                   # 前端界面（Next.js）
│   ├── app/
│   │   ├── page.tsx            # 主页面（聊天）
│   │   ├── profile/            # 用户画像
│   │   ├── admin/              # 运营后台
│   │   ├── agent-dashboard/    # 客服工作台
│   │   ├── eval-report/        # 评估报告
│   │   ├── experiment-report/  # 实验报告
│   │   ├── human-support/      # 人工客服
│   │   └── api/                # API路由代理
│   ├── components/
│   │   ├── ChatInterface.tsx   # 聊天界面
│   │   ├── ThoughtChainPanel.tsx  # 思考链展示
│   │   ├── ToolVisualization.tsx  # 工具可视化
│   │   └── Header.tsx
│   └── package.json
│
├── data/                       # 数据文件
│   ├── bubble_tea_all.json     # 门店信息
│   ├── orders_mock.json        # 订单模拟数据
│   ├── knowledge_graph.json    # 知识图谱
│   ├── menu_data.json          # 菜单数据
│   ├── test_cases.json         # 测试用例
│   └── eval_report.json        # 评估报告
│
├── scripts/                    # 工具脚本
│   ├── bubble_eval_runner.py   # 评估脚本
│   ├── stratified_eval.py      # 分层评测
│   ├── llm_baseline_test.py    # LLM基线测试
│   └── generate_test_data.py   # 生成测试数据
│
├── docs/                       # 文档
│   ├── 30天执行计划.md
│   ├── 技术架构设计.md
│   └── KEY_DESIGN_DECISIONS.md
│
├── start.bat                   # Windows启动脚本
├── start.sh                    # Linux/Mac启动脚本
└── docker-compose.yml          # Docker部署
```

## 核心功能

### 🤖 智能客服
- 意图识别：规则+关键词+LLM兜底（18+种意图，测试集准确率100%）
- 工具调用：订单查询、门店查询、菜单查询、投诉处理、优惠查询
- 思考链可视化：实时展示Agent推理过程
- 会话记忆：滑动窗口（5轮）+ 自动摘要压缩

### 👤 用户画像
- 口味偏好自动提取（糖度、冰量）
- 订单历史展示
- 投诉记录追踪

### 📊 运营后台
- 投诉统计：按类型分布、今日新增、解决率
- 知识图谱管理：审核知识点、删除无效知识
- 全局数据监控

### 🛠️ 客服工作台
- 会话上下文查看
- 人工接管会话
- 用户画像快速定位

## 三个角色分离

| 角色 | 页面 | 功能 |
|------|------|------|
| 普通用户 | `/` + `/profile` | 发消息、看自己的偏好和订单 |
| 运营人员 | `/admin` | 查看全局统计、审核知识图谱 |
| 客服人员 | `/agent-dashboard` | 查看会话、人工接管、发送回复 |

## 技术栈

- **后端**: Python 3.10+, FastAPI, LangChain, SQLite
- **前端**: Next.js 14+, React, Tailwind CSS
- **LLM**: 智谱AI (GLM-4)

## 运行方式

```bash
# 后端（端口8000）
cd backend
pip install -r requirements.txt
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 前端（端口3001）
cd frontend
npm install
npm run dev
```

## API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 聊天对话 |
| `/intent/{text}` | GET | 意图识别 |
| `/shops` | GET | 门店列表 |
| `/menu` | GET | 菜单查询 |
| `/api/user/profile` | GET | 用户画像 |
| `/api/admin/complaints` | GET | 所有投诉 |
| `/api/admin/stats` | GET | 统计数据 |
| `/api/admin/knowledge` | GET | 知识图谱 |
| `/api/admin/context/{session_id}` | GET | 会话上下文 |

## 关键设计决策

1. **意图识别**: 规则优先→关键词阈值→LLM兜底，平衡准确率和成本
2. **记忆管理**: 5轮滑动窗口最优，超过自动摘要压缩
3. **数据持久化**: SQLite本地存储，重启不丢数据
4. **用户区分**: session_id映射到稳定user_id，支持多用户数据隔离

## 实验结果

| 指标 | 测试集内 | 泛化验证 |
|------|---------|---------|
| 意图识别准确率 | 100.0% | 96.7% |
| 工具调用成功率 | 100.0% | - |
| 对抗样本通过率 | 100.0% | - |

## 访问地址

- 聊天界面: http://localhost:3001
- 用户画像: http://localhost:3001/profile
- 运营后台: http://localhost:3001/admin（密码: bubble2026）
- 客服工作台: http://localhost:3001/agent-dashboard（密码: bubble2026）