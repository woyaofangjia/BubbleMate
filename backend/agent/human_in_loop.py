"""
BubbleMate - Human-in-the-Loop机制
置信度计算 + 人工介入触发 + 知识库更新
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import time
from datetime import datetime

class InterventionType(Enum):
    """人工介入类型"""
    LOW_CONFIDENCE = "low_confidence"      # 置信度低
    TOOL_FAILURE = "tool_failure"          # 工具连续失败
    USER_COMPLAINT = "user_complaint"      # 用户明确投诉
    SAFETY_CHECK = "safety_check"          # 安全检查触发
    COMPLEX_QUERY = "complex_query"        # 复杂查询

@dataclass
class ConfidenceScore:
    """置信度评分"""
    intent_confidence: float      # 意图识别置信度
    tool_reliability: float       # 工具可靠性
    context_continuity: float     # 上下文连续性
    safety_score: float           # 安全评分
    overall: float = 0.0          # 综合置信度
    
    def __post_init__(self):
        # 加权计算综合置信度
        weights = {
            'intent': 0.4,
            'tool': 0.25,
            'context': 0.2,
            'safety': 0.15
        }
        self.overall = (
            self.intent_confidence * weights['intent'] +
            self.tool_reliability * weights['tool'] +
            self.context_continuity * weights['context'] +
            self.safety_score * weights['safety']
        )

@dataclass
class HumanIntervention:
    """人工介入记录"""
    id: str
    session_id: str
    intervention_type: InterventionType
    confidence: ConfidenceScore
    user_message: str
    agent_response: str
    status: str = "pending"  # pending, assigned, resolved, escalated
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "type": self.intervention_type.value,
            "confidence": {
                "overall": round(self.confidence.overall, 3),
                "intent": round(self.confidence.intent_confidence, 3),
                "tool": round(self.confidence.tool_reliability, 3),
                "context": round(self.confidence.context_continuity, 3),
                "safety": round(self.confidence.safety_score, 3),
            },
            "user_message": self.user_message,
            "agent_response": self.agent_response,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "resolution": self.resolution,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "resolved_at": datetime.fromtimestamp(self.resolved_at).isoformat() if self.resolved_at else None,
        }

class ConfidenceCalculator:
    """置信度计算器"""
    
    def __init__(self):
        self.thresholds = {
            "high": 0.8,      # 高置信度，自动处理
            "medium": 0.5,    # 中置信度，提示用户确认
            "low": 0.3,       # 低置信度，转人工
        }
        self.failure_history: Dict[str, List[bool]] = {}  # 工具失败历史
    
    def calculate(self, 
                  intent_result: Dict,
                  tool_results: List[Dict],
                  session_history: List[Dict]) -> ConfidenceScore:
        """
        计算综合置信度
        
        Args:
            intent_result: 意图识别结果
            tool_results: 工具调用结果列表
            session_history: 会话历史
        """
        # 1. 意图识别置信度
        intent_conf = intent_result.get("confidence", 0.5)
        
        # 2. 工具可靠性（基于最近调用成功率）
        if tool_results:
            success_count = sum(1 for t in tool_results if t.get("success", False))
            tool_reliability = success_count / len(tool_results)
        else:
            tool_reliability = 0.8  # 无工具调用时默认较高
        
        # 3. 上下文连续性
        context_continuity = self._calculate_context_continuity(session_history)
        
        # 4. 安全评分
        safety_score = self._calculate_safety_score(intent_result, session_history)
        
        return ConfidenceScore(
            intent_confidence=intent_conf,
            tool_reliability=tool_reliability,
            context_continuity=context_continuity,
            safety_score=safety_score
        )
    
    def _calculate_context_continuity(self, session_history: List[Dict]) -> float:
        """计算上下文连续性"""
        if len(session_history) < 2:
            return 1.0
        
        # 检查最近是否有异常模式
        recent = session_history[-3:]
        
        # 用户重复提问检测
        user_messages = [h.get("content", "") for h in recent if h.get("role") == "user"]
        if len(user_messages) >= 2:
            # 简单重复检测
            if user_messages[-1] == user_messages[-2]:
                return 0.3  # 用户重复提问，可能之前回答不满意
        
        # 检查是否有连续澄清
        clarify_count = sum(1 for h in recent if "?" in h.get("content", ""))
        if clarify_count >= 2:
            return 0.5  # 多次提问，可能上下文断裂
        
        return 0.9
    
    def _calculate_safety_score(self, intent_result: Dict, session_history: List[Dict]) -> float:
        """计算安全评分"""
        intent_name = intent_result.get("name", "")
        
        # 高风险意图检查
        high_risk_intents = ["complaint_taste_refund", "complaint_taste_price"]
        if intent_name in high_risk_intents:
            return 0.4  # 需要人工复核
        
        # 检查敏感词
        user_message = intent_result.get("text", "")
        sensitive_words = ["举报", "律师", "315", "投诉", "曝光"]
        if any(word in user_message for word in sensitive_words):
            return 0.3
        
        return 0.95
    
    def should_intervene(self, confidence: ConfidenceScore) -> Optional[InterventionType]:
        """判断是否需要人工介入"""
        if confidence.overall < self.thresholds["low"]:
            return InterventionType.LOW_CONFIDENCE
        
        if confidence.intent_confidence < 0.4:
            return InterventionType.COMPLEX_QUERY
        
        if confidence.safety_score < 0.5:
            return InterventionType.SAFETY_CHECK
        
        return None

class HumanInLoopManager:
    """Human-in-the-Loop管理器"""
    
    def __init__(self):
        self.calculator = ConfidenceCalculator()
        self.interventions: Dict[str, HumanIntervention] = {}
        self.knowledge_base_updates: List[Dict] = []
    
    def evaluate(self, 
                 session_id: str,
                 intent_result: Dict,
                 tool_results: List[Dict],
                 session_history: List[Dict],
                 user_message: str,
                 agent_response: str) -> Dict:
        """
        评估当前对话状态，决定是否需要人工介入
        
        Returns:
            {
                "needs_intervention": bool,
                "intervention_type": str | None,
                "confidence": ConfidenceScore,
                "suggestion": str,
                "intervention_id": str | None
            }
        """
        # 计算置信度
        confidence = self.calculator.calculate(
            intent_result, tool_results, session_history
        )
        
        # 判断是否需要介入
        intervention_type = self.calculator.should_intervene(confidence)
        
        if intervention_type:
            # 创建介入记录
            intervention_id = f"HIL-{session_id}-{int(time.time())}"
            intervention = HumanIntervention(
                id=intervention_id,
                session_id=session_id,
                intervention_type=intervention_type,
                confidence=confidence,
                user_message=user_message,
                agent_response=agent_response
            )
            self.interventions[intervention_id] = intervention
            
            return {
                "needs_intervention": True,
                "intervention_type": intervention_type.value,
                "confidence": {
                    "overall": round(confidence.overall, 3),
                    "intent": round(confidence.intent_confidence, 3),
                    "tool": round(confidence.tool_reliability, 3),
                    "context": round(confidence.context_continuity, 3),
                    "safety": round(confidence.safety_score, 3),
                },
                "suggestion": self._get_suggestion(intervention_type),
                "intervention_id": intervention_id,
                "message": self._get_user_message(intervention_type)
            }
        
        return {
            "needs_intervention": False,
            "intervention_type": None,
            "confidence": {
                "overall": round(confidence.overall, 3),
            },
            "suggestion": "自动处理",
            "intervention_id": None,
            "message": None
        }
    
    def _get_suggestion(self, intervention_type: InterventionType) -> str:
        """获取给客服的建议"""
        suggestions = {
            InterventionType.LOW_CONFIDENCE: "系统置信度低，建议人工确认用户意图",
            InterventionType.TOOL_FAILURE: "工具调用失败，可能需要手动查询",
            InterventionType.USER_COMPLAINT: "用户明确投诉，建议人工安抚",
            InterventionType.SAFETY_CHECK: "触发安全检查，建议人工复核",
            InterventionType.COMPLEX_QUERY: "复杂查询，建议人工处理",
        }
        return suggestions.get(intervention_type, "建议人工介入")
    
    def _get_user_message(self, intervention_type: InterventionType) -> str:
        """获取给用户的提示消息"""
        messages = {
            InterventionType.LOW_CONFIDENCE: "这个问题比较复杂，我为您转接人工客服...",
            InterventionType.TOOL_FAILURE: "系统暂时无法处理，正在为您转接人工...",
            InterventionType.USER_COMPLAINT: "非常抱歉给您带来不好的体验，马上为您安排专属客服...",
            InterventionType.SAFETY_CHECK: "为了给您更好的服务，正在为您转接人工客服...",
            InterventionType.COMPLEX_QUERY: "这个问题需要更专业的解答，正在为您转接...",
        }
        return messages.get(intervention_type, "正在为您转接人工客服...")
    
    def resolve_intervention(self, intervention_id: str, 
                           resolution: str,
                           agent_id: str) -> bool:
        """解决人工介入请求"""
        if intervention_id not in self.interventions:
            return False
        
        intervention = self.interventions[intervention_id]
        intervention.status = "resolved"
        intervention.resolution = resolution
        intervention.assigned_to = agent_id
        intervention.resolved_at = time.time()
        
        # 记录知识库更新
        self.knowledge_base_updates.append({
            "intervention_id": intervention_id,
            "user_message": intervention.user_message,
            "resolution": resolution,
            "timestamp": time.time()
        })
        
        return True
    
    def get_pending_interventions(self) -> List[Dict]:
        """获取待处理的人工介入列表"""
        pending = [
            i.to_dict() 
            for i in self.interventions.values() 
            if i.status == "pending"
        ]
        return sorted(pending, key=lambda x: x["created_at"])
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.interventions)
        resolved = sum(1 for i in self.interventions.values() if i.status == "resolved")
        pending = sum(1 for i in self.interventions.values() if i.status == "pending")
        
        return {
            "total_interventions": total,
            "resolved": resolved,
            "pending": pending,
            "resolution_rate": round(resolved / total, 3) if total > 0 else 0,
            "avg_resolution_time": self._avg_resolution_time(),
            "knowledge_base_updates": len(self.knowledge_base_updates)
        }
    
    def _avg_resolution_time(self) -> float:
        """计算平均解决时间"""
        resolved = [
            i for i in self.interventions.values() 
            if i.status == "resolved" and i.resolved_at
        ]
        if not resolved:
            return 0.0
        
        times = [i.resolved_at - i.created_at for i in resolved]
        return round(sum(times) / len(times), 2)


# 全局实例
hil_manager = HumanInLoopManager()

if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("Human-in-the-Loop 测试")
    print("=" * 60)
    
    # 场景1: 高置信度
    result = hil_manager.evaluate(
        session_id="test-1",
        intent_result={"name": "query_menu", "confidence": 0.95, "text": "推荐奶茶"},
        tool_results=[{"success": True}],
        session_history=[],
        user_message="推荐奶茶",
        agent_response=""
    )
    print(f"高置信度场景: {result}")
    
    # 场景2: 低置信度
    result = hil_manager.evaluate(
        session_id="test-2",
        intent_result={"name": "unknown", "confidence": 0.2, "text": "你们这个怎么样"},
        tool_results=[],
        session_history=[],
        user_message="你们这个怎么样",
        agent_response=""
    )
    print(f"低置信度场景: {result}")
    
    # 场景3: 安全触发
    result = hil_manager.evaluate(
        session_id="test-3",
        intent_result={"name": "complaint_taste", "confidence": 0.7, "text": "我要举报你们"},
        tool_results=[],
        session_history=[],
        user_message="我要举报你们",
        agent_response=""
    )
    print(f"安全触发场景: {result}")
    
    print("\n统计:")
    print(hil_manager.get_stats())