import re
import json
import os
import random
import time
import sqlite3
import asyncio
import difflib
from collections import deque
from functools import lru_cache

try:
    import requests
except:
    requests = None

try:
    from storage.database import save_session, get_user_by_session, save_user_preference, get_user_preferences, save_complaint, save_complaint_with_candidate, get_knowledge_graph, save_knowledge as _save_knowledge, save_complaint_db as _save_complaint_db, get_complaint_stats
    from storage.data_access import get_shops, get_menu_items, get_orders, get_inventory, get_shop_by_name
except:
    save_session = lambda s, u: None
    get_user_by_session = lambda s: None
    save_user_preference = lambda u, k, v: None
    get_shops = lambda **kwargs: []
    get_menu_items = lambda **kwargs: []
    get_orders = lambda **kwargs: []
    get_inventory = lambda **kwargs: []
    get_shop_by_name = lambda name: None
    get_user_preferences = lambda u: {}
    save_complaint = lambda u, d: None
    save_complaint_with_candidate = lambda u, ct, d: (None, None)
    get_knowledge_graph = lambda: []
    _save_knowledge = lambda ct, s, c: None
    _save_complaint_db = lambda u, ct, d: None
    get_complaint_stats = lambda: {"by_type": []}

# ==================== Harness自我反思 ====================

def reflect_on_result(tool_name, params, result, intent_name, user_query):
    assessment = "reasonable"
    confidence = 0.8
    suggestions = []
    
    if not result:
        return {"assessment": "unreasonable", "confidence": 0.9, "suggestions": ["工具未调用，需要重新规划"]}
    
    success = result.get("success", False)
    data = result.get("data", [])
    
    if not success:
        error = result.get("error", "")
        if "超时" in error:
            assessment = "unreasonable"
            suggestions.append("工具执行超时，尝试减少参数复杂度")
        elif "失败" in error:
            assessment = "partial"
            suggestions.append("工具调用失败，尝试替代方案")
        elif intent_name.startswith("query"):
            assessment = "partial"
            if intent_name == "query_location" or intent_name == "query_store":
                suggestions.append("查询结果为空，尝试询问用户具体位置")
            elif intent_name == "query_order" or intent_name == "query_history":
                suggestions.append("查询结果为空，尝试询问用户订单号")
            elif intent_name == "query_menu":
                suggestions.append("查询结果为空，尝试询问用户具体门店")
            else:
                suggestions.append("查询结果为空，尝试询问用户更具体的信息")
            confidence = 0.5
        else:
            assessment = "unreasonable"
            suggestions.append(f"工具返回错误: {error}")
            confidence = 0.3
    else:
        if intent_name == "query_location" and (not data or len(data) == 0):
            assessment = "partial"
            suggestions.append("未找到门店，尝试询问用户具体位置")
            confidence = 0.5
        
        elif intent_name == "query_order" and (not data or len(data) == 0):
            assessment = "partial"
            suggestions.append("未找到订单，尝试询问用户订单号")
            confidence = 0.5
        
        elif intent_name == "query_menu" and (not data or len(data) == 0):
            assessment = "unreasonable"
            suggestions.append("菜单查询失败，检查数据源")
            confidence = 0.2
        
        elif intent_name.startswith("complaint") and tool_name == "log_complaint":
            complaint_id = result.get("complaint_id")
            if complaint_id:
                assessment = "reasonable"
                confidence = 0.9
            else:
                assessment = "partial"
                suggestions.append("投诉记录可能未保存成功")
                confidence = 0.5
        
        else:
            if data and len(data) > 0:
                assessment = "reasonable"
                confidence = 0.8
            else:
                assessment = "partial"
                suggestions.append("返回数据为空，可能需要调整参数")
                confidence = 0.5
    
    if assessment == "reasonable" and suggestions:
        assessment = "partial"
    
    return {
        "assessment": assessment,
        "confidence": confidence,
        "suggestions": suggestions,
        "tool_name": tool_name,
        "params": params,
        "result_summary": {"success": success, "data_count": len(data) if isinstance(data, list) else 0},
    }

REFLECTION_ASSESSMENT = {
    "reasonable": "完全合理，继续",
    "partial": "部分合理，需要调整",
    "unreasonable": "完全不合理，需要换方案",
}

# ==================== Harness错误恢复 ====================

def recover_from_failure(reflection_result, intent_name, user_query, session_id=None):
    assessment = reflection_result["assessment"]
    suggestions = reflection_result["suggestions"]
    
    recovery_plan = {
        "action": "continue",
        "reason": "",
        "new_intent": None,
        "new_params": None,
        "clarification": None,
    }
    
    if assessment == "reasonable":
        recovery_plan["action"] = "continue"
        return recovery_plan
    
    fallback_intents = {
        "query_location": ["query_store"],
        "query_store": ["query_location"],
        "query_order": ["query_history"],
        "query_history": ["query_order"],
        "query_refund": ["query_order"],
        "query_menu": ["query_recommend"],
        "query_recommend": ["query_menu"],
    }
    
    if assessment == "partial":
        if "订单号" in suggestions[0]:
            recovery_plan["action"] = "clarify"
            recovery_plan["clarification"] = "请问您能提供一下订单号吗？这样我可以帮您查询相关信息。"
        elif "具体位置" in suggestions[0] or "门店" in suggestions[0]:
            recovery_plan["action"] = "clarify"
            recovery_plan["clarification"] = "请问您想查询哪个位置附近的门店呢？比如街道名或地标。"
        elif "具体信息" in suggestions[0]:
            if intent_name == "query_location" or intent_name == "query_store":
                recovery_plan["action"] = "clarify"
                recovery_plan["clarification"] = "请问您想查询哪个位置附近的门店呢？"
            elif intent_name == "query_order" or intent_name == "query_history":
                recovery_plan["action"] = "clarify"
                recovery_plan["clarification"] = "请问您能提供一下订单号吗？"
            elif intent_name == "query_menu":
                recovery_plan["action"] = "clarify"
                recovery_plan["clarification"] = "请问您想查询哪个门店的菜单呢？"
            else:
                recovery_plan["action"] = "clarify"
                recovery_plan["clarification"] = "抱歉，我需要更多信息才能帮您处理，请问您可以再详细描述一下吗？"
        elif "调整参数" in suggestions[0]:
            recovery_plan["action"] = "retry_with_adjustment"
            recovery_plan["reason"] = "参数需要调整，尝试使用默认参数"
            recovery_plan["new_params"] = {}
        elif "替代方案" in suggestions[0]:
            recovery_plan["action"] = "switch_tool"
            recovery_plan["new_intent"] = fallback_intents.get(intent_name)
            recovery_plan["reason"] = f"尝试替代工具: {recovery_plan['new_intent']}"
        else:
            recovery_plan["action"] = "clarify"
            recovery_plan["clarification"] = "抱歉，我需要更多信息才能帮您处理，请问您可以再详细描述一下吗？"
    
    elif assessment == "unreasonable":
        alternative = fallback_intents.get(intent_name)
        if alternative:
            recovery_plan["action"] = "switch_tool"
            recovery_plan["new_intent"] = alternative
            recovery_plan["reason"] = f"原方案完全失败，切换到替代工具: {alternative}"
        elif intent_name.startswith("query"):
            recovery_plan["action"] = "clarify"
            recovery_plan["clarification"] = "抱歉，我需要更多信息才能帮您查询，请问您可以提供更具体的信息吗？"
        else:
            recovery_plan["action"] = "human_handover"
            recovery_plan["reason"] = "系统无法处理，需要转人工"
    
    return recovery_plan

