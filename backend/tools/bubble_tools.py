"""
BubbleMate 工具实现
按"2+1+2"策略实现5个工具
"""

import json
import os
import random
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# ============================================
# 工具1: 菜单查询（本地JSON，半真半Mock）
# ============================================

def query_menu(store_name: str = None, keyword: str = None, category: str = None) -> Dict:
    """
    查询菜单
    
    Args:
        store_name: 门店名称（可选，不传则返回所有门店菜单概览）
        keyword: 搜索关键词（可选）
        category: 分类筛选（可选：奶茶/果茶/纯茶/冰淇淋/软欧包）
    
    Returns:
        {
            "success": bool,
            "data": list,
            "count": int,
            "stores": list  # 如果没指定门店，返回门店列表
        }
    """
    menu_path = os.path.join(os.path.dirname(__file__), "../../data/menu_data.json")
    
    if not os.path.exists(menu_path):
        return {
            "success": False,
            "error": "菜单数据不可用",
            "response": "抱歉，菜单系统暂时维护中。"
        }
    
    with open(menu_path, "r", encoding="utf-8") as f:
        menu_data = json.load(f)
    
    # 未指定门店 → 返回门店列表 + 热门单品
    if not store_name:
        stores = list(menu_data.keys())
        # 每家店取销量最高的1款
        hot_items = []
        for store, items in menu_data.items():
            available = [i for i in items if i["available"]]
            if available:
                top = max(available, key=lambda x: x["sales"])
                hot_items.append({
                    "store": store,
                    "name": top["name"],
                    "price": top["price"],
                    "category": top["category"]
                })
        
        return {
            "success": True,
            "data": hot_items,
            "count": len(hot_items),
            "stores": stores,
            "store_count": len(stores),
            "response": f"当前有{len(stores)}家门店，以下是各店招牌推荐。"
        }
    
    # 指定门店 → 返回该店菜单
    # 模糊匹配门店名
    matched_store = None
    for name in menu_data.keys():
        if store_name.lower() in name.lower() or name.lower() in store_name.lower():
            matched_store = name
            break
    
    if not matched_store:
        return {
            "success": False,
            "error": f"未找到门店 '{store_name}'",
            "hint": f"可用门店: {', '.join(list(menu_data.keys())[:3])}",
            "response": f"抱歉，没找到'{store_name}'这家门店。您可以查询：茶颜悦色、喜茶、奈雪的茶等。"
        }
    
    items = menu_data[matched_store]
    
    # 过滤
    filtered = items
    
    # 关键词筛选
    if keyword:
        filtered = [
            i for i in filtered 
            if keyword.lower() in i["name"].lower() 
            or keyword.lower() in i["description"].lower()
        ]
    
    # 分类筛选
    if category:
        filtered = [i for i in filtered if i["category"] == category]
    
    # 只返回有货的
    available_items = [i for i in filtered if i["available"]]
    unavailable_items = [i for i in filtered if not i["available"]]
    
    result = {
        "success": True,
        "store": matched_store,
        "data": available_items,
        "count": len(available_items),
        "unavailable": len(unavailable_items),
        "response": f"{matched_store} 当前有{len(available_items)}款饮品可点。"
    }
    
    if len(unavailable_items) > 0:
        result["response"] += f"（{len(unavailable_items)}款暂时缺货）"
    
    if keyword and len(available_items) == 0:
        result["response"] = f"{matched_store}暂时没有'{keyword}'相关饮品。您可以试试其他关键词。"
    
    return result


# ============================================
# 工具2: 门店查询（高德API真调用）⭐核心
# ============================================

AMAP_KEY = os.environ.get("AMAP_API_KEY", "您的KEY")

