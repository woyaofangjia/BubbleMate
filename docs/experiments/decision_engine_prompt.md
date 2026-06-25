# 决策引擎Prompt设计

## 设计目标

面试问题：**"你的Agent凭什么说自己'知道什么时候该调工具'？"**

回答：我给大模型画了**决策边界**——强制走固定的决策链路。

## 核心设计

### 意图路由表

```python
# 意图 → 处理策略的硬编码映射
ROUTE_MAP = {
    "complaint_taste":      "_handle_complaint",   # 安抚 + 记录 + 补偿方案
    "complaint_quantity":   "_handle_complaint",   # 安抚 + 记录 + 补偿方案
    "query_recommend":      "_handle_query",       # 调用菜单工具
    "query_order":          "_handle_query",       # 调用订单工具（需订单号）
    "query_location":       "_handle_query",       # 调用门店工具
    "place_order":          "_handle_order",       # 引导到小程序
}
```

**关键设计**：意图识别后，不是让模型"自由决定"怎么处理，而是**强制路由到预设的处理函数**。

### 工具调用检查清单

```python
def execute_tool(tool_name, arguments):
    # 检查1：必填参数
    if missing_params := validate_params(tool_name, arguments):
        return ask_user_for_params(missing_params)  # 反问
    
    # 检查2：调用工具
    result = call_tool(tool_name, arguments)
    
    # 检查3：结果处理
    if result.is_empty():
        return fallback_response(tool_name)  # 降级回复
    
    return result
```

### 副作用控制

退款/取消等不可逆操作，必须二次确认：

```python
if tool_name in SIDE_EFFECT_TOOLS:
    if not user_confirmed:
        return "确认要执行此操作吗？（回复'确认'继续）"
```

## 实验验证

### 意图路由准确率

```
端到端对话测试：
- 测试用例数：5
- 意图识别准确率：100.0%
- 平均相关度：83.3%
- 平均响应时间：0.1ms
```

### 边界Case验证

| Case | 输入 | 普通Agent可能行为 | BubbleMate行为 |
|------|------|------------------|----------------|
| 参数缺失 | "我要查订单" | 可能报错或编造 | **反问**"请提供订单号" |
| 空结果 | "查火星上的门店" | 可能编造地址 | **引导**"未找到，建议换关键词" |
| 长对话 | 第6轮"换刚才那杯" | 可能忘记 | **通过摘要记住**"杨枝甘露" |

## 面试官话术

> "我的Agent不是让大模型自由发挥，而是给它画了决策边界。意图识别后强制路由到预设处理函数，工具调用前必须过检查清单，有副作用的操作必须二次确认。这套机制保证了即使模型'犯傻'，也不会越过红线。"
