# 会话记忆管理

## 概述
记忆系统管理对话历史、用户偏好和滑动窗口摘要压缩。

## 架构

```
用户会话
    │
    ▼
[MemoryStore]
    │
    ├── [Redis Storage]  ← 优先
    │   └── 降级到 [内存字典]
    │
    ├── 滑动窗口 (window_size=5)
    ├── 摘要压缩
    └── 偏好提取
```

## 会话存储

### Redis 模式 (优先)
```python
# 会话数据结构
session:{session_id}: {
    "messages": [...],      # 完整对话历史
    "preferences": {...},   # 提取的用户偏好
    "complaints": [...]     # 投诉记录
}
```

### 内存降级模式
```python
# Redis 不可用时自动降级
self._store = {"sessions": {}}
```

## 滑动窗口

### 策略
- 保留最近 5 轮对话
- 超过窗口时触发摘要压缩
- 摘要注入上下文

### 实现
```python
class MemoryStore:
    def __init__(self, window_size=5):
        self._window_size = window_size

    def _save_session(self, session_id, data):
        # 保存完整对话
        # 检查是否需要摘要压缩
        # 保留最近 N 轮 + 历史摘要
```

## 用户偏好提取

### 可提取偏好
- `sugar_level`: 糖度偏好（少糖/标准糖/无糖）
- `ice_level`: 冰量偏好（少冰/正常冰/去冰）
- `favorite_drinks`: 常点饮品
- `order_history`: 历史订单ID

### 提取逻辑
```python
def _extract_preferences(text, session_id):
    # 正则匹配糖度/冰量关键词
    # 匹配饮品名称
    # 保存到用户画像
```

## 上下文组装

### 获取上下文
```python
def get_context(memory_store, session_id):
    session = memory_store._get_session(session_id)
    # 组装: 历史摘要 + 最近对话 + 用户偏好
    return context_string
```

### 上下文结构
```
[用户偏好]
- 糖度: 少糖
- 常点: 杨枝甘露

[历史摘要]
用户点了杨枝甘露，要求少糖少冰...

[最近对话]
用户: 杨枝甘露少糖少冰
Agent: 好的，已为您下单...
```

## 记忆窗口调优

| 窗口大小 | 消息保留 | 优点 | 缺点 |
|---------|---------|------|------|
| 3轮 | 4条 | 延迟最低 | 上下文不足 |
| **5轮** | **6条** | **甜点区间** | - |
| 10轮 | 6条 | 覆盖完整场景 | 触发摘要，延迟增加 |

### 当前选择
- **窗口大小**: 5轮
- **摘要阈值**: 超过窗口自动压缩
- **偏好**: 显式注入，不受窗口限制

## 清理策略

### 会话过期
- Redis TTL: 会话数据无自动过期
- 建议: 实现定期清理过期会话

### 缓存清理
- `clear_intent_cache()`: 清理意图缓存
- `clear_response_cache()`: 清理响应缓存
- 管理接口: `POST /api/admin/cache/clear`
