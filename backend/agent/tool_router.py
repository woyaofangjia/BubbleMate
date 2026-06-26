import re
from typing import Dict, List, Optional, Any

from .keywords import STORE_KEYWORDS, DRINK_KEYWORDS, CATEGORY_KEYWORDS, INGREDIENT_KEYWORDS, COMPLAINT_CATEGORY_MAP

TOOL_SCHEMAS = {
    "query_stores": {
        "params": {"location": {"required": True, "desc": "位置关键词"}},
        "intent_mapping": ["query_location"],
        "clarification": "请问您在哪个位置/商圈？"
    },
    "query_menu": {
        "params": {"category": {"required": False, "desc": "饮品类别"}, "keyword": {"required": False, "desc": "搜索关键词"}},
        "intent_mapping": ["query_menu", "query_recommend", "query_price"],
        "clarification": "请问您想了解哪个系列或哪款饮品？"
    },
    "query_order": {
        "params": {"order_id": {"required": True, "desc": "订单编号"}, "phone_number": {"required": False, "desc": "手机号码"}},
        "intent_mapping": ["query_order"],
        "clarification": "请提供您的订单号（如12345）"
    },
    "check_stock": {
        "params": {"store_id": {"required": True, "desc": "门店名称"}, "ingredient": {"required": False, "desc": "原料名称"}},
        "intent_mapping": ["query_inventory"],
        "clarification": "请提供门店名称（如武汉大学店、银泰店）"
    },
    "log_complaint": {
        "params": {"user_id": {"required": True, "desc": "用户ID"}, "complaint": {"required": True, "desc": "投诉内容"}, "category": {"required": False, "desc": "投诉类型"}, "severity": {"required": False, "desc": "严重程度"}},
        "intent_mapping": ["complaint_taste", "complaint_quantity", "complaint_service", "complaint_delivery", "complaint_price"],
        "clarification": "请提供订单号（如有）"
    }
}

INTENT_TOOL = {}
for tool_name, schema in TOOL_SCHEMAS.items():
    for intent in schema["intent_mapping"]:
        INTENT_TOOL[intent] = tool_name

def get_tool_name(intent_name: str) -> Optional[str]:
    return INTENT_TOOL.get(intent_name)

def route(intent_name: str) -> Optional[Dict]:
    tool_name = INTENT_TOOL.get(intent_name)
    return TOOL_SCHEMAS.get(tool_name) if tool_name else None

def extract_params(user_input: str, schema: Dict) -> Dict[str, Any]:
    params = {}
    for param_name, config in schema["params"].items():
        if param_name == "location":
            for kw in STORE_KEYWORDS:
                if kw in user_input:
                    params["location"] = kw
                    break
            if "location" not in params:
                match = re.search(r"(在|附近|周边)\s*([\u4e00-\u9fa5]{2,})", user_input)
                if match:
                    candidate = match.group(2).strip()
                    exclude_words = ["门店", "奶茶", "店", "有", "的", "吗", "卖"]
                    if not any(exclude in candidate for exclude in exclude_words):
                        params["location"] = candidate
        elif param_name == "order_id":
            match = re.search(r"(\d{5,})", user_input)
            if match:
                params["order_id"] = match.group(1)
        elif param_name == "phone_number":
            match = re.search(r"(\d{11})", user_input)
            if match:
                params["phone_number"] = match.group(1)
        elif param_name == "category":
            for cat, cat_name in CATEGORY_KEYWORDS.items():
                if cat in user_input:
                    params["category"] = cat_name
                    break
        elif param_name == "keyword":
            for kw in DRINK_KEYWORDS:
                if kw in user_input:
                    params["keyword"] = kw
                    break
        elif param_name == "store_id":
            for kw in STORE_KEYWORDS:
                if kw in user_input:
                    params["store_id"] = kw
                    break
        elif param_name == "ingredient":
            for kw in INGREDIENT_KEYWORDS:
                if kw in user_input:
                    params["ingredient"] = kw
                    break
        elif param_name == "user_id":
            params["user_id"] = "default_user"
        elif param_name == "complaint":
            params["complaint"] = user_input
        elif param_name == "category":
            for keyword, category in COMPLAINT_CATEGORY_MAP.items():
                if keyword in user_input:
                    params["category"] = category
                    break
        elif param_name == "description":
            params["description"] = user_input
    return params

def check_params(user_input: str, schema: Dict) -> Dict:
    extracted = extract_params(user_input, schema)
    required = [p for p, c in schema["params"].items() if c["required"]]
    missing = [p for p in required if p not in extracted or not extracted[p]]
    if missing:
        return {"status": "incomplete", "missing_params": missing, "suggestion": schema["clarification"]}
    return {"status": "complete", "params": extracted}