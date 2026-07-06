import re
import json
import os
import random
import time
from collections import deque

try:
    import requests
except:
    requests = None

# ==================== 关键词 & 配置 ====================

INTENT_KEYWORDS = {
    "complaint_taste": ["太甜", "太酸", "太苦", "难喝", "不好喝", "口感", "味道怪", "喝不下"],
    "complaint_quantity": ["份量", "分量", "冰块太多", "配料少", "珍珠少", "料少"],
    "complaint_service": ["服务差", "态度差", "电话打不通", "备注没按", "服务不好"],
    "complaint_delivery": ["配送慢", "超时", "送得晚", "等太久", "包装破了"],
    "complaint_price": ["太贵", "价格高", "不值", "被坑了", "性价比低"],
    "complaint_refund": ["退款", "退钱", "要求退款", "申请退款"],
    "complaint_sarcasm": ["呵呵", "绝了", "也是绝了", "真是", "一言难尽"],
    "complaint_accessory": ["吸管", "冰沙", "细吸管"],
    "query_recommend": ["推荐", "招牌", "热门", "特色", "好喝", "有什么好喝"],
    "query_menu": ["菜单", "饮品", "有什么", "菜单发一下"],
    "query_order": ["订单", "单号", "配送", "送到", "查订单", "我的单"],
    "query_refund": ["退款", "退钱", "售后", "怎么退款"],
    "query_hours": ["几点关门", "几点开门", "营业时间"],
    "query_location": ["门店", "地址", "附近", "在哪", "附近有门店吗"],
    "query_store": ["门店", "店铺", "店", "地址", "位置"],
    "query_price": ["多少钱", "价格", "贵不贵", "价位"],
    "query_temp": ["热", "冰", "温度", "热的", "冰的", "温的"],
    "query_delivery": ["外卖", "配送", "能送", "送到"],
    "query_promotion": ["优惠", "活动", "折扣", "特价", "第二杯半价"],
    "query_member": ["会员", "会员卡", "积分", "会员权益"],
    "query_invoice": ["发票", "开票", "开发票"],
    "query_customize": ["加料", "配料", "珍珠", "椰果", "仙草", "芋圆", "定制"],
    "query_history": ["历史订单", "之前的订单", "买过", "订单记录"],
    "place_order": ["点", "买", "下单", "来一杯", "我要"],
    "unclear": ["那个", "跟之前一样", "上次那个", "还行吧"],
}

CATEGORY_MAP = {
    "complaint_taste": "口感投诉", "complaint_quantity": "份量投诉",
    "complaint_service": "服务投诉", "complaint_delivery": "配送投诉",
    "complaint_price": "价格投诉", "complaint_refund": "退款投诉",
    "complaint_sarcasm": "讽刺投诉", "complaint_accessory": "配件投诉",
    "query_recommend": "推荐查询", "query_menu": "菜单查询",
    "query_order": "订单查询", "query_refund": "退款查询",
    "query_hours": "营业时间查询", "query_location": "门店查询",
    "query_store": "门店查询", "query_price": "价格查询",
    "query_temp": "温度查询", "query_delivery": "配送查询",
    "query_promotion": "优惠查询", "query_member": "会员查询",
    "query_invoice": "发票查询", "query_customize": "加料定制",
    "query_history": "历史订单", "place_order": "下单",
    "general": "通用", "unclear": "不明确",
}

