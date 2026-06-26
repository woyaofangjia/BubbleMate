import os
from zhipuai import ZhipuAI

client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

def call_llm(messages, model="glm-4-flash", max_tokens=500, temperature=0.7):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.choices[0].message.content

def call_llm_with_stream(messages, model="glm-4-flash"):
    for chunk in client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True
    ):
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def call_llm_with_tools(messages, tools, model="glm-4-flash"):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools
    )
    return response