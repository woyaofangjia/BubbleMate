"""
BubbleMate Tools - 工具层
MCP工具服务器实现
"""

import json
import os
from typing import Dict, Callable, Any

class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self.handlers: Dict[str, Callable] = {}
    
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
    
    def call(self, name: str, arguments: Dict) -> Any:
        """调用工具"""
        if name not in self.handlers:
            return {"error": f"工具 {name} 不存在"}
        
        handler = self.handlers[name]
        try:
            result = handler(**arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

# 创建工具注册实例
tool_registry = ToolRegistry()

def register_all_tools():
    """注册所有工具"""
    
    # 订单查询工具
    def query_order_status(order_id: str, phone_number: str = "") -> Dict:
        """查询订单状态"""
        # Mock订单数据
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
    
    tool_registry.register(
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
    def check_inventory(store_id: str, ingredient: str = "") -> Dict:
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
        
        store_key = "武汉大学" if "武大" in store_id or "武汉" in store_id else "银泰"
        
        if store_key in mock_inventory:
            inventory = mock_inventory[store_key]
            if ingredient:
                return {
                    "store": store_key,
                    "ingredient": ingredient,
                    "status": inventory.get(ingredient, "未知")
                }
            return {"store": store_key, "inventory": inventory}
        
        return {"error": "门店不存在"}
    
    tool_registry.register(
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
        # 加载真实门店数据
        shops_path = os.path.join("data", "bubble_tea_all.json")
        if os.path.exists(shops_path):
            with open(shops_path, "r", encoding="utf-8") as f:
                shops = json.load(f)
            
            # 按位置筛选
            if location:
                filtered = [s for s in shops if location in s.get("address", "") or location in s.get("name", "")]
                if filtered:
                    return {"shops": filtered[:5]}
            
            return {"shops": shops[:5]}
        
        return {"error": "门店数据暂不可用"}
    
    tool_registry.register(
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
            return {"category": category, "items": menu.get(category, [])}
        
        return {"menu": menu}
    
    tool_registry.register(
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
    def handle_complaint(complaint_type: str, order_id: str = "", description: str = "") -> Dict:
        """处理投诉"""
        responses = {
            "taste": "口感问题已记录，我们将在24小时内为您重新制作或退款。",
            "quantity": "份量问题已记录，我们将核查门店标准，为您提供补偿。",
            "service": "服务问题已记录，客服将联系门店整改并为您处理。",
            "delivery": "配送问题已记录，将为您申请超时赔付。",
            "price": "价格反馈已记录，我们会考虑调整定价策略。",
        }
        
        response = responses.get(complaint_type, "投诉已记录，客服将在24小时内联系您处理。")
        
        return {
            "status": "已受理",
            "complaint_id": f"CP-{order_id[:3]}",
            "response": response,
            "next_step": "客服将在24小时内联系您"
        }
    
    tool_registry.register(
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


def test_tools():
    """测试工具"""
    register_all_tools()
    
    print("\n已注册工具:")
    print("-" * 50)
    for tool in tool_registry.list_tools():
        print(f"  {tool['name']}: {tool['description']}")
    
    print("\n工具调用测试:")
    print("-" * 50)
    
    # 测试订单查询
    result = tool_registry.call("query_order_status", {"order_id": "12345"})
    print(f"订单查询: {result}")
    
    # 测试库存查询
    result = tool_registry.call("check_inventory", {"store_id": "武汉大学"})
    print(f"库存查询: {result}")
    
    # 测试门店查询
    result = tool_registry.call("query_shop_info", {"location": "武大"})
    print(f"门店查询: {result}")
    
    # 测试投诉处理
    result = tool_registry.call("handle_complaint", {"complaint_type": "taste", "description": "太甜了"})
    print(f"投诉处理: {result}")

if __name__ == "__main__":
    test_tools()