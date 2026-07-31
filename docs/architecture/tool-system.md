# 工具调用系统

## 概述
工具系统负责将识别到的意图路由到对应函数，并提取参数后执行。

## 工具列表

| 工具函数 | 意图路由 | 参数 | 超时 |
|---------|---------|------|------|
| `query_menu` | query_menu, query_recommend | store_name, keyword, category | 3s |
| `query_stores` | query_location, query_store | location, radius | 3s |
| `query_order` | query_order, query_history | user_id, order_id | 3s |
| `check_stock` | - | item_name, store_name | 3s |
| `log_complaint` | complaint_* | user_id, complaint, severity, category | 3s |
| `query_promotions` | query_promotion | - | 3s |
| `query_customize` | query_customize | item_name | 3s |
| `query_history` | query_history | user_id, limit | 3s |
| `query_recommend` | query_recommend | preference | 3s |

## 执行流程

```
意图识别结果
    │
    ▼
[1] 工具路由 (INTENT_TOOL)
    │ 查找对应工具名
    ▼
[2] 参数提取 (extract_params)
    │ 提取成功
    ▼
[3] 工具执行 (_run_with_timeout)
    │ 执行成功
    ▼
返回结果
    │ 参数缺失
    ▼
返回缺失参数列表（触发反问）
    │ 执行超时/异常
    ▼
返回错误信息
```

## 参数提取

### 位置提取
```python
PARAM_EXTRACTORS = {
    "location": lambda text: re.search(r"([\u4e00-\u9fa5]{2,})(附近|周边)|...", text),
    "order_id": lambda text: re.search(r"(ORD-\d{8}-\d{3}|\d{5,})", text),
}
```

### 提取规则
- `query_stores`: 提取位置关键词，缺失则反问
- `query_order/query_history`: 提取订单号，缺失则反问
- `log_complaint`: 直接传递用户原文作为投诉内容

## 超时机制

```python
def _run_with_timeout(func, args=(), kwargs=None, timeout=3):
    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        raise ToolTimeoutError(f"工具执行超时({timeout}s)")
```

## 降级策略

### 三层降级链路
```
[第一层] 参数验证 → 缺失则反问（硬编码）
[第二层] 工具调用 → 失败则重试（代码层）
[第三层] 结果处理 → 空结果则引导（硬编码兜底）
```

### 反问逻辑
```python
missing_params = ["订单号"]
# Agent生成反问: "请问您能提供一下订单号吗？"
```

### 兜底响应
```python
DIRECT_RESPONSES = {
    "query_order": "抱歉，订单查询暂时有点小问题，请您稍后再试。",
    # ...
}
```

## 添加新工具

### 步骤
1. 在 `bubble_agent.py` 定义工具函数
2. 将函数添加到 `TOOLS` 字典
3. 在 `INTENT_TOOL` 添加意图→工具映射
4. 在 `DIRECT_RESPONSES` 添加降级响应（可选）

### 示例
```python
def query_new_feature(param1, param2=None):
    return {"success": True, "data": [...]}

TOOLS["query_new_feature"] = query_new_feature
INTENT_TOOL["query_new_intent"] = "query_new_feature"
```
