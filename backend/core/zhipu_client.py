import os
import asyncio
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

api_key = os.getenv("ZHIPUAI_API_KEY")
client = None
ollama_client = None
aiohttp_session = None

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "zhipu")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "glm-4-9b")
LLM_SEMAPHORE = int(os.getenv("LLM_SEMAPHORE", 10))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 30))

_llm_semaphore = asyncio.Semaphore(LLM_SEMAPHORE)

try:
    if LLM_PROVIDER == "zhipu":
        from zhipuai import ZhipuAI
        if api_key:
            client = ZhipuAI(api_key=api_key)
        else:
            print("警告: ZHIPUAI_API_KEY 未设置，LLM功能不可用")
    elif LLM_PROVIDER == "ollama":
        import requests
        ollama_client = requests.Session()
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
except ImportError as e:
    print(f"警告: 依赖库未安装，LLM功能不可用: {e}")

async def _get_aiohttp_session():
    global aiohttp_session
    if aiohttp_session is None:
        import aiohttp
        aiohttp_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=LLM_TIMEOUT))
    return aiohttp_session

def call_llm(messages, model=None, max_tokens=500, temperature=0.7):
    if model is None:
        model = DEFAULT_MODEL
    
    if LLM_PROVIDER == "zhipu":
        if not client:
            raise RuntimeError("LLM客户端未初始化，请检查API Key和zhipuai库")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content
    elif LLM_PROVIDER == "ollama":
        if not ollama_client:
            raise RuntimeError("Ollama客户端未初始化，请检查requests库和Ollama服务")
        
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = ollama_client.post(f"{ollama_base_url}/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError(f"不支持的LLM_PROVIDER: {LLM_PROVIDER}")

async def call_llm_async(messages, model=None, max_tokens=500, temperature=0.7):
    if model is None:
        model = DEFAULT_MODEL
    
    async with _llm_semaphore:
        if LLM_PROVIDER == "zhipu":
            if not api_key:
                raise RuntimeError("LLM客户端未初始化，请检查API Key")
            
            import aiohttp
            session = await _get_aiohttp_session()
            zhipu_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                async with session.post(zhipu_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        raise RuntimeError(f"智谱API调用失败，状态码: {response.status}")
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
            except asyncio.TimeoutError:
                raise RuntimeError("LLM调用超时")
            except Exception as e:
                raise RuntimeError(f"LLM调用失败: {str(e)}")
        
        elif LLM_PROVIDER == "ollama":
            import aiohttp
            session = await _get_aiohttp_session()
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            try:
                async with session.post(f"{ollama_base_url}/v1/chat/completions", json=payload) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama API调用失败，状态码: {response.status}")
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
            except asyncio.TimeoutError:
                raise RuntimeError("LLM调用超时")
            except Exception as e:
                raise RuntimeError(f"LLM调用失败: {str(e)}")
        
        else:
            raise RuntimeError(f"不支持的LLM_PROVIDER: {LLM_PROVIDER}")

def call_llm_with_stream(messages, model=None):
    if model is None:
        model = DEFAULT_MODEL
    
    if LLM_PROVIDER == "zhipu":
        if not client:
            raise RuntimeError("LLM客户端未初始化，请检查API Key和zhipuai库")
        
        for chunk in client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        ):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    elif LLM_PROVIDER == "ollama":
        if not ollama_client:
            raise RuntimeError("Ollama客户端未初始化，请检查requests库和Ollama服务")
        
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        
        response = ollama_client.post(f"{ollama_base_url}/v1/chat/completions", json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                import json
                try:
                    data = json.loads(line.decode("utf-8").replace("data: ", ""))
                    if "choices" in data and data["choices"][0]["delta"].get("content"):
                        yield data["choices"][0]["delta"]["content"]
                except:
                    continue
    else:
        raise RuntimeError(f"不支持的LLM_PROVIDER: {LLM_PROVIDER}")

def call_llm_with_tools(messages, tools, model=None):
    if model is None:
        model = DEFAULT_MODEL
    
    if LLM_PROVIDER == "zhipu":
        if not client:
            raise RuntimeError("LLM客户端未初始化，请检查API Key和zhipuai库")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools
        )
        return response
    elif LLM_PROVIDER == "ollama":
        raise NotImplementedError("Ollama暂不支持工具调用")
    else:
        raise RuntimeError(f"不支持的LLM_PROVIDER: {LLM_PROVIDER}")

def is_available():
    if LLM_PROVIDER == "zhipu":
        return client is not None
    elif LLM_PROVIDER == "ollama":
        if not ollama_client:
            return False
        try:
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            response = ollama_client.get(f"{ollama_base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    return False