import re
import json
import os
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
    from .storage.database import save_session, get_user_by_session, save_user_preference, get_user_preferences, save_complaint, save_complaint_with_candidate, get_knowledge_graph, save_knowledge as _save_knowledge, save_complaint_db as _save_complaint_db, get_complaint_stats
    from .storage.data_access import get_shops, get_menu_items, get_orders, get_shop_by_name, get_shop_by_id, get_hot_menu_items
except Exception as e:
    import sys as _sys
    print(f"Warning: storage modules not fully available: {e}", file=_sys.stderr)
    save_session = lambda s, u: None
    get_user_by_session = lambda s: None
    save_user_preference = lambda u, k, v: None
    get_shops = lambda **kwargs: []
    get_menu_items = lambda **kwargs: []
    get_orders = lambda **kwargs: []
    get_shop_by_name = lambda name: None
    get_shop_by_id = lambda shop_id: None
    get_user_preferences = lambda u: {}
    save_complaint = lambda u, d: None
    save_complaint_with_candidate = lambda u, ct, d: (None, None)
    get_knowledge_graph = lambda: []
    _save_knowledge = lambda ct, s, c: None
    _save_complaint_db = lambda u, ct, d: None
    get_complaint_stats = lambda: {"by_type": []}

try:
    from .core.cache import cache
except Exception:
    cache = None

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
    "complaint_service": ["服务差", "态度差", "电话打不通", "备注没按", "服务不好", "联系商家", "不理我", "不理", "不回", "态度恶劣", "不耐烦", "服务态度", "客服态度", "没人理"],
    "complaint_delivery": ["配送慢", "超时", "送得晚", "等太久", "包装破了", "等了", "还没到", "送错", "漏送", "破损", "撒了", "等了多久", "预计到达", "什么时候到", "还在路上", "一直没到", "送达时间"],
    "complaint_price": ["太贵", "价格高", "不值", "被坑了", "性价比低", "又贵"],
    "complaint_refund": ["要求退款", "申请退款"],
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
    "query_promotion": ["优惠", "活动", "折扣", "特价", "第二杯半价", "吗", "打折", "促销", "优惠券", "满减", "团购", "套餐"],
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
    "complaint_service": [re.compile(r"(服务|态度).*?(差|不好|恶劣)", re.I), re.compile(r"(联系商家|商家.*?(不理|不回|没回))", re.I), re.compile(r"(态度).*?(不耐烦|恶劣|太差)", re.I), re.compile(r"(客服|服务).*?(态度.*?(差|不好)|没人理)", re.I)],
    "complaint_delivery": [re.compile(r"(配送|送达|送).*?(慢|超时|晚)", re.I), re.compile(r"(配送速度).*?(打破认知|惊到我|意想不到|感人)", re.I), re.compile(r"(配送速度).*?(认知|想象|预料)", re.I), re.compile(r"(等了|等待).*?(多久|长时间)", re.I), re.compile(r"(预计|什么时候|几点).*?(到达|送到|到)", re.I), re.compile(r"(还在路上|一直没到|迟迟没到)", re.I)],
    "complaint_price": [re.compile(r"(贵|价格).*?(高|不值)", re.I), re.compile(r"(又贵|太贵了)", re.I), re.compile(r"(价格|贵).*?(具有竞争力|很有竞争力|感人)", re.I)],
    "complaint_refund": [re.compile(r"(要求退款|申请退款|我要退款)", re.I)],
    "complaint_sarcasm": [re.compile(r"(呵呵|绝了|也是绝了|太坑了)", re.I), re.compile(r"(一言难尽|太离谱)", re.I)],
    "complaint_accessory": [re.compile(r"(吸管).*?(细|怎么喝)", re.I), re.compile(r"(吸管|配件).*?(少|没|缺失|不见)", re.I)],
    "complaint_vague": [re.compile(r"(就是那个|你们懂的|懂的都懂|又少又难喝)", re.I)],
    "complaint_compare_history": [re.compile(r"(跟这次不一样|跟之前不一样)", re.I)],
    "complaint_taste_service": [re.compile(r"(口味|口感|甜|酸|苦|难喝).*?(服务|不理|不回)", re.I)],
    "complaint_taste_price": [re.compile(r"(苦|难喝|甜).*?(贵|不值)", re.I)],
    "query_recommend": [re.compile(r"(推荐|招牌|热门|特色|新品|必点)", re.I), re.compile(r"(有什么).*?(好喝|推荐)", re.I)],
    "query_menu": [re.compile(r"(菜单|饮品).*?(列出|看看|都有)", re.I), re.compile(r"(有什么).*?(喝的|饮品)", re.I), re.compile(r"(上次买的|之前买的).*?(没了|下架|不卖)", re.I)],
    "query_order": [re.compile(r"(订单|单号).*?(查询|状态|进度|到哪)", re.I), re.compile(r"(订单).*?(\d{5,})|(\d{5,}).*?(订单)", re.I), re.compile(r"(查|查看|我的).*?(订单)", re.I), re.compile(r"(查.*?上次点的|上次点的是什么)", re.I)],
    "query_hours": [re.compile(r"(营业时间|开门|关门|几点开门)", re.I)],
    "query_location": [re.compile(r"(门店|地址|位置)", re.I), re.compile(r"(附近|周边).*?(有|店|奶茶)", re.I), re.compile(r"(最近的一家店|最近的店)", re.I)],
    "query_refund": [re.compile(r"(怎么退款|如何退款|退款流程)", re.I), re.compile(r"(可以退吗|能退吗|能退款吗)", re.I)],
    "query_price": [re.compile(r"(多少钱|价格|贵不贵)", re.I)],
    "query_promotion": [re.compile(r"(优惠|活动|折扣|券).*?(有|今天)", re.I), re.compile(r"(有什么|今天).*?(优惠|活动|折扣)", re.I), re.compile(r"(打折|促销|团购|套餐).*?(有|吗|今天)", re.I), re.compile(r"(优惠券|满减|第二杯).*?(半价|活动|有吗)", re.I)],
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
    "query_recommend": "query_recommend", "query_refund": "query_order",
    "query_price": "query_menu",
}

