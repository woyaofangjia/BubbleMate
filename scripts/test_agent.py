"""
BubbleMate - 简易测试入口（无需FastAPI）
直接测试Agent核心功能
"""

import sys
import os

# 添加backend路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.intent_recognizer import IntentRecognizer
from backend.agent.react_agent import ReActAgent, create_tools
from backend.agent.memory_manager import MemoryManager
from backend.tools.tool_registry import tool_registry, register_all_tools

def interactive_test():
    """交互式测试Agent"""
    # 初始化组件
    intent_recognizer = IntentRecognizer("data")
    tools = create_tools()
    memory_manager = MemoryManager(window_size=5, use_redis=False)
    agent = ReActAgent(tools, intent_recognizer, memory_manager)
    
    # 注册工具
    register_all_tools()
    
    print("=" * 60)
    print("BubbleMate Agent 交互式测试")
    print("=" * 60)
    print("输入消息测试Agent，输入 'quit' 退出")
    print("=" * 60)
    
    session_id = "test_session"
    
    while True:
        user_input = input("\n用户: ").strip()
        
        if user_input.lower() == "quit":
            print("测试结束")
            break
        
        if not user_input:
            continue
        
        # 处理消息
        response = agent.process(user_input, session_id)
        
        # 显示意图
        intent = intent_recognizer.recognize(user_input)
        print(f"\n[意图] {intent.name} (置信度: {intent.confidence:.2f})")
        
        # 显示回复
        print(f"\nAgent: {response}")
        
        # 显示记忆状态
        stats = memory_manager.get_session_stats(session_id)
        print(f"\n[记忆] 已保存 {stats['message_count']} 条消息")

def batch_test():
    """批量测试"""
    intent_recognizer = IntentRecognizer("data")
    tools = create_tools()
    memory_manager = MemoryManager(window_size=5, use_redis=False)
    agent = ReActAgent(tools, intent_recognizer, memory_manager)
    
    test_cases = [
        ("太甜了，喝不下去", "投诉口感"),
        ("冰块太多，饮料都没了", "投诉份量"),
        ("你们有什么招牌推荐？", "推荐查询"),
        ("订单12345什么时候能送到？", "订单查询"),
        ("附近有门店吗？", "门店查询"),
        ("可以退款吗？", "退款查询"),
        ("门店营业时间？", "营业时间查询"),
    ]
    
    print("\n" + "=" * 60)
    print("BubbleMate Agent 批量测试")
    print("=" * 60)
    
    for user_input, expected_type in test_cases:
        response = agent.process(user_input, "batch_test")
        intent = intent_recognizer.recognize(user_input)
        
        print(f"\n测试: {expected_type}")
        print(f"输入: {user_input}")
        print(f"意图: {intent.name} (置信度: {intent.confidence:.2f})")
        print(f"回复: {response[:100]}...")
        print("-" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BubbleMate Agent测试")
    parser.add_argument("--interactive", action="store_true", help="交互式测试")
    parser.add_argument("--batch", action="store_true", help="批量测试")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_test()
    elif args.batch:
        batch_test()
    else:
        # 默认批量测试
        batch_test()