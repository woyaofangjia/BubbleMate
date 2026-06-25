"""
BubbleMate - 真实实验运行器
基于真实Agent运行，收集实验数据
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
from backend.agent.react_agent_v2 import ReActAgentV2, create_tools_v2
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2

class RealExperimentRunner:
    """真实实验运行器"""
    
    def __init__(self):
        self.intent_recognizer = IntentRecognizerV2("data")
        self.tools = create_tools_v2()
        register_all_tools_v2()
    
    def experiment_1_intent_accuracy(self):
        """实验1：意图识别准确率（真实数据）"""
        print("\n" + "=" * 60)
        print("实验1：意图识别准确率")
        print("=" * 60)
        
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
        results = []
        
        for text, expected in test_cases:
            intent = self.intent_recognizer.recognize(text)
            is_correct = intent.name == expected
            if is_correct:
                correct += 1
            
            results.append({
                "input": text,
                "expected": expected,
                "actual": intent.name,
                "confidence": round(intent.confidence, 2),
                "correct": is_correct
            })
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [{intent.name}] {text[:25]}... (置信度: {intent.confidence:.2f})")
        
        accuracy = correct / len(test_cases) * 100
        print(f"\n准确率: {accuracy:.1f}% ({correct}/{len(test_cases)})")
        
        return {
            "experiment": "intent_accuracy",
            "total": len(test_cases),
            "correct": correct,
            "accuracy": accuracy,
            "details": results
        }
    
    def experiment_2_tool_fallback(self):
        """实验2：工具调用异常处理（真实数据）"""
        print("\n" + "=" * 60)
        print("实验2：工具调用异常处理")
        print("=" * 60)
        
        test_cases = [
            {"name": "参数缺失-订单查询", "tool": "query_order_status", "args": {}, "expected": "ask_user"},
            {"name": "正常调用-订单查询", "tool": "query_order_status", "args": {"order_id": "12345"}, "expected": "success"},
            {"name": "订单不存在", "tool": "query_order_status", "args": {"order_id": "99999"}, "expected": "business_error"},
            {"name": "参数缺失-库存查询", "tool": "check_inventory", "args": {}, "expected": "ask_user"},
            {"name": "正常调用-库存查询", "tool": "check_inventory", "args": {"store_id": "武汉大学"}, "expected": "success"},
            {"name": "未找到门店", "tool": "query_shop_info", "args": {"location": "火星"}, "expected": "business_error"},
            {"name": "正常门店查询", "tool": "query_shop_info", "args": {"location": "武大"}, "expected": "success"},
            {"name": "参数缺失-投诉", "tool": "handle_complaint", "args": {}, "expected": "ask_user"},
            {"name": "正常投诉", "tool": "handle_complaint", "args": {"complaint_type": "taste"}, "expected": "success"},
        ]
        
        correct = 0
        results = []
        
        for test in test_cases:
            result = tool_registry_v2.call(test["tool"], test["args"])
            actual_type = result.get("type")
            is_correct = actual_type == test["expected"]
            if is_correct:
                correct += 1
            
            results.append({
                "name": test["name"],
                "tool": test["tool"],
                "expected": test["expected"],
                "actual": actual_type,
                "response": result.get("response", "")[:50],
                "correct": is_correct
            })
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [{actual_type}] {test['name']}")
            if result.get("response"):
                print(f"   回复: {result['response'][:60]}...")
        
        success_rate = correct / len(test_cases) * 100
        print(f"\n工具调用成功率: {success_rate:.1f}% ({correct}/{len(test_cases)})")
        
        return {
            "experiment": "tool_fallback",
            "total": len(test_cases),
            "correct": correct,
            "success_rate": success_rate,
            "details": results
        }
    
    def experiment_3_memory_window(self):
        """实验3：记忆窗口对比（真实数据）"""
        print("\n" + "=" * 60)
        print("实验3：记忆窗口对比测试")
        print("=" * 60)
        
        test_conversation = [
            ("给我推荐一款好喝的", "推荐芝芝莓莓、杨枝甘露..."),
            ("杨枝甘露多少钱？", "18元..."),
            ("太甜了，下次我要少糖的", "已记录您偏好少糖..."),
            ("附近有门店吗？", "武汉大学梅园店..."),
            ("那家有外卖吗？", "支持外卖配送..."),
            ("算了，换刚才那杯", "测试关键问题：能否记住'那杯'是杨枝甘露？"),
        ]
        
        results = []
        
        for window_size in [3, 5, 10]:
            print(f"\n--- 窗口大小 = {window_size} ---")
            memory = MemoryManagerV2(window_size=window_size, use_redis=False)
            session_id = f"test_window_{window_size}"
            
            start_time = time.time()
            
            for user_msg, agent_msg in test_conversation:
                memory.save_message(session_id, user_msg, agent_msg)
            
            end_time = time.time()
            
            context = memory.get_context(session_id)
            stats = memory.get_session_stats(session_id)
            
            # 检查是否记住"杨枝甘露"和"少糖"
            remembers_drink = "杨枝甘露" in context
            remembers_sugar = "少糖" in context or "糖" in context
            
            print(f"  消息数: {stats['message_count']}")
            print(f"  有摘要: {stats['has_summary']}")
            print(f"  记住饮品: {'✓' if remembers_drink else '✗'}")
            print(f"  记住偏好: {'✓' if remembers_sugar else '✗'}")
            print(f"  响应时间: {(end_time - start_time)*1000:.1f}ms")
            
            results.append({
                "window_size": window_size,
                "message_count": stats['message_count'],
                "has_summary": stats['has_summary'],
                "remembers_drink": remembers_drink,
                "remembers_sugar": remembers_sugar,
                "response_time_ms": round((end_time - start_time) * 1000, 1),
                "context_length": len(context)
            })
        
        return {
            "experiment": "memory_window",
            "results": results
        }
    
    def experiment_4_end_to_end(self):
        """实验4：端到端对话质量（真实数据）"""
        print("\n" + "=" * 60)
        print("实验4：端到端对话质量")
        print("=" * 60)
        
        memory = MemoryManagerV2(window_size=5, use_redis=False)
        agent = ReActAgentV2(self.tools, self.intent_recognizer, memory)
        
        test_cases = [
            {
                "input": "你们有什么推荐？",
                "check_keywords": ["推荐", "芝芝", "杨枝"],
                "expected_intent": "query_recommend"
            },
            {
                "input": "太甜了，喝不下去",
                "check_keywords": ["抱歉", "糖", "退款"],
                "expected_intent": "complaint_taste"
            },
            {
                "input": "订单12345什么时候能送到？",
                "check_keywords": ["配送", "15分钟"],
                "expected_intent": "query_order"
            },
            {
                "input": "附近有门店吗？",
                "check_keywords": ["门店", "地址"],
                "expected_intent": "query_location"
            },
            {
                "input": "甜度有几种选择？",
                "check_keywords": ["糖", "五分糖"],
                "expected_intent": "query_sugar"
            },
        ]
        
        session_id = "e2e_test"
        results = []
        total_time = 0
        
        for test in test_cases:
            start_time = time.time()
            response = agent.process(test["input"], session_id)
            end_time = time.time()
            
            response_time = end_time - start_time
            total_time += response_time
            
            # 提取回复内容
            if "【回复】" in response:
                reply = response.split("【回复】")[-1].strip()
            else:
                reply = response
            
            # 检查关键词
            matched_keywords = [kw for kw in test["check_keywords"] if kw in reply]
            relevance = len(matched_keywords) / len(test["check_keywords"])
            
            # 检查意图
            intent = self.intent_recognizer.recognize(test["input"])
            intent_correct = intent.name == test["expected_intent"]
            
            results.append({
                "input": test["input"],
                "intent": intent.name,
                "intent_correct": intent_correct,
                "relevance": round(relevance * 100, 1),
                "response_time_ms": round(response_time * 1000, 1),
                "reply_preview": reply[:60]
            })
            
            status = "✓" if relevance >= 0.5 and intent_correct else "✗"
            print(f"{status} [{intent.name}] {test['input'][:20]}... "
                  f"(相关度: {relevance*100:.0f}%, 耗时: {response_time*1000:.1f}ms)")
        
        avg_relevance = sum(r["relevance"] for r in results) / len(results)
        intent_accuracy = sum(1 for r in results if r["intent_correct"]) / len(results) * 100
        avg_time = total_time / len(results) * 1000
        
        print(f"\n平均相关度: {avg_relevance:.1f}%")
        print(f"意图准确率: {intent_accuracy:.1f}%")
        print(f"平均响应时间: {avg_time:.1f}ms")
        
        return {
            "experiment": "end_to_end",
            "avg_relevance": avg_relevance,
            "intent_accuracy": intent_accuracy,
            "avg_response_time_ms": avg_time,
            "details": results
        }
    
    def run_all(self):
        """运行所有实验"""
        print("\n" + "=" * 70)
        print("BubbleMate 真实实验运行器")
        print("=" * 70)
        
        results = {}
        
        results["intent_accuracy"] = self.experiment_1_intent_accuracy()
        results["tool_fallback"] = self.experiment_2_tool_fallback()
        results["memory_window"] = self.experiment_3_memory_window()
        results["end_to_end"] = self.experiment_4_end_to_end()
        
        # 保存结果
        import json
        result_path = os.path.join("data", "experiment_results.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 70)
        print("实验完成！结果已保存到: data/experiment_results.json")
        print("=" * 70)
        
        return results


if __name__ == "__main__":
    runner = RealExperimentRunner()
    runner.run_all()
