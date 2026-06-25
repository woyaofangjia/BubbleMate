"""
BubbleMate - 增强版实验运行器
包含Bad Case分析和对比基线实验
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
from backend.agent.react_agent_v2 import ReActAgentV2, create_tools_v2
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2


class EnhancedExperimentRunner:
    """增强版实验运行器"""
    
    def __init__(self):
        self.intent_recognizer = IntentRecognizerV2("data")
        self.tools = create_tools_v2()
        register_all_tools_v2()
    
    # ============ 实验1: 意图识别（含Bad Case分析） ============
    
    def experiment_1_intent_accuracy(self):
        """实验1：意图识别准确率 + Bad Case分析"""
        print("\n" + "=" * 70)
        print("实验1：意图识别准确率")
        print("=" * 70)
        
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
        
        results = []
        bad_cases = []
        
        for text, expected in test_cases:
            intent = self.intent_recognizer.recognize(text)
            is_correct = intent.name == expected
            
            results.append({
                "input": text,
                "expected": expected,
                "actual": intent.name,
                "confidence": round(intent.confidence, 2),
                "correct": is_correct
            })
            
            if not is_correct:
                bad_cases.append({
                    "input": text,
                    "expected": expected,
                    "actual": intent.name,
                    "confidence": round(intent.confidence, 2)
                })
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [{intent.name}] {text[:25]}...")
        
        accuracy = sum(1 for r in results if r["correct"]) / len(results) * 100
        
        print(f"\n准确率: {accuracy:.1f}% ({sum(1 for r in results if r['correct'])}/{len(results)})")
        
        # Bad Case 分析
        self._analyze_bad_cases(bad_cases)
        
        return {
            "experiment": "intent_accuracy",
            "total": len(results),
            "correct": sum(1 for r in results if r["correct"]),
            "accuracy": accuracy,
            "bad_cases": bad_cases,
            "details": results
        }
    
    def _analyze_bad_cases(self, bad_cases):
        """Bad Case根因分析"""
        if not bad_cases:
            print("\n✅ 无Bad Case！")
            return
        
        print("\n" + "-" * 70)
        print("❌ Bad Case 根因分析")
        print("-" * 70)
        
        root_causes = {
            "关键词重叠": [],
            "意图边界模糊": [],
            "训练数据不足": [],
        }
        
        for case in bad_cases:
            root_cause = self._identify_root_cause(case)
            root_causes[root_cause].append(case)
            
            print(f"\n❌ 输入: {case['input']}")
            print(f"   预测: {case['actual']} | 期望: {case['expected']}")
            print(f"   置信度: {case['confidence']}")
            print(f"   🔍 原因: {root_cause}")
            
            if case["input"] == "珍珠奶茶多少钱？":
                print(f"   💡 改进方向: 增加'价格'类关键词('多少钱','价格','贵')的优先级")
            elif case["input"] == "今天有什么优惠？":
                print(f"   💡 改进方向: 增加'优惠'类关键词('优惠','活动','折扣','券')")
        
        print("\n" + "-" * 70)
        print("📊 Bad Case 统计")
        print("-" * 70)
        for cause, cases in root_causes.items():
            if cases:
                print(f"  {cause}: {len(cases)}个")
    
    def _identify_root_cause(self, case):
        """识别根因"""
        inp = case["input"]
        expected = case["expected"]
        actual = case["actual"]
        
        # 关键词重叠：输入包含多个意图的关键词
        if ("甜" in inp or "好喝" in inp or "难喝" in inp) and actual.startswith("complaint_"):
            return "关键词重叠"
        
        # 意图边界模糊：价格查询和菜单查询容易混淆
        if "优惠" in inp and actual == "query_menu":
            return "意图边界模糊"
        
        # 训练数据不足
        return "训练数据不足"
    
    # ============ 实验2: 对比基线 ============
    
    def experiment_2_baseline_comparison(self):
        """实验2：与Baseline对比"""
        print("\n" + "=" * 70)
        print("实验2：对比基线（简单关键词 vs 完整Agent）")
        print("=" * 70)
        
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
        ]
        
        # Baseline: 简单关键词匹配
        print("\n--- Baseline: 简单关键词匹配 ---")
        baseline_correct = 0
        baseline_results = []
        
        for text, expected in test_cases:
            predicted = self._baseline_predict(text)
            is_correct = predicted == expected
            if is_correct:
                baseline_correct += 1
            
            baseline_results.append({
                "input": text,
                "expected": expected,
                "baseline_pred": predicted,
                "correct": is_correct
            })
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [Baseline: {predicted}] {text[:20]}...")
        
        baseline_acc = baseline_correct / len(test_cases) * 100
        print(f"\nBaseline准确率: {baseline_acc:.1f}% ({baseline_correct}/{len(test_cases)})")
        
        # 完整Agent: 规则+关键词+训练数据
        print("\n--- 完整Agent: 规则+关键词+训练数据 ---")
        agent_correct = 0
        agent_results = []
        
        for text, expected in test_cases:
            intent = self.intent_recognizer.recognize(text)
            is_correct = intent.name == expected
            if is_correct:
                agent_correct += 1
            
            agent_results.append({
                "input": text,
                "expected": expected,
                "agent_pred": intent.name,
                "confidence": intent.confidence,
                "correct": is_correct
            })
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [Agent: {intent.name}] {text[:20]}...")
        
        agent_acc = agent_correct / len(test_cases) * 100
        print(f"\n完整Agent准确率: {agent_acc:.1f}% ({agent_correct}/{len(test_cases)})")
        
        # 对比结果
        print("\n" + "-" * 70)
        print("📊 对比结果")
        print("-" * 70)
        print(f"  Baseline准确率:    {baseline_acc:.1f}%")
        print(f"  完整Agent准确率:   {agent_acc:.1f}%")
        print(f"  提升幅度:          +{agent_acc - baseline_acc:.1f}%")
        
        # 详细对比表
        print("\n详细对比:")
        print(f"{'输入':<25} {'Baseline':<18} {'Agent':<18} {'提升'}")
        print("-" * 70)
        for i, (text, expected) in enumerate(test_cases):
            base_pred = baseline_results[i]["baseline_pred"]
            agent_pred = agent_results[i]["agent_pred"]
            base_ok = "✓" if baseline_results[i]["correct"] else "✗"
            agent_ok = "✓" if agent_results[i]["correct"] else "✗"
            
            # 计算提升
            if not baseline_results[i]["correct"] and agent_results[i]["correct"]:
                improvement = "✓ 修复"
            elif baseline_results[i]["correct"] and not agent_results[i]["correct"]:
                improvement = "✗ 退化"
            else:
                improvement = "- 持平"
            
            print(f"{text[:22]:<25} {base_pred:<15} {base_ok:<3} {agent_pred:<15} {agent_ok:<3} {improvement}")
        
        return {
            "baseline_accuracy": baseline_acc,
            "agent_accuracy": agent_acc,
            "improvement": agent_acc - baseline_acc,
            "baseline_results": baseline_results,
            "agent_results": agent_results
        }
    
    def _baseline_predict(self, text: str) -> str:
        """Baseline预测：纯关键词匹配"""
        # 简单规则
        if any(kw in text for kw in ["太甜", "太酸", "太苦", "难喝", "不好喝"]):
            return "complaint_taste"
        elif any(kw in text for kw in ["份量", "冰块太多", "饮料都没"]):
            return "complaint_quantity"
        elif any(kw in text for kw in ["推荐", "招牌", "好喝"]):
            return "query_recommend"
        elif any(kw in text for kw in ["订单", "送到"]):
            return "query_order"
        elif any(kw in text for kw in ["门店", "附近", "地址"]):
            return "query_location"
        elif any(kw in text for kw in ["退款", "退钱"]):
            return "query_refund"
        elif any(kw in text for kw in ["营业时间", "开门"]):
            return "query_opentime"
        elif any(kw in text for kw in ["配送", "超时", "慢"]):
            return "complaint_delivery"
        elif any(kw in text for kw in ["服务", "态度", "差"]):
            return "complaint_service"
        else:
            return "unknown"
    
    # ============ 实验3: 工具调用 ============
    
    def experiment_3_tool_fallback(self):
        """实验3：工具调用异常处理"""
        print("\n" + "=" * 70)
        print("实验3：工具调用异常处理")
        print("=" * 70)
        
        test_cases = [
            {"name": "参数缺失-订单", "tool": "query_order_status", "args": {}, "expected": "ask_user"},
            {"name": "正常-订单", "tool": "query_order_status", "args": {"order_id": "12345"}, "expected": "success"},
            {"name": "订单不存在", "tool": "query_order_status", "args": {"order_id": "99999"}, "expected": "business_error"},
            {"name": "参数缺失-库存", "tool": "check_inventory", "args": {}, "expected": "ask_user"},
            {"name": "正常-库存", "tool": "check_inventory", "args": {"store_id": "武汉大学"}, "expected": "success"},
            {"name": "门店不存在", "tool": "query_shop_info", "args": {"location": "火星"}, "expected": "business_error"},
            {"name": "正常-门店", "tool": "query_shop_info", "args": {"location": "武大"}, "expected": "success"},
            {"name": "参数缺失-投诉", "tool": "handle_complaint", "args": {}, "expected": "ask_user"},
            {"name": "正常-投诉", "tool": "handle_complaint", "args": {"complaint_type": "taste"}, "expected": "success"},
        ]
        
        correct = 0
        results = []
        
        for test in test_cases:
            result = tool_registry_v2.call(test["tool"], test["args"])
            actual = result.get("type")
            is_correct = actual == test["expected"]
            if is_correct:
                correct += 1
            
            results.append({
                "name": test["name"],
                "expected": test["expected"],
                "actual": actual,
                "correct": is_correct
            })
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [{actual}] {test['name']}")
        
        success_rate = correct / len(test_cases) * 100
        print(f"\n工具调用成功率: {success_rate:.1f}% ({correct}/{len(test_cases)})")
        
        return {
            "success_rate": success_rate,
            "details": results
        }
    
    # ============ 实验4: 记忆窗口 ============
    
    def experiment_4_memory_window(self):
        """实验4：记忆窗口对比"""
        print("\n" + "=" * 70)
        print("实验4：记忆窗口对比测试")
        print("=" * 70)
        
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
            session_id = f"test_{window_size}"
            
            start_time = time.time()
            for user_msg, agent_msg in test_conversation:
                memory.save_message(session_id, user_msg, agent_msg)
            end_time = time.time()
            
            context = memory.get_context(session_id)
            stats = memory.get_session_stats(session_id)
            
            remembers_drink = "杨枝甘露" in context
            remembers_sugar = "少糖" in context or "糖" in context
            
            print(f"  消息数: {stats['message_count']}, 有摘要: {'✓' if stats['has_summary'] else '✗'}")
            print(f"  记住饮品: {'✓' if remembers_drink else '✗'}, 记住偏好: {'✓' if remembers_sugar else '✗'}")
            print(f"  耗时: {(end_time - start_time)*1000:.1f}ms")
            
            results.append({
                "window_size": window_size,
                "message_count": stats['message_count'],
                "has_summary": stats['has_summary'],
                "remembers_drink": remembers_drink,
                "remembers_sugar": remembers_sugar,
                "time_ms": round((end_time - start_time) * 1000, 1)
            })
        
        return {"memory_results": results}
    
    # ============ 运行所有实验 ============
    
    def run_all(self):
        """运行所有实验"""
        print("\n" + "#" * 70)
        print("# BubbleMate 增强版实验运行器")
        print("#" * 70)
        
        results = {}
        
        results["intent_accuracy"] = self.experiment_1_intent_accuracy()
        results["baseline_comparison"] = self.experiment_2_baseline_comparison()
        results["tool_fallback"] = self.experiment_3_tool_fallback()
        results["memory_window"] = self.experiment_4_memory_window()
        
        # 保存结果
        result_path = os.path.join("data", "enhanced_experiment_results.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 汇总
        print("\n" + "#" * 70)
        print("# 实验汇总")
        print("#" * 70)
        print(f"\n意图识别准确率: {results['intent_accuracy']['accuracy']:.1f}%")
        print(f"  - Baseline: {results['baseline_comparison']['baseline_accuracy']:.1f}%")
        print(f"  - 完整Agent: {results['baseline_comparison']['agent_accuracy']:.1f}%")
        print(f"  - 提升: +{results['baseline_comparison']['improvement']:.1f}%")
        print(f"\n工具调用成功率: {results['tool_fallback']['success_rate']:.1f}%")
        print(f"\nBad Case数: {len(results['intent_accuracy']['bad_cases'])}")
        
        print(f"\n结果已保存: {result_path}")
        
        return results


if __name__ == "__main__":
    runner = EnhancedExperimentRunner()
    runner.run_all()
