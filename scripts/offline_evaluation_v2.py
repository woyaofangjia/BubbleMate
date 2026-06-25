"""
BubbleMate - 离线评测脚本V2
使用增强版组件进行评测
"""

import sys
import os
import json
import time
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
from backend.agent.react_agent_v2 import ReActAgentV2, create_tools_v2
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2

class OfflineEvaluatorV2:
    """离线评测器V2"""
    
    def __init__(self):
        self.intent_recognizer = IntentRecognizerV2("data")
        self.tools = create_tools_v2()
        self.memory_manager = MemoryManagerV2(window_size=5, use_redis=False)
        self.agent = ReActAgentV2(self.tools, self.intent_recognizer, self.memory_manager)
        
        register_all_tools_v2()
        
        self.metrics = {
            "intent_accuracy": 0.0,
            "tool_success_rate": 0.0,
            "response_relevance": 0.0,
            "response_correctness": 0.0,
            "avg_response_time": 0.0,
        }
        
        self.results: List[Dict] = []
    
    def evaluate(self):
        """执行完整评测"""
        print("\n" + "=" * 70)
        print("BubbleMate 离线评测 V2")
        print("=" * 70)
        
        print("\n1. 意图识别评测")
        self._evaluate_intent_recognition()
        
        print("\n2. 工具调用评测")
        self._evaluate_tool_calling()
        
        print("\n3. 完整对话评测")
        self._evaluate_conversation()
        
        self._generate_report()
    
    def _evaluate_intent_recognition(self):
        """评测意图识别"""
        test_cases = [
            ("太甜了，喝不下去", "complaint_taste"),
            ("冰块太多，饮料都没了", "complaint_quantity"),
            ("你们有什么招牌推荐？", "query_recommend"),
            ("订单12345什么时候能送到？", "query_order"),
            ("附近有门店吗？", "query_location"),
            ("可以退款吗？", "query_refund"),
            ("门店营业时间？", "query_opentime"),
            ("配送超时一小时", "complaint_delivery"),
            ("服务太差了", "complaint_service"),
            ("这么贵还这么难喝", "complaint_taste"),
            ("珍珠奶茶多少钱？", "query_price"),
            ("可以做热的吗？", "query_temp"),
            ("甜度有几种选择？", "query_sugar"),
            ("有外卖吗？", "query_delivery"),
            ("今天有什么优惠？", "query_promo"),
            ("上次的投诉处理好了吗？", "query_complaint_status"),
            ("我要下单", "place_order"),
            ("会员卡怎么办？", "query_member"),
            ("能开发票吗？", "query_invoice"),
            ("不好喝，要求退款", "complaint_taste"),
        ]
        
        correct = 0
        total = len(test_cases)
        
        for text, expected in test_cases:
            intent = self.intent_recognizer.recognize(text)
            is_correct = intent.name == expected
            
            self.results.append({
                "type": "intent",
                "input": text,
                "expected": expected,
                "actual": intent.name,
                "confidence": intent.confidence,
                "correct": is_correct
            })
            
            if is_correct:
                correct += 1
        
        self.metrics["intent_accuracy"] = correct / total * 100
        print(f"  意图识别准确率: {self.metrics['intent_accuracy']:.1f}% ({correct}/{total})")
    
    def _evaluate_tool_calling(self):
        """评测工具调用"""
        test_cases = [
            {"tool": "query_order_status", "args": {"order_id": "12345"}, "expected_type": "success"},
            {"tool": "query_order_status", "args": {}, "expected_type": "ask_user"},
            {"tool": "query_order_status", "args": {"order_id": "99999"}, "expected_type": "business_error"},
            {"tool": "check_inventory", "args": {"store_id": "武汉大学"}, "expected_type": "success"},
            {"tool": "check_inventory", "args": {}, "expected_type": "ask_user"},
            {"tool": "query_shop_info", "args": {"location": "武大"}, "expected_type": "success"},
            {"tool": "query_shop_info", "args": {"location": "火星"}, "expected_type": "business_error"},
            {"tool": "query_menu_info", "args": {"category": "芝士系列"}, "expected_type": "success"},
            {"tool": "handle_complaint", "args": {}, "expected_type": "ask_user"},
            {"tool": "handle_complaint", "args": {"complaint_type": "taste"}, "expected_type": "success"},
        ]
        
        correct = 0
        total = len(test_cases)
        
        for test in test_cases:
            result = tool_registry_v2.call(test["tool"], test["args"])
            is_correct = result.get("type") == test["expected_type"]
            
            self.results.append({
                "type": "tool",
                "tool": test["tool"],
                "expected_type": test["expected_type"],
                "actual_type": result.get("type"),
                "correct": is_correct
            })
            
            if is_correct:
                correct += 1
        
        self.metrics["tool_success_rate"] = correct / total * 100
        print(f"  工具调用成功率: {self.metrics['tool_success_rate']:.1f}% ({correct}/{total})")
    
    def _evaluate_conversation(self):
        """评测完整对话质量"""
        test_cases = [
            {
                "input": "你们有什么推荐？",
                "expected_intent": "query_recommend",
                "relevance_check": ["推荐", "招牌", "菜单"],
                "correctness_check": ["饮品", "价格"]
            },
            {
                "input": "太甜了，喝不下去",
                "expected_intent": "complaint_taste",
                "relevance_check": ["抱歉", "糖", "投诉"],
                "correctness_check": ["退款", "重做", "补偿"]
            },
            {
                "input": "订单12345什么时候能送到？",
                "expected_intent": "query_order",
                "relevance_check": ["订单", "配送", "时间"],
                "correctness_check": ["配送中", "15分钟"]
            },
            {
                "input": "附近有门店吗？",
                "expected_intent": "query_location",
                "relevance_check": ["门店", "地址", "附近"],
                "correctness_check": ["武汉大学", "银泰"]
            },
            {
                "input": "甜度有几种选择？",
                "expected_intent": "query_sugar",
                "relevance_check": ["糖度", "甜度", "选择"],
                "correctness_check": ["五分糖", "无糖"]
            },
            {
                "input": "有外卖吗？",
                "expected_intent": "query_delivery",
                "relevance_check": ["外卖", "配送"],
                "correctness_check": ["免配送费", "美团"]
            },
            {
                "input": "今天有什么优惠？",
                "expected_intent": "query_promo",
                "relevance_check": ["优惠", "活动"],
                "correctness_check": ["第二杯半价", "优惠券"]
            },
            {
                "input": "会员卡怎么办？",
                "expected_intent": "query_member",
                "relevance_check": ["会员", "办理"],
                "correctness_check": ["免费", "首单"]
            },
        ]
        
        total_relevance = 0
        total_correctness = 0
        total_time = 0
        
        session_id = "eval_session"
        self.memory_manager.clear_session(session_id)
        
        for test in test_cases:
            start_time = time.time()
            response = self.agent.process(test["input"], session_id)
            end_time = time.time()
            
            response_time = end_time - start_time
            total_time += response_time
            
            if "【回复】" in response:
                reply = response.split("【回复】")[-1].strip()
            else:
                reply = response
            
            relevance_score = sum(1 for kw in test["relevance_check"] if kw in reply) / len(test["relevance_check"])
            correctness_score = sum(1 for kw in test["correctness_check"] if kw in reply) / len(test["correctness_check"])
            
            total_relevance += relevance_score
            total_correctness += correctness_score
            
            status = "✓" if relevance_score >= 0.5 else "✗"
            print(f"  {status} {test['input'][:20]}... ({response_time:.2f}s)")
        
        total = len(test_cases)
        self.metrics["response_relevance"] = total_relevance / total * 100
        self.metrics["response_correctness"] = total_correctness / total * 100
        self.metrics["avg_response_time"] = total_time / total
        
        print(f"\n  回复相关度: {self.metrics['response_relevance']:.1f}%")
        print(f"  回复正确率: {self.metrics['response_correctness']:.1f}%")
        print(f"  平均响应时间: {self.metrics['avg_response_time']:.2f}s")
    
    def _generate_report(self):
        """生成评测报告"""
        print("\n" + "=" * 70)
        print("评测报告 V2")
        print("=" * 70)
        
        print("\n【综合指标】")
        print(f"  意图识别准确率: {self.metrics['intent_accuracy']:.1f}%")
        print(f"  工具调用成功率: {self.metrics['tool_success_rate']:.1f}%")
        print(f"  回复相关度: {self.metrics['response_relevance']:.1f}%")
        print(f"  回复正确率: {self.metrics['response_correctness']:.1f}%")
        print(f"  平均响应时间: {self.metrics['avg_response_time']:.2f}s")
        
        weighted_score = (
            self.metrics["intent_accuracy"] * 0.3 +
            self.metrics["tool_success_rate"] * 0.25 +
            self.metrics["response_relevance"] * 0.25 +
            self.metrics["response_correctness"] * 0.2
        )
        
        print(f"\n【综合得分】")
        print(f"  总分: {weighted_score:.1f}/100")
        
        if weighted_score >= 90:
            grade = "S"
            comment = "优秀！所有指标表现良好"
        elif weighted_score >= 80:
            grade = "A"
            comment = "良好！部分指标可进一步优化"
        elif weighted_score >= 70:
            grade = "B"
            comment = "合格！建议关注回复质量"
        else:
            grade = "C"
            comment = "需要改进！建议优化回复模板"
        
        print(f"  评级: {grade}")
        print(f"  评语: {comment}")
        
        report_path = os.path.join("data", "evaluation_report_v2.json")
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": self.metrics,
            "overall_score": weighted_score,
            "grade": grade,
            "comment": comment,
            "results": self.results
        }
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    evaluator = OfflineEvaluatorV2()
    evaluator.evaluate()
