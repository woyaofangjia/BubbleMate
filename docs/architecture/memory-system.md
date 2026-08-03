# 会话记忆管理

## 概述
记忆系统管理对话历史、用户偏好和实体级记忆存储，支持滑动窗口摘要压缩与指代消解。

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
    ├── 实体记忆（窗口无关）
    │   ├── 糖度 / 冰量 / 温度
    │   ├── 加料 / 杯型
    │   ├── 饮品名 / 价格
    │   ├── 订单号 / 位置
    │   └── 投诉原因 / 偏好饮品
    │
    ├── 对话窗口（滑动窗口）
    │   └── 窗口大小: 3 轮（成本-覆盖率最优平衡点）
    │
    └── 摘要压缩（超窗口自动触发）
```

## 会话存储

### Redis 模式 (优先)
```python
# 会话数据结构
session:{session_id}: {
    "history": [...],        # 对话历史（含压缩摘要）
    "preferences": {...},    # 用户偏好（持久化）
    "entities": {...},       # 实体记忆（窗口无关，永久保留）
    "summary": ""            # 历史摘要
}
```

### 内存降级模式
```python
# Redis 不可用时自动降级
self._store = {"sessions": {}}
```

## 双层记忆体系

### 第一层：实体记忆（窗口无关）
实体提取后永久存储，不受对话窗口大小限制。支持以下实体类型：

| 实体 | 提取关键词 | 示例 |
|------|-----------|------|
| sugar (糖度) | 无糖/三分糖/五分糖/七分糖 | "三分糖" → `sugar: 三分糖` |
| ice (冰量) | 热饮/去冰/少冰/温热 | "去冰" → `ice: 去冰` |
| temperature (温度) | 热/温/去冰/少冰/多冰 | "热饮" → `temperature: 热` |
| topping (加料) | 珍珠/椰果/布丁/红豆/芋圆等 | "加珍珠" → `topping: 珍珠` |
| size (杯型) | 大杯/中杯/小杯 | "大杯" → `size: 大杯` |
| drink (饮品) | 菜单名称匹配 | "杨枝甘露" → `drink: 杨枝甘露` |
| price (价格) | 数字+元符号 | "18元" → `price: 18` |
| order_id (订单号) | ORD-数字 | "ORD-12345" → `order_id: 12345` |
| location (位置) | 地名关键词 | "光谷" → `location: 光谷` |
| complaint_reason | 太甜/太咸/变质等 | "太甜" → `complaint_reason: 太甜` |

### 第二层：对话窗口（滑动窗口）
窗口大小默认 3 轮，仅保留最近 N 轮对话历史，超出部分自动压缩为摘要。

### 实体提取实现
```python
def _extract_entities(text):
    entities = {}
    # 糖度
    for level, patterns in sugar_map.items():
        if any(p in text for p in patterns): entities["sugar"] = level
    # 冰量
    for level, patterns in ice_map.items():
        if any(p in text for p in patterns): entities["ice"] = level
    # 加料、温度、杯型等...
    return entities
```

## 指代消解

当用户使用"刚才"、"那个"、"之前"等指代词时，系统自动从实体记忆中检索：

```python
def _resolve_reference(text, entities, context_str):
    if "糖度" in text and entities.get("sugar"):
        return f"您之前选择的是{entities['sugar']}"
    if "加料" in text and entities.get("topping"):
        return f"您之前加的是{entities['topping']}"
    # ... 更多实体类型
```

## 滑动窗口

### 策略
- 默认保留最近 3 轮对话
- 超过窗口时触发摘要压缩
- 实体记忆不受窗口限制
- 窗口大小可通过 `config.py` 中的 `MAX_MEMORY_WINDOW` 配置

### 实现
```python
class MemoryStore:
    def __init__(self, window_size=3):
        self._window_size = window_size

    def _save_session(self, session_id, data):
        # 检查是否需要摘要压缩
        if len(data["history"]) > self._window_size:
            data["history"] = _compress_history(data["history"], self._window_size)
        # 实体提取（独立于窗口）
        new_entities = _extract_entities(user_msg)
        for k, v in new_entities.items():
            data["entities"][k] = v
```

## 上下文组装

### 获取上下文
```python
def get_context(memory_store, session_id):
    session = memory_store._get_session(session_id)
    # 组装: 偏好 + 实体记忆 + 历史摘要 + 最近对话
    parts = []
    if prefs: parts.append(f"偏好: {', '.join(prefs)}")
    if entities: parts.append(f"记忆实体: {', '.join(entities)}")
    for msg in history: parts.append(f"用户: {msg['user']}")
    return "\n".join(parts), entities
```

### 上下文结构
```
[偏好]
- 糖度: 三分糖
- 温度: 热

[记忆实体]
- 糖度: 三分糖, 饮品: 杨枝甘露, 价格: 18, 温度: 热

[最近对话]
用户: 我要一杯热饮
Agent: 好的，热饮
```

## 记忆窗口调优

### 成本-覆盖率分析（2026-08-03）

| 窗口大小 | 预估Tokens | 节省比例 | 实体记忆准确率 | 说明 |
|---------|-----------|---------|--------------|------|
| 1 轮 | 367 | 基准 | 100% | 首次运行含缓存预热 |
| 2 轮 | 91 | 75% | 100% | Token最低，但覆盖不足 |
| **3 轮** ⭐ | **119** | **67%** | **100%** | **最优平衡点** |
| 5 轮 | 168 | 54% | 100% | 比3轮多消耗41 tokens |
| 7 轮 | 212 | 42% | 100% | 线性增长，无额外收益 |
| 10 轮 | 265 | 28% | 100% | 2.2倍消耗，收益无差异 |

### 当前选择
- **窗口大小**: 3 轮（默认值，可配置）
- **配置**: `MAX_MEMORY_WINDOW = 3`（backend/core/config.py）
- **实体记忆**: 11 场景 × 5 窗口 = 55 用例，100% 通过
- **摘要阈值**: 超过窗口自动压缩
- **偏好**: 显式注入，不受窗口限制

### 选择3轮的理由
1. 实体记忆准确率在所有窗口下均为100%（实体提取后永久存储）
2. 3轮Token消耗仅为10轮的45%、1轮的32%
3. 3轮窗口可覆盖最近3轮对话的指代消解
4. 5轮以上Token增长线性（每增1轮约+20 tokens），但准确率无额外提升

## 清理策略

### 会话过期
- Redis TTL: 会话数据无自动过期
- 建议: 实现定期清理过期会话

### 缓存清理
- `clear_intent_cache()`: 清理意图缓存
- `clear_response_cache()`: 清理响应缓存
- 管理接口: `POST /api/admin/cache/clear`

## 测试验证

### 记忆召回测试
- 脚本: `scripts/test_memory_recall.py`
- 场景: 11个（糖度/冰量/订单号/位置/饮品偏好/投诉/价格/复合指代/加料/温度/杯型）
- 窗口: 1/3/5/7/10轮
- 结果: **55用例全部100%通过**

### CI集成
- 工作流: `.github/workflows/memory-recall-ci.yml`
- 触发: push/PR到main/develop、每日定时
- 产物: JUnit XML报告 + JSON结果报告