# ==================== Harness任务终止判断 ====================

TERMINATION_KEYWORDS = {
    "positive": ["好的", "谢谢", "感谢", "没问题", "可以", "搞定", "解决了", "拜拜", "再见"],
    "negative": ["不行", "不好", "不满意", "换人工", "找客服", "人工客服"],
}

def should_terminate(user_query, trace, max_retries=3, max_rounds=5):
    user_query_lower = user_query.lower()
    
    for kw in TERMINATION_KEYWORDS["positive"]:
        if kw in user_query_lower:
            return {"terminate": True, "reason": "用户表示满意", "action": "end_conversation"}
    
    for kw in TERMINATION_KEYWORDS["negative"]:
        if kw in user_query_lower:
            return {"terminate": True, "reason": "用户要求转人工", "action": "human_handover"}
    
    if trace.retry_count >= max_retries:
        return {"terminate": True, "reason": f"连续重试{max_retries}次失败", "action": "human_handover"}
    
    if len(trace.steps) >= max_rounds * 2:
        return {"terminate": True, "reason": f"超过{max_rounds}轮对话未解决", "action": "human_handover"}
    
    tool_results = [s for s in trace.steps if s["type"] == "tool_result"]
    if tool_results:
        latest_result = tool_results[-1]["data"]
        if latest_result.get("success") and latest_result.get("data"):
            return {"terminate": True, "reason": "工具返回明确结果", "action": "end_conversation"}
    
    return {"terminate": False, "reason": "继续处理", "action": "continue"}

# ==================== Harness状态恢复 ====================

def recover_state(trace):
    reasonable_steps = [s for s in trace.steps if s["type"] == "reflection" and s["data"].get("assessment") == "reasonable"]
    
    if reasonable_steps:
        latest_reasonable = reasonable_steps[-1]
        previous_step = None
        for i, s in enumerate(trace.steps):
            if s["timestamp"] == latest_reasonable["timestamp"] and i > 0:
                previous_step = trace.steps[i-1]
                break
        
        if previous_step and previous_step["type"] == "intent":
            return {
                "recovered": True,
                "reason": "从最近可靠的意图识别恢复",
                "recovered_intent": previous_step["data"],
                "recovered_step": previous_step,
            }
    
    if len(trace.steps) >= 2:
        second_last = trace.steps[-2]
        if second_last["type"] == "intent":
            return {
                "recovered": True,
                "reason": "从倒数第二步恢复",
                "recovered_intent": second_last["data"],
                "recovered_step": second_last,
            }
    
    return {
        "recovered": False,
        "reason": "无法恢复，需要从头开始",
        "recovered_intent": None,
        "recovered_step": None,
    }

# ==================== Harness执行轨迹 ====================

class ExecutionTrace:
    def __init__(self):
        self.steps = []
        self.session_id = None
        self.max_steps = 10
        self.retry_count = 0
    
    def add_step(self, step_type, data):
        step = {
            "type": step_type,
            "timestamp": time.time(),
            "data": data,
            "retry_count": self.retry_count,
        }
        self.steps.append(step)
        if len(self.steps) > self.max_steps:
            self.steps = self.steps[-self.max_steps:]
    
    def get_latest(self, step_type=None):
        if step_type:
            return next((s for s in reversed(self.steps) if s["type"] == step_type), None)
        return self.steps[-1] if self.steps else None
    
    def get_trace_summary(self):
        summary = []
        for s in self.steps:
            t = s["type"]
            d = s["data"]
            if t == "intent":
                summary.append(f"意图: {d.get('name')} (置信度:{d.get('confidence', 0):.2f})")
            elif t == "tool_call":
                summary.append(f"工具: {d.get('tool_name')} ({d.get('params', {})})")
            elif t == "tool_result":
                success = d.get("success", False)
                summary.append(f"结果: {'成功' if success else '失败'}")
            elif t == "reflection":
                summary.append(f"反思: {d.get('assessment', '')}")
            elif t == "replan":
                summary.append(f"重规划: {d.get('reason', '')}")
        return "\n".join(summary)
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "steps": self.steps,
            "retry_count": self.retry_count,
            "total_steps": len(self.steps),
        }
    
    def save_to_file(self, filename=None):
        if not filename:
            filename = f"trace_{self.session_id or int(time.time())}.json"
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root_dir, "data", "traces", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

# ==================== 用户映射 ====================

SESSION_TO_USER = {}

def get_user_id(session_id: str) -> str:
    if session_id in SESSION_TO_USER:
        return SESSION_TO_USER[session_id]
    stored = get_user_by_session(session_id)
    if stored:
        SESSION_TO_USER[session_id] = stored
        return stored
    user_id = f"user_{session_id}"
    SESSION_TO_USER[session_id] = user_id
    save_session(session_id, user_id)
    return user_id

# ==================== 关键词 & 配置 ====================

INTENT_KEYWORDS = {
    "complaint_taste": ["太甜", "太酸", "太苦", "难喝", "不好喝", "口感", "味道怪", "喝不下", "糖浆劣质", "巨甜", "像药", "酸死了", "苦死了", "涩", "太淡", "没味道", "香精味"],
    "complaint_quantity": ["份量", "分量", "冰块太多", "配料少", "珍珠少", "料少", "少的可怜", "少得可怜", "只有半杯", "大杯", "送来只有", "太少了", "不够多", "只有一点点", "就几颗"],
    "complaint_service": ["服务差", "态度差", "电话打不通", "备注没按", "服务不好", "联系商家", "不理我", "不理", "不回"],
    "complaint_delivery": ["配送慢", "超时", "送得晚", "等太久", "包装破了", "等了", "还没到", "送错", "漏送", "破损", "撒了"],
    "complaint_price": ["太贵", "价格高", "不值", "被坑了", "性价比低", "又贵"],
    "complaint_refund": ["退款", "退钱", "要求退款", "申请退款"],
    "complaint_sarcasm": ["呵呵", "绝了", "也是绝了", "真是", "太坑了"],
    "complaint_accessory": ["吸管", "冰沙", "细吸管"],
    "complaint_vague": ["那个", "你们懂的", "就是那个", "懂的都懂"],
    "complaint_compare_history": ["上次那个", "跟这次不一样", "之前那次", "换配方", "不一样"],
    "query_recommend": ["推荐", "招牌", "热门", "特色", "好喝", "有什么好喝"],
    "query_menu": ["菜单", "饮品", "有什么", "菜单发一下", "没了", "下架", "不卖了", "没有了", "停售"],
    "query_order": ["订单", "单号", "配送", "送到", "查订单", "我的单"],
    "query_refund": ["退款", "退钱", "售后", "怎么退款"],
    "query_hours": ["几点关门", "几点开门", "营业时间"],
    "query_location": ["门店", "地址", "附近", "在哪", "附近有门店吗", "最近的一家店", "最近的店"],
    "query_store": ["门店", "店铺", "店", "地址", "位置", "在哪"],
    "query_price": ["多少钱", "价格", "贵不贵", "价位"],
    "query_temp": ["热", "冰", "温度", "热的", "冰的", "温的"],
    "query_delivery": ["外卖", "配送", "能送", "送到"],
    "query_promotion": ["优惠", "活动", "折扣", "特价", "第二杯半价", "吗"],
    "query_member": ["会员", "会员卡", "积分", "会员权益"],
    "query_invoice": ["发票", "开票", "开发票"],
    "query_customize": ["加料", "配料", "珍珠", "椰果", "仙草", "芋圆", "定制", "加", "添加"],
    "query_history": ["历史订单", "之前的订单", "买过", "订单记录"],
    "place_order": ["点", "买", "下单", "来一杯", "我要"],
    "unclear": ["那个", "跟之前一样", "上次那个", "还行吧"],
    "general": ["随便", "都行", "没什么事", "没事了", "不用了", "算了"],
}