RULE_PATTERNS = {
    "complaint_taste": [re.compile(r"(太甜|太酸|太苦|难喝|不好喝|口感不好|味道怪|喝不下)", re.I)],
    "complaint_quantity": [re.compile(r"(份量|分量|量).*?(少|小|不够)", re.I), re.compile(r"(冰块).*?(太多|全是)", re.I)],
    "complaint_service": [re.compile(r"(服务|态度).*?(差|不好|恶劣)", re.I)],
    "complaint_delivery": [re.compile(r"(配送|送达|送).*?(慢|超时|晚)", re.I)],
    "complaint_price": [re.compile(r"(贵|价格).*?(高|不值)", re.I)],
    "complaint_refund": [re.compile(r"(要求退款|申请退款|我要退款)", re.I)],
    "complaint_sarcasm": [re.compile(r"(呵呵|绝了|也是绝了|太坑了)", re.I)],
    "complaint_accessory": [re.compile(r"(吸管).*?(细|怎么喝)", re.I)],
    "query_recommend": [re.compile(r"(推荐|招牌|热门|特色|新品|必点)", re.I), re.compile(r"(有什么).*?(好喝|推荐)", re.I)],
    "query_menu": [re.compile(r"(菜单|饮品).*?(列出|看看|都有)", re.I), re.compile(r"(有什么).*?(喝的|饮品)", re.I)],
    "query_order": [re.compile(r"(订单|单号).*?(查询|状态|进度|到哪)", re.I), re.compile(r"(订单).*?(\d{5,})|(\d{5,}).*?(订单)", re.I)],
    "query_hours": [re.compile(r"(营业时间|开门|关门|几点开门)", re.I)],
    "query_location": [re.compile(r"(门店|地址|位置)", re.I), re.compile(r"(附近|周边).*?(有|店|奶茶)", re.I)],
    "query_price": [re.compile(r"(多少钱|价格|贵不贵)", re.I)],
    "query_promotion": [re.compile(r"(优惠|活动|折扣|券).*?(有|今天)", re.I), re.compile(r"(有什么|今天).*?(优惠|活动|折扣)", re.I)],
    "query_customize": [re.compile(r"(加料|配料|珍珠|椰果).*?(可以|能加|有哪些)", re.I)],
    "query_history": [re.compile(r"(历史订单|之前.*?(订单|买过))", re.I)],
    "place_order": [re.compile(r"(点|买|要).*?(一杯|奶茶|饮品)", re.I), re.compile(r"(下单|来一杯)", re.I)],
    "unclear": [re.compile(r"(那个)$|(跟之前一样|上次那个)", re.I)],
}

PRIORITY_ORDER = [
    "complaint_sarcasm", "complaint_refund", "complaint_accessory",
    "complaint_taste", "complaint_delivery", "complaint_service",
    "complaint_price", "complaint_quantity",
    "query_order", "query_refund", "query_hours", "query_price",
    "query_store", "query_location", "query_promotion",
    "query_recommend", "query_menu", "query_customize",
    "place_order", "unclear",
]

COMPOSITE_PATTERNS = [
    (re.compile(r"(太甜).*?(还.*?贵|又.*?贵)", re.I), ["complaint_taste", "complaint_price"]),
    (re.compile(r"(料.*?少).*?(还.*?甜|又.*?甜)", re.I), ["complaint_quantity", "complaint_taste"]),
]

DIRECT_RESPONSES = {
    "query_recommend": "招牌饮品：芝芝莓莓、杨枝甘露、茉莉绿茶。您喜欢什么口味？",
    "query_menu": "菜单分芝士、鲜果茶、奶茶、纯茶系列，人均8-20元。",
    "query_hours": "武汉大学店10:00-22:00，银泰店10:00-21:30。",
    "query_location": "附近门店：武汉大学梅园店、银泰创意城店、街道口店。",
    "query_price": "饮品8-20元不等，具体看菜单。",
    "query_temp": "支持热、温、冰三种温度。",
    "query_delivery": "支持外卖，满20免配送费。",
    "query_promotion": "今日优惠：新品第二杯半价，会员9折。",
    "query_member": "会员卡免费办理，首单立减5元。",
    "query_invoice": "支持电子发票，小程序申请。",
}

COMPLAINT_RESPONSES = {
    "complaint_taste": "抱歉口感不符预期，核实后为您重做或退款。",
    "complaint_quantity": "抱歉份量不足，已记录并安排补偿。",
    "complaint_service": "抱歉服务不佳，已通知门店整改。",
    "complaint_delivery": "抱歉配送超时，已申请超时赔付。",
    "complaint_price": "抱歉价格问题，核实后提供优惠券补偿。",
}

INTENT_TOOL = {
    "query_location": "query_stores", "query_menu": "query_menu",
    "query_order": "query_order", "query_promotion": "query_promotions",
    "query_customize": "query_customize", "query_history": "query_history",
    "query_recommend": "query_recommend",
    "complaint_taste": "log_complaint", "complaint_quantity": "log_complaint",
    "complaint_service": "log_complaint", "complaint_delivery": "log_complaint",
    "complaint_price": "log_complaint",
}

