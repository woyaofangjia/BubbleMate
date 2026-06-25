# BubbleMate Frontend

智能奶茶店客服Agent前端界面

## 技术栈

- **Next.js 14** - React框架（App Router）
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式系统
- **Vercel AI SDK** - 流式输出支持

## 目录结构

```
frontend/
├── app/                # Next.js App Router
│   ├── page.tsx        # 主页面
│   ├── layout.tsx      # 根布局
│   ├── globals.css     # 全局样式
│   └── api/            # API路由（代理后端）
│       ├── chat/
│       ├── tools/
│       └── menu/
├── components/         # React组件
│   ├── Header.tsx      # 头部导航
│   ├── ChatInterface.tsx  # 聊天界面
│   ├── ThoughtChainPanel.tsx  # 思考链面板
│   └── ToolVisualization.tsx  # 工具可视化
├── lib/
│   └── api.ts          # API调用封装
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

访问 http://localhost:3000

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
- MCP协议演示

## 前后端联调

1. 启动后端服务：
```bash
cd backend
python -m uvicorn backend.api.main:app --reload
```

2. 启动前端服务：
```bash
cd frontend
npm run dev
```

3. 访问 http://localhost:3000 测试完整功能

## API路由

| 路径 | 说明 | 对应后端 |
|------|------|----------|
| `/api/chat` | 聊天接口 | POST `/chat` |
| `/api/tools` | 工具列表 | GET `/tools` |
| `/api/menu` | 菜单查询 | GET `/menu` |

## 注意事项

- 前端默认连接 `localhost:8000` 的后端
- 修改 `.env.local` 可调整后端地址
- 生产环境需要配置正确的 `BACKEND_URL`