CATEGORY_MAP = {
    "complaint_taste": "口感投诉", "complaint_quantity": "份量投诉",
    "complaint_service": "服务投诉", "complaint_delivery": "配送投诉",
    "complaint_price": "价格投诉", "complaint_refund": "退款投诉",
    "complaint_sarcasm": "讽刺投诉", "complaint_accessory": "配件投诉",
    "complaint_vague": "指代不明", "complaint_compare_history": "对比投诉",
    "complaint_taste_service": "口感+服务", "complaint_taste_price": "口感+价格",
    "query_recommend": "推荐查询", "query_menu": "菜单查询",
    "query_order": "订单查询", "query_refund": "退款查询",
    "query_hours": "营业时间查询", "query_location": "门店查询",
    "query_store": "门店查询", "query_price": "价格查询",
    "query_temp": "温度查询", "query_delivery": "配送查询",
    "query_promotion": "优惠查询", "query_member": "会员查询",
    "query_invoice": "发票查询", "query_customize": "加料定制",
    "query_history": "历史订单", "place_order": "下单",
    "general": "通用", "unclear": "不明确", "unknown": "未知",
}

RULE_PATTERNS = {
    "complaint_taste": [re.compile(r"(太甜|太酸|太苦|难喝|不好喝|口感不好|味道怪|喝不下)", re.I), re.compile(r"(糖浆.*?(劣质|不好)|巨甜|像药)", re.I), re.compile(r"(冰放太多.*?头疼|喝着头疼)", re.I)],
    "complaint_quantity": [re.compile(r"(份量|分量|量).*?(少|小|不够)", re.I), re.compile(r"(冰块).*?(太多|全是)", re.I), re.compile(r"(少的可怜|少得可怜|只有半杯|大杯.*?送来)", re.I)],
    "complaint_service": [re.compile(r"(服务|态度).*?(差|不好|恶劣)", re.I), re.compile(r"(联系商家|商家.*?(不理|不回|没回))", re.I)],
    "complaint_delivery": [re.compile(r"(配送|送达|送).*?(慢|超时|晚)", re.I)],
    "complaint_price": [re.compile(r"(贵|价格).*?(高|不值)", re.I), re.compile(r"(又贵|太贵了)", re.I)],
    "complaint_refund": [re.compile(r"(要求退款|申请退款|我要退款)", re.I)],
    "complaint_sarcasm": [re.compile(r"(呵呵|绝了|也是绝了|太坑了)", re.I)],
    "complaint_accessory": [re.compile(r"(吸管).*?(细|怎么喝)", re.I), re.compile(r"(吸管|配件).*?(少|没|缺失|不见)", re.I)],
    "complaint_vague": [re.compile(r"(就是那个|你们懂的|懂的都懂|又少又难喝)", re.I)],
    "complaint_compare_history": [re.compile(r"(跟这次不一样|换配方)", re.I)],
    "complaint_taste_service": [re.compile(r"(口味|口感|甜|酸|苦|难喝).*?(服务|不理|不回)", re.I)],
    "complaint_taste_price": [re.compile(r"(苦|难喝|甜).*?(贵|不值)", re.I)],
    "query_recommend": [re.compile(r"(推荐|招牌|热门|特色|新品|必点)", re.I), re.compile(r"(有什么).*?(好喝|推荐)", re.I)],
    "query_menu": [re.compile(r"(菜单|饮品).*?(列出|看看|都有)", re.I), re.compile(r"(有什么).*?(喝的|饮品)", re.I), re.compile(r"(上次买的|之前买的).*?(没了|下架|不卖)", re.I)],
    "query_order": [re.compile(r"(订单|单号).*?(查询|状态|进度|到哪)", re.I), re.compile(r"(订单).*?(\d{5,})|(\d{5,}).*?(订单)", re.I), re.compile(r"(查|查看|我的).*?(订单)", re.I), re.compile(r"(查.*?上次点的|上次点的是什么)", re.I)],
    "query_hours": [re.compile(r"(营业时间|开门|关门|几点开门)", re.I)],
    "query_location": [re.compile(r"(门店|地址|位置)", re.I), re.compile(r"(附近|周边).*?(有|店|奶茶)", re.I), re.compile(r"(最近的一家店|最近的店)", re.I)],
    "query_refund": [re.compile(r"(怎么退款|如何退款|退款流程)", re.I), re.compile(r"(可以退吗|能退吗|能退款吗)", re.I)],
    "query_price": [re.compile(r"(多少钱|价格|贵不贵)", re.I)],
    "query_promotion": [re.compile(r"(优惠|活动|折扣|券).*?(有|今天)", re.I), re.compile(r"(有什么|今天).*?(优惠|活动|折扣)", re.I)],
    "query_customize": [re.compile(r"(加料|配料|珍珠|椰果).*?(可以|能加|有哪些)", re.I), re.compile(r"(可以|能).*?(加.*?珍珠|加.*?配料)", re.I), re.compile(r"(我要.*?(少糖|无糖|去冰|少冰)|给我.*?(热|温))", re.I)],
    "query_history": [re.compile(r"(历史订单|之前.*?(订单|买过))", re.I), re.compile(r"(之前点过什么|之前买过什么)", re.I)],
    "place_order": [re.compile(r"(点|买|要).*?(一杯|奶茶|饮品)", re.I), re.compile(r"(下单|来一杯)", re.I)],
    "unclear": [re.compile(r"(那个)$|(跟之前一样|上次那个)", re.I), re.compile(r"(我点的那个|那个饮料|那个吃的)", re.I), re.compile(r"(那个.*?算了|算了吧)", re.I)],
    "general": [re.compile(r"(随便|都行|没什么事|没事了|不用了|算了)", re.I)],
    "unknown": [re.compile(r"^\s*$", re.I)],
}

