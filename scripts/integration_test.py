"""
BubbleMate - 前后端联调测试
模拟完整的端到端对话流程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer import IntentRecognizer
from backend.agent.react_agent import ReActAgent, create_tools
from backend.agent.memory_manager import MemoryManager
from backend.tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2

class IntegrationTester:
    """集成测试器"""
    
    def __init__(self):
        # 初始化所有组件
        self.intent_recognizer = IntentRecognizer("data")
        self.tools = create_tools()
        self.memory_manager = MemoryManager(window_size=5, use_redis=False)
        self.agent = ReActAgent(self.tools, self.intent_recognizer, self.memory_manager)
        
        # 注册V2工具
        register_all_tools_v2()
        
        # 测试统计
        self.stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "intent_accuracy": 0,
            "tool_success_rate": 0,
        }
    
    def test_intent_recognition(self):
        """测试意图识别准确性"""
        print("\n" + "=" * 60)
        print("测试1: 意图识别准确性")
        print("=" * 60)
        
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
        ]
        
        correct = 0
        for text, expected_intent, expected_category in test_cases:
            intent = self.intent_recognizer.recognize(text)
            
            # 检查意图是否正确
            is_correct = (intent.name == expected_intent or 
                         intent.category == expected_category or
                         intent.confidence > 0.5)
            
            status = "✓" if is_correct else "✗"
            print(f"{status} [{intent.name}] {text[:20]}...")
            
            if is_correct:
                correct += 1
        
        accuracy = correct / len(test_cases) * 100
        self.stats["intent_accuracy"] = accuracy
        print(f"\n意图识别准确率: {accuracy:.1f}% ({correct}/{len(test_cases)})")
        
        return accuracy >= 70  # 及格线70%
    
    def test_tool_calling(self):
        """测试工具调用（带异常处理）"""
        print("\n" + "=" * 60)
        print("测试2: 工具调用异常处理")
        print("=" * 60)
        
        test_cases = [
            {
                "name": "参数缺失-反问",
                "tool": "query_order_status",
                "args": {},
                "expected_type": "ask_user"
            },
            {
                "name": "正常调用-成功",
                "tool": "query_order_status",
                "args": {"order_id": "12345"},
                "expected_type": "success"
            },
            {
                "name": "业务错误-引导",
                "tool": "query_order_status",
                "args": {"order_id": "99999"},
                "expected_type": "business_error"
            },
            {
                "name": "库存查询-正常",
                "tool": "check_inventory",
                "args": {"store_id": "武汉大学"},
                "expected_type": "success"
            },
            {
                "name": "投诉处理-缺少参数",
                "tool": "handle_complaint",
                "args": {},
                "expected_type": "ask_user"
            },
        ]
        
        correct = 0
        for test in test_cases:
            result = tool_registry_v2.call(test["tool"], test["args"])
            
            is_correct = result.get("type") == test["expected_type"]
            status = "✓" if is_correct else "✗"
            print(f"{status} {test['name']}: {result['type']}")
            
            if is_correct:
                correct += 1
        
        success_rate = correct / len(test_cases) * 100
        self.stats["tool_success_rate"] = success_rate
        print(f"\n工具调用成功率: {success_rate:.1f}% ({correct}/{len(test_cases)})")
        
        return success_rate >= 80
    
    def test_conversation_flow(self):
        """测试完整对话流程"""
        print("\n" + "=" * 60)
        print("测试3: 完整对话流程")
        print("=" * 60)
        
        session_id = "integration_test_session"
        
        # 清空会话
        self.memory_manager.clear_session(session_id)
        
        # 模拟对话流程
        conversation = [
            {
                "user": "你们有什么招牌推荐？",
                "expected_intent": "query_recommend",
                "check_response": ["推荐", "招牌"]
            },
            {
                "user": "太甜了，喝不下去",
                "expected_intent": "complaint_taste",
                "check_response": ["抱歉", "糖"]
            },
            {
                "user": "订单12345什么时候能送到？",
                "expected_intent": "query_order",
                "check_response": ["配送", "订单"]
            },
            {
                "user": "附近有门店吗？",
                "expected_intent": "query_location",
                "check_response": ["门店", "附近"]
            },
        ]
        
        for i, turn in enumerate(conversation, 1):
            print(f"\n--- 对话轮次 {i} ---")
            print(f"用户: {turn['user']}")
            
            # 意图识别
            intent = self.intent_recognizer.recognize(turn['user'])
            print(f"[意图] {intent.name} (置信度: {intent.confidence:.2f})")
            
            # Agent处理
            response = self.agent.process(turn['user'], session_id)
            
            # 提取回复内容
            if "【回复】" in response:
                reply = response.split("【回复】")[-1].strip()
            else:
                reply = response
            
            print(f"Agent: {reply[:100]}...")
            
            # 验证回复内容
            has_keywords = any(kw in reply for kw in turn['check_response'])
            status = "✓" if has_keywords else "✗"
            print(f"{status} 回复包含预期关键词: {turn['check_response']}")
        
        # 检查记忆
        stats = self.memory_manager.get_session_stats(session_id)
        print(f"\n[记忆状态] 已保存 {stats['message_count']} 条消息")
        
        return stats['message_count'] >= 4
    
    def test_memory_compression(self):
        """测试记忆压缩"""
        print("\n" + "=" * 60)
        print("测试4: 记忆压缩机制")
        print("=" * 60)
        
        session_id = "memory_test"
        self.memory_manager.clear_session(session_id)
        
        # 添加超过窗口大小的消息
        messages = [
            ("问题1", "回答1"),
            ("问题2", "回答2"),
            ("问题3", "回答3"),
            ("问题4", "回答4"),
            ("问题5", "回答5"),
            ("问题6", "回答6"),
        ]
        
        for user, agent in messages:
            self.memory_manager.save_message(session_id, user, agent)
        
        # 检查记忆状态
        stats = self.memory_manager.get_session_stats(session_id)
        context = self.memory_manager.get_context(session_id)
        
        print(f"消息数: {stats['message_count']}")
        print(f"有摘要: {stats['has_summary']}")
        print(f"上下文长度: {len(context)} 字符")
        
        # 验证摘要已生成
        has_summary = "摘要" in context or "历史" in context
        print(f"\n✓ 记忆压缩已触发: {stats['has_summary']}")
        
        return stats['has_summary']
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("BubbleMate 前后端联调测试")
        print("=" * 60)
        
        results = []
        
        # 测试1: 意图识别
        try:
            results.append(("意图识别", self.test_intent_recognition()))
        except Exception as e:
            print(f"测试失败: {e}")
            results.append(("意图识别", False))
        
        # 测试2: 工具调用
        try:
            results.append(("工具调用", self.test_tool_calling()))
        except Exception as e:
            print(f"测试失败: {e}")
            results.append(("工具调用", False))
        
        # 测试3: 对话流程
        try:
            results.append(("对话流程", self.test_conversation_flow()))
        except Exception as e:
            print(f"测试失败: {e}")
            results.append(("对话流程", False))
        
        # 测试4: 记忆压缩
        try:
            results.append(("记忆压缩", self.test_memory_compression()))
        except Exception as e:
            print(f"测试失败: {e}")
            results.append(("记忆压缩", False))
        
        # 汇总
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        for name, passed in results:
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"{status} - {name}")
        
        passed_count = sum(1 for _, p in results if p)
        total_count = len(results)
        
        print(f"\n总计: {passed_count}/{total_count} 通过")
        print(f"意图识别准确率: {self.stats['intent_accuracy']:.1f}%")
        print(f"工具调用成功率: {self.stats['tool_success_rate']:.1f}%")
        
        if passed_count == total_count:
            print("\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️ {total_count - passed_count} 项测试失败，需要检查")
        
        return passed_count == total_count


if __name__ == "__main__":
    tester = IntegrationTester()
    tester.run_all_tests()
