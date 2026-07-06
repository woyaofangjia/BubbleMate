import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"已加载.env文件: {env_path}")
except ImportError:
    pass

api_key = os.getenv("ZHIPUAI_API_KEY")
client = None

try:
    from zhipuai import ZhipuAI
    if api_key:
        client = ZhipuAI(api_key=api_key)
        print("LLM客户端初始化成功")
    else:
        print("警告: ZHIPUAI_API_KEY 未设置，LLM功能不可用")
except ImportError:
    print("警告: zhipuai库未安装，LLM功能不可用。请运行: pip install zhipuai")

def call_llm(messages, model="glm-4-flash", max_tokens=500, temperature=0.7):
    if not client:
        raise RuntimeError("LLM客户端未初始化，请检查API Key和zhipuai库")
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.choices[0].message.content

def call_llm_with_stream(messages, model="glm-4-flash"):
    if not client:
        raise RuntimeError("LLM客户端未初始化，请检查API Key和zhipuai库")
    
    for chunk in client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True
    ):
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def call_llm_with_tools(messages, tools, model="glm-4-flash"):
    if not client:
        raise RuntimeError("LLM客户端未初始化，请检查API Key和zhipuai库")
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools
    )
    return response

def is_available():
    """检查LLM是否可用"""
    return client is not None