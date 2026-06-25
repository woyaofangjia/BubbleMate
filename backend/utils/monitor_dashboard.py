"""
BubbleMate Monitor Dashboard - 监控看板数据服务
实现工具失败率、用户纠偏率、意图准确率等核心指标采集
"""

import json
import time
import os
from typing import Dict, List
from dataclasses import dataclass, field, asdict
from collections import deque

@dataclass
class SessionMetrics:
    """会话级指标"""
    session_id: str
    start_time: float
    message_count: int = 0
    tool_calls: int = 0
    tool_failures: int = 0
    user_corrections: int = 0  # 用户纠偏次数
    intent_confidence_sum: float = 0.0
    intent_count: int = 0
    avg_response_time: float = 0.0
    response_time_sum: float = 0.0
    
    @property
    def tool_failure_rate(self) -> float:
        if self.tool_calls == 0:
            return 0.0
        return self.tool_failures / self.tool_calls * 100
    
    @property
    def correction_rate(self) -> float:
        """用户纠偏率 = 纠偏次数 / 总消息数"""
        if self.message_count == 0:
            return 0.0
        return self.user_corrections / self.message_count * 100
    
    @property
    def avg_intent_confidence(self) -> float:
        if self.intent_count == 0:
            return 0.0
        return self.intent_confidence_sum / self.intent_count