PRIORITY_ORDER = [
    "complaint_sarcasm", "complaint_refund", "complaint_accessory",
    "complaint_vague", "complaint_compare_history",
    "complaint_taste_service", "complaint_taste_price",
    "complaint_taste", "complaint_delivery", "complaint_service",
    "complaint_price", "complaint_quantity",
    "query_order", "query_refund", "query_hours", "query_price",
    "query_store", "query_location", "query_promotion",
    "query_recommend", "query_menu", "query_customize",
    "place_order", "unclear", "general", "unknown",
]

COMPOSITE_PATTERNS = [
    (re.compile(r"(太甜).*?(还.*?贵|又.*?贵)", re.I), ["complaint_taste", "complaint_price"]),
    (re.compile(r"(料.*?少).*?(还.*?甜|又.*?甜)", re.I), ["complaint_quantity", "complaint_taste"]),
    (re.compile(r"(好喝吗).*?(多少钱|价格)", re.I), ["query_recommend", "query_price"]),
    (re.compile(r"(点.*?一杯|下单).*?(优惠|活动)", re.I), ["place_order", "query_promotion"]),
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
    "query_order": "抱歉，订单查询暂时有点小问题，请您稍后再试，或者拨打客服电话咨询。",
}

INTENT_TO_CATEGORY = {
    "complaint_taste": "口味",
    "complaint_quantity": "份量",
    "complaint_service": "服务",
    "complaint_delivery": "配送",
    "complaint_price": "价格",
    "complaint_refund": "退款",
    "complaint_sarcasm": "讽刺",
    "complaint_accessory": "配件",
    "complaint_vague": "指代不明",
    "complaint_compare_history": "对比",
    "complaint_taste_service": "口感+服务",
    "complaint_taste_price": "口感+价格",
    "unknown": "未知",
}

DEFAULT_SOLUTIONS = {
    "口味": "非常抱歉您对口味不满意，我们会尽快为您处理。",
    "份量": "非常抱歉份量不足，我们会为您补发或补偿。",
    "服务": "非常抱歉服务态度不佳，我们已通知门店整改。",
    "配送": "非常抱歉配送超时，我们会申请超时赔付。",
    "价格": "非常抱歉价格问题，核实后提供优惠券补偿。",
    "退款": "非常抱歉，我们会为您办理退款。",
    "讽刺": "非常抱歉给您带来不好的体验，请问具体是什么问题？",
    "配件": "非常抱歉配件缺失，我们会为您补发。",
    "指代不明": "抱歉，我不太理解您的意思，请问可以再详细描述一下吗？",
    "对比": "非常抱歉给您带来不一致的体验，请问您说的是哪次消费呢？",
    "口感+服务": "非常抱歉您对口味和服务都不满意，我们会全面整改。",
    "口感+价格": "非常抱歉您对口味和价格都不满意，我们会核实处理。",
    "未知": "您好，请问您有什么需要帮助的？",
}

DEFAULT_COMPENSATIONS = {
    "口味": "免费重做或退款",
    "份量": "补发配料或5元优惠券",
    "服务": "赠送饮品券",
    "配送": "超时赔付或免单",
    "价格": "优惠券补偿",
    "退款": "全额退款",
    "讽刺": "请告知具体问题",
    "配件": "补发配件",
    "指代不明": "请详细描述问题",
    "对比": "优惠券或免费饮品",
    "口感+服务": "免费重做+优惠券",
    "口感+价格": "退款或折扣",
}

def get_knowledge_response(intent_name):
    category = INTENT_TO_CATEGORY.get(intent_name)
    if not category:
        return None, None
    graph = get_knowledge_graph()
    for node in graph:
        if node.get("is_active") and node.get("node_name") == category and node.get("node_type") == "complaint":
            solution = ""
            compensation = ""
            for child in node.get("children", []):
                if child.get("node_type") == "solution":
                    solution = child.get("content", "")
                elif child.get("node_type") == "compensation":
                    compensation = child.get("content", "")
            return solution, compensation
    return None, None

INTENT_TOOL = {
    "query_location": "query_stores", "query_menu": "query_menu",
    "query_order": "query_order", "query_promotion": "query_promotions",
    "query_customize": "query_customize", "query_history": "query_history",
    "query_recommend": "query_recommend",
    "query_refund": "query_order",
}

