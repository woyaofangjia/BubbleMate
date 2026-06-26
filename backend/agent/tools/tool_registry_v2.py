"""
Tool Registry V2 - 工具注册表
- 支持动态注册工具
- 统一工具调用接口
- 与ToolRouter配合使用
"""

import json
import os
import re
from typing import Dict, Callable, Any, Optional


class ToolRegistryV2:
    """工具注册表"""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.descriptions: Dict[str, str] = {}

    def register(self, name: str, func: Callable, description: str = ""):
        """注册工具"""
        self.tools[name] = func
        self.descriptions[name] = description

    def call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if name not in self.tools:
            return {"success": False, "response": f"工具 {name} 未注册"}

        try:
            result = self.tools[name](**args)
            return {"success": True, "response": result}
        except Exception as e:
            return {"success": False, "response": f"工具调用失败: {str(e)}"}

    def get_description(self, name: str) -> str:
        """获取工具描述"""
        return self.descriptions.get(name, "")

    def list_tools(self) -> list:
        """列出所有工具"""
        return list(self.tools.keys())


tool_registry_v2 = ToolRegistryV2()


def register_all_tools_v2():
    """注册所有工具"""

    def query_stores(location: str = "") -> str:
        """查询附近门店"""
        shops_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "bubble_tea_all.json")
        shops_path = os.path.abspath(shops_path)

        if os.path.exists(shops_path):
            with open(shops_path, "r", encoding="utf-8") as f:
                shops = json.load(f)

            if location:
                filtered = [s for s in shops if location in s.get("address", "") or location in s.get("name", "")]
                if filtered:
                    result = f"找到{len(filtered)}家匹配门店：\n"
                    for shop in filtered[:3]:
                        result += f"- {shop.get('name', '')}: {shop.get('address', '')}\n"
                    return result
                return f"未找到'{location}'附近的门店，请尝试其他关键词。"

            shop_list = shops[:3]
            result = "附近门店：\n"
            for shop in shop_list:
                result += f"- {shop.get('name', '')}: {shop.get('address', '')}\n"
            return result

        return "门店数据暂不可用"

    def query_menu(keyword: str = "", category: str = "") -> str:
        """查询菜单"""
        menu = {
            "芝士系列": [
                {"name": "芝芝莓莓", "price": 20, "desc": "鲜草莓芝士奶盖"},
                {"name": "芝芝芒果", "price": 18, "desc": "芒果芝士奶盖"},
            ],
            "鲜果茶系列": [
                {"name": "杨枝甘露", "price": 18, "desc": "椰奶芒果西柚"},
                {"name": "葡萄冰茶", "price": 15, "desc": "新鲜葡萄冰茶"},
            ],
            "奶茶系列": [
                {"name": "珍珠奶茶", "price": 12, "desc": "经典珍珠奶茶"},
                {"name": "糯米奶茶", "price": 14, "desc": "糯米珍珠奶茶"},
            ],
            "纯茶系列": [
                {"name": "茉莉绿茶", "price": 15, "desc": "零糖低卡"},
                {"name": "柠檬茶", "price": 10, "desc": "清爽柠檬"},
            ]
        }

        if category and category in menu:
            items = menu[category]
            result = f"{category}：\n"
            for item in items:
                result += f"- {item['name']} - ¥{item['price']} - {item['desc']}\n"
            return result

        if keyword:
            for category_name, items in menu.items():
                for item in items:
                    if keyword in item["name"] or keyword in item["desc"]:
                        return f"- {item['name']} - ¥{item['price']} - {item['desc']}"

        return """招牌推荐：
1. 芝芝莓莓 - ¥20 - 鲜草莓芝士奶盖
2. 杨枝甘露 - ¥18 - 椰奶芒果西柚
3. 茉莉绿茶 - ¥15 - 零糖低卡
4. 珍珠奶茶 - ¥12 - 经典珍珠奶茶"""

    def query_order(order_id: str = "", user_id: str = "") -> str:
        """查询订单"""
        orders = {
            "12345": {"status": "配送中", "drink": "芝芝莓莓", "eta": "15分钟", "store": "武汉大学梅园店"},
            "67890": {"status": "制作中", "drink": "杨枝甘露", "eta": "25分钟", "store": "银泰创意城店"},
            "11111": {"status": "已完成", "drink": "茉莉绿茶", "eta": "已送达", "store": "街道口店"},
        }

        if order_id:
            if order_id in orders:
                order = orders[order_id]
                return f"订单{order_id}状态：{order['status']}，饮品-{order['drink']}，{order['eta']}，门店-{order['store']}"
            return f"抱歉，订单{order_id}不存在，请检查订单号是否正确。"

        return "请提供订单号（如：12345），我帮您查询订单状态。"

    def check_stock(store_name: str = "", ingredient: str = "") -> str:
        """查询库存"""
        stock_data = {
            "武汉大学梅园店": {"珍珠": 50, "椰果": 30, "奶盖": 20, "茶底": 100},
            "银泰创意城店": {"珍珠": 20, "椰果": 40, "奶盖": 15, "茶底": 80},
            "街道口店": {"珍珠": 30, "椰果": 25, "奶盖": 25, "茶底": 90},
        }

        if store_name and ingredient:
            if store_name in stock_data:
                stock = stock_data[store_name].get(ingredient, 0)
                status = "充足" if stock > 10 else "紧张" if stock > 0 else "缺货"
                return f"{store_name}的{ingredient}库存：{stock}份，状态：{status}"
            return f"未找到门店: {store_name}"

        return "请提供门店名称和原料名称"

    def log_complaint(complaint_type: str = "", order_id: str = "", description: str = "") -> str:
        """处理投诉"""
        complaint_types = {
            "口感": "taste",
            "份量": "quantity",
            "服务": "service",
            "配送": "delivery",
            "价格": "price",
        }

        code = complaint_types.get(complaint_type, complaint_type)
        order_str = f"订单{order_id}" if order_id else "您的投诉"

        complaint_log = {
            "type": code,
            "order_id": order_id,
            "description": description,
            "timestamp": "2024-01-01 00:00:00",
            "status": "pending",
        }

        return f"{order_str}已受理（类型：{complaint_type}），客服将在24小时内联系您处理。"

    tool_registry_v2.register("query_stores", query_stores, "查询附近门店，需要位置关键词")
    tool_registry_v2.register("query_menu", query_menu, "查询菜单饮品，支持按类别或关键词搜索")
    tool_registry_v2.register("query_order", query_order, "查询订单状态，需要订单号")
    tool_registry_v2.register("check_stock", check_stock, "查询原料库存，需要门店名和原料名")
    tool_registry_v2.register("log_complaint", log_complaint, "处理投诉，需要投诉类型")