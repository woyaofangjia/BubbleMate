from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os

from backend.bubble_agent import process_message, recognize_intent, create_memory_store, get_context, TOOLS

app = FastAPI(title="BubbleMate API", version="0.3.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

memory_store = create_memory_store()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    intent: Dict
    session_id: str

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

def main():
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()