PARAM_EXTRACTORS = {
    "location": lambda text: re.search(r"(在|附近|周边)\s*([\u4e00-\u9fa5]{2,}广场|[\u4e00-\u9fa5]{2,}路|[\u4e00-\u9fa5]{2,}街|[\u4e00-\u9fa5]{2,}店|[\u4e00-\u9fa5]{2,}校区|[\u4e00-\u9fa5]{2,}中心|[\u4e00-\u9fa5]{2,}大厦|[\u4e00-\u9fa5]{2,}商场)", text),
    "order_id": lambda text: re.search(r"(ORD-\d{8}-\d{3}|\d{5,})", text),
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
            if count == 1 and len(keywords) > 10:
                s = min(s * 2, 0.4)
            if count == 1:
                s = min(s * 3, 0.5)
            if s > score: score, best = s, intent_name
    return (best, score) if best and score >= 0.1 else None

def _composite_match(text):
    for pattern, intent_names in COMPOSITE_PATTERNS:
        if pattern.search(text):
            return {"name": "composite", "sub_intents": intent_names}
    return None

def _get_llm_result(text):
    try:
        from backend.core.zhipu_client import call_llm, is_available
        if not is_available():
            return None
        prompt = f"判断用户意图：'{text}'\n可选：{', '.join(INTENT_KEYWORDS.keys())}\n只返回意图名称，不要其他内容。"
        resp = call_llm([{"role": "user", "content": prompt}], max_tokens=20, temperature=0.1)
        intent_name = resp.strip().strip("'\"")
        if intent_name in CATEGORY_MAP:
            return {"name": intent_name, "confidence": 0.6, "category": CATEGORY_MAP.get(intent_name, "通用")}
    except Exception as e:
        pass
    return None

LLM_FALLBACK_THRESHOLD = 0.55

INTENT_CACHE = {}
INTENT_CACHE_MAX_SIZE = 500
INTENT_CACHE_SIMILARITY_THRESHOLD = 0.8

def _get_cached_intent(text):
    text = text.strip()
    if text in INTENT_CACHE:
        cached = INTENT_CACHE[text]
        if time.time() - cached["timestamp"] < 300:
            return cached["intent"]
    
    for cached_text, cached_data in INTENT_CACHE.items():
        similarity = difflib.SequenceMatcher(None, text, cached_text).ratio()
        if similarity >= INTENT_CACHE_SIMILARITY_THRESHOLD:
            if time.time() - cached_data["timestamp"] < 300:
                return cached_data["intent"]
    
    return None

def _cache_intent(text, intent):
    text = text.strip()
    if len(INTENT_CACHE) >= INTENT_CACHE_MAX_SIZE:
        oldest_key = min(INTENT_CACHE.keys(), key=lambda k: INTENT_CACHE[k]["timestamp"])
        del INTENT_CACHE[oldest_key]
    INTENT_CACHE[text] = {"intent": intent, "timestamp": time.time()}

def clear_intent_cache():
    INTENT_CACHE.clear()

def recognize_intent(text, llm_client=None):
    if not text or text.strip() == "":
        return {"name": "unknown", "confidence": 0.9, "category": "未知"}
    
    cached_intent = _get_cached_intent(text)
    if cached_intent:
        return cached_intent
    
    rule = _rule_match(text)
    composite = _composite_match(text)
    if composite:
        result = {"name": "composite", "confidence": 0.85, "category": "复合意图", "sub_intents": composite["sub_intents"]}
        _cache_intent(text, result)
        return result
    if rule:
        name, kw, conf = rule
        if conf < LLM_FALLBACK_THRESHOLD:
            llm_result = _get_llm_result(text)
            if llm_result:
                _cache_intent(text, llm_result)
                return llm_result
        result = {"name": name, "confidence": conf, "category": CATEGORY_MAP.get(name, "通用"), "keywords": [kw]}
        _cache_intent(text, result)
        return result
    kw_match = _multi_keyword_match(text)
    if kw_match:
        name, score = kw_match
        conf = min(score + 0.2, 0.9)
        if conf < LLM_FALLBACK_THRESHOLD:
            llm_result = _get_llm_result(text)
            if llm_result:
                _cache_intent(text, llm_result)
                return llm_result
        result = {"name": name, "confidence": conf, "category": CATEGORY_MAP.get(name, "通用")}
        _cache_intent(text, result)
        return result
    llm_result = _get_llm_result(text)
    if llm_result:
        _cache_intent(text, llm_result)
        return llm_result
    result = {"name": "general", "confidence": 0.2, "category": "通用"}
    _cache_intent(text, result)
    return result

# ==================== 工具函数 ====================

def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@lru_cache(maxsize=32)
def query_menu(store_name=None, keyword=None, category=None, data_dir=None):
    if store_name:
        shop = get_shop_by_name(store_name)
        if not shop:
            shops = get_shops(location=store_name)
            if shops:
                shop = shops[0]
            else:
                return {"success": False, "data": []}
        items = get_menu_items(shop_id=shop['id'], keyword=keyword, category=category)
        return {"success": True, "data": items, "store": shop['name']}
    
    hot_items = get_hot_menu_items(limit=5)
    hot = []
    for item in hot_items:
        shop = get_shop_by_name(item.get('shop_id', ''))
        shop_name = shop['name'] if shop else '未知门店'
        hot.append({"store": shop_name, "name": item['name'], "price": item['price'], "category": item.get('category'), "sales": item.get('sales', 0)})
    
    all_shops = get_shops()
    return {"success": True, "data": hot, "stores": [s['name'] for s in all_shops]}

def query_stores(location, radius=3000, data_dir=None):
    key = os.environ.get("AMAP_API_KEY", "")
    if key and requests:
        url = "https://restapi.amap.com/v3/geocode/geo"
        geocode = requests.get(url, params={"key": key, "address": location, "city": "武汉"}, timeout=5).json()
        if geocode.get("status") != "1": return {"success": False, "data": []}
        loc = geocode["geocodes"][0]["location"].split(",")
        around = requests.get("https://restapi.amap.com/v3/place/around", params={
            "key": key, "location": f"{loc[0]},{loc[1]}", "keywords": "奶茶", "radius": radius
        }, timeout=5).json()
        if around.get("status") != "1": return {"success": False, "data": []}
        return {"success": True, "data": around["pois"], "count": len(around["pois"])}
    
    stores = get_shops(location=location)
    if stores:
        return {"success": True, "data": stores, "count": len(stores)}
    return {"success": True, "data": [
        {"name": f"{location}附近门店1", "address": f"{location}街道1号"},
        {"name": f"{location}附近门店2", "address": f"{location}街道2号"},
    ], "count": 2}

def query_order(user_id=None, order_id=None, data_dir=None):
    user_id = user_id or "default_user"
    
    if order_id:
        matched = get_orders(order_id=order_id)
        result = []
        for order in matched:
            shop = get_shop_by_name(order.get('shop_id', '')) if order.get('shop_id') else None
            result.append({
                "order_id": order['id'],
                "store": shop['name'] if shop else order.get('shop_id', ''),
                "items": order.get('items', []),
                "total": order.get('total'),
                "status": order.get('status', 'pending'),
                "create_time": order.get('create_time'),
                "delivery_time": order.get('delivery_time'),
                "address": order.get('address')
            })
        return {"success": True, "data": result, "count": len(result)}
    
    user_orders = get_orders(user_id=user_id)
    result = []
    for order in user_orders:
        shop = get_shop_by_name(order.get('shop_id', '')) if order.get('shop_id') else None
        result.append({
            "order_id": order['id'],
            "store": shop['name'] if shop else order.get('shop_id', ''),
            "items": order.get('items', []),
            "total": order.get('total'),
            "status": order.get('status', 'pending'),
            "create_time": order.get('create_time'),
            "delivery_time": order.get('delivery_time'),
            "address": order.get('address')
        })
    return {"success": True, "data": result, "count": len(result)}

def check_stock(item_name, store_name=None):
    shop = None
    if store_name:
        shop = get_shop_by_name(store_name)
        if not shop:
            shops = get_shops(location=store_name)
            if shops:
                shop = shops[0]
    
    if shop:
        items = get_menu_items(shop_id=shop['id'], keyword=item_name)
        if items:
            inv = get_inventory(shop_id=shop['id'], menu_item_id=items[0]['id'])
            if inv:
                return {"success": True, "item": item_name, "available": inv['quantity'] > 0, "quantity": inv['quantity']}
            return {"success": True, "item": item_name, "available": True, "quantity": 50}
    
    hot = ["幽兰拿铁", "多肉葡萄", "霸气芝士草莓", "珍珠奶茶"]
    available = random.choice([True, True, False]) if item_name in hot else random.choice([True, True, True, False])
    return {"success": True, "item": item_name, "available": available, "quantity": random.randint(0, 50) if available else 0}

def log_complaint(user_id=None, complaint=None, severity="普通", category="口味", intent_name=None):
    user_id = user_id or "default_user"
    complaint = complaint or ""
    complaint_id = f"CMP-{int(time.time())}"
    log_path = os.path.join("data", "complaints.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{complaint_id} | {user_id} | {severity} | {category} | {complaint}\n")
    save_complaint(user_id, {"complaint_id": complaint_id, "complaint": complaint, "severity": severity, "category": category, "time": time.time()})
    
    has_knowledge = False
    if intent_name:
        solution, compensation = get_knowledge_response(intent_name)
        has_knowledge = solution is not None
    
    if has_knowledge:
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "../data/bubblemate.db"))
        c = conn.cursor()
        c.execute("""
            INSERT INTO complaints (user_id, complaint_type, description)
            VALUES (?, ?, ?)
        """, (user_id, category, complaint))
        db_id = c.lastrowid
        c.execute("""
            SELECT id FROM knowledge_graph WHERE node_type = 'complaint' AND node_name = ? AND is_active = 1
        """, (category,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE complaints SET knowledge_id = ?, status = '已解决', resolved_at = CURRENT_TIMESTAMP WHERE id = ?", (row[0], db_id))
        conn.commit()
        conn.close()
        return {"success": True, "complaint_id": complaint_id, "db_id": db_id, "candidate_id": None}
    else:
        db_id, candidate_id = save_complaint_with_candidate(user_id, category, complaint)
        return {"success": True, "complaint_id": complaint_id, "db_id": db_id, "candidate_id": candidate_id}

def _auto_learn_knowledge(category, complaint):
    knowledge_list = get_knowledge_list(reviewed_only=False)
    existing = [k for k in knowledge_list if k.get("node_name") == category and k.get("node_type") == "complaint"]
    if existing:
        _create_variant_node(category, complaint)
        return
    solution = _generate_solution(category)
    compensation = _generate_compensation(category)
    _save_knowledge(category, solution, compensation)

def _create_variant_node(parent_category, complaint):
    knowledge_list = get_knowledge_list(reviewed_only=False)
    parent_node = next((k for k in knowledge_list if k.get("node_name") == parent_category and k.get("node_type") == "complaint"), None)
    if not parent_node:
        return
    variant_keywords = ["太甜", "太酸", "太苦", "难喝", "冰块太多", "料少", "服务差", "超时", "太贵"]
    matched = next((kw for kw in variant_keywords if kw in complaint), None)
    if not matched:
        return
    variant_content = f"{parent_category}_{matched}"
    existing_variant = [k for k in knowledge_list if k.get("node_name") == variant_content]
    if existing_variant:
        return
    solution = _generate_solution(parent_category)
    compensation = _generate_compensation(parent_category)
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "../data/bubblemate.db"))
    c = conn.cursor()
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, ?, 2)", (variant_content, 'issue', variant_content, parent_node["id"]))
    variant_id = c.lastrowid
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, ?, 3)", (solution[:50], 'solution', solution, variant_id))
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, ?, 3)", (compensation[:50], 'compensation', compensation, variant_id))
    conn.commit()
    conn.close()

