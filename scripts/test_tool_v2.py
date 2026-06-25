"""
BubbleMate - 测试工具注册中心V2
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.tools.tool_wrapper import ToolWrapper, ToolResult, ToolStatus
from backend.tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2

def test_tool_registry_v2():
    """测试工具注册中心V2"""
    register_all_tools_v2()
    
    print("\n" + "=" * 60)
    print("工具注册中心V2 测试")
    print("=" * 60)
    
    # 测试1: 参数缺失 - 反问
    print("\n测试1: 订单查询 - 缺少参数（反问）")
    result = tool_registry_v2.call("query_order_status", {})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试2: 正常调用
    print("\n测试2: 订单查询 - 正常")
    result = tool_registry_v2.call("query_order_status", {"order_id": "12345"})
    print(f"类型: {result['type']}")
    print(f"结果: {result.get('result', {})}")
    
    # 测试3: 业务错误 - 订单不存在
    print("\n测试3: 订单查询 - 订单不存在（引导换关键词）")
    result = tool_registry_v2.call("query_order_status", {"order_id": "00000"})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试4: 库存查询 - 缺少参数
    print("\n测试4: 库存查询 - 缺少参数（反问）")
    result = tool_registry_v2.call("check_inventory", {})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试5: 正常库存查询
    print("\n测试5: 库存查询 - 正常")
    result = tool_registry_v2.call("check_inventory", {"store_id": "武汉大学"})
    print(f"类型: {result['type']}")
    print(f"结果: {result.get('result', {})}")
    
    # 测试6: 投诉处理 - 缺少参数
    print("\n测试6: 投诉处理 - 缺少参数（反问+选项）")
    result = tool_registry_v2.call("handle_complaint", {})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试7: 门店查询 - 空结果
    print("\n测试7: 门店查询 - 未找到（引导换关键词）")
    result = tool_registry_v2.call("query_shop_info", {"location": "不存在的地方"})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试8: 正常门店查询
    print("\n测试8: 门店查询 - 正常")
    result = tool_registry_v2.call("query_shop_info", {"location": "武大"})
    print(f"类型: {result['type']}")
    print(f"找到 {result.get('result', {}).get('count', 0)} 家门店")
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    test_tool_registry_v2()
