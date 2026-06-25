"""
BubbleMate - 离线评测脚本
包含20道标准问答测试题，评估意图识别准确率、工具调用成功率、回复质量
"""

import sys
import os
import json
import time
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer import IntentRecognizer
from backend.agent.react_agent import ReActAgent, create_tools
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2

class OfflineEvaluator:
    """离线评测器"""
    
    def __init__(self):
        # 初始化组件
        self.intent_recognizer = IntentRecognizer("data")
        self.tools = create_tools()
        self.memory_manager = MemoryManagerV2(window_size=5, use_redis=False)
        self.agent = ReActAgent(self.tools, self.intent_recognizer, self.memory_manager)
        
        register_all_tools_v2()
        
        # 评测指标
        self.metrics = {
            "intent_accuracy": 0.0,
            "tool_success_rate": 0.0,
            "response_relevance": 0.0,
            "response_correctness": 0.0,
            "avg_response_time": 0.0,
            "memory_usage": 0.0,
        }
        
        # 测试结果
        self.results: List[Dict] = []
    
    def evaluate(self):
        """执行完整评测"""
        print("\n" + "=" * 70)
        print("BubbleMate 离线评测")
        print("=" * 70)
        
        # 1. 意图识别评测
        print("\n1. 意图识别评测")
        self._evaluate_intent_recognition()
        
        # 2. 工具调用评测
        print("\n2. 工具调用评测")
        self._evaluate_tool_calling()
        
        # 3. 完整对话评测
        print("\n3. 完整对话评测")
        self._evaluate_conversation()
        
        # 4. 输出报告
        self._generate_report()
    
    def _evaluate_intent_recognition(self):
        """评测意图识别"""
        test_cases = [
            ("太甜了，喝不下去", "complaint_taste", "口感投诉"),
            ("冰块太多，饮料都没了", "complaint_quantity", "份量投诉"),
            ("你们有什么招牌推荐？", "query_recommend", "推荐查询"),
            ("订单12345什么时候能送到？", "query_order", "订单查询"),
            ("附近有门店吗？", "query_location", "门店查询"),
            ("可以退款吗？", "query_refund", "退款查询"),
            ("门店营业时间？", "query_opentime", "营业时间查询"),
            ("配送超时一小时", "complaint_delivery", "配送投诉"),
            ("服务太差了", "complaint_service", "服务投诉"),
            ("这么贵还这么难喝", "complaint_taste_price", "口感投诉"),
            ("珍珠奶茶多少钱？", "query_price", "价格查询"),
            ("可以做热的吗？", "query_temp", "温度查询"),
            ("甜度有几种选择？", "query_sugar", "甜度查询"),
            ("有外卖吗？", "query_delivery", "配送查询"),
            ("今天有什么优惠？", "query_promo", "优惠查询"),
            ("上次的投诉处理好了吗？", "query_complaint_status", "投诉状态"),
            ("我要下单", "place_order", "下单"),
            ("会员卡怎么办？", "query_member", "会员查询"),
            ("能开发票吗？", "query_invoice", "发票查询"),
            ("不好喝，要求退款", "complaint_taste_refund", "口感投诉"),
        ]
        
        correct = 0
        total = len(test_cases)
        
        for text, expected_name, expected_category in test_cases:
            intent = self.intent_recognizer.recognize(text)
            
            # 意图名称匹配或类别匹配视为正确
            is_correct = (intent.name == expected_name or 
                         intent.category == expected_category)
            
            self.results.append({
                "type": "intent",
                "input": text,
                "expected": expected_name,
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
            {
                "name": "订单查询-参数齐全",
                "tool": "query_order_status",
                "args": {"order_id": "12345"},
                "expected_type": "success",
                "expected_keys": ["status", "drink", "eta"]
            },
            {
                "name": "订单查询-参数缺失",
                "tool": "query_order_status",
                "args": {},
                "expected_type": "ask_user",
                "expected_keys": ["missing_params"]
            },
            {
                "name": "订单查询-订单不存在",
                "tool": "query_order_status",
                "args": {"order_id": "99999"},
                "expected_type": "business_error",
                "expected_keys": ["error"]
            },
            {
                "name": "库存查询-正常",
                "tool": "check_inventory",
                "args": {"store_id": "武汉大学"},
                "expected_type": "success",
                "expected_keys": ["store", "inventory"]
            },
            {
                "name": "库存查询-参数缺失",
                "tool": "check_inventory",
                "args": {},
                "expected_type": "ask_user",
                "expected_keys": ["missing_params"]
            },
            {
                "name": "门店查询-正常",
                "tool": "query_shop_info",
                "args": {"location": "武大"},
                "expected_type": "success",
                "expected_keys": ["shops", "count"]
            },
            {
                "name": "门店查询-未找到",
                "tool": "query_shop_info",
                "args": {"location": "火星"},
                "expected_type": "business_error",
                "expected_keys": ["error"]
            },
            {
                "name": "菜单查询-分类",
                "tool": "query_menu_info",
                "args": {"category": "芝士系列"},
                "expected_type": "success",
                "expected_keys": ["category", "items"]
            },
            {
                "name": "投诉处理-参数缺失",
                "tool": "handle_complaint",
                "args": {},
                "expected_type": "ask_user",
                "expected_keys": ["missing_params"]
            },
            {
                "name": "投诉处理-正常",
                "tool": "handle_complaint",
                "args": {"complaint_type": "taste"},
                "expected_type": "success",
                "expected_keys": ["status", "response"]
            },
        ]
        
        correct = 0
        total = len(test_cases)
        
        for test in test_cases:
            result = tool_registry_v2.call(test["tool"], test["args"])
            
            is_correct = (result.get("type") == test["expected_type"])
            
            # 检查结果是否包含预期关键字段
            if is_correct and result.get("result"):
                result_data = result["result"]
                for key in test["expected_keys"]:
                    if key not in result_data:
                        is_correct = False
                        break
            
            self.results.append({
                "type": "tool",
                "tool": test["tool"],
                "name": test["name"],
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
                "id": "conv_001",
                "input": "你们有什么推荐？",
                "expected_intent": "query_recommend",
                "relevance_check": ["推荐", "招牌", "菜单"],
                "correctness_check": ["饮品", "价格", "描述"]
            },
            {
                "id": "conv_002",
                "input": "太甜了，喝不下去",
                "expected_intent": "complaint_taste",
                "relevance_check": ["抱歉", "糖", "投诉"],
                "correctness_check": ["退款", "补偿", "重做"]
            },
            {
                "id": "conv_003",
                "input": "订单12345什么时候能送到？",
                "expected_intent": "query_order",
                "relevance_check": ["订单", "配送", "时间"],
                "correctness_check": ["配送中", "ETA", "15分钟"]
            },
            {
                "id": "conv_004",
                "input": "附近有门店吗？",
                "expected_intent": "query_location",
                "relevance_check": ["门店", "地址", "附近"],
                "correctness_check": ["武汉大学", "街道口", "银泰"]
            },
            {
                "id": "conv_005",
                "input": "太甜了，能重做吗？",
                "expected_intent": "complaint_taste",
                "relevance_check": ["抱歉", "重做", "糖"],
                "correctness_check": ["退款", "重做", "补偿"]
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
            
            # 提取回复内容
            if "【回复】" in response:
                reply = response.split("【回复】")[-1].strip()
            else:
                reply = response
            
            # 检查相关性（是否包含预期关键词）
            relevance_score = sum(1 for kw in test["relevance_check"] if kw in reply) / len(test["relevance_check"])
            
            # 检查正确性（是否包含正确答案）
            correctness_score = sum(1 for kw in test["correctness_check"] if kw in reply) / len(test["correctness_check"])
            
            total_relevance += relevance_score
            total_correctness += correctness_score
            
            self.results.append({
                "type": "conversation",
                "id": test["id"],
                "input": test["input"],
                "response_time": response_time,
                "relevance_score": relevance_score,
                "correctness_score": correctness_score,
                "reply": reply[:100]
            })
            
            status = "✓" if relevance_score >= 0.5 else "✗"
            print(f"  {status} [{test['id']}] {test['input'][:20]}... ({response_time:.2f}s)")
        
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
        print("评测报告")
        print("=" * 70)
        
        print("\n【综合指标】")
        print(f"  意图识别准确率: {self.metrics['intent_accuracy']:.1f}%")
        print(f"  工具调用成功率: {self.metrics['tool_success_rate']:.1f}%")
        print(f"  回复相关度: {self.metrics['response_relevance']:.1f}%")
        print(f"  回复正确率: {self.metrics['response_correctness']:.1f}%")
        print(f"  平均响应时间: {self.metrics['avg_response_time']:.2f}s")
        
        # 计算综合得分
        weighted_score = (
            self.metrics["intent_accuracy"] * 0.3 +
            self.metrics["tool_success_rate"] * 0.25 +
            self.metrics["response_relevance"] * 0.25 +
            self.metrics["response_correctness"] * 0.2
        )
        
        print(f"\n【综合得分】")
        print(f"  总分: {weighted_score:.1f}/100")
        
        # 评级
        if weighted_score >= 90:
            grade = "S"
            comment = "优秀！所有指标表现良好"
        elif weighted_score >= 80:
            grade = "A"
            comment = "良好！部分指标可进一步优化"
        elif weighted_score >= 70:
            grade = "B"
            comment = "合格！建议关注意图识别准确率"
        else:
            grade = "C"
            comment = "需要改进！建议增加训练数据"
        
        print(f"  评级: {grade}")
        print(f"  评语: {comment}")
        
        # 保存报告
        report_path = os.path.join("data", "evaluation_report.json")
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
    evaluator = OfflineEvaluator()
    evaluator.evaluate()