class MonitorDashboard:
    """监控看板"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        
        # 全局指标
        self.total_sessions = 0
        self.total_messages = 0
        self.total_tool_calls = 0
        self.total_tool_failures = 0
        self.total_user_corrections = 0
        self.total_response_time = 0.0
        
        # 滑动窗口（最近N条消息）
        self.message_window: deque = deque(maxlen=window_size)
        self.tool_call_window: deque = deque(maxlen=window_size)
        
        # 会话指标
        self.sessions: Dict[str, SessionMetrics] = {}
        
        # 时间序列数据（用于折线图）
        self.time_series: List[Dict] = []
        self.last_save_time = time.time()
    
    def start_session(self, session_id: str):
        """开始会话"""
        self.total_sessions += 1
        self.sessions[session_id] = SessionMetrics(
            session_id=session_id,
            start_time=time.time()
        )
    
    def record_message(self, session_id: str, intent_confidence: float, 
                       response_time: float, is_correction: bool = False):
        """记录消息指标"""
        if session_id not in self.sessions:
            self.start_session(session_id)
        
        session = self.sessions[session_id]
        session.message_count += 1
        session.intent_confidence_sum += intent_confidence
        session.intent_count += 1
        session.response_time_sum += response_time
        session.avg_response_time = session.response_time_sum / session.message_count
        
        if is_correction:
            session.user_corrections += 1
            self.total_user_corrections += 1
        
        self.total_messages += 1
        self.total_response_time += response_time
        
        # 记录到滑动窗口
        self.message_window.append({
            "timestamp": time.time(),
            "session_id": session_id,
            "intent_confidence": intent_confidence,
            "response_time": response_time,
            "is_correction": is_correction
        })
        
        # 定期保存时间序列数据
        if time.time() - self.last_save_time > 60:  # 每分钟保存一次
            self._save_time_series()
    
    def record_tool_call(self, session_id: str, tool_name: str, 
                         success: bool, latency: float):
        """记录工具调用指标"""
        if session_id not in self.sessions:
            self.start_session(session_id)
        
        session = self.sessions[session_id]
        session.tool_calls += 1
        self.total_tool_calls += 1
        
        if not success:
            session.tool_failures += 1
            self.total_tool_failures += 1
        
        # 记录到滑动窗口
        self.tool_call_window.append({
            "timestamp": time.time(),
            "session_id": session_id,
            "tool_name": tool_name,
            "success": success,
            "latency": latency
        })
    
    def detect_correction(self, session_id: str, user_message: str) -> bool:
        """
        检测用户是否在纠偏（重复提问、否定之前回复等）
        纠偏信号：
        1. 用户说"不对"、"错了"、"不是"
        2. 用户重复问同一个问题（意图相同但回答不满意）
        3. 用户追问"真的吗"、"你确定"
        """
        correction_signals = [
            "不对", "错了", "不是", "你搞错了",
            "真的吗", "你确定", "再确认一下",
            "我说的是", "我的意思是",
            "重新", "再查", "再搜",
        ]
        
        return any(signal in user_message for signal in correction_signals)
    
    def get_global_stats(self) -> Dict:
        """获取全局统计"""
        recent_messages = list(self.message_window)
        recent_tools = list(self.tool_call_window)
        
        # 计算滑动窗口指标
        recent_corrections = sum(1 for m in recent_messages if m.get("is_correction"))
        recent_tool_failures = sum(1 for t in recent_tools if not t.get("success"))
        
        return {
            "total_sessions": self.total_sessions,
            "total_messages": self.total_messages,
            "total_tool_calls": self.total_tool_calls,
            
            # 核心指标（面试重点）
            "tool_failure_rate": round(
                self.total_tool_failures / self.total_tool_calls * 100 
                if self.total_tool_calls > 0 else 0, 2
            ),
            "user_correction_rate": round(
                self.total_user_corrections / self.total_messages * 100 
                if self.total_messages > 0 else 0, 2
            ),
            "avg_response_time_ms": round(
                self.total_response_time / self.total_messages * 1000 
                if self.total_messages > 0 else 0, 2
            ),
            "avg_intent_confidence": round(
                sum(s.avg_intent_confidence for s in self.sessions.values()) / len(self.sessions)
                if self.sessions else 0, 2
            ),
            
            # 滑动窗口指标（最近100条）
            "recent_correction_rate": round(
                recent_corrections / len(recent_messages) * 100 
                if recent_messages else 0, 2
            ),
            "recent_tool_failure_rate": round(
                recent_tool_failures / len(recent_tools) * 100 
                if recent_tools else 0, 2
            ),
            
            # 会话活跃情况
            "active_sessions": len([s for s in self.sessions.values() 
                                   if time.time() - s.start_time < 3600]),
        }
    
    def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计"""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "duration": round(time.time() - session.start_time, 2),
            "message_count": session.message_count,
            "tool_failure_rate": round(session.tool_failure_rate, 2),
            "correction_rate": round(session.correction_rate, 2),
            "avg_response_time_ms": round(session.avg_response_time * 1000, 2),
            "avg_intent_confidence": round(session.avg_intent_confidence, 2),
        }
    
    def get_time_series(self) -> List[Dict]:
        """获取时间序列数据（用于折线图）"""
        return self.time_series
    
    def _save_time_series(self):
        """保存时间序列数据"""
        stats = self.get_global_stats()
        stats["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_series.append(stats)
        
        # 只保留最近100个点
        if len(self.time_series) > 100:
            self.time_series = self.time_series[-100:]
        
        self.last_save_time = time.time()
    
    def export_report(self) -> str:
        """导出监控报告"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "global_stats": self.get_global_stats(),
            "time_series": self.time_series[-20:],  # 最近20个点
            "top_sessions": sorted(
                [asdict(s) for s in self.sessions.values()],
                key=lambda x: x["message_count"],
                reverse=True
            )[:10]
        }
        
        # 保存到文件
        report_path = os.path.join("data", "monitor_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report_path
    
    def health_check(self) -> Dict:
        """健康检查"""
        stats = self.get_global_stats()
        status = "healthy"
        issues = []
        
        # 核心指标阈值
        if stats["tool_failure_rate"] > 10:
            status = "warning"
            issues.append(f"工具失败率过高: {stats['tool_failure_rate']}%")
        
        if stats["user_correction_rate"] > 15:
            status = "warning"
            issues.append(f"用户纠偏率过高: {stats['user_correction_rate']}%")
        
        if stats["avg_response_time_ms"] > 2000:
            status = "warning"
            issues.append(f"平均响应时间过长: {stats['avg_response_time_ms']}ms")
        
        if stats["avg_intent_confidence"] < 0.7:
            status = "warning"
            issues.append(f"意图置信度偏低: {stats['avg_intent_confidence']}")
        
        return {
            "status": status,
            "issues": issues,
            "metrics": stats
        }


# 创建全局监控实例
monitor_dashboard = MonitorDashboard()


def test_monitor_dashboard():
    """测试监控看板"""
    monitor = MonitorDashboard()
    
    print("\n" + "=" * 60)
    print("监控看板测试")
    print("=" * 60)
    
    # 模拟会话
    session_id = "test_session"
    monitor.start_session(session_id)
    
    # 模拟10轮对话
    messages = [
        ("太甜了，喝不下去", 0.85, 0.05),
        ("不对，我说的是冰块太多", 0.75, 0.08),  # 纠偏！
        ("订单12345什么时候能送到？", 0.9, 0.03),
        ("附近有门店吗？", 0.8, 0.04),
        ("你确定有外卖？", 0.7, 0.06),  # 纠偏！
        ("可以退款吗？", 0.85, 0.05),
        ("门店营业时间？", 0.88, 0.04),
        ("甜度有几种选择？", 0.82, 0.05),
        ("有外卖吗？", 0.78, 0.04),
        ("今天有什么优惠？", 0.8, 0.06),
    ]
    
    for msg, confidence, response_time in messages:
        is_correction = monitor.detect_correction(session_id, msg)
        monitor.record_message(session_id, confidence, response_time, is_correction)
        
        # 模拟工具调用（部分失败）
        tool_success = confidence > 0.75
        monitor.record_tool_call(session_id, "query_order", tool_success, 0.1)
    
    # 输出统计
    stats = monitor.get_global_stats()
    print("\n全局统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 会话统计
    session_stats = monitor.get_session_stats(session_id)
    print(f"\n会话统计:")
    for key, value in session_stats.items():
        print(f"  {key}: {value}")
    
    # 健康检查
    health = monitor.health_check()
    print(f"\n健康状态: {health['status']}")
    if health["issues"]:
        print(f"问题: {', '.join(health['issues'])}")
    
    # 导出报告
    report_path = monitor.export_report()
    print(f"\n报告已导出: {report_path}")

if __name__ == "__main__":
    test_monitor_dashboard()
