# 意图识别系统

## 概述
意图识别是 BubbleMate Agent 的第一环节，采用 **规则匹配 → 关键词匹配 → LLM兜底** 的三级降级策略。

## 识别流程

```
用户输入
    │
    ▼
[1] 规则匹配 (_rule_match)
    │ 匹配成功
    ▼
返回结果 (高置信度)
    │ 未匹配
    ▼
[2] 复合意图检测 (_composite_match)
    │ 命中复合模板
    ▼
返回具体合并意图（如 complaint_taste_price）
    │ 未检测到
    ▼
[3] 关键词匹配 (_multi_keyword_match)
    │ 得分 >= 阈值
    ▼
返回结果 (中置信度)
    │ 得分 < 阈值
    ▼
[4] LLM兜底 (_get_llm_result)
    │ LLM可用
    ▼
返回结果 (低置信度 0.6)
    │ LLM不可用
    ▼
返回 general (置信度 0.2)
```

## 意图类型

### 投诉类 (complaint_*)
- `complaint_taste` - 口味投诉（太甜/太酸/难喝）
- `complaint_quantity` - 份量投诉（料少/冰块多）
- `complaint_service` - 服务投诉（态度差/电话不通）
- `complaint_delivery` - 配送投诉（超时/洒了）
- `complaint_price` - 价格投诉（太贵/不值）
- `complaint_refund` - 退款请求
- `complaint_sarcasm` - 讽刺语气（呵呵/绝了）
- `complaint_accessory` - 配件投诉（吸管错）
- `complaint_vague` - 指代不明（那个/你们懂的）
- `complaint_compare_history` - 历史对比（跟上次不一样）
- `complaint_taste_service` - 口味 + 服务（复合）
- `complaint_taste_price` - 口味 + 价格（复合）
- `complaint_quantity_taste` - 份量 + 口味（复合）

### 查询类 (query_*)
- `query_menu` - 菜单查询 → 工具 `query_menu`
- `query_order` - 订单查询 → 工具 `query_order`
- `query_location` - 门店查询 → 工具 `query_stores`
- `query_store` - 门店查询(别名) → 工具 `query_stores`
- `query_hours` - 营业时间查询 → 直接响应(硬编码)
- `query_price` - 价格查询 → 直接响应(硬编码)
- `query_promotion` - 优惠活动查询 → 工具 `query_promotions`
- `query_customize` - 加料定制 → 工具 `query_customize`
- `query_history` - 历史订单查询 → 工具 `query_history`(与 query_order 共用 SQLite 数据源)
- `query_refund` - 退款查询 → 工具 `query_order`
- `query_recommend` - 推荐咨询 → 工具 `query_recommend`
- `query_recommend_price` - 推荐 + 价格（复合）

### 其他
- `place_order` - 下单
- `place_order_promotion` - 下单 + 优惠（复合）
- `general` - 通用（寒暄/告别）
- `unclear` - 不明确

## 复合意图处理

复合模板命中后**不再返回孤儿 `composite`**，而是直接映射到有答案的合并意图，
保证后续有工具路由或模板答案。

| 文本模板 | 合并意图 | 子意图 |
|---|---|---|
| 太甜…还/又…贵 | `complaint_taste_price` | 口味 + 价格 |
| 料少…还/又…甜 | `complaint_quantity_taste` | 份量 + 口味 |
| 好喝吗…多少钱/价格 | `query_recommend_price` | 推荐 + 价格 |
| 下单/点一杯…优惠/活动 | `place_order_promotion` | 下单 + 优惠 |

- 回复必须覆盖两个子诉求，禁止退化为通用兜底。
- 模板外的组合（如“退款 + 查订单”）按单意图处理，不承诺通用复合能力。
- 升级前缓存中的 `composite` 结果由 `COMPOSITE_TO_MERGED` 兜底映射，缓存过期后自然收敛；建议发布后观察 1–2 天（意图 300s + 响应 600s TTL）再删除该映射。
- 回归测试：`scripts/test_composite_intent.py`，断言意图、子意图、双诉求关键词和非兜底回复。

## 规则匹配

### 优先级
```python
PRIORITY_ORDER = [
    "complaint_sarcasm", "complaint_refund", "complaint_accessory",
    "complaint_vague", "complaint_compare_history",
    "complaint_taste_service", "complaint_taste_price",
    "complaint_taste", "complaint_delivery", "complaint_service",
    # ... 更多
]
```
高优先级意图优先匹配，确保敏感投诉不被误判。

### 置信度计算
```python
def _calculate_confidence(pattern, match_text, text_length):
    base = 0.5 + min(len(pattern.pattern) // 3, 0.3)
    ratio = len(match_text) / text_length
    bonus = 0.15 if ratio >= 0.7 else 0.1 if ratio >= 0.5 else 0.05
    return min(base + bonus, 0.95)
```

## LLM 兜底

### 触发条件
- 规则匹配置信度 < `LLM_FALLBACK_THRESHOLD` (0.55)
- 关键词匹配得分 < 0.3

### Prompt 模板
```
判断用户意图：'{text}'
可选：{intent_list}
只返回意图名称，不要其他内容。
```

## 缓存策略

| 缓存类型 | Key | TTL | 命中优先 |
|---------|-----|-----|---------|
| 意图缓存 | 用户原文 | 1小时 | 精确匹配 |
| 响应缓存 | 用户原文 | 10分钟 | 精确匹配 |

## 修改指南

### 新增意图
1. 在 `INTENT_KEYWORDS` 添加关键词列表
2. 在 `RULE_PATTERNS` 添加正则模式
3. 在 `CATEGORY_MAP` 添加分类映射
4. 在 `INTENT_TOOL` 添加工具路由（如果需要）
5. 若不需要工具调用（直接响应），在 `DIRECT_RESPONSES` 添加响应文本
6. 若是复合意图，额外补齐覆盖双诉求的答案，并在 `scripts/test_composite_intent.py` 增加用例

### 调整阈值
- `LLM_FALLBACK_THRESHOLD` (默认 0.55)：降低可减少 LLM 调用
- 关键词匹配权重：在 `_multi_keyword_match` 中调整 multiplier
