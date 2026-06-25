"""
BubbleMate API - FastAPI主入口
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os

# 导入Agent组件
from backend.agent.intent_recognizer import IntentRecognizer
from backend.agent.react_agent import ReActAgent, create_tools
from backend.agent.memory_manager import MemoryManager
from backend.tools.tool_registry import tool_registry, register_all_tools
from backend.core.config import config

# 创建FastAPI应用
app = FastAPI(
    title="BubbleMate API",
    description="智能奶茶店客服Agent API",
    version="0.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件
intent_recognizer = IntentRecognizer(config.get_data_path(""))
tools = create_tools()
memory_manager = MemoryManager(window_size=config.MAX_MEMORY_WINDOW, use_redis=False)
agent = ReActAgent(tools, intent_recognizer, memory_manager)

# 注册MCP工具
register_all_tools()

# API模型
class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = "default"
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    intent: Dict
    session_id: str
    tool_calls: Optional[list] = None

class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any]

# API端点
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running"
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        # 处理消息
        response = agent.process(request.message, request.session_id)
        
        # 获取意图
        intent = intent_recognizer.recognize(request.message)
        
        # 获取会话统计
        stats = memory_manager.get_session_stats(request.session_id)
        
        return ChatResponse(
            response=response,
            intent={
                "name": intent.name,
                "confidence": intent.confidence,
                "category": intent.category
            },
            session_id=request.session_id,
            tool_calls=[]  # 后续实现
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """列出可用工具"""
    return {"tools": tool_registry.list_tools()}

@app.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    """调用工具"""
    try:
        result = tool_registry.call(request.tool_name, request.arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/intent/{text}")
async def recognize_intent(text: str):
    """识别意图"""
    intent = intent_recognizer.recognize(text)
    return {
        "text": text,
        "intent": {
            "name": intent.name,
            "confidence": intent.confidence,
            "category": intent.category,
            "keywords": intent.keywords,
            "source": intent.source
        }
    }

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话信息"""
    context = memory_manager.get_context(session_id)
    stats = memory_manager.get_session_stats(session_id)
    
    return {
        "session_id": session_id,
        "context": context,
        "stats": stats
    }

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除会话"""
    memory_manager.clear_session(session_id)
    return {"message": f"Session {session_id} cleared"}

@app.get("/shops")
async def list_shops():
    """列出奶茶店"""
    shops_path = config.get_data_path("bubble_tea_all.json")
    if os.path.exists(shops_path):
        with open(shops_path, "r", encoding="utf-8") as f:
            shops = json.load(f)
        return {"shops": shops, "count": len(shops)}
    return {"shops": [], "count": 0}

@app.get("/shops/{name}")
async def get_shop(name: str):
    """获取门店详情"""
    shops_path = config.get_data_path("bubble_tea_all.json")
    if os.path.exists(shops_path):
        with open(shops_path, "r", encoding="utf-8") as f:
            shops = json.load(f)
        
        # 搜索门店
        for shop in shops:
            if name.lower() in shop.get("name", "").lower():
                return shop
        
        return {"error": "门店不存在"}
    return {"error": "数据不可用"}

@app.get("/menu")
async def get_menu(category: Optional[str] = None):
    """获取菜单"""
    menu_path = config.get_data_path("qa_pairs.json")
    
    # 简化版菜单数据
    menu = {
        "芝士系列": [
            {"name": "芝芝莓莓", "price": 20, "description": "鲜草莓芝士奶盖"},
            {"name": "芝芝芒果", "price": 18, "description": "芒果芝士奶盖"},
        ],
        "鲜果茶系列": [
            {"name": "杨枝甘露", "price": 18, "description": "椰奶芒果西柚"},
            {"name": "葡萄冰茶", "price": 15, "description": "新鲜葡萄冰茶"},
        ],
        "奶茶系列": [
            {"name": "珍珠奶茶", "price": 12, "description": "经典珍珠奶茶"},
            {"name": "糯米奶茶", "price": 14, "description": "糯米珍珠奶茶"},
        ],
        "纯茶系列": [
            {"name": "茉莉绿茶", "price": 15, "description": "零糖低卡"},
            {"name": "柠檬茶", "price": 10, "description": "清爽柠檬"},
        ]
    }
    
    if category:
        return {"category": category, "items": menu.get(category, [])}
    
    return {"menu": menu}

# 启动事件
@app.on_event("startup")
async def startup_event():
    """启动事件"""
    print(f"BubbleMate API 启动")
    print(f"版本: {config.APP_VERSION}")
    
    if not config.OPENAI_API_KEY:
        print("警告: OPENAI_API_KEY 未设置，使用本地模式")

# 主函数
def main():
    """启动服务"""
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG
    )

if __name__ == "__main__":
    main()