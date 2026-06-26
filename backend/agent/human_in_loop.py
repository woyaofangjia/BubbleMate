import time
from typing import Dict, List

THRESHOLDS = {"high": 0.8, "medium": 0.5, "low": 0.3}

INTERVENTION_SUGGESTIONS = {
    "low_confidence": "系统置信度低，建议人工确认用户意图",
    "tool_failure": "工具调用失败，可能需要手动查询",
    "user_complaint": "用户明确投诉，建议人工安抚",
    "safety_check": "触发安全检查，建议人工复核",
    "complex_query": "复杂查询，建议人工处理",
}

INTERVENTION_MESSAGES = {
    "low_confidence": "这个问题比较复杂，我为您转接人工客服...",
    "tool_failure": "系统暂时无法处理，正在为您转接人工...",
    "user_complaint": "非常抱歉给您带来不好的体验，马上为您安排专属客服...",
    "safety_check": "为了给您更好的服务，正在为您转接人工客服...",
    "complex_query": "这个问题需要更专业的解答，正在为您转接...",
}

interventions = {}

def calculate_confidence(intent_result: Dict, tool_results: List[Dict], session_history: List[Dict]) -> Dict:
    intent_conf = intent_result.get("confidence", 0.5)
    tool_reliability = sum(1 for t in tool_results if t.get("success", False)) / len(tool_results) if tool_results else 0.8
    context_continuity = 0.3 if len(session_history) >= 2 and session_history[-1].get("content") == session_history[-2].get("content") else 0.5 if len(session_history) >= 2 and sum(1 for h in session_history[-3:] if "?" in h.get("content", "")) >= 2 else 1.0 if len(session_history) < 2 else 0.9
    intent_name = intent_result.get("name", "")
    user_message = intent_result.get("text", "")
    safety_score = 0.4 if intent_name in ["complaint_taste_refund", "complaint_taste_price"] else 0.3 if any(word in user_message for word in ["举报", "律师", "315", "投诉", "曝光"]) else 0.95
    overall = intent_conf * 0.4 + tool_reliability * 0.25 + context_continuity * 0.2 + safety_score * 0.15
    return {"overall": round(overall, 3), "intent": round(intent_conf, 3), "tool": round(tool_reliability, 3), "context": round(context_continuity, 3), "safety": round(safety_score, 3)}

def should_intervene(confidence: Dict) -> str:
    if confidence["overall"] < THRESHOLDS["low"]:
        return "low_confidence"
    if confidence["intent"] < 0.4:
        return "complex_query"
    if confidence["safety"] < 0.5:
        return "safety_check"
    return ""

def evaluate(session_id: str, intent_result: Dict, tool_results: List[Dict], session_history: List[Dict], user_message: str, agent_response: str) -> Dict:
    confidence = calculate_confidence(intent_result, tool_results, session_history)
    intervention_type = should_intervene(confidence)
    if intervention_type:
        intervention_id = f"HIL-{session_id}-{int(time.time())}"
        interventions[intervention_id] = {"id": intervention_id, "session_id": session_id, "type": intervention_type, "confidence": confidence, "user_message": user_message, "agent_response": agent_response, "status": "pending", "created_at": time.time()}
        return {"needs_intervention": True, "intervention_type": intervention_type, "confidence": confidence, "suggestion": INTERVENTION_SUGGESTIONS[intervention_type], "intervention_id": intervention_id, "message": INTERVENTION_MESSAGES[intervention_type]}
    return {"needs_intervention": False, "intervention_type": None, "confidence": {"overall": confidence["overall"]}, "suggestion": "自动处理", "intervention_id": None, "message": None}

def resolve_intervention(intervention_id: str, resolution: str, agent_id: str) -> bool:
    if intervention_id not in interventions:
        return False
    interventions[intervention_id].update({"status": "resolved", "resolution": resolution, "assigned_to": agent_id, "resolved_at": time.time()})
    return True

def get_pending_interventions() -> List[Dict]:
    pending = [i for i in interventions.values() if i["status"] == "pending"]
    return sorted(pending, key=lambda x: x["created_at"])

def get_stats() -> Dict:
    total = len(interventions)
    resolved = sum(1 for i in interventions.values() if i["status"] == "resolved")
    pending = sum(1 for i in interventions.values() if i["status"] == "pending")
    resolved_items = [i for i in interventions.values() if i["status"] == "resolved" and i.get("resolved_at")]
    avg_time = round(sum(i["resolved_at"] - i["created_at"] for i in resolved_items) / len(resolved_items), 2) if resolved_items else 0.0
    return {"total_interventions": total, "resolved": resolved, "pending": pending, "resolution_rate": round(resolved / total, 3) if total > 0 else 0, "avg_resolution_time": avg_time}