def _generate_solution(category):
    templates = {
        "口味": f"非常抱歉您对{category}不满意，我们会尽快为您处理。",
        "份量": f"非常抱歉{category}不足，我们会为您补发或补偿。",
        "服务": f"非常抱歉{category}态度不佳，我们已通知门店整改。",
        "配送": f"非常抱歉{category}超时，我们会申请超时赔付。",
        "价格": f"非常抱歉{category}问题，核实后提供优惠券补偿。",
        "退款": "非常抱歉，我们会为您办理退款。",
        "讽刺": "非常抱歉给您带来不好的体验，请问具体是什么问题？",
        "配件": f"非常抱歉{category}缺失，我们会为您补发。",
    }
    return templates.get(category, f"非常抱歉给您带来不好的体验，关于{category}问题我们会尽快处理。")

def _generate_compensation(category):
    templates = {
        "口味": "免费重做或退款",
        "份量": "补发配料或5元优惠券",
        "服务": "赠送饮品券",
        "配送": "超时赔付或免单",
        "价格": "优惠券补偿",
        "退款": "全额退款",
        "讽刺": "请告知具体问题",
        "配件": "补发配件",
    }
    return templates.get(category, "请联系客服处理")

@lru_cache(maxsize=16)
def query_promotions(data_dir="data"):
    promo = _read_json(os.path.join(data_dir, "promotions.json"))
    return {"success": True, "data": promo.get("active", [])}

@lru_cache(maxsize=64)
def query_customize(item_name):
    toppings = [{"name": t, "price": 3 if t in ["珍珠", "椰果"] else 4} for t in ["珍珠", "椰果", "仙草冻", "芋圆", "布丁"]]
    return {"success": True, "item": item_name, "toppings": toppings, "sugar": ["标准糖", "七分糖", "五分糖", "三分糖", "无糖"]}

def query_history(user_id=None, limit=3, data_dir="data"):
    user_id = user_id or "default_user"
    orders = _read_json(os.path.join(data_dir, "orders_mock.json"))
    return {"success": True, "data": orders.get(user_id, [])[:limit]}

