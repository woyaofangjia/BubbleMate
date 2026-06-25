"""
测试增强版Agent
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.agent.react_agent_v2 import ReActAgentV2, create_tools_v2

def test_agent_v2():
    """测试增强版Agent"""
    intent_recognizer = IntentRecognizerV2("data")
    tools = create_tools_v2()
    memory_manager = MemoryManagerV2(window_size=5, use_redis=False)
    agent = ReActAgentV2(tools, intent_recognizer, memory_manager)
    
    test_inputs = [
        "太甜了，喝不下去",
        "你们有什么招牌推荐？",
        "订单12345什么时候能送到？",
        "附近有门店吗？",
        "可以退款吗？",
        "门店营业时间？",
        "甜度有几种选择？",
        "有外卖吗？",
        "今天有什么优惠？",
        "会员卡怎么办？",
    ]
    
    print("\n" + "=" * 60)
    print("增强版Agent测试")
    print("=" * 60)
    
    session_id = "test_session"
    for input_text in test_inputs:
        response = agent.process(input_text, session_id)
        print(f"用户: {input_text}")
        print(f"Agent:\n{response}")
        print("=" * 60)

if __name__ == "__main__":
    test_agent_v2()
