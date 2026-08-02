# API 端点与数据库结构

## API 端点

### 公开接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/chat` | 聊天对话（同步，一次性返回） |
| POST | `/chat/stream` | 聊天对话（SSE 流式，逐事件推送） |
| GET | `/intent/{text}` | 意图识别测试 |
| GET | `/tools` | 获取工具列表 |
| GET | `/menu` | 菜单查询 |
| GET | `/shops` | 门店列表 |
| GET | `/health` | 健康检查 |
| DELETE | `/session/{session_id}` | 清除会话 |

### 用户相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/user/profile?session_id=` | 用户画像 |
| POST | `/api/feedback` | 提交反馈（含 user_query/agent_response/intent） |

### 管理接口（需登录）

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/admin/login` | 管理员登录 |
| GET | `/api/admin/stats` | 统计数据 |
| GET | `/api/admin/complaints` | 投诉列表 |
| POST | `/api/admin/complaints/resolve/{id}` | 解决投诉 |
| GET | `/api/admin/candidates` | 知识候选 |
| POST | `/api/admin/candidates/{id}/approve` | 批准候选 |
| POST | `/api/admin/candidates/{id}/reject` | 拒绝候选 |
| GET | `/api/admin/knowledge` | 知识图谱 |
| POST | `/api/admin/knowledge` | 添加知识 |
| POST | `/api/admin/knowledge/review` | 审核知识 |
| DELETE | `/api/admin/knowledge/{id}` | 删除知识 |
| POST | `/api/admin/cache/clear` | 清除缓存 |
| GET | `/api/cache/stats` | 缓存统计 |
| GET | `/api/admin/feedback-analysis` | 负反馈分析（按意图聚合 Top 失败） |
| GET | `/api/admin/eval-report` | 获取评测报告 |
| POST | `/api/admin/run-eval` | 触发评测 |

### 客服接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/admin/context/{session_id}` | 会话上下文 |
| POST | `/api/admin/takeover/{session_id}` | 人工接管 |
| POST | `/api/admin/reply/{session_id}` | 发送回复 |
| POST | `/api/admin/release/{session_id}` | 释放会话 |

## 请求/响应格式

### 聊天请求
```json
POST /chat
{
    "message": "我想查一下订单",
    "session_id": "user_abc123"
}
```

### 聊天响应
```json
{
    "response": "请您提供订单号，以便我为您查询。",
    "intent": {
        "name": "query_order",
        "confidence": 0.85,
        "category": "订单查询"
    },
    "session_id": "user_abc123"
}
```

### 通用响应结构
```json
{
    "success": true/false,
    "data": [...],
    "error": "错误信息（如有）",
    "count": 5
}
```

## 数据库表结构

### users - 用户表
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    preferences TEXT DEFAULT '{}',
    complaint_history TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### sessions - 会话表
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### complaints - 投诉记录表
```sql
CREATE TABLE complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    complaint_type TEXT,
    description TEXT,
    status TEXT DEFAULT '待处理',
    knowledge_id INTEGER,
    candidate_id INTEGER,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### feedback - 用户反馈表
```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    message_id TEXT,
    feedback_type TEXT,      -- 'positive' | 'negative'
    user_query TEXT,         -- 触发回复的用户原始消息（负反馈根因分析）
    agent_response TEXT,     -- 被反馈的 Agent 回复内容
    intent TEXT,             -- 该次对话的意图名（按意图聚合失败率）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### knowledge_graph - 知识图谱
```sql
CREATE TABLE knowledge_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT,
    node_type TEXT,
    content TEXT,
    parent_id INTEGER,
    level INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### knowledge_candidates - 知识候选
```sql
CREATE TABLE knowledge_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER,
    complaint_type TEXT,
    proposed_solution TEXT,
    proposed_compensation TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### shops - 门店表
```sql
CREATE TABLE shops (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    location TEXT,
    tel TEXT,
    rating TEXT,
    cost TEXT,
    opentime TEXT,
    business_area TEXT,
    status TEXT DEFAULT 'active'
);
```

### menu_items - 菜单表
```sql
CREATE TABLE menu_items (
    id TEXT PRIMARY KEY,
    shop_id TEXT REFERENCES shops(id),
    name TEXT NOT NULL,
    category TEXT,
    price REAL,
    available BOOLEAN DEFAULT 1,
    description TEXT,
    sales INTEGER DEFAULT 0
);
```

### orders - 订单表
```sql
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    shop_id TEXT REFERENCES shops(id),
    items TEXT,
    total REAL,
    status TEXT DEFAULT 'pending',
    address TEXT,
    create_time TEXT,
    delivery_time TEXT
);
```

## 数据库初始化

启动时自动创建：
```python
# backend/api/main.py
init_db()  # 自动创建所有表和索引
```

## 速率限制

| 限制 | 窗口 | 阈值 |
|------|------|------|
| IP 频率 | 1秒 | 5000 次 |
| 会话频率 | 1秒 | 1000 次 |

## 认证

### 管理员密码
- 密码: `bubble2026`
- 配置: `ADMIN_KEY = "bubble2026"` (backend/api/main.py)
