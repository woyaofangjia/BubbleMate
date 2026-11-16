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
    │ 命中复合模板 → 返回具体合并意图（如 complaint_taste_price）
    │ 命中通用拆解 (_decompose_intents) → 返回 composite + sub_intents
    │ 均未命中
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

复合意图分两级处理：

**1. 模板快速路径（高精度）**

命中 `COMPOSITE_PATTERNS` 时直接返回预定义合并意图，保证有稳定的工具路由或模板答案。

| 文本模板 | 合并意图 | 子意图 |
|---|---|---|
| 太甜…还/又…贵 | `complaint_taste_price` | 口味 + 价格 |
| 料少…还/又…甜 | `complaint_quantity_taste` | 份量 + 口味 |
| 好喝吗…多少钱/价格 | `query_recommend_price` | 推荐 + 价格 |
| 下单/点一杯…优惠/活动 | `place_order_promotion` | 下单 + 优惠 |

**2. 通用拆解（覆盖模板外组合）**

`_decompose_intents` 对模板未命中的输入做通用拆解：

1. `_split_clauses` 按标点（，。；、！？等）与连接词（顺便/另外/同时/还有/以及/并且/而且/然后）切分子句。
2. `_classify_clause` 对每个子句跑规则匹配，未命中再跑关键词匹配；不调用 LLM，避免多倍调用成本。
3. 去重后得到 ≥2 个不同子意图时返回 `composite`，并在 `sub_intents` 中保留顺序；不足 2 个仍走单意图链路。
4. 下游 `collect_composite_tool_results` 按子意图逐个执行工具（缺参数时跳过工具、由回复层追问），`build_composite_response` 再把各子意图的回复按分类标签拼成一条完整回复，保证每个诉求都有答案。

**当前限制**

- 子句识别依赖规则/关键词，不做跨子句的依赖分析、指代消解与逻辑排序。
- 同一子句内无连接词的隐含多意图仍可能只取主意图。
- LLM 兜底提示词仍是单标签输出，不承担多意图拆解。

**兼容与回归**

- 升级前缓存中的 `composite` 结果由 `COMPOSITE_TO_MERGED` 映射到合并意图；意图缓存 TTL 300s、响应缓存 600s。
- 回归测试：`scripts/test_composite_intent.py`，覆盖模板路径、通用拆解、单意图边界、双诉求关键词、非兜底回复和旧缓存重映射。

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