PARAM_EXTRACTORS = {
    "location": lambda text: re.search(r"([\u4e00-\u9fa5]{2,})(附近|周边)|(在|附近|周边)\s*([\u4e00-\u9fa5]{2,}广场|[\u4e00-\u9fa5]{2,}路|[\u4e00-\u9fa5]{2,}街|[\u4e00-\u9fa5]{2,}校区|[\u4e00-\u9fa5]{2,}中心|[\u4e00-\u9fa5]{2,}大厦|[\u4e00-\u9fa5]{2,}商场)", text),
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

async def _get_llm_result_async(text):
    try:
        from backend.core.zhipu_client import call_llm_async, is_available
        if not is_available():
            return None
        prompt = f"判断用户意图：'{text}'\n可选：{', '.join(INTENT_KEYWORDS.keys())}\n只返回意图名称，不要其他内容。"
        resp = await call_llm_async([{"role": "user", "content": prompt}], max_tokens=20, temperature=0.1)
        intent_name = resp.strip().strip("'\"")
        if intent_name in CATEGORY_MAP:
            return {"name": intent_name, "confidence": 0.6, "category": CATEGORY_MAP.get(intent_name, "通用")}
    except Exception as e:
        pass
    return None

LLM_FALLBACK_THRESHOLD = 0.55

INTENT_CACHE_SIMILARITY_THRESHOLD = 0.8

def _get_cached_intent(text):
    text = text.strip()
    if cache:
        cached = cache.get("intent", text)
        if cached:
            return cached
    
    return None

def _cache_intent(text, intent):
    text = text.strip()
    if cache:
        cache.set("intent", text, intent, ttl=3600)

def clear_intent_cache():
    if cache:
        cache.clear("intent")

def _get_cached_response(text):
    text = text.strip()
    if cache:
        cached = cache.get("response", text)
        if cached:
            return cached
    return None

def _cache_response(text, response):
    text = text.strip()
    if cache:
        cache.set("response", text, response, ttl=600)

def clear_response_cache():
    if cache:
        cache.clear("response")

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

async def recognize_intent_async(text, llm_client=None):
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
            llm_result = await _get_llm_result_async(text)
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
            llm_result = await _get_llm_result_async(text)
            if llm_result:
                _cache_intent(text, llm_result)
                return llm_result
        result = {"name": name, "confidence": conf, "category": CATEGORY_MAP.get(name, "通用")}
        _cache_intent(text, result)
        return result
    llm_result = await _get_llm_result_async(text)
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
    if keyword and not store_name:
        all_items = []
        shops = get_shops()
        for shop in shops:
            items = get_menu_items(shop_id=shop['id'], keyword=keyword, category=category)
            for item in items:
                item['store'] = shop['name']
                all_items.append(item)
        if all_items:
            return {"success": True, "data": all_items[:5], "keyword": keyword}
        return {"success": False, "data": [], "message": f"未找到与 {keyword} 相关的饮品"}
    
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
        shop = get_shop_by_id(item.get('shop_id', ''))
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
    return {"success": False, "data": [], "count": 0, "message": f"未找到 {location} 附近的门店"}

def query_order(user_id=None, order_id=None, data_dir=None):
    user_id = user_id or "default_user"
    
    if order_id:
        matched = get_orders(order_id=order_id)
        result = []
        for order in matched:
            shop = get_shop_by_id(order.get('shop_id', '')) if order.get('shop_id') else None
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
        shop = get_shop_by_id(order.get('shop_id', '')) if order.get('shop_id') else None
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
    orders = get_orders(user_id=user_id)[:limit]
    result = []
    for order in orders:
        shop = get_shop_by_id(order.get('shop_id', '')) if order.get('shop_id') else None
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

_menu_vectors_cache = None

def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

@lru_cache(maxsize=32)
def query_recommend(query=None, preference=None, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    # 优先语义检索：用户 query 向量与菜单向量算余弦相似度
    if query:
        global _menu_vectors_cache
        if _menu_vectors_cache is None:
            vec_path = os.path.join(data_dir, "menu_vectors.json")
            _menu_vectors_cache = _read_json(vec_path) if os.path.exists(vec_path) else []
        if _menu_vectors_cache:
            try:
                from core.zhipu_client import embed_text
                qv = embed_text(query)
                scored = sorted(
                    ((_cosine(qv, v["vector"]), v) for v in _menu_vectors_cache),
                    key=lambda x: x[0], reverse=True,
                )
                top = [{k: v[k] for k in ("name", "store", "price", "category", "description", "sales")}
                       for _, v in scored[:3]]
                return {"success": True, "data": top, "matched_by": "semantic"}
            except Exception as e:
                print(f"语义推荐失败，回退销量排序: {e}")
    # 兜底：按销量排序
    menu = _read_json(os.path.join(data_dir, "menu_data.json"))
    all_items = []
    for store, items in menu.items():
        all_items.extend([{**i, "store": store} for i in items if i["available"]])
    if preference:
        if "甜" in preference or "奶茶" in preference: all_items = [i for i in all_items if i["category"] == "奶茶"]
        elif "酸" in preference or "果茶" in preference: all_items = [i for i in all_items if i["category"] == "果茶"]
    all_items.sort(key=lambda x: x["sales"], reverse=True)
    return {"success": True, "data": all_items[:3], "matched_by": "sales"}

TOOLS = {
    "query_menu": query_menu, "query_stores": query_stores, "query_order": query_order,
    "log_complaint": log_complaint,
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
            location = match.group(1) or match.group(4)
            if location and location not in ["有门店", "有店", "有奶茶", "门店", "店"]:
                params["location"] = location
            else:
                missing_params.append("位置信息")
        elif "附近" in text or "周边" in text:
            missing_params.append("位置信息")
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
    elif tool_name == "query_menu":
        drink_kw = _extract_drink_keyword(text)
        if drink_kw:
            params["keyword"] = drink_kw
    return params, missing_params

def _extract_drink_keyword(text):
    menu_names = _get_menu_names()
    for name in menu_names:
        if name in text:
            return name
    return None

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
    from .storage.redis_store import session_store
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class MemoryStore:
    def __init__(self, window_size=3):
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

def create_memory_store(window_size=3):
    return MemoryStore(window_size)

def _extract_entities(text):
    entities = {}
    
    sugar_map = {"无糖": ["无糖", "零糖"], "三分糖": ["三分糖", "少糖"], "五分糖": ["五分糖", "半糖"], "七分糖": ["七分糖"]}
    for level, patterns in sugar_map.items():
        if any(p in text for p in patterns): entities["sugar"] = level
    
    ice_map = {"热": ["热饮", "热的"], "去冰": ["去冰"], "少冰": ["少冰"], "温": ["温的", "温热"]}
    for level, patterns in ice_map.items():
        if any(p in text for p in patterns): entities["ice"] = level
    
    order_match = re.search(r'(?:ORD-)?(\d{5,})', text)
    if order_match: entities["order_id"] = order_match.group(1)
    
    location_patterns = [
        re.compile(r'(光谷|街道口|银泰|武大|华师|汉口|武昌|江夏|汉阳|江汉|硚口|洪山)'),
        re.compile(r'(在|去|到)([^\s，。的]{2,6})(?:附近|周边|这里)'),
    ]
    for pat in location_patterns:
        m = pat.search(text)
        if m:
            loc = m.group(1) if m.lastindex == 1 else m.group(2)
            if loc not in ["附近", "周边", "这里"]:
                entities["location"] = loc
                break
    
    menu_items = _get_menu_names()
    for name in menu_items:
        if name in text:
            entities["drink"] = name
            break
    
    price_match = re.search(r'[¥￥]?\s*(\d{1,3}(?:\.\d+)?)\s*元?\s*', text)
    if price_match: entities["price"] = price_match.group(1)
    
    topping_map = {
        "珍珠": ["珍珠", "加珍珠", "珍珠奶茶"],
        "椰果": ["椰果"],
        "布丁": ["布丁"],
        "红豆": ["红豆"],
        "绿豆": ["绿豆"],
        "仙草": ["仙草"],
        "芋圆": ["芋圆"],
        "奶盖": ["奶盖", "加奶盖"],
        "燕麦": ["燕麦", "加燕麦"],
        "水果": ["加水果", "水果"],
    }
    for topping, patterns in topping_map.items():
        if any(p in text for p in patterns):
            entities["topping"] = topping
            break
    
    temp_map = {
        "热": ["热饮", "热的", "加热"],
        "温": ["温的", "温热", "常温"],
        "去冰": ["去冰", "不要冰", "无冰"],
        "少冰": ["少冰", "少放点冰"],
        "正常冰": ["正常冰", "标准冰"],
        "多冰": ["多冰", "加冰"],
    }
    for temp, patterns in temp_map.items():
        if any(p in text for p in patterns):
            entities["temperature"] = temp
            break
    
    size_map = {
        "大杯": ["大杯", "大的", "L", "XL"],
        "中杯": ["中杯", "中的", "M"],
        "小杯": ["小杯", "小的", "S"],
    }
    for size, patterns in size_map.items():
        if any(p in text for p in patterns):
            entities["size"] = size
            break
    
    if "太甜" in text:
        entities["complaint_reason"] = "太甜"
    elif "太咸" in text:
        entities["complaint_reason"] = "太咸"
    elif "太辣" in text:
        entities["complaint_reason"] = "太辣"
    elif "太淡" in text:
        entities["complaint_reason"] = "太淡"
    elif "变质" in text or "不新鲜" in text:
        entities["complaint_reason"] = "变质/不新鲜"
    
    compliment_patterns = [
        re.compile(r'(真好喝|好喝|不错|喜欢|爱喝|最爱)', re.I),
    ]
    for pat in compliment_patterns:
        m = pat.search(text)
        if m:
            drink = entities.get("drink", "")
            entities["complimented_drink"] = drink if drink else m.group(0)
            break
    
    return entities

def _get_menu_names():
    global _menu_names_cache
    if '_menu_names_cache' not in globals():
        try:
            menu_path = os.path.join(os.path.dirname(__file__), "../data/menu_data.json")
            if os.path.exists(menu_path):
                with open(menu_path, 'r', encoding='utf-8') as f:
                    menu_data = json.load(f)
                names = []
                for store_items in menu_data.values():
                    for item in store_items:
                        if isinstance(item, dict) and 'name' in item:
                            names.append(item['name'])
                        elif isinstance(item, str):
                            names.append(item)
                _menu_names_cache = list(set(names))
            else:
                _menu_names_cache = []
        except Exception:
            _menu_names_cache = []
    return _menu_names_cache

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
            sess = {"history": [], "preferences": {}, "entities": {}, "summary": ""}
        sess["history"].append({"user": user_msg, "agent": agent_msg})
        if len(sess["history"]) > store._window_size:
            sess["history"] = _compress_history(sess["history"], store._window_size)
        user_id = get_user_id(session_id)
        new_entities = _extract_entities(user_msg)
        agent_entities = _extract_entities(agent_msg)
        existing_entities = sess.get("entities", {})
        if agent_entities.get("drink") and agent_entities.get("price"):
            drink_in_agent = agent_entities["drink"]
            if drink_in_agent in agent_msg and existing_entities.get("drink") and existing_entities["drink"] not in agent_msg:
                agent_entities = {}
        for k, v in agent_entities.items():
            if k == "price" and k in new_entities:
                continue
            if k == "drink" and k in new_entities:
                continue
            if k not in new_entities:
                new_entities[k] = v
        for k, v in new_entities.items():
            if k in ("sugar", "ice"):
                save_user_preference(user_id, k, v)
                sess["preferences"][k] = v
            sess["entities"][k] = v
        store._save_session(session_id, sess)
    else:
        if session_id not in store["sessions"]:
            store["sessions"][session_id] = {"history": [], "preferences": {}, "entities": {}, "window_size": store["window_size"]}
        store["sessions"][session_id]["history"].append({"user": user_msg, "agent": agent_msg})
        window_size = store["sessions"][session_id]["window_size"]
        if len(store["sessions"][session_id]["history"]) > window_size:
            store["sessions"][session_id]["history"] = _compress_history(store["sessions"][session_id]["history"], window_size)
        user_id = get_user_id(session_id)
        new_entities = _extract_entities(user_msg)
        agent_entities = _extract_entities(agent_msg)
        existing_entities = store["sessions"][session_id].get("entities", {})
        if agent_entities.get("drink") and agent_entities.get("price"):
            drink_in_agent = agent_entities["drink"]
            if drink_in_agent in agent_msg and existing_entities.get("drink") and existing_entities["drink"] not in agent_msg:
                agent_entities = {}
        for k, v in agent_entities.items():
            if k == "price" and k in new_entities:
                continue
            if k == "drink" and k in new_entities:
                continue
            if k not in new_entities:
                new_entities[k] = v
        for k, v in new_entities.items():
            if k in ("sugar", "ice"):
                save_user_preference(user_id, k, v)
                store["sessions"][session_id]["preferences"][k] = v
            store["sessions"][session_id]["entities"][k] = v

def get_context(store, session_id):
    if isinstance(store, MemoryStore):
        sess = store._get_session(session_id)
    else:
        sess = store["sessions"].get(session_id)
    if not sess: return "", {}
    user_id = get_user_id(session_id)
    db_prefs = get_user_preferences(user_id)
    prefs = {**db_prefs, **(sess.get("preferences", {}))}
    entities = sess.get("entities", {})
    parts = []
    if prefs:
        parts.append(f"偏好: {', '.join([f'{k}={v}' for k, v in prefs.items()])}")
    if entities:
        parts.append(f"记忆实体: {', '.join([f'{k}={v}' for k, v in entities.items()])}")
    for msg in sess["history"]:
        parts.append(f"用户: {msg['user']}")
        parts.append(f"客服: {msg['agent']}")
    return "\n".join(parts), entities

REFERENCE_KEYWORDS = ["刚才", "之前", "那个", "这件", "上次", "前面", "之前那个", "刚才那个", "刚才那件"]

def _has_reference(text):
    return any(kw in text for kw in REFERENCE_KEYWORDS)

def _resolve_reference(text, entities, context_str):
    if not entities and not context_str:
        return None
    
    if ("糖度" in text or "甜" in text) and entities.get("sugar"):
        return f"您之前选择的是{entities['sugar']}"
    
    if ("冰" in text or "温度" in text) and entities.get("ice"):
        return f"您之前选择的是{entities['ice']}"
    
    if ("温度" in text or "多少度" in text or "热不热" in text) and entities.get("temperature"):
        return f"您之前选择的温度是{entities['temperature']}"
    
    if ("加料" in text or "配料" in text or "加了什么" in text or "加啥" in text) and entities.get("topping"):
        return f"您之前加的是{entities['topping']}"
    
    if ("大杯" in text or "中杯" in text or "小杯" in text or "杯型" in text or "规格" in text) and entities.get("size"):
        return f"您之前选择的是{entities['size']}"
    
    if ("订单号" in text or "单号" in text) and entities.get("order_id"):
        return f"您之前提到的订单号是{entities['order_id']}"
    
    if ("订单" in text or "查单" in text) and entities.get("order_id"):
        return f"您之前提到的订单号是{entities['order_id']}"
    
    if ("位置" in text or "在哪" in text or "哪里" in text or "门店" in text) and entities.get("location"):
        return f"您之前提到在{entities['location']}"
    
    if ("多少钱" in text or "价格" in text or "价钱" in text or "多少钱" in text or "报价" in text):
        price = entities.get("price")
        drink = entities.get("drink", "")
        if not price and context_str:
            context_lines = context_str.split("\n")
            for i, line in enumerate(context_lines):
                if drink and drink in line and "用户:" in line:
                    if i + 1 < len(context_lines):
                        next_line = context_lines[i + 1]
                        m = re.search(r'[¥￥]?\s*(\d{1,3}(?:\.\d+)?)\s*元?', next_line)
                        if m:
                            price = m.group(1)
                            break
                    if price:
                        break
            if not price:
                for i, line in enumerate(context_lines):
                    if drink and drink in line:
                        m = re.search(r'[¥￥]?\s*(\d{1,3}(?:\.\d+)?)\s*元?', line)
                        if m:
                            price = m.group(1)
                            break
            if not price:
                for line in reversed(context_lines):
                    m = re.search(r'[¥￥]?\s*(\d{1,3}(?:\.\d+)?)\s*元?', line)
                    if m:
                        price = m.group(1)
                        break
        if price:
            price_display = price.rstrip('0').rstrip('.') if '.' in price else price
            return f"{drink}的价格是{price_display}元" if drink else f"之前提到的价格是{price_display}元"
    
    if ("投诉" in text or "为什么" in text or "原因" in text or "后悔" in text):
        reason = entities.get("complaint_reason")
        if reason:
            return f"您之前投诉的原因是：{reason}"
        drink = entities.get("drink", "")
        for line in context_str.split("\n"):
            if "用户:" in line and ("甜" in line or "投诉" in line or "退款" in line or "太" in line or "咸" in line):
                content = line.replace('用户:', '').strip()
                if content and len(content) > 2:
                    return f"您之前投诉的原因是：{content}"
        if entities:
            for k, v in entities.items():
                if k in ("sugar", "ice", "complaint_reason", "temperature", "topping"):
                    return f"您之前提到的问题与{v}有关"
    
    if ("推荐" in text or "类似" in text) and entities.get("complimented_drink"):
        return f"您之前喜欢{entities['complimented_drink']}，类似风格的饮品还有：芝芝莓莓、杨枝甘露"
    
    if ("那个" in text or "这件" in text) and entities.get("drink"):
        return f"您说的是{entities['drink']}"
    
    if entities:
        parts = [f"{k}={v}" for k, v in entities.items()]
        return f"我记得：{', '.join(parts)}"
    
    return None

# ==================== Agent核心 ====================

def build_response(intent, text, tool_result=None, missing_params=None, context_str=None, entities=None):
    if missing_params:
        params_text = "、".join(missing_params)
        return f"【思考】{intent['name']}\n【回复】请问您能提供一下{params_text}吗？这样我可以更好地帮助您。"
    
    if _has_reference(text):
        resolved = _resolve_reference(text, entities or {}, context_str or "")
        if resolved:
            return f"【思考】指代消解\n【回复】{resolved}"
    
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
            if entities and entities.get("order_id"):
                return f"【思考】指代消解\n【回复】您之前提到的订单号是{entities['order_id']}，可以用来查询退款。"
            return f"【思考】{intent['name']}\n【回复】请问您能提供一下订单号吗？这样我可以帮您查询退款相关信息。"
        
        if intent["name"] == "query_recommend" and entities and entities.get("complimented_drink"):
            resolved = _resolve_reference(text, entities, context_str or "")
            if resolved:
                return f"【思考】记忆回复\n【回复】{resolved}"
        
        if intent["name"] == "query_order" and entities and entities.get("order_id"):
            if tool_error or not tool_result or not tool_result.get("data"):
                resolved = _resolve_reference(text, entities, context_str or "")
                if resolved:
                    return f"【思考】记忆回复\n【回复】{resolved}"
        
        if intent["name"] == "query_location" and entities and entities.get("location"):
            if tool_error or not tool_result or not tool_result.get("data"):
                return f"【思考】记忆回复\n【回复】您之前提到在{entities['location']}，附近门店信息需要实时查询，请确认网络连接。"
        
        if intent["name"] == "query_temp" and entities and entities.get("ice"):
            return f"【思考】记忆回复\n【回复】您之前选择的是{entities['ice']}"
        
        if entities and entities.get("temperature") and ("温度" in text or "多少度" in text or "热不热" in text):
            return f"【思考】记忆回复\n【回复】您之前选择的温度是{entities['temperature']}"
        
        if entities and entities.get("topping") and ("加料" in text or "配料" in text or "加了什么" in text or "加啥" in text):
            return f"【思考】记忆回复\n【回复】您之前加的是{entities['topping']}"
        
        if entities and entities.get("size") and ("大杯" in text or "中杯" in text or "小杯" in text or "规格" in text):
            return f"【思考】记忆回复\n【回复】您之前选择的是{entities['size']}"
        
        if tool_error:
            if entities:
                resolved = _resolve_reference(text, entities, context_str or "")
                if resolved:
                    return f"【思考】记忆回复\n【回复】{resolved}"
            fallback = DIRECT_RESPONSES.get(intent["name"], "暂时无法查询，请稍后再试。")
            return f"【思考】{intent['name']}\n【行动】调用工具(失败)\n【回复】{fallback}"
        if tool_result and tool_result["success"]:
            if entities and entities.get("complimented_drink") and ("类似" in text or "刚才" in text or "之前" in text):
                resolved = _resolve_reference(text, entities, context_str or "")
                if resolved:
                    return f"【思考】记忆回复\n【回复】{resolved}"
            return f"【思考】{intent['name']}\n【行动】调用工具\n【回复】{_format_tool_result(intent['name'], tool_result)}"
        if entities:
            resolved = _resolve_reference(text, entities, context_str or "")
            if resolved:
                return f"【思考】记忆回复\n【回复】{resolved}"
        return f"【思考】{intent['name']}\n【回复】{DIRECT_RESPONSES.get(intent['name'], '请告诉我具体查询内容。')}"
    
    if intent["name"] in ["place_order", "order_modify"]:
        return f"【思考】{intent['name']}\n【回复】请提供您想点的饮品名称。"
    
    if entities:
        resolved = _resolve_reference(text, entities, context_str or "")
        if resolved:
            return f"【思考】记忆回复\n【回复】{resolved}"
    
    return f"【思考】{intent['name']}\n【回复】{DIRECT_RESPONSES.get(intent['name'], '您好，有什么可以帮助您的？')}"

def _format_tool_result(intent_name, result):
    if intent_name == "query_stores" or intent_name == "query_location":
        names = [p.get("name", "") for p in result["data"][:3]]
        return f"附近门店：{', '.join(names)}。"
    if intent_name in ("query_menu", "query_price"):
        if result.get("keyword"):
            items = [f"{i.get('name', '')}（¥{i.get('price', '')}）" for i in result["data"][:3]]
            return f"{', '.join(items)}。"
        names = [i.get("name", "") for i in result["data"][:3]]
        return f"饮品：{', '.join(names)}。"
    if intent_name in ("query_order", "query_history"):
        if result["data"]:
            orders = []
            for o in result["data"]:
                orders.append(f"{o.get('order_id', '')} ({o.get('store', '')})：{o.get('status', '')}")
            return f"您有{len(result['data'])}个订单：{'；'.join(orders)}。"
        return "抱歉，没有找到相关的订单记录。请确认订单号是否正确，或稍后再试。"
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
    
    if not text or not text.strip():
        response = "【思考】空输入\n【回复】您好，请问有什么可以帮助您的？"
        trace.add_step("clarify", {"missing_params": ["用户意图"]})
        trace.add_step("response", {"text": response})
        trace.save_to_file()
        if memory_store:
            save_message(memory_store, session_id, text or "", response)
        return response, {"name": "unclear", "confidence": 0.0, "category": "通用"}
    
    cached_response = _get_cached_response(text)
    if cached_response:
        if memory_store:
            asyncio.create_task(asyncio.to_thread(save_message, memory_store, session_id, text, cached_response))
        return cached_response, {"name": "cached", "confidence": 1.0, "category": "缓存"}
    
    termination = should_terminate(text, trace)
    if termination["terminate"]:
        if termination["action"] == "human_handover":
            reply = "【思考】终止判断：需要转人工\n【回复】抱歉，我无法解决您的问题，已为您转接人工客服。"
        else:
            reply = "【思考】终止判断：对话结束\n【回复】很高兴能帮到您，祝您生活愉快！"
        if memory_store:
            save_message(memory_store, session_id, text, reply)
        return reply, {"name": "terminated", "confidence": 1.0, "category": "终止"}
    
    intent_task = asyncio.create_task(recognize_intent_async(text, llm_client))
    
    def load_context():
        if memory_store:
            return get_context(memory_store, session_id)
        return None
    
    context_task = asyncio.create_task(asyncio.to_thread(load_context))
    
    intent, context_result = await asyncio.gather(intent_task, context_task)
    context_str, entities = context_result if isinstance(context_result, tuple) else (context_result or "", {})
    
    trace.add_step("intent", {"name": intent["name"], "confidence": intent["confidence"], "category": intent.get("category")})
    
    if intent["confidence"] >= 0.6:
        tool_name = INTENT_TOOL.get(intent["name"])
        
        drink_kw_for_price = _extract_drink_keyword(text)
        if drink_kw_for_price and ("多少钱" in text or "价格" in text or "价钱" in text) and intent["name"] == "query_recommend":
            intent = {"name": "query_price", "confidence": 0.8, "category": CATEGORY_MAP.get("query_price", "价格查询")}
            tool_name = "query_menu"
        
        if intent["name"] == "query_recommend":
            try:
                tool_result = await asyncio.to_thread(query_recommend, query=text)
            except Exception as e:
                tool_result = {"success": False, "data": [], "error": str(e)}
            response = build_response(intent, text, tool_result, [], context_str, entities)
            trace.add_step("tool_call", {"tool_name": "query_recommend", "intent_name": intent["name"], "params": {}})
            trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": tool_result.get("data", [])})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            _cache_response(text, response)
            return response, intent
        
        elif intent["name"] == "query_menu" or intent["name"] == "query_price":
            def _call_tool():
                return get_tool_response(intent["name"], text, TOOLS, session_id)
            tool_result, _ = await asyncio.to_thread(_call_tool)
            response = build_response(intent, text, tool_result, [], context_str, entities)
            trace.add_step("tool_call", {"tool_name": "query_menu", "intent_name": intent["name"], "params": {}})
            trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": tool_result.get("data", []) if tool_result else []})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            _cache_response(text, response)
            return response, intent
        
        elif intent["name"] == "query_order" or intent["name"] == "query_refund":
            params, missing = extract_params(text, intent["name"], session_id)
            if params.get("order_id"):
                def _call_tool():
                    return get_tool_response(intent["name"], text, TOOLS, session_id)
                tool_result, _ = await asyncio.to_thread(_call_tool)
                response = build_response(intent, text, tool_result, [], context_str, entities)
                trace.add_step("tool_call", {"tool_name": "query_order", "intent_name": intent["name"], "params": params})
                trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": tool_result.get("data", [])})
                trace.add_step("response", {"text": response})
                trace.save_to_file()
                if memory_store:
                    save_message(memory_store, session_id, text, response)
                _cache_response(text, response)
                return response, intent
            else:
                if entities and entities.get("order_id"):
                    response = f"【思考】记忆回复\n【回复】您之前提到的订单号是{entities['order_id']}，请确认是否需要查询该订单。"
                else:
                    response = f"【思考】{intent['name']}\n【回复】请问您能提供一下订单号吗？这样我可以帮您查询相关信息。"
                trace.add_step("clarify", {"missing_params": ["订单号"]})
                trace.add_step("response", {"text": response})
                trace.save_to_file()
                if memory_store:
                    save_message(memory_store, session_id, text, response)
                _cache_response(text, response)
                return response, intent
        
        elif intent["name"] == "query_location" or intent["name"] == "query_store":
            params, missing = extract_params(text, intent["name"], session_id)
            if params.get("location"):
                def _call_tool():
                    return get_tool_response(intent["name"], text, TOOLS, session_id)
                tool_result, _ = await asyncio.to_thread(_call_tool)
                response = build_response(intent, text, tool_result, [], context_str, entities)
                trace.add_step("tool_call", {"tool_name": "query_stores", "intent_name": intent["name"], "params": params})
                trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": tool_result.get("data", []) if tool_result else []})
                trace.add_step("response", {"text": response})
                trace.save_to_file()
                if memory_store:
                    save_message(memory_store, session_id, text, response)
                _cache_response(text, response)
                return response, intent
            else:
                if entities and entities.get("location"):
                    response = f"【思考】记忆回复\n【回复】您之前提到在{entities['location']}，附近门店信息需要实时查询，请确认网络连接。"
                else:
                    response = f"【思考】{intent['name']}\n【回复】请问您当前的位置在哪里？这样我可以帮您查询附近的门店。"
                trace.add_step("clarify", {"missing_params": ["位置信息"]})
                trace.add_step("response", {"text": response})
                trace.save_to_file()
                if memory_store:
                    save_message(memory_store, session_id, text, response)
                _cache_response(text, response)
                return response, intent
        
        elif intent["name"].startswith("complaint"):
            tool_result = None
            if tool_name == "log_complaint":
                tool_result = await asyncio.to_thread(log_complaint, get_user_id(session_id), text, category=INTENT_TO_CATEGORY.get(intent["name"], "口味"), intent_name=intent["name"])
                trace.add_step("tool_call", {"tool_name": "log_complaint", "intent_name": intent["name"], "params": {"complaint": text}})
                trace.add_step("tool_result", {"success": tool_result.get("success", False), "data": {"complaint_id": tool_result.get("complaint_id")}})
            response = build_response(intent, text, tool_result, [], context_str, entities)
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            _cache_response(text, response)
            return response, intent
    
    return await asyncio.to_thread(harness_handle, text, session_id, intent, trace, memory_store)


def process_message(text, session_id="default", memory_store=None, llm_client=None):
    return asyncio.run(process_message_async(text, session_id, memory_store, llm_client))


async def process_message_stream_async(text, session_id="default", memory_store=None, llm_client=None):
    """流式版本：分步 yield SSE 事件（start/thinking/tool_call/tool_result/response/done/error）。
    复用 process_message_async 的子函数，保持业务逻辑一致。"""
    import json as _json

    def _evt(data):
        return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

    async def _emit_tool_done(intent, text, trace, memory_store, tool_label, tool_result, params=None):
        data_list = (tool_result.get("data", []) if tool_result else [])
        yield _evt({"type": "tool_result",
                    "success": bool(tool_result.get("success", False)) if tool_result else False,
                    "data": data_list[:5], "count": len(data_list)})
        context_str, entities = get_context(memory_store, session_id) if memory_store else ("", {})
        response = build_response(intent, text, tool_result, [], context_str, entities)
        trace.add_step("tool_call", {"tool_name": tool_label, "intent_name": intent["name"], "params": params or {}})
        trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": data_list})
        trace.add_step("response", {"text": response})
        trace.save_to_file()
        if memory_store:
            save_message(memory_store, session_id, text, response)
        _cache_response(text, response)
        yield _evt({"type": "response", "content": response, "intent": intent})
        yield _evt({"type": "done", "intent": intent})

    async def _call_get_tool_response():
        return await asyncio.to_thread(get_tool_response, intent["name"], text, TOOLS, session_id)

    trace = ExecutionTrace()
    trace.session_id = session_id

    try:
        # ---- 空输入 ----
        if not text or not text.strip():
            response = "【思考】空输入\n【回复】您好，请问有什么可以帮助您的？"
            trace.add_step("clarify", {"missing_params": ["用户意图"]})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text or "", response)
            intent = {"name": "unclear", "confidence": 0.0, "category": "通用"}
            yield _evt({"type": "response", "content": response, "intent": intent})
            yield _evt({"type": "done", "intent": intent})
            return

        # ---- 缓存命中 ----
        cached_response = _get_cached_response(text)
        if cached_response:
            if memory_store:
                asyncio.create_task(asyncio.to_thread(save_message, memory_store, session_id, text, cached_response))
            intent = {"name": "cached", "confidence": 1.0, "category": "缓存"}
            yield _evt({"type": "thinking", "intent": intent})
            yield _evt({"type": "response", "content": cached_response, "intent": intent})
            yield _evt({"type": "done", "intent": intent})
            return

        # ---- 终止判断 ----
        termination = should_terminate(text, trace)
        if termination["terminate"]:
            if termination["action"] == "human_handover":
                reply = "【思考】终止判断：需要转人工\n【回复】抱歉，我无法解决您的问题，已为您转接人工客服。"
            else:
                reply = "【思考】终止判断：对话结束\n【回复】很高兴能帮到您，祝您生活愉快！"
            if memory_store:
                save_message(memory_store, session_id, text, reply)
            intent = {"name": "terminated", "confidence": 1.0, "category": "终止"}
            yield _evt({"type": "response", "content": reply, "intent": intent})
            yield _evt({"type": "done", "intent": intent})
            return

        # ---- 意图识别 + 上下文（并行）----
        intent_task = asyncio.create_task(recognize_intent_async(text, llm_client))

        def load_context():
            if memory_store:
                return get_context(memory_store, session_id)
            return None

        context_task = asyncio.create_task(asyncio.to_thread(load_context))
        intent, context_result = await asyncio.gather(intent_task, context_task)
        context_str, entities = context_result if isinstance(context_result, tuple) else (context_result or "", {})
        trace.add_step("intent", {"name": intent["name"], "confidence": intent["confidence"], "category": intent.get("category")})
        yield _evt({"type": "thinking", "intent": intent})

        # ---- 工具调用分支 ----
        if intent["confidence"] >= 0.6:
            tool_name = INTENT_TOOL.get(intent["name"])

            if intent["name"] == "query_recommend":
                yield _evt({"type": "tool_call", "tool": "query_recommend", "params": {}})
                try:
                    tool_result = await asyncio.to_thread(query_recommend, query=text)
                except Exception as e:
                    tool_result = {"success": False, "data": [], "error": str(e)}
                async for evt in _emit_tool_done(intent, text, trace, memory_store, "query_recommend", tool_result):
                    yield evt
                return

            if intent["name"] == "query_menu":
                yield _evt({"type": "tool_call", "tool": "query_menu", "params": {}})
                tool_result, _ = await _call_get_tool_response()
                async for evt in _emit_tool_done(intent, text, trace, memory_store, "query_menu", tool_result):
                    yield evt
                return

            if intent["name"] in ("query_order", "query_refund"):
                params, missing = extract_params(text, intent["name"], session_id)
                if params.get("order_id"):
                    yield _evt({"type": "tool_call", "tool": "query_order", "params": params})
                    tool_result, _ = await _call_get_tool_response()
                    async for evt in _emit_tool_done(intent, text, trace, memory_store, "query_order", tool_result, params):
                        yield evt
                else:
                    response = f"【思考】{intent['name']}\n【回复】请问您能提供一下订单号吗？这样我可以帮您查询相关信息。"
                    trace.add_step("clarify", {"missing_params": ["订单号"]})
                    trace.add_step("response", {"text": response})
                    trace.save_to_file()
                    if memory_store:
                        save_message(memory_store, session_id, text, response)
                    _cache_response(text, response)
                    yield _evt({"type": "response", "content": response, "intent": intent})
                    yield _evt({"type": "done", "intent": intent})
                return

            if intent["name"] in ("query_location", "query_store"):
                params, missing = extract_params(text, intent["name"], session_id)
                if params.get("location"):
                    yield _evt({"type": "tool_call", "tool": "query_stores", "params": params})
                    tool_result, _ = await _call_get_tool_response()
                    async for evt in _emit_tool_done(intent, text, trace, memory_store, "query_stores", tool_result, params):
                        yield evt
                else:
                    response = f"【思考】{intent['name']}\n【回复】请问您当前的位置在哪里？这样我可以帮您查询附近的门店。"
                    trace.add_step("clarify", {"missing_params": ["位置信息"]})
                    trace.add_step("response", {"text": response})
                    trace.save_to_file()
                    if memory_store:
                        save_message(memory_store, session_id, text, response)
                    _cache_response(text, response)
                    yield _evt({"type": "response", "content": response, "intent": intent})
                    yield _evt({"type": "done", "intent": intent})
                return

            if intent["name"].startswith("complaint"):
                tool_result = None
                if tool_name == "log_complaint":
                    yield _evt({"type": "tool_call", "tool": "log_complaint", "params": {"complaint": text}})
                    tool_result = await asyncio.to_thread(log_complaint, get_user_id(session_id), text,
                                                          category=INTENT_TO_CATEGORY.get(intent["name"], "口味"),
                                                          intent_name=intent["name"])
                async for evt in _emit_tool_done(intent, text, trace, memory_store, "log_complaint", tool_result):
                    yield evt
                return

            # 其他命中工具的意图：通用流程
            if tool_name:
                yield _evt({"type": "tool_call", "tool": tool_name, "params": {}})
                tool_result, _ = await _call_get_tool_response()
                async for evt in _emit_tool_done(intent, text, trace, memory_store, tool_name, tool_result):
                    yield evt
                return

        # ---- 兜底：harness_handle ----
        response, intent = await asyncio.to_thread(harness_handle, text, session_id, intent, trace, memory_store)
        yield _evt({"type": "response", "content": response, "intent": intent})
        yield _evt({"type": "done", "intent": intent})

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield _evt({"type": "error", "message": f"服务异常: {e}"})


def harness_handle(text, session_id, intent, trace, memory_store):
    context_str, entities = get_context(memory_store, session_id) if memory_store else ("", {})
    tool_name = INTENT_TOOL.get(intent["name"])
    tool_result = None
    missing_params = []
    
    if tool_name and tool_name != "log_complaint":
        tool_result, missing_params = get_tool_response(intent["name"], text, session_id=session_id)
        
        if missing_params:
            response = build_response(intent, text, None, missing_params, context_str, entities)
            trace.add_step("clarify", {"missing_params": missing_params})
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
        
        trace.add_step("tool_call", {"tool_name": tool_name, "intent_name": intent["name"], "params": extract_params(text, intent["name"], session_id)[0]})
        trace.add_step("tool_result", {"success": tool_result.get("success", False) if tool_result else False, "data": tool_result.get("data", []) if tool_result else []})
        
        if tool_result and tool_result.get("success"):
            response = build_response(intent, text, tool_result, [], context_str, entities)
            trace.add_step("response", {"text": response})
            trace.save_to_file()
            if memory_store:
                save_message(memory_store, session_id, text, response)
            return response, intent
        
        if intent["name"] == "query_menu":
            response = build_response(intent, text, tool_result, [], context_str, entities)
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
    
    response = build_response(intent, text, tool_result, missing_params, context_str, entities)
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