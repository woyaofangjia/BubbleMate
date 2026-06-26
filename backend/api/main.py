from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
from backend.agent.react_agent_v2 import ReActAgentV2
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.agent.human_in_loop import evaluate, resolve_intervention, get_pending_interventions
from backend.tools.bubble_tools import TOOL_REGISTRY as BUBBLE_TOOLS
from backend.core.config import config

# 创建FastAPI应用
app = FastAPI(
    title="BubbleMate API",
    description="智能奶茶店客服Agent API",
    version="0.2.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化组件（使用增强版）
intent_recognizer = IntentRecognizerV2(config.get_data_path(""))
memory_manager = MemoryManagerV2(window_size=config.MAX_MEMORY_WINDOW, use_redis=False)

# 注册新工具
bubble_tools = {}
for tool_name, tool_config in BUBBLE_TOOLS.items():
    bubble_tools[tool_name] = tool_config["handler"]

# 创建Agent（使用新工具）
agent = ReActAgentV2(bubble_tools, intent_recognizer, memory_manager)

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
    tools_list = []
    for name, tool_config in BUBBLE_TOOLS.items():
        tools_list.append({
            "name": name,
            "description": tool_config["description"],
            "parameters": tool_config["parameters"],
            "type": "真实API" if name == "query_stores" else "Mock"
        })
    return {"tools": tools_list, "count": len(tools_list)}

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

# Human-in-the-Loop API端点
@app.get("/human-in-loop/pending")
async def get_pending_interventions_api():
    return get_pending_interventions()

@app.get("/eval/report")
async def get_eval_report():
    """获取评测报告"""
    report_path = os.path.join(os.path.dirname(__file__), "../../data/eval_report.json")
    
    if not os.path.exists(report_path):
        # 返回提示信息
        return {
            "timestamp": "未生成",
            "test_cases_count": 0,
            "level1_component": {
                "intent_accuracy": 0,
                "tool_accuracy": 0,
                "clarification_rate": 0,
                "avg_latency_ms": 0
            },
            "level2_end_to_end": {
                "solved_rate": 0,
                "partial_rate": 0,
                "failure_rate": 0
            },
            "level3_adversarial": {
                "adversarial_pass_rate": 0,
                "category_breakdown": {}
            },
            "overall_pass_rate": 0,
            "bad_cases": [],
            "message": "请运行评测脚本: python scripts/bubble_eval_runner.py"
        }
    
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    return report

@app.post("/eval/run")
async def run_eval():
    """运行评测（触发脚本）"""
    # 简化版：返回提示
    return {
        "message": "请在终端运行: python scripts/bubble_eval_runner.py",
        "command": "python scripts/bubble_eval_runner.py"
    }

@app.post("/human-in-loop/{intervention_id}/resolve")
async def resolve_intervention_api(intervention_id: str, request: Dict[str, Any]):
    resolution = request.get("resolution", "")
    agent_id = request.get("agent_id", "unknown")
    
    success = resolve_intervention(intervention_id, resolution, agent_id)
    
    if success:
        return {"success": True, "message": f"介入请求 {intervention_id} 已解决"}
    else:
        raise HTTPException(status_code=404, detail="介入请求不存在")

@app.get("/human-in-loop/evaluate")
async def evaluate_hil(session_id: str, user_message: str, agent_response: str = ""):
    intent = intent_recognizer.recognize(user_message)
    tool_results = [{"success": True}]
    session_history = memory_manager.get_context(session_id) or []
    
    result = evaluate(
        session_id=session_id,
        intent_result={"name": intent.name, "confidence": intent.confidence, "text": user_message},
        tool_results=tool_results,
        session_history=session_history,
        user_message=user_message,
        agent_response=agent_response
    )
    
    return result

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