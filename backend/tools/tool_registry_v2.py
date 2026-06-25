"""
BubbleMate Tools V2 - 增强版工具注册中心
集成异常处理、参数验证、反问逻辑
"""

import json
import os
from typing import Dict, Callable, Any
from .tool_wrapper import ToolWrapper, ToolResult, ToolStatus

class ToolRegistryV2:
    """增强版工具注册中心"""
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self.handlers: Dict[str, Callable] = {}
        self.wrapper = ToolWrapper(max_retries=2)
    
    def register(self, name: str, description: str, handler: Callable, parameters: Dict):
        """注册工具"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        self.handlers[name] = handler
    
    def list_tools(self) -> list:
        """列出所有工具"""
        return list(self.tools.values())
    
    def call(self, name: str, arguments: Dict) -> Dict:
        """
        调用工具（带异常处理）
        返回标准化结果
        """
        if name not in self.handlers:
            return {
                "success": False,
                "error": f"工具 '{name}' 不存在",
                "available_tools": list(self.tools.keys()),
                "response": "抱歉，该功能暂不可用。"
            }
        
        tool_config = self.tools[name]
        handler = self.handlers[name]
        
        # 使用包装器执行
        result: ToolResult = self.wrapper.execute(
            tool_config, handler, arguments, name
        )
        
        # 构建标准化响应
        if result.status == ToolStatus.MISSING_PARAM:
            return {
                "success": False,
                "error": "参数缺失",
                "missing_params": result.missing_params,
                "response": result.response,
                "type": "ask_user"
            }
        
        if result.status == ToolStatus.FAILED:
            return {
                "success": False,
                "error": result.error,
                "response": result.response,
                "retry_count": result.retry_count,
                "type": "error"
            }
        
        # 业务逻辑错误
        if isinstance(result.result, dict) and "error" in result.result:
            return {
                "success": False,
                "error": result.result["error"],
                "hint": result.result.get("hint", ""),
                "response": result.response,
                "type": "business_error"
            }
        
        return {
            "success": True,
            "result": result.result,
            "response": result.response,
            "retry_count": result.retry_count,
            "type": "success"
        }

# 创建全局实例
tool_registry_v2 = ToolRegistryV2()

def register_all_tools_v2():
    """注册所有工具（V2版）"""
    
    # 订单查询工具
    def query_order_status(order_id: str = "", phone_number: str = "") -> Dict:
        """查询订单状态"""
        if not order_id:
            return {"error": "订单号不能为空", "hint": "请提供订单号"}
        
        mock_orders = {
            "12345": {
                "status": "配送中",
                "drink": "芝芝莓莓",
                "eta": "15分钟",
                "store": "武汉大学梅园店"
            },
            "67890": {
                "status": "制作中",
                "drink": "杨枝甘露", 
                "eta": "25分钟",
                "store": "银泰创意城店"
            },
            "11111": {
                "status": "已完成",
                "drink": "茉莉绿茶",
                "eta": "已送达",
                "store": "街道口店"
            }
        }
        
        if order_id in mock_orders:
            return mock_orders[order_id]
        else:
            return {"error": "订单不存在", "hint": "请检查订单号是否正确"}
    
    tool_registry_v2.register(
        name="query_order_status",
        description="查询奶茶订单状态，需要订单号和手机号验证",
        handler=query_order_status,
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单编号"},
                "phone_number": {"type": "string", "description": "手机号（可选）"}
            },
            "required": ["order_id"]
        }
    )
    
    # 库存查询工具
    def check_inventory(store_id: str = "", ingredient: str = "") -> Dict:
        """查询门店库存"""
        mock_inventory = {
            "武汉大学": {
                "珍珠": "充足",
                "糯米": "充足",
                "芝士": "充足",
                "芒果": "紧张",
                "草莓": "充足"
            },
            "银泰": {
                "珍珠": "紧张",
                "糯米": "充足",
                "芝士": "充足",
                "芒果": "充足",
                "草莓": "紧张"
            }
        }
        
        if not store_id:
            return {"error": "请提供门店名称", "hint": "如：武汉大学、银泰"}
        
        store_key = "武汉大学" if "武大" in store_id or "武汉" in store_id else "银泰"
        
        if store_key in mock_inventory:
            inventory = mock_inventory[store_key]
            if ingredient:
                status = inventory.get(ingredient, "未知")
                return {
                    "store": store_key,
                    "ingredient": ingredient,
                    "status": status,
                    "note": "紧张" if status == "紧张" else ""
                }
            return {"store": store_key, "inventory": inventory}
        
        return {"error": "门店不存在", "hint": "请提供正确的门店名称"}
    
    tool_registry_v2.register(
        name="check_inventory",
        description="查询门店原料库存情况",
        handler=check_inventory,
        parameters={
            "type": "object",
            "properties": {
                "store_id": {"type": "string", "description": "门店名称或ID"},
                "ingredient": {"type": "string", "description": "原料名称（可选）"}
            },
            "required": ["store_id"]
        }
    )
    
    # 门店查询工具
    def query_shop_info(location: str = "") -> Dict:
        """查询门店信息"""
        shops_path = os.path.join("data", "bubble_tea_all.json")
        if os.path.exists(shops_path):
            with open(shops_path, "r", encoding="utf-8") as f:
                shops = json.load(f)
            
            if location:
                filtered = [s for s in shops if location in s.get("address", "") or location in s.get("name", "")]
                if filtered:
                    return {"shops": filtered[:5], "count": len(filtered)}
                return {"error": "未找到匹配的门店", "hint": "尝试换个关键词，如：武大、银泰、街道口"}
            
            return {"shops": shops[:5], "count": len(shops)}
        
        return {"error": "门店数据暂不可用"}
    
    tool_registry_v2.register(
        name="query_shop_info",
        description="查询门店信息，可按位置筛选",
        handler=query_shop_info,
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "位置关键词（可选）"}
            },
            "required": []
        }
    )
    
    # 菜单查询工具
    def query_menu_info(category: str = "") -> Dict:
        """查询菜单/饮品信息"""
        menu = {
            "芝士系列": [
                {"name": "芝芝莓莓", "price": 20, "description": "鲜草莓芝士奶盖"},
                {"name": "芝芝芒果", "price": 18, "description": "芒果芝士奶盖"},
            ],
            "鲜果茶系列": [
                {"name": "杨枝甘露", "price": 18, "description": "椰奶芒果西柚"},
                {"name": "葡萄冰茶", "price": 15, "description": "新鲜葡萄冰茶"},
            ],
            "奶茶系列": [
                {"name": "珍珠奶茶", "price": 12, "description": "经典珍珠奶茶"},
                {"name": "糯米奶茶", "price": 14, "description": "糯米珍珠奶茶"},
            ],
            "纯茶系列": [
                {"name": "茉莉绿茶", "price": 15, "description": "零糖低卡"},
                {"name": "柠檬茶", "price": 10, "description": "清爽柠檬"},
            ]
        }
        
        if category:
            if category in menu:
                return {"category": category, "items": menu[category]}
            return {"error": "分类不存在", "hint": f"可选分类: {', '.join(menu.keys())}"}
        
        return {"menu": menu}
    
    tool_registry_v2.register(
        name="query_menu_info",
        description="查询菜单饮品信息",
        handler=query_menu_info,
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "饮品类别（可选）"}
            },
            "required": []
        }
    )
    
    # 投诉处理工具
    def handle_complaint(complaint_type: str = "", order_id: str = "", description: str = "") -> Dict:
        """处理投诉"""
        if not complaint_type:
            return {"error": "请提供投诉类型", "hint": "可选: taste(口感), quantity(份量), service(服务), delivery(配送), price(价格)"}
        
        responses = {
            "taste": "口感问题已记录，我们将在24小时内为您重新制作或退款。",
            "quantity": "份量问题已记录，我们将核查门店标准，为您提供补偿。",
            "service": "服务问题已记录，客服将联系门店整改并为您处理。",
            "delivery": "配送问题已记录，将为您申请超时赔付。",
            "price": "价格反馈已记录，我们会考虑调整定价策略。",
        }
        
        response = responses.get(complaint_type)
        if not response:
            return {"error": "投诉类型不支持", "hint": f"可选: {', '.join(responses.keys())}"}
        
        return {
            "status": "已受理",
            "complaint_id": f"CP-{order_id[:3] if order_id else '001'}",
            "response": response,
            "next_step": "客服将在24小时内联系您"
        }
    
    tool_registry_v2.register(
        name="handle_complaint",
        description="处理顾客投诉",
        handler=handle_complaint,
        parameters={
            "type": "object",
            "properties": {
                "complaint_type": {"type": "string", "description": "投诉类型: taste/quantity/service/delivery/price"},
                "order_id": {"type": "string", "description": "订单号（可选）"},
                "description": {"type": "string", "description": "投诉描述"}
            },
            "required": ["complaint_type"]
        }
    )


def test_tool_registry_v2():
    """测试工具注册中心V2"""
    register_all_tools_v2()
    
    print("\n" + "=" * 60)
    print("工具注册中心V2 测试")
    print("=" * 60)
    
    # 测试1: 参数缺失
    print("\n测试1: 订单查询 - 缺少参数")
    result = tool_registry_v2.call("query_order_status", {})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试2: 正常调用
    print("\n测试2: 订单查询 - 正常")
    result = tool_registry_v2.call("query_order_status", {"order_id": "12345"})
    print(f"类型: {result['type']}")
    print(f"结果: {result.get('result', {})}")
    
    # 测试3: 业务错误（订单不存在）
    print("\n测试3: 订单查询 - 订单不存在")
    result = tool_registry_v2.call("query_order_status", {"order_id": "00000"})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试4: 库存查询 - 缺少参数
    print("\n测试4: 库存查询 - 缺少参数")
    result = tool_registry_v2.call("check_inventory", {})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试5: 投诉处理 - 缺少参数
    print("\n测试5: 投诉处理 - 缺少参数")
    result = tool_registry_v2.call("handle_complaint", {})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")
    
    # 测试6: 门店查询 - 空结果
    print("\n测试6: 门店查询 - 未找到")
    result = tool_registry_v2.call("query_shop_info", {"location": "不存在的地方"})
    print(f"类型: {result['type']}")
    print(f"回复: {result['response']}")

if __name__ == "__main__":
    test_tool_registry_v2()
