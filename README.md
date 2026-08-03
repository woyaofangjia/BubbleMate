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
│   │   ├── zhipu_client.py     # 智谱AI/Ollama客户端
│   │   └── cache.py            # Redis+内存降级缓存
│   ├── storage/
│   │   ├── database.py         # SQLite数据库管理
│   │   ├── data_access.py      # 门店/菜单/订单查询
│   │   ├── redis_store.py      # Redis会话管理
│   │   └── __init__.py         # 包初始化
│   ├── bubble_agent.py         # Agent核心逻辑（单文件，含8个工具）
│   └── requirements.txt
│
├── frontend/                   # 前端界面（Next.js 14）
│   ├── app/
│   │   ├── page.tsx            # 主页面（聊天）
│   │   ├── profile/            # 用户画像
│   │   ├── admin/              # 运营后台
│   │   ├── agent-dashboard/    # 客服工作台
│   │   ├── human-support/      # 人工客服
│   │   ├── landing/            # 落地页
│   │   └── api/                # API路由代理
│   ├── components/             # React组件（11个）
│   ├── context/                # RoleContext
│   └── package.json
│
├── data/                       # 数据文件
│   ├── bubble_tea_all.json     # 门店信息
│   ├── orders_mock.json        # 订单种子数据（DB初始化用，由 migrate_data.py 导入）
│   ├── knowledge_graph.json    # 知识图谱
│   ├── menu_data.json          # 菜单数据
│   ├── menu_vectors.json       # 菜单向量缓存（语义检索，由 gen_menu_vectors.py 生成）
│   ├── promotions.json         # 优惠活动
│   └── eval_dataset.json       # 评测数据集
│
├── scripts/                    # 工具脚本
│   ├── run_comprehensive_eval.py    # 综合评估
│   ├── run_pure_llm_baseline.py     # LLM基线测试
│   ├── run_memory_window_experiment.py  # 记忆窗口实验
│   ├── run_token_consumption_test.py # Token消耗测试
│   ├── api_load_test.py        # API压测
│   ├── generate_test_data.py   # 生成测试数据
│   ├── crawler_mall.py         # 数据爬取
│   ├── gen_menu_vectors.py     # 预生成菜单向量（语义检索）
│   └── token_cost_analysis.py  # 成本分析
│
├── docs/                       # 文档（分层）
│   ├── README.md               # 文档导航
│   ├── design-decisions.md     # 关键设计决策
│   ├── architecture/           # 核心架构文档
│   └── development/            # 开发参考文档
│
├── reports/                    # 实验与评测报告
├── CodeAgent.md                # 架构概览 + 代码规范（必读）
├── Dockerfile + docker-compose.yml  # Docker部署
├── nginx.conf + nginx-lb.conf  # Nginx配置
├── start.bat / start.sh        # 启动脚本
└── README.md                   # 本文件
```

## 核心功能

### 🤖 智能客服
- 意图识别：规则+关键词+LLM兜底（18+种意图，测试集准确率100%）
- 工具调用：8个工具——菜单查询、门店查询、订单查询、历史订单查询、投诉处理、优惠查询、加料定制、智能推荐
- 流式输出：SSE 逐事件推送（思考→工具调用→回复），前端实时展示进度
- 语义推荐：embedding 向量匹配替代关键词，支持"清爽的""便宜的"等模糊需求
- 思考链可视化：实时展示Agent推理过程
- 会话记忆：实体级记忆（10类实体，窗口无关）+ 3轮滑动窗口摘要压缩

### 👤 用户画像
- 口味偏好自动提取（糖度、冰量）
- 订单历史展示
- 投诉记录追踪

### 📊 运营后台
- 投诉统计：按类型分布、今日新增、解决率
- 知识图谱管理：审核知识点、删除无效知识
- 负反馈分析：按意图聚合 Top 失败意图 + 待分析样本，驱动规则/Prompt 优化
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

- **后端**: Python 3.10+, FastAPI, 原生 Agent（自研框架）, SQLite, 智谱 embedding-3（语义检索）
- **前端**: Next.js 14+, React, Tailwind CSS
- **LLM**: 智谱AI (GLM-4)

## 运行方式

```bash
# 后端（端口8000，在项目根目录执行）
pip install -r backend/requirements.txt
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
2. **记忆管理**: 3轮滑动窗口+实体提取，成本-覆盖率最优平衡点
3. **数据持久化**: SQLite本地存储，重启不丢数据
4. **用户区分**: session_id映射到稳定user_id，支持多用户数据隔离

## 实验结果

| 指标 | 测试集内 | 泛化验证 |
|------|---------|---------|
| 意图识别准确率 | 100.0% | 96.7% |
| 工具调用成功率 | 100.0% | - |
| 对抗样本通过率 | 100.0% | - |
| 记忆召回准确率 | 100.0% | - |

## 记忆召回测试

系统提供专门的记忆召回测试脚本，验证Agent在不同窗口大小下的记忆能力：

```bash
python scripts/test_memory_recall.py --ci --min-accuracy 100.0
```

测试结果（11场景 × 5窗口 = 55用例全部通过）：

| 窗口 | 糖度 | 冰量 | 订单号 | 位置 | 饮品偏好 | 投诉 | 价格 | 复合指代 | 加料 | 温度 | 杯型 |
|------|------|------|--------|------|---------|------|------|---------|------|------|------|
| 1轮 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3轮 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 5轮 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7轮 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 10轮 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## 访问地址

- 聊天界面: http://localhost:3001
- 用户画像: http://localhost:3001/profile
- 运营后台: http://localhost:3001/admin（密码: bubble2026）
- 客服工作台: http://localhost:3001/agent-dashboard（密码: bubble2026）