PARAM_EXTRACTORS = {
    "location": lambda text: re.search(r"(在|附近|周边)\s*([\u4e00-\u9fa5]{2,})", text),
    "order_id": lambda text: re.search(r"(\d{5,})", text),
    "user_id": lambda text: "default_user",
    "complaint": lambda text: text,
}

# ==================== 意图识别 ====================

def _calculate_confidence(pattern, match_text, text_length):
    base = 0.5 + min(len(pattern.pattern) // 3, 0.3)
    if "*?" in pattern.pattern: base = min(base, 0.55)
    ratio = len(match_text) / text_length if text_length else 0
    bonus = 0.15 if ratio >= 0.7 else 0.1 if ratio >= 0.5 else 0.05 if ratio >= 0.3 else 0
    return min(base + bonus, 0.95)

def _rule_match(text):
    matched = []
    for intent_name, patterns in RULE_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                matched.append((intent_name, match.group(), _calculate_confidence(pattern, match.group(), len(text))))
    if matched:
        for priority in PRIORITY_ORDER:
            hits = [m for m in matched if m[0] == priority]
            if hits:
                return hits[0]
        return sorted(matched, key=lambda x: -x[2])[0]
    return None

def _multi_keyword_match(text):
    best, score = None, 0
    for intent_name, keywords in INTENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            s = count / len(keywords)
            if count >= 2: s = min(s * 1.2, 0.95)
            if s > score: score, best = s, intent_name
    return (best, score) if best and score >= 0.4 else None

def _composite_match(text):
    for pattern, intent_names in COMPOSITE_PATTERNS:
        if pattern.search(text):
            return {"name": "composite", "sub_intents": intent_names}
    return None

def recognize_intent(text, llm_client=None):
    rule = _rule_match(text)
    composite = _composite_match(text)
    if composite: return {"name": "composite", "confidence": 0.85, "category": "复合意图", "sub_intents": composite["sub_intents"]}
    if rule:
        name, kw, conf = rule
        return {"name": name, "confidence": conf, "category": CATEGORY_MAP.get(name, "通用"), "keywords": [kw]}
    kw_match = _multi_keyword_match(text)
    if kw_match:
        name, score = kw_match
        return {"name": name, "confidence": min(score + 0.2, 0.9), "category": CATEGORY_MAP.get(name, "通用")}
    if llm_client:
        try:
            prompt = f"判断用户意图：'{text}'\n可选：{', '.join(INTENT_KEYWORDS.keys())}"
            resp = llm_client([{"role": "user", "content": prompt}], max_tokens=20, temperature=0.1)
            if resp.strip() in CATEGORY_MAP:
                return {"name": resp.strip(), "confidence": 0.6, "category": CATEGORY_MAP.get(resp.strip(), "通用")}
        except: pass
    return {"name": "general", "confidence": 0.2, "category": "通用"}

# ==================== 工具函数 ====================

def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def query_menu(store_name=None, keyword=None, category=None, data_dir="data"):
    menu_data = _read_json(os.path.join(data_dir, "menu_data.json"))
    if not store_name:
        hot = []
        for store, items in menu_data.items():
            available = [i for i in items if i["available"]]
            if available: hot.append({"store": store, **max(available, key=lambda x: x["sales"])})
        return {"success": True, "data": hot, "stores": list(menu_data.keys())}
    matched = next((n for n in menu_data if store_name.lower() in n.lower()), None)
    if not matched: return {"success": False, "data": []}
    items = menu_data[matched]
    filtered = [i for i in items if i["available"]]
    if keyword: filtered = [i for i in filtered if keyword.lower() in i["name"].lower()]
    if category: filtered = [i for i in filtered if i["category"] == category]
    return {"success": True, "data": filtered, "store": matched}

def query_stores(location, radius=3000, data_dir="data"):
    if not requests:
        return {"success": True, "data": [
            {"name": f"{location}附近门店1", "address": f"{location}街道1号"},
            {"name": f"{location}附近门店2", "address": f"{location}街道2号"},
        ], "count": 2}
    url = "https://restapi.amap.com/v3/geocode/geo"
    key = os.environ.get("AMAP_API_KEY", "")
    geocode = requests.get(url, params={"key": key, "address": location, "city": "武汉"}, timeout=5).json()
    if geocode.get("status") != "1": return {"success": False, "data": []}
    loc = geocode["geocodes"][0]["location"].split(",")
    around = requests.get("https://restapi.amap.com/v3/place/around", params={
        "key": key, "location": f"{loc[0]},{loc[1]}", "keywords": "奶茶", "radius": radius
    }, timeout=5).json()
    if around.get("status") != "1": return {"success": False, "data": []}
    return {"success": True, "data": around["pois"], "count": len(around["pois"])}

def query_order(user_id, order_id=None, data_dir="data"):
    orders = _read_json(os.path.join(data_dir, "orders_mock.json"))
    user_orders = orders.get(f"user_{user_id}", [])
    if order_id: user_orders = [o for o in user_orders if o["order_id"] == order_id]
    return {"success": True, "data": user_orders, "count": len(user_orders)}

def check_stock(item_name, store_name=None):
    hot = ["幽兰拿铁", "多肉葡萄", "霸气芝士草莓", "珍珠奶茶"]
    available = random.choice([True, True, False]) if item_name in hot else random.choice([True, True, True, False])
    return {"success": True, "item": item_name, "available": available, "quantity": random.randint(0, 50) if available else 0}

def log_complaint(user_id, complaint, severity="普通", category="口味"):
    complaint_id = f"CMP-{int(time.time())}"
    log_path = os.path.join("data", "complaints.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{complaint_id} | {user_id} | {severity} | {category} | {complaint}\n")
    return {"success": True, "complaint_id": complaint_id}

def query_promotions(data_dir="data"):
    promo = _read_json(os.path.join(data_dir, "promotions.json"))
    return {"success": True, "data": promo.get("active", [])}

def query_customize(item_name):
    toppings = [{"name": t, "price": 3 if t in ["珍珠", "椰果"] else 4} for t in ["珍珠", "椰果", "仙草冻", "芋圆", "布丁"]]
    return {"success": True, "item": item_name, "toppings": toppings, "sugar": ["标准糖", "七分糖", "五分糖", "三分糖", "无糖"]}

def query_history(user_id, limit=3, data_dir="data"):
    orders = _read_json(os.path.join(data_dir, "orders_mock.json"))
    return {"success": True, "data": orders.get(f"user_{user_id}", [])[:limit]}

def query_recommend(preference=None, data_dir="data"):
    menu = _read_json(os.path.join(data_dir, "menu_data.json"))
    all_items = []
    for store, items in menu.items():
        all_items.extend([{**i, "store": store} for i in items if i["available"]])
    if preference:
        if "甜" in preference or "奶茶" in preference: all_items = [i for i in all_items if i["category"] == "奶茶"]
        elif "酸" in preference or "果茶" in preference: all_items = [i for i in all_items if i["category"] == "果茶"]
    all_items.sort(key=lambda x: x["sales"], reverse=True)
    return {"success": True, "data": all_items[:3]}

TOOLS = {
    "query_menu": query_menu, "query_stores": query_stores, "query_order": query_order,
    "check_stock": check_stock, "log_complaint": log_complaint,
    "query_promotions": query_promotions, "query_customize": query_customize,
    "query_history": query_history, "query_recommend": query_recommend,
}

# ==================== 路由 & 参数提取 ====================

def extract_params(text, intent_name):
    params = {}
    tool_name = INTENT_TOOL.get(intent_name)
    if tool_name == "query_stores":
        match = PARAM_EXTRACTORS["location"](text)
        if match: params["location"] = match.group(2)
    elif tool_name in ["query_order", "query_history"]:
        match = PARAM_EXTRACTORS["order_id"](text)
        if match: params["order_id"] = match.group(1)
    elif tool_name == "log_complaint":
        params["user_id"] = PARAM_EXTRACTORS["user_id"](text)
        params["complaint"] = PARAM_EXTRACTORS["complaint"](text)
    return params

def get_tool_response(intent_name, text, tools=TOOLS):
    tool_name = INTENT_TOOL.get(intent_name)
    if not tool_name or tool_name not in tools: return None
    params = extract_params(text, intent_name)
    return tools[tool_name](**params)

# ==================== 记忆管理 ====================

def create_memory_store(window_size=5):
    return {"sessions": {}, "window_size": window_size}

def save_message(store, session_id, user_msg, agent_msg):
    if session_id not in store["sessions"]:
        store["sessions"][session_id] = {"history": deque(maxlen=store["window_size"]), "preferences": {}}
    store["sessions"][session_id]["history"].append({"user": user_msg, "agent": agent_msg})
    _extract_prefs(store["sessions"][session_id]["preferences"], user_msg)

def _extract_prefs(prefs, text):
    sugar_map = {"无糖": ["无糖", "零糖"], "三分糖": ["少糖"], "五分糖": ["半糖"]}
    ice_map = {"热": ["热饮"], "去冰": ["去冰"], "少冰": ["少冰"]}
    for level, patterns in sugar_map.items():
        if any(p in text for p in patterns): prefs["sugar"] = level
    for level, patterns in ice_map.items():
        if any(p in text for p in patterns): prefs["ice"] = level

def get_context(store, session_id):
    sess = store["sessions"].get(session_id)
    if not sess: return ""
    parts = []
    if sess["preferences"]:
        parts.append(f"偏好: {', '.join([f'{k}={v}' for k, v in sess['preferences'].items()])}")
    for msg in sess["history"]:
        parts.append(f"用户: {msg['user']}")
        parts.append(f"客服: {msg['agent']}")
    return "\n".join(parts)

# ==================== Agent核心 ====================

def build_response(intent, text, tool_result=None):
    if intent["name"].startswith("complaint"):
        if tool_result and tool_result["success"]:
            return f"【思考】{intent['name']}\n【行动】记录投诉\n【回复】{COMPLAINT_RESPONSES.get(intent['name'], '抱歉给您带来不好的体验。')}"
        return f"【思考】{intent['name']}\n【回复】{COMPLAINT_RESPONSES.get(intent['name'], '抱歉给您带来不好的体验。')}"
    if intent["name"].startswith("query"):
        if tool_result and tool_result["success"]:
            return f"【思考】{intent['name']}\n【行动】调用工具\n【回复】{_format_tool_result(intent['name'], tool_result)}"
        return f"【思考】{intent['name']}\n【回复】{DIRECT_RESPONSES.get(intent['name'], '请告诉我具体查询内容。')}"
    if intent["name"] in ["place_order", "order_modify"]:
        return f"【思考】{intent['name']}\n【回复】请提供您想点的饮品名称。"
    return f"【思考】{intent['name']}\n【回复】{DIRECT_RESPONSES.get(intent['name'], '您好，有什么可以帮助您的？')}"

def _format_tool_result(intent_name, result):
    if intent_name == "query_stores":
        names = [p.get("name", "") for p in result["data"][:3]]
        return f"附近门店：{', '.join(names)}。"
    if intent_name == "query_menu":
        names = [i.get("name", "") for i in result["data"][:3]]
        return f"饮品：{', '.join(names)}。"
    if intent_name == "query_order":
        if result["data"]:
            return f"订单状态：{result['data'][0].get('status', '')}。"
        return "未找到订单记录。"
    return "查询完成。"

def process_message(text, session_id="default", memory_store=None, llm_client=None):
    intent = recognize_intent(text, llm_client)
    tool_result = get_tool_response(intent["name"], text)
    response = build_response(intent, text, tool_result)
    if memory_store:
        save_message(memory_store, session_id, text, response)
    return response, intent

# ==================== 测试 ====================

def test_agent():
    store = create_memory_store()
    test_cases = [
        ("太甜了喝不下去", "complaint_taste"),
        ("附近有门店吗", "query_location"),
        ("推荐一款饮品", "query_recommend"),
        ("订单12345", "query_order"),
        ("今天有什么优惠", "query_promotion"),
    ]
    correct = sum(1 for text, expected in test_cases if recognize_intent(text)["name"] == expected)
    print(f"准确率: {correct}/{len(test_cases)} ({correct/len(test_cases)*100:.0f}%)")
    return correct == len(test_cases)

if __name__ == "__main__":
    test_agent()