def amap_geocode(address: str) -> Optional[Dict]:
    """高德地理编码：地址 → 经纬度"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": AMAP_KEY,
        "address": address,
        "city": "武汉"  # 限定城市
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("geocodes"):
            geocode = data["geocodes"][0]
            location = geocode.get("location", "").split(",")
            if len(location) == 2:
                return {
                    "lng": float(location[0]),
                    "lat": float(location[1]),
                    "formatted_address": geocode.get("formatted_address", address)
                }
    except Exception as e:
        print(f"高德地理编码失败: {e}")
    
    return None


def amap_around_search(lat: float, lng: float, keywords: str = "奶茶", radius: int = 3000) -> List[Dict]:
    """高德周边搜索：经纬度 → 门店列表"""
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        "key": AMAP_KEY,
        "location": f"{lng},{lat}",
        "keywords": keywords,
        "radius": radius,
        "offset": 10,  # 返回10条
        "extensions": "all"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if data.get("status") == "1" and data.get("pois"):
            pois = data["pois"]
            results = []
            for poi in pois:
                results.append({
                    "name": poi.get("name", ""),
                    "address": poi.get("address", ""),
                    "distance": poi.get("distance", "未知"),
                    "type": poi.get("type", ""),
                    "tel": poi.get("tel", ""),
                    "location": poi.get("location", "")
                })
            return results
    except Exception as e:
        print(f"高德周边搜索失败: {e}")
    
    return []


def query_stores(location: str, radius: int = 3000, keywords: str = "奶茶") -> Dict:
    """
    门店查询（真·高德API）
    
    Args:
        location: 位置描述（如"光谷广场"、"武汉大学"）
        radius: 搜索半径（米）
        keywords: 搜索关键词
    
    Returns:
        {
            "success": bool,
            "data": list,
            "count": int,
            "center": dict  # 中心点坐标
        }
    """
    # 1. 地理编码
    geocode = amap_geocode(location)
    
    if not geocode:
        return {
            "success": False,
            "error": f"无法识别位置 '{location}'",
            "hint": "建议尝试：光谷广场、武汉大学、街道口",
            "response": f"抱歉，无法找到'{location}'的位置。您可以换个关键词试试。"
        }
    
    # 2. 周边搜索
    stores = amap_around_search(geocode["lat"], geocode["lng"], keywords, radius)
    
    if not stores:
        return {
            "success": False,
            "error": "附近无奶茶门店",
            "center": geocode,
            "radius": radius,
            "response": f"抱歉，{location}附近{radius}米内暂无奶茶门店。建议扩大搜索范围或换位置。"
        }
    
    return {
        "success": True,
        "data": stores,
        "count": len(stores),
        "center": geocode,
        "radius": radius,
        "response": f"在{location}附近{radius}米内找到{len(stores)}家奶茶门店。"
    }


# ============================================
# 工具3: 订单查询（Mock数据）
# ============================================

def query_order(user_id: str, order_id: str = None, status: str = None) -> Dict:
    """
    订单查询（Mock）
    
    Args:
        user_id: 用户手机号
        order_id: 订单号（可选）
        status: 状态筛选（可选：已完成/配送中/待配送）
    
    Returns:
        {
            "success": bool,
            "data": list,
            "user_id": str
        }
    """
    orders_path = os.path.join(os.path.dirname(__file__), "../../data/orders_mock.json")
    
    if not os.path.exists(orders_path):
        return {
            "success": False,
            "error": "订单系统不可用",
            "response": "抱歉，订单查询系统暂时维护中。"
        }
    
    with open(orders_path, "r", encoding="utf-8") as f:
        orders_data = json.load(f)
    
    # 查询用户的订单
    user_orders = orders_data.get(f"user_{user_id}", [])
    
    if not user_orders:
        # 提示注册的测试用户
        test_users = list(orders_data.keys())
        return {
            "success": False,
            "error": f"用户 {user_id} 无订单记录",
            "hint": f"测试用户: {', '.join([u.replace('user_', '') for u in test_users[:2]])}",
            "response": f"抱歉，未找到您的订单记录。如需查询，请先登录（测试用户：13800138000）。"
        }
    
    # 按订单号筛选
    if order_id:
        user_orders = [o for o in user_orders if o["order_id"] == order_id]
        if not user_orders:
            return {
                "success": False,
                "error": f"订单 {order_id} 不存在",
                "response": f"抱歉，未找到订单 {order_id}。请确认订单号是否正确。"
            }
    
    # 按状态筛选
    if status:
        user_orders = [o for o in user_orders if o["status"] == status]
    
    return {
        "success": True,
        "data": user_orders,
        "count": len(user_orders),
        "user_id": user_id,
        "response": f"为您找到{len(user_orders)}条订单记录。"
    }


# ============================================
# 工具4: 库存查询（随机Mock）
# ============================================

def check_stock(item_name: str, store_name: str = None) -> Dict:
    """
    库存查询（随机Mock）
    
    Args:
        item_name: 饮品名称
        store_name: 门店名称（可选）
    
    Returns:
        {
            "success": bool,
            "item": str,
            "available": bool,
            "quantity": int,
            "estimated_wait": str  # 预估等待时间
        }
    """
    # 热销款更容易缺货
    hot_items = ["幽兰拿铁", "多肉葡萄", "霸气芝士草莓", "珍珠奶茶"]
    
    if item_name in hot_items:
        available = random.choice([True, True, False])  # 热销款66%有货
    else:
        available = random.choice([True, True, True, False])  # 普通75%有货
    
    quantity = random.randint(0, 50) if available else 0
    
    result = {
        "success": True,
        "item": item_name,
        "store": store_name or "全门店",
        "available": available,
        "quantity": quantity,
        "estimated_wait": random.choice(["5分钟", "10分钟", "15分钟", "20分钟"]) if available else "暂无",
        "response": f"{item_name} 当前{'有货' if available else '缺货'}。"
    }
    
    if not available:
        result["response"] += "建议选择其他饮品或稍后再试。"
    
    return result


# ============================================
# 工具5: 投诉处理（日志记录）
# ============================================

COMPLAINTS_LOG = os.path.join(os.path.dirname(__file__), "../../data/complaints.log")

def log_complaint(user_id: str, complaint: str, severity: str = "普通", category: str = "口味") -> Dict:
    """
    投诉处理（日志记录）
    
    Args:
        user_id: 用户ID
        complaint: 投诉内容
        severity: 严重程度（普通/严重）
        category: 投诉类型（口味/服务/配送/价格）
    
    Returns:
        {
            "success": bool,
            "complaint_id": str,
            "response": str
        }
    """
    import time
    complaint_id = f"CMP-{int(time.time())}"
    
    # 写入日志
    log_entry = f"{complaint_id} | {user_id} | {severity} | {category} | {complaint} | {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    os.makedirs(os.path.dirname(COMPLAINTS_LOG), exist_ok=True)
    with open(COMPLAINTS_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    # 根据严重程度返回不同话术
    responses = {
        "普通": "感谢您的反馈，我们会认真改进。如有需要可联系店长获得补偿。",
        "严重": "非常抱歉给您带来不好的体验！已升级处理，客服会在24小时内联系您。"
    }
    
    return {
        "success": True,
        "complaint_id": complaint_id,
        "severity": severity,
        "category": category,
        "response": responses.get(severity, responses["普通"]),
        "logged": True
    }


# ============================================
# 工具注册
# ============================================

TOOL_REGISTRY = {
    "query_menu": {
        "name": "query_menu",
        "description": "查询门店菜单，支持按关键词和分类筛选",
        "handler": query_menu,
        "parameters": {
            "store_name": {"type": "string", "required": False, "description": "门店名称"},
            "keyword": {"type": "string", "required": False, "description": "搜索关键词"},
            "category": {"type": "string", "required": False, "description": "分类"}
        }
    },
    "query_stores": {
        "name": "query_stores",
        "description": "查询附近奶茶门店（高德地图API）",
        "handler": query_stores,
        "parameters": {
            "location": {"type": "string", "required": True, "description": "位置描述"},
            "radius": {"type": "integer", "required": False, "description": "搜索半径（米）"},
            "keywords": {"type": "string", "required": False, "description": "搜索关键词"}
        }
    },
    "query_order": {
        "name": "query_order",
        "description": "查询用户订单",
        "handler": query_order,
        "parameters": {
            "user_id": {"type": "string", "required": True, "description": "用户手机号"},
            "order_id": {"type": "string", "required": False, "description": "订单号"},
            "status": {"type": "string", "required": False, "description": "状态筛选"}
        }
    },
    "check_stock": {
        "name": "check_stock",
        "description": "查询饮品库存",
        "handler": check_stock,
        "parameters": {
            "item_name": {"type": "string", "required": True, "description": "饮品名称"},
            "store_name": {"type": "string", "required": False, "description": "门店名称"}
        }
    },
    "log_complaint": {
        "name": "log_complaint",
        "description": "记录用户投诉",
        "handler": log_complaint,
        "parameters": {
            "user_id": {"type": "string", "required": True, "description": "用户ID"},
            "complaint": {"type": "string", "required": True, "description": "投诉内容"},
            "severity": {"type": "string", "required": False, "description": "严重程度"},
            "category": {"type": "string", "required": False, "description": "投诉类型"}
        }
    }
}

def query_promotions() -> Dict:
    promotions_path = os.path.join(os.path.dirname(__file__), "../../data/promotions.json")
    if not os.path.exists(promotions_path):
        return {"success": False, "error": "优惠活动数据不可用", "response": "抱歉，活动信息暂时查询不到。"}
    with open(promotions_path, "r", encoding="utf-8") as f:
        promo_data = json.load(f)
    active = promo_data.get("active", [])
    names = [p['name'] for p in active[:3]]
    return {
        "success": True,
        "data": active,
        "count": len(active),
        "response": f"当前有{len(active)}个活动正在进行：{', '.join(names)}等。"
    }


def query_customize(item_name: str) -> Dict:
    all_toppings = [
        {"name": "珍珠", "price": 3, "category": "Q弹系列"},
        {"name": "椰果", "price": 3, "category": "Q弹系列"},
        {"name": "仙草冻", "price": 4, "category": "Q弹系列"},
        {"name": "芋圆", "price": 4, "category": "Q弹系列"},
        {"name": "西米", "price": 3, "category": "Q弹系列"},
        {"name": "红豆", "price": 3, "category": "加料系列"},
        {"name": "燕麦", "price": 3, "category": "加料系列"},
        {"name": "布丁", "price": 4, "category": "加料系列"},
        {"name": "芝士奶盖", "price": 6, "category": "顶料系列"},
        {"name": "奶油顶", "price": 5, "category": "顶料系列"},
        {"name": "碧根果碎", "price": 3, "category": "顶料系列"}
    ]
    sugar_options = ["标准糖", "七分糖", "五分糖", "三分糖", "无糖"]
    temp_options = ["正常冰", "少冰", "去冰", "温热", "热饮"]
    return {
        "success": True,
        "item": item_name,
        "toppings": all_toppings,
        "sugar_options": sugar_options,
        "temp_options": temp_options,
        "response": f"{item_name}支持{len(all_toppings)}种加料和5档糖度温度选择。"
    }


def query_history(user_id: str, limit: int = 3) -> Dict:
    orders_path = os.path.join(os.path.dirname(__file__), "../../data/orders_mock.json")
    if not os.path.exists(orders_path):
        return {"success": False, "error": "订单系统不可用", "response": "抱歉，历史订单暂时查询不到。"}
    with open(orders_path, "r", encoding="utf-8") as f:
        orders_data = json.load(f)
    user_orders = orders_data.get(f"user_{user_id}", [])
    if not user_orders:
        return {"success": False, "error": f"用户 {user_id} 无历史订单", "response": "抱歉，未找到您的历史订单。"}
    recent = user_orders[:limit]
    return {
        "success": True,
        "data": recent,
        "count": len(recent),
        "total": len(user_orders),
        "response": f"为您找到最近{len(recent)}条历史订单。"
    }


def query_recommend(preference: str = None, season: str = None) -> Dict:
    menu_path = os.path.join(os.path.dirname(__file__), "../../data/menu_data.json")
    with open(menu_path, "r", encoding="utf-8") as f:
        menu_data = json.load(f)
    all_items = []
    for store, items in menu_data.items():
        for item in items:
            if item["available"]:
                item["store"] = store
                all_items.append(item)
    if preference:
        pref_lower = preference.lower()
        if "甜" in pref_lower or "奶茶" in pref_lower:
            filtered = [i for i in all_items if i["category"] == "奶茶"]
        elif "酸" in pref_lower or "果茶" in pref_lower or "清爽" in pref_lower:
            filtered = [i for i in all_items if i["category"] == "果茶"]
        elif "纯茶" in pref_lower or "茶" in pref_lower:
            filtered = [i for i in all_items if i["category"] == "纯茶"]
        else:
            filtered = all_items
    else:
        filtered = all_items
    filtered.sort(key=lambda x: x["sales"], reverse=True)
    top3 = filtered[:3]
    return {
        "success": True,
        "data": top3,
        "count": len(top3),
        "preference": preference or "热门推荐",
        "response": f"根据{'您的偏好：'+preference if preference else '热门销量'}，为您推荐：{', '.join([i['name'] for i in top3])}。"
    }


TOOL_REGISTRY["query_promotions"] = {
    "name": "query_promotions",
    "description": "查询当前优惠活动",
    "handler": query_promotions,
    "parameters": {}
}

TOOL_REGISTRY["query_customize"] = {
    "name": "query_customize",
    "description": "查询饮品加料和定制选项",
    "handler": query_customize,
    "parameters": {
        "item_name": {"type": "string", "required": True, "description": "饮品名称"}
    }
}

TOOL_REGISTRY["query_history"] = {
    "name": "query_history",
    "description": "查询用户历史订单",
    "handler": query_history,
    "parameters": {
        "user_id": {"type": "string", "required": True, "description": "用户手机号"},
        "limit": {"type": "integer", "required": False, "description": "返回数量"}
    }
}

TOOL_REGISTRY["query_recommend"] = {
    "name": "query_recommend",
    "description": "智能推荐饮品",
    "handler": query_recommend,
    "parameters": {
        "preference": {"type": "string", "required": False, "description": "口味偏好（甜/酸/果茶/奶茶）"},
        "season": {"type": "string", "required": False, "description": "季节"}
    }
}

def get_tool_registry():
    """获取工具注册表"""
    return TOOL_REGISTRY

if __name__ == "__main__":
    # 测试菜单查询
    print("=" * 60)
    print("测试菜单查询")
    print("=" * 60)
    print(query_menu())
    print(query_menu("茶颜悦色", keyword="拿铁"))
    
    # 测试订单查询
    print("\n" + "=" * 60)
    print("测试订单查询")
    print("=" * 60)
    print(query_order("13800138000"))
    
    # 测试库存查询
    print("\n" + "=" * 60)
    print("测试库存查询")
    print("=" * 60)
    print(check_stock("幽兰拿铁"))
    
    # 测试投诉处理
    print("\n" + "=" * 60)
    print("测试投诉处理")
    print("=" * 60)
    print(log_complaint("user_001", "太甜了喝不下去", severity="普通"))