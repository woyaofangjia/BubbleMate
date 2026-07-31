# BubbleMate 文档索引

## Read First

- **[CodeAgent.md](../CodeAgent.md)** - 架构概览 + 代码规范（必读）

## Read Based on Task

### 核心架构
- **[intent-recognition.md](architecture/intent-recognition.md)** - 意图识别系统（修改意图规则时读）
- **[tool-system.md](architecture/tool-system.md)** - 工具调用系统（添加新工具时读）
- **[memory-system.md](architecture/memory-system.md)** - 会话记忆管理（调整记忆策略时读）
- **[knowledge-graph.md](architecture/knowledge-graph.md)** - 知识图谱系统（修改投诉处理逻辑时读）

### 开发参考
- **[api-and-db.md](development/api-and-db.md)** - API 端点 & 数据库结构（开发新功能时读）
- **[design-decisions.md](design-decisions.md)** - 关键设计决策与取舍（理解系统设计原因时读）

## 文档结构

```
docs/
├── README.md                          # 本文件（导航）
├── architecture/                      # 核心架构文档
│   ├── intent-recognition.md         # 意图识别
│   ├── tool-system.md                # 工具系统
│   ├── memory-system.md              # 记忆管理
│   └── knowledge-graph.md            # 知识图谱
└── development/                       # 开发参考文档
    ├── api-and-db.md                 # API & 数据库
    └── design-decisions.md            # 设计决策
```