@lru_cache(maxsize=32)
def query_recommend(preference=None, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
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

def extract_params(text, intent_name, session_id=None):
    params = {}
    missing_params = []
    tool_name = INTENT_TOOL.get(intent_name)
    if session_id and tool_name in ["query_order", "query_history", "log_complaint"]:
        params["user_id"] = get_user_id(session_id)
    if tool_name == "query_stores":
        match = PARAM_EXTRACTORS["location"](text)
        if match:
            location = match.group(2)
            if location and location not in ["有门店", "有店", "有奶茶", "门店", "店"]:
                params["location"] = location
            elif "附近" in text or "周边" in text:
                params["location"] = "光谷广场"
            else:
                missing_params.append("位置信息")
        elif "附近" in text or "周边" in text:
            params["location"] = "光谷广场"
        else:
            missing_params.append("位置信息")
    elif tool_name in ["query_order", "query_history"]:
        match = PARAM_EXTRACTORS["order_id"](text)
        if match:
            params["order_id"] = match.group(1)
        else:
            missing_params.append("订单号")
    elif tool_name == "log_complaint":
        params["complaint"] = PARAM_EXTRACTORS["complaint"](text)
        params["intent_name"] = intent_name
        params["category"] = INTENT_TO_CATEGORY.get(intent_name, "口味")
    return params, missing_params

import threading

class ToolTimeoutError(Exception):
    pass

def _run_with_timeout(func, args=(), kwargs=None, timeout=3):
    result = [None]
    error = [None]
    if kwargs is None:
        kwargs = {}
    
    def wrapper():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            error[0] = e
    
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        raise ToolTimeoutError(f"工具执行超时({timeout}s)")
    if error[0]:
        raise error[0]
    return result[0]

def get_tool_response(intent_name, text, tools=TOOLS, session_id=None):
    tool_name = INTENT_TOOL.get(intent_name)
    if not tool_name or tool_name not in tools:
        return None, []
    params, missing_params = extract_params(text, intent_name, session_id)
    if missing_params:
        return None, missing_params
    try:
        result = _run_with_timeout(tools[tool_name], (), params)
        return result, []
    except ToolTimeoutError:
        return {"success": False, "data": [], "error": "工具执行超时"}, []
    except Exception as e:
        return {"success": False, "data": [], "error": str(e)}, []

# ==================== 记忆管理 ====================

try:
    from storage.redis_store import session_store
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class MemoryStore:
    def __init__(self, window_size=5):
        self._window_size = window_size
        self._store = {"sessions": {}}
    
    def _get_session(self, session_id):
        if REDIS_AVAILABLE:
            return session_store.get_session(session_id)
        return self._store["sessions"].get(session_id)
    
    def _save_session(self, session_id, data):
        if REDIS_AVAILABLE:
            session_store.save_session(session_id, data)
        else:
            self._store["sessions"][session_id] = data
    
    def get_sessions(self):
        if REDIS_AVAILABLE:
            return session_store.get_all_sessions()
        return dict(self._store["sessions"])

def create_memory_store(window_size=5):
    return MemoryStore(window_size)

def _extract_prefs(text):
    sugar_map = {"无糖": ["无糖", "零糖"], "三分糖": ["少糖"], "五分糖": ["半糖"]}
    ice_map = {"热": ["热饮"], "去冰": ["去冰"], "少冰": ["少冰"]}
    prefs = {}
    for level, patterns in sugar_map.items():
        if any(p in text for p in patterns): prefs["sugar"] = level
    for level, patterns in ice_map.items():
        if any(p in text for p in patterns): prefs["ice"] = level
    return prefs

def _compress_history(history, window_size):
    if len(history) <= window_size:
        return history
    to_compress = history[:-window_size + 1]
    summary_parts = []
    for msg in to_compress:
        user_part = msg["user"][:30] + "..." if len(msg["user"]) > 30 else msg["user"]
        agent_part = msg["agent"][:30] + "..." if len(msg["agent"]) > 30 else msg["agent"]
        summary_parts.append(f"用户:{user_part} 客服:{agent_part}")
    summary = f"[对话摘要] {'; '.join(summary_parts)}"
    return [{"user": summary, "agent": "", "is_summary": True}] + history[-window_size + 1:]

def save_message(store, session_id, user_msg, agent_msg):
    if isinstance(store, MemoryStore):
        sess = store._get_session(session_id)
        if not sess:
            sess = {"history": [], "preferences": {}, "summary": ""}
        sess["history"].append({"user": user_msg, "agent": agent_msg})
        if len(sess["history"]) > store._window_size:
            sess["history"] = _compress_history(sess["history"], store._window_size)
        user_id = get_user_id(session_id)
        new_prefs = _extract_prefs(user_msg)
        for k, v in new_prefs.items():
            save_user_preference(user_id, k, v)
            sess["preferences"][k] = v
        store._save_session(session_id, sess)
    else:
        if session_id not in store["sessions"]:
            store["sessions"][session_id] = {"history": [], "preferences": {}, "window_size": store["window_size"]}
        store["sessions"][session_id]["history"].append({"user": user_msg, "agent": agent_msg})
        window_size = store["sessions"][session_id]["window_size"]
        if len(store["sessions"][session_id]["history"]) > window_size:
            store["sessions"][session_id]["history"] = _compress_history(store["sessions"][session_id]["history"], window_size)
        user_id = get_user_id(session_id)
        new_prefs = _extract_prefs(user_msg)
        for k, v in new_prefs.items():
            save_user_preference(user_id, k, v)
            store["sessions"][session_id]["preferences"][k] = v

def get_context(store, session_id):
    if isinstance(store, MemoryStore):
        sess = store._get_session(session_id)
    else:
        sess = store["sessions"].get(session_id)
    if not sess: return ""
    user_id = get_user_id(session_id)
    db_prefs = get_user_preferences(user_id)
    prefs = {**db_prefs, **(sess.get("preferences", {}))}
    parts = []
    if prefs:
        parts.append(f"偏好: {', '.join([f'{k}={v}' for k, v in prefs.items()])}")
    for msg in sess["history"]:
        parts.append(f"用户: {msg['user']}")
        parts.append(f"客服: {msg['agent']}")
    return "\n".join(parts)

# ==================== Agent核心 ====================

def build_response(intent, text, tool_result=None, missing_params=None):
    if missing_params:
        params_text = "、".join(missing_params)
        return f"【思考】{intent['name']}\n【回复】请问您能提供一下{params_text}吗？这样我可以更好地帮助您。"
    
    tool_error = tool_result and not tool_result.get("success")
    
    if intent["name"] in ["complaint_vague", "complaint_compare_history", "unknown"]:
        reply = DEFAULT_SOLUTIONS.get(INTENT_TO_CATEGORY.get(intent["name"]), "抱歉，我不太理解您的意思，可以再详细描述一下吗？")
        return f"【思考】{intent['name']}\n【回复】{reply}"
    
    if intent["name"].startswith("complaint"):
        solution, compensation = get_knowledge_response(intent["name"])
        category = INTENT_TO_CATEGORY.get(intent["name"])
        if not solution:
            solution = DEFAULT_SOLUTIONS.get(category, "非常抱歉给您带来不好的体验，我们会尽快处理。")
        if not compensation:
            compensation = DEFAULT_COMPENSATIONS.get(category, "请联系客服处理")
        reply = f"{solution} 补偿方案：{compensation}"
        if tool_error:
            reply = f"{reply}（投诉记录暂存中，稍后为您处理）"
            return f"【思考】{intent['name']}\n【行动】记录投诉(降级)\n【回复】{reply}"
        if tool_result and tool_result["success"]:
            return f"【思考】{intent['name']}\n【行动】记录投诉\n【回复】{reply}"
        return f"【思考】{intent['name']}\n【回复】{reply}"
    
    if intent["name"].startswith("query"):
        if intent["name"] == "query_refund":
            return f"【思考】{intent['name']}\n【回复】请问您能提供一下订单号吗？这样我可以帮您查询退款相关信息。"
        if tool_error:
            fallback = DIRECT_RESPONSES.get(intent["name"], "暂时无法查询，请稍后再试。")
            return f"【思考】{intent['name']}\n【行动】调用工具(失败)\n【回复】{fallback}"
        if tool_result and tool_result["success"]:
            return f"【思考】{intent['name']}\n【行动】调用工具\n【回复】{_format_tool_result(intent['name'], tool_result)}"
        return f"【思考】{intent['name']}\n【回复】{DIRECT_RESPONSES.get(intent['name'], '请告诉我具体查询内容。')}"
    
    if intent["name"] in ["place_order", "order_modify"]:
        return f"【思考】{intent['name']}\n【回复】请提供您想点的饮品名称。"
    
    return f"【思考】{intent['name']}\n【回复】{DIRECT_RESPONSES.get(intent['name'], '您好，有什么可以帮助您的？')}"

def _format_tool_result(intent_name, result):
    if intent_name == "query_stores" or intent_name == "query_location":
        names = [p.get("name", "") for p in result["data"][:3]]
        return f"附近门店：{', '.join(names)}。"
    if intent_name == "query_menu":
        names = [i.get("name", "") for i in result["data"][:3]]
        return f"饮品：{', '.join(names)}。"
    if intent_name == "query_order":
        if result["data"]:
            orders = []
            for o in result["data"]:
                orders.append(f"{o.get('order_id', '')} ({o.get('store', '')})：{o.get('status', '')}")
            return f"您有{len(result['data'])}个订单：{'；'.join(orders)}。"
        return "抱歉，没有找到相关的订单记录呢。请问您提供的订单号是否正确？或者您可以稍后再试。"
    if intent_name == "query_recommend":
        if result["data"]:
            items = []
            for i in result["data"]:
                items.append(f"{i.get('name', '')}（¥{i.get('price', '')}）")
            return f"推荐：{', '.join(items)}。"
        return "暂无推荐。"
    return "查询完成。"

async def process_message_async(text, session_id="default", memory_store=None, llm_client=None):
    trace = ExecutionTrace()
    trace.session_id = session_id
    
    termination = should_terminate(text, trace)
    if termination["terminate"]:
        if termination["action"] == "human_handover":
            reply = "【思考】终止判断：需要转人工\n【回复】抱歉，我无法解决您的问题，已为您转接人工客服。"
        else:
            reply = "【思考】终止判断：对话结束\n【回复】很高兴能帮到您，祝您生活愉快！"
        if memory_store:
            save_message(memory_store, session_id, text, reply)
        return reply, {"name": "terminated", "confidence": 1.0, "category": "终止"}
    
    intent_task = asyncio.create_task(asyncio.to_thread(recognize_intent, text, llm_client))
    
    def load_context():
        if memory_store:
            return get_context(memory_store, session_id)
        return None
    
    context_task = asyncio.create_task(asyncio.to_thread(load_context))
    
    intent, context = await asyncio.gather(intent_task, context_task)
    
    trace.add_step("intent", {"name": intent["name"], "confidence": intent["confidence"], "category": intent.get("category")})
    
    if intent["confidence"] >= 0.6:
        tool_name = INTENT_TOOL.get(intent["name"])
        
        if intent["name"] == "query_recommend":
            tool_result, _ = await asyncio.to_thread(get_tool_response, intent["name"], text, session_id=session_id)
            response = build_response(intent, text, tool_result, [])
            trace.add_step("tool_call", {"tool_name": "query_recommend", "intent_name": intent["name"], "params": {}})
            trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": tool_result.get("data", [])})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
        
        elif intent["name"] == "query_order":
            params, missing = extract_params(text, intent["name"], session_id)
            if params.get("order_id"):
                tool_result, _ = await asyncio.to_thread(get_tool_response, intent["name"], text, session_id=session_id)
                response = build_response(intent, text, tool_result, [])
                trace.add_step("tool_call", {"tool_name": "query_order", "intent_name": intent["name"], "params": params})
                trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": tool_result.get("data", [])})
                trace.add_step("response", {"text": response})
                trace.save_to_file()
                if memory_store:
                    save_message(memory_store, session_id, text, response)
                return response, intent
            else:
                response = f"【思考】{intent['name']}\n【回复】请问您能提供一下订单号吗？这样我可以帮您查询相关信息。"
                trace.add_step("clarify", {"missing_params": ["订单号"]})
                trace.add_step("response", {"text": response})
                trace.save_to_file()
                if memory_store:
                    save_message(memory_store, session_id, text, response)
                return response, intent
        
        elif intent["name"] == "query_location" or intent["name"] == "query_store":
            tool_result, _ = await asyncio.to_thread(get_tool_response, intent["name"], text, session_id=session_id)
            response = build_response(intent, text, tool_result, [])
            trace.add_step("tool_call", {"tool_name": "query_stores", "intent_name": intent["name"], "params": extract_params(text, intent["name"], session_id)[0]})
            trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": tool_result.get("data", []) if tool_result else []})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
        
        elif intent["name"].startswith("complaint"):
            tool_result = None
            if tool_name == "log_complaint":
                tool_result = await asyncio.to_thread(log_complaint, get_user_id(session_id), text, category=INTENT_TO_CATEGORY.get(intent["name"], "口味"), intent_name=intent["name"])
                trace.add_step("tool_call", {"tool_name": "log_complaint", "intent_name": intent["name"], "params": {"complaint": text}})
                trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": {"complaint_id": tool_result.get("complaint_id")}})
            response = build_response(intent, text, tool_result, [])
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
    
    return await asyncio.to_thread(harness_handle, text, session_id, intent, trace, memory_store)


def process_message(text, session_id="default", memory_store=None, llm_client=None):
    return asyncio.run(process_message_async(text, session_id, memory_store, llm_client))


def harness_handle(text, session_id, intent, trace, memory_store):
    tool_name = INTENT_TOOL.get(intent["name"])
    tool_result = None
    missing_params = []
    
    if tool_name and tool_name != "log_complaint":
        tool_result, missing_params = get_tool_response(intent["name"], text, session_id=session_id)
        
        if missing_params:
            response = build_response(intent, text, None, missing_params)
            trace.add_step("clarify", {"missing_params": missing_params})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
        
        trace.add_step("tool_call", {"tool_name": tool_name, "intent_name": intent["name"], "params": extract_params(text, intent["name"], session_id)[0]})
        trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": tool_result.get("data", []) if tool_result else []})
        
        if tool_result and tool_result.get("success"):
            response = build_response(intent, text, tool_result, [])
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
        
        if tool_result and not tool_result.get("success"):
            reflection = reflect_on_result(tool_name, extract_params(text, intent["name"], session_id)[0], tool_result, intent["name"], text)
            trace.add_step("reflection", reflection)
            
            if reflection["assessment"] != "reasonable":
                recovery = recover_from_failure(reflection, intent["name"], text, session_id)
                trace.add_step("replan", {"action": recovery["action"], "reason": recovery["reason"]})
                
                if recovery["action"] == "clarify":
                    reply = f"【思考】反思：{REFLECTION_ASSESSMENT[reflection['assessment']]}\n【回复】{recovery['clarification']}"
                    if memory_store:
                        save_message(memory_store, session_id, text, reply)
                    return reply, intent
                
                elif recovery["action"] == "switch_tool" and recovery["new_intent"]:
                    new_intent_name = recovery["new_intent"][0] if isinstance(recovery["new_intent"], list) else recovery["new_intent"]
                    new_intent = {"name": new_intent_name, "confidence": 0.7, "category": CATEGORY_MAP.get(new_intent_name, "通用")}
                    trace.add_step("intent", {"name": new_intent_name, "confidence": 0.7, "category": new_intent["category"]})
                    intent = new_intent
                    tool_name = INTENT_TOOL.get(new_intent_name)
                    tool_result, missing_params = get_tool_response(new_intent_name, text, session_id=session_id)
                    trace.add_step("tool_call", {"tool_name": tool_name, "intent_name": new_intent_name, "params": extract_params(text, new_intent_name, session_id)[0]})
                    trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": tool_result.get("data", []) if tool_result else []})
                
                elif recovery["action"] == "human_handover":
                    reply = "【思考】反思：完全不合理\n【回复】抱歉，系统暂时无法处理您的问题，已为您转接人工客服。"
                    if memory_store:
                        save_message(memory_store, session_id, text, reply)
                    return reply, intent
    
    elif tool_name == "log_complaint":
        tool_result = log_complaint(get_user_id(session_id), text, category=INTENT_TO_CATEGORY.get(intent["name"], "口味"), intent_name=intent["name"])
        trace.add_step("tool_call", {"tool_name": "log_complaint", "intent_name": intent["name"], "params": {"complaint": text}})
        trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": {"complaint_id": tool_result.get("complaint_id")}})
    
    response = build_response(intent, text, tool_result, missing_params)
    trace.add_step("response", {"text": response})
    trace.save_to_file()
    
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