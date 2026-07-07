from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os

from backend.bubble_agent import process_message, recognize_intent, create_memory_store, get_context, TOOLS, get_user_id
from backend.storage.database import init_db, get_user_preferences, get_complaint_history, get_user_stats
from backend.storage.memory_store import get_all_complaints, get_knowledge_list, review_knowledge, delete_knowledge, get_complaint_stats

init_db()

ADMIN_KEY = "bubble2026"
TAKEOVER_SESSIONS = set()

app = FastAPI(title="BubbleMate API", version="0.4.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

memory_store = create_memory_store()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    intent: Dict
    session_id: str

class LoginRequest(BaseModel):
    key: str

class ReviewRequest(BaseModel):
    id: int

class ReplyRequest(BaseModel):
    message: str

@app.get("/")
async def root():
    return {"name": "BubbleMate", "version": "0.3.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response, intent = process_message(request.message, request.session_id, memory_store)
    return ChatResponse(response=response, intent=intent, session_id=request.session_id)

@app.get("/tools")
async def list_tools():
    return {"tools": list(TOOLS.keys()), "count": len(TOOLS)}

@app.get("/intent/{text}")
async def get_intent(text: str):
    intent = recognize_intent(text)
    return {"text": text, "intent": intent}

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    context = get_context(memory_store, session_id)
    return {"session_id": session_id, "context": context}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    memory_store["sessions"].pop(session_id, None)
    return {"message": f"Session {session_id} cleared"}

@app.get("/menu")
async def get_menu(category: Optional[str] = None):
    menu = {
        "芝士系列": [{"name": "芝芝莓莓", "price": 20}, {"name": "芝芝芒果", "price": 18}],
        "鲜果茶系列": [{"name": "杨枝甘露", "price": 18}, {"name": "葡萄冰茶", "price": 15}],
        "奶茶系列": [{"name": "珍珠奶茶", "price": 12}, {"name": "糯米奶茶", "price": 14}],
        "纯茶系列": [{"name": "茉莉绿茶", "price": 15}, {"name": "柠檬茶", "price": 10}],
    }
    return {"menu": menu} if not category else {"category": category, "items": menu.get(category, [])}

@app.get("/shops")
async def list_shops():
    path = os.path.join(os.path.dirname(__file__), "../../data/bubble_tea_all.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            shops = json.load(f)
        return {"shops": shops, "count": len(shops)}
    return {"shops": [], "count": 0}

@app.get("/eval/report")
async def get_eval_report():
    path = os.path.join(os.path.dirname(__file__), "../../data/eval_report.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"message": "请运行评测脚本"}

@app.get("/api/user/profile")
async def get_user_profile(session_id: str):
    user_id = get_user_id(session_id)
    preferences = get_user_preferences(user_id)
    complaints = get_complaint_history(user_id)
    stats = get_user_stats(user_id)
    orders_path = os.path.join(os.path.dirname(__file__), "../../data/orders_mock.json")
    recent_orders = []
    if os.path.exists(orders_path):
        with open(orders_path, "r", encoding="utf-8") as f:
            orders_data = json.load(f)
            user_orders = orders_data.get(user_id, [])
            recent_orders = [{"order_id": o["order_id"], "store": o["store"], "items": o["items"], "total": o["total"], "status": o["status"], "create_time": o["create_time"]} for o in user_orders][:5]
    return {
        "user_id": user_id,
        "preferences": preferences,
        "stats": {
            "total_complaints": stats["total_complaints"],
            "total_feedback": stats["total_feedback"],
            "total_orders": len(recent_orders),
        },
        "complaints": complaints,
        "recent_orders": recent_orders,
    }

@app.post("/api/admin/login")
async def admin_login(request: LoginRequest):
    if request.key == ADMIN_KEY:
        return {"success": True, "token": "admin_token"}
    raise HTTPException(status_code=401, detail="密码错误")

@app.get("/api/admin/complaints")
async def admin_get_complaints():
    complaints = get_all_complaints()
    return {"complaints": complaints}

@app.get("/api/admin/stats")
async def admin_get_stats():
    stats = get_complaint_stats()
    return stats

@app.get("/api/admin/knowledge")
async def admin_get_knowledge(reviewed_only: Optional[bool] = False):
    knowledge = get_knowledge_list(reviewed_only)
    return {"knowledge": knowledge}

@app.post("/api/admin/knowledge/review")
async def admin_review_knowledge(request: ReviewRequest):
    review_knowledge(request.id)
    return {"success": True, "id": request.id}

@app.delete("/api/admin/knowledge/{id}")
async def admin_delete_knowledge(id: int):
    delete_knowledge(id)
    return {"success": True, "id": id}

@app.get("/api/admin/context/{session_id}")
async def admin_get_context(session_id: str):
    user_id = get_user_id(session_id)
    preferences = get_user_preferences(user_id)
    complaints = get_complaint_history(user_id)
    context = get_context(memory_store, session_id)
    is_taken_over = session_id in TAKEOVER_SESSIONS
    return {
        "session_id": session_id,
        "user_id": user_id,
        "preferences": preferences,
        "complaints": complaints,
        "context": context,
        "is_taken_over": is_taken_over,
    }

@app.post("/api/admin/takeover/{session_id}")
async def admin_takeover(session_id: str):
    TAKEOVER_SESSIONS.add(session_id)
    return {"success": True, "session_id": session_id, "status": "taken_over"}

@app.post("/api/admin/reply/{session_id}")
async def admin_reply(session_id: str, request: ReplyRequest):
    return {"success": True, "session_id": session_id, "message": request.message}

@app.post("/api/admin/release/{session_id}")
async def admin_release(session_id: str):
    TAKEOVER_SESSIONS.discard(session_id)
    return {"success": True, "session_id": session_id, "status": "released"}

def main():
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()