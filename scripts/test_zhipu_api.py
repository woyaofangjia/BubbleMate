"""测试智谱API Key是否有效"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载.env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from backend.core.zhipu_client import call_llm

# 测试1: 简单对话
print("=" * 60)
print("测试1: 简单对话")
print("=" * 60)

messages = [{"role": "user", "content": "你好，我是BubbleMate奶茶店客服"}]
response = call_llm(messages)
print(f"回复: {response}")

# 测试2: 意图识别
print("\n" + "=" * 60)
print("测试2: 意图识别")
print("=" * 60)

intent_prompt = """你是一个意图识别器，用户说："附近有门店吗"
请判断意图类别（query_location/query_menu/query_order/complaint_taste/complaint_quantity）：
直接输出类别名称，不要其他文字。"""

response = call_llm([{"role": "user", "content": intent_prompt}])
print(f"意图: {response}")

# 测试3: 工具调用（如果支持）
print("\n" + "=" * 60)
print("测试3: 工具调用")
print("=" * 60)

try:
    from backend.core.zhipu_client import call_llm_with_tools
    
    tools = [{
        "type": "function",
        "function": {
            "name": "query_stores",
            "description": "查询附近门店",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "位置名称"}
                },
                "required": ["location"]
            }
        }
    }]
    
    messages = [{"role": "user", "content": "光谷附近有门店吗"}]
    response = call_llm_with_tools(messages, tools)
    print(f"工具调用结果: {response}")
except Exception as e:
    print(f"工具调用测试失败: {e}")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("=" * 60)