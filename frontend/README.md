# BubbleMate Frontend

智能奶茶店客服Agent前端界面

## 技术栈

- **Next.js 14** - React框架（App Router）
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式系统
- **Vercel AI SDK** - 流式输出支持
- **D3.js** - 知识图谱可视化
- **SWR** - 数据请求

## 目录结构

```
frontend/
├── app/                # Next.js App Router
│   ├── page.tsx        # 主页面（聊天）
│   ├── layout.tsx      # 根布局
│   ├── globals.css     # 全局样式
│   ├── admin/          # 运营后台
│   ├── agent-dashboard/  # 客服工作台
│   ├── profile/        # 用户画像
│   ├── human-support/  # 人工支持
│   ├── landing/        # 落地页
│   └── api/            # API路由（代理后端）
│       ├── chat/       # 聊天接口
│       ├── tools/      # 工具列表
│       ├── menu/       # 菜单查询
│       ├── admin/      # 管理/客服接口
│       ├── user/       # 用户画像
│       ├── feedback/   # 反馈
│       ├── human-in-loop/  # 人工接管
│       └── voice-to-text/  # 语音转文字
├── components/         # React组件
│   ├── Header.tsx              # 头部导航
│   ├── NavBar.tsx              # 导航栏
│   ├── ChatInterface.tsx       # 聊天界面
│   ├── ThoughtChainPanel.tsx   # 思考链面板
│   ├── ToolVisualization.tsx   # 工具可视化
│   ├── KnowledgeGraphD3.tsx    # D3知识图谱
│   ├── KnowledgeGraphAggregated.tsx  # 聚合图谱
│   ├── VoiceRecorder.tsx       # 语音录入
│   ├── PasswordModal.tsx       # 密码弹窗
│   ├── LoadingSpinner.tsx      # 加载动画
│   └── DynamicImports.tsx      # 动态导入
├── context/
│   └── RoleContext.tsx  # 角色上下文
└── public/             # 静态资源
```

## 安装与运行

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3001

### 3. 构建生产版本

```bash
npm run build
npm start
```

## 核心功能

### 1. 聊天界面
- 实时对话
- 消息气泡样式
- 快捷提示按钮

### 2. 思考链展示
- 显示Agent推理过程
- 可视化思考步骤
- 调试辅助工具

### 3. 工具调用可视化
- 实时显示工具调用状态
- 工具执行结果展示
- 思考链展示

## 前后端联调

1. 启动后端服务：
```bash
python -m uvicorn backend.api.main:app --reload
```

2. 启动前端服务：
```bash
cd frontend
npm run dev
```

3. 访问 http://localhost:3001 测试完整功能

## API路由

| 路径 | 说明 | 对应后端 |
|------|------|----------|
| `/api/chat` | 聊天接口 | POST `/chat` |
| `/api/tools` | 工具列表 | GET `/tools` |
| `/api/menu` | 菜单查询 | GET `/menu` |
| `/api/feedback` | 提交反馈 | POST `/api/feedback` |
| `/api/voice-to-text` | 语音转文字 | POST `/api/voice-to-text` |
| `/api/user/profile` | 用户画像 | GET `/api/user/profile` |
| `/api/admin/stats` | 管理统计 | GET `/api/admin/stats` |
| `/api/admin/candidates` | 知识候选 | GET `/api/admin/candidates` |
| `/api/admin/knowledge` | 知识图谱 | GET `/api/admin/knowledge` |
| `/api/admin/context/{id}` | 会话上下文 | GET `/api/admin/context/{id}` |
| `/api/admin/takeover/{id}` | 人工接管 | POST `/api/admin/takeover/{id}` |
| `/api/admin/reply/{id}` | 客服回复 | POST `/api/admin/reply/{id}` |
| `/api/human-in-loop/pending` | 待接管列表 | GET `/api/human-in-loop/pending` |

## 注意事项

- 前端默认连接 `localhost:8000` 的后端
- 修改 `.env.local` 可调整后端地址
- 生产环境需要配置正确的 `BACKEND_URL`