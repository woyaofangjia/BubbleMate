from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bubble_agent import process_message, process_message_async, recognize_intent, create_memory_store, get_context, TOOLS, get_user_id, query_menu, query_promotions, query_recommend, query_customize, MemoryStore, clear_intent_cache
from storage.database import init_db, get_user_preferences, get_complaint_history, get_user_stats, get_knowledge_candidates, approve_candidate, reject_candidate, get_complaint_knowledge, get_knowledge_complaints, update_knowledge_parent, get_all_complaints, get_knowledge_list, get_knowledge_graph, get_knowledge_graph_aggregated, review_knowledge, delete_knowledge, get_complaint_stats, resolve_complaint, add_knowledge_node
from storage.data_access import get_shops, get_menu_items, get_orders, get_shop_by_name
from storage.redis_store import session_store

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

class AddKnowledgeRequest(BaseModel):
    node_type: str
    content: str
    parent_id: Optional[int] = None

class AddRelationRequest(BaseModel):
    parent_id: int
    child_id: int

@app.get("/")
async def root():
    return {"name": "BubbleMate", "version": "0.3.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

async def process_complaint_async(session_id: str, message: str, intent_name: str):
    user_id = get_user_id(session_id)
    category_map = {
        "complaint_taste": "口味", "complaint_quantity": "份量",
        "complaint_service": "服务", "complaint_delivery": "配送",
        "complaint_price": "价格", "complaint_refund": "退款",
        "complaint_sarcasm": "讽刺", "complaint_accessory": "配件",
    }
    category = category_map.get(intent_name, "口味")
    log_complaint(user_id=user_id, complaint=message, severity="普通", category=category, intent_name=intent_name)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    response, intent = await process_message_async(request.message, request.session_id, memory_store)
    
    if intent["name"].startswith("complaint"):
        background_tasks.add_task(process_complaint_async, request.session_id, request.message, intent["name"])
    
    return ChatResponse(response=response, intent=intent, session_id=request.session_id)

@app.get("/tools")
async def list_tools():
    return {"tools": list(TOOLS.keys()), "count": len(TOOLS)}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "redis_enabled": session_store.is_using_redis(),
        "version": "0.4.0"
    }

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
    if isinstance(memory_store, MemoryStore):
        session_store.delete_session(session_id)
    else:
        memory_store["sessions"].pop(session_id, None)
    return {"message": f"Session {session_id} cleared"}

@app.get("/menu")
async def get_menu(category: Optional[str] = None):
    items = get_menu_items(category=category)
    if category:
        result = {"category": category, "items": items}
    else:
        menu = {}
        for item in items:
            cat = item.get('category', '其他')
            if cat not in menu:
                menu[cat] = []
            menu[cat].append({"name": item['name'], "price": item['price']})
        result = {"menu": menu}
    return Response(content=json.dumps(result, ensure_ascii=False), media_type="application/json", headers={"Cache-Control": "public, max-age=300"})

@app.get("/shops")
async def list_shops():
    shops = get_shops()
    result = {"shops": shops, "count": len(shops)}
    return Response(content=json.dumps(result, ensure_ascii=False), media_type="application/json", headers={"Cache-Control": "public, max-age=600"})

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
    db_orders = get_orders(user_id=user_id)
    recent_orders = []
    for order in db_orders[:5]:
        shop = get_shop_by_name(order.get('shop_id', '')) if order.get('shop_id') else None
        recent_orders.append({
            "order_id": order['id'],
            "store": shop['name'] if shop else order.get('shop_id', ''),
            "items": order.get('items', []),
            "total": order.get('total'),
            "status": order.get('status', 'pending'),
            "create_time": order.get('create_time'),
        })
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
async def admin_get_knowledge():
    graph = get_knowledge_graph()
    all_nodes = []
    def count_types(node):
        all_nodes.append(node)
        for child in node.get('children', []):
            count_types(child)
    for root in graph:
        count_types(root)
    stats = {
        'total_nodes': len(all_nodes),
        'by_type': {}
    }
    for node in all_nodes:
        node_type = node.get('node_type', '')
        stats['by_type'][node_type] = stats['by_type'].get(node_type, 0) + 1
    return {"tree": graph, "statistics": stats}

@app.get("/api/admin/knowledge/graph")
async def admin_get_knowledge_graph():
    graph = get_knowledge_graph()
    return {"graph": graph}

@app.get("/api/admin/knowledge/graph/aggregated")
async def admin_get_knowledge_graph_aggregated():
    result = get_knowledge_graph_aggregated()
    return result

@app.post("/api/admin/knowledge/review")
async def admin_review_knowledge(request: ReviewRequest):
    review_knowledge(request.id)
    return {"success": True, "id": request.id}

@app.delete("/api/admin/knowledge/{id}")
async def admin_delete_knowledge(id: int):
    delete_knowledge(id)
    return {"success": True, "id": id, "message": "已软删除该节点及其所有子节点"}

@app.post("/api/admin/knowledge")
async def admin_add_knowledge(request: AddKnowledgeRequest):
    new_id = add_knowledge_node(request.node_type, request.content, request.parent_id)
    return {"success": True, "id": new_id}

@app.post("/api/admin/knowledge/relation")
async def admin_add_relation(request: AddRelationRequest):
    update_knowledge_parent(request.child_id, request.parent_id)
    return {"success": True}

@app.post("/api/admin/complaints/resolve/{id}")
async def admin_resolve_complaint(id: int):
    resolve_complaint(id)
    return {"success": True, "id": id}

@app.get("/api/admin/candidates")
async def admin_get_candidates(status: Optional[str] = None):
    candidates = get_knowledge_candidates(status)
    return {"candidates": candidates}

@app.post("/api/admin/candidates/{id}/approve")
async def admin_approve_candidate(id: int):
    success = approve_candidate(id)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"success": True, "id": id}

@app.post("/api/admin/candidates/{id}/reject")
async def admin_reject_candidate(id: int):
    success = reject_candidate(id)
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"success": True, "id": id}

@app.post("/api/admin/candidate-approve")
async def admin_candidate_approve(request: Request):
    data = await request.json()
    success = approve_candidate(data.get("id"))
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"success": True, "id": data.get("id")}

@app.post("/api/admin/candidate-reject")
async def admin_candidate_reject(request: Request):
    data = await request.json()
    success = reject_candidate(data.get("id"))
    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"success": True, "id": data.get("id")}

@app.get("/api/admin/complaints/{id}/knowledge")
async def admin_get_complaint_knowledge(id: int):
    knowledge = get_complaint_knowledge(id)
    return {"knowledge": knowledge}

@app.get("/api/admin/knowledge/{id}/complaints")
async def admin_get_knowledge_complaints(id: int):
    complaints = get_knowledge_complaints(id)
    return {"complaints": complaints}

@app.get("/api/admin/knowledge-complaints")
async def admin_get_knowledge_complaints_v2(knowledge_id: int):
    complaints = get_knowledge_complaints(knowledge_id)
    return {"complaints": complaints}

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

@app.post("/api/admin/cache/clear")
async def admin_clear_cache():
    from storage.data_access import get_shops, get_shop_by_name, get_menu_items, get_hot_menu_items
    from storage.database import get_knowledge_list, get_knowledge_graph
    
    query_menu.cache_clear()
    query_promotions.cache_clear()
    query_recommend.cache_clear()
    query_customize.cache_clear()
    get_shops.cache_clear()
    get_shop_by_name.cache_clear()
    get_menu_items.cache_clear()
    get_hot_menu_items.cache_clear()
    get_knowledge_list.cache_clear()
    get_knowledge_graph.cache_clear()
    clear_intent_cache()
    return {"success": True, "message": "缓存已清除"}

class FeedbackRequest(BaseModel):
    message_id: str
    feedback_type: str
    session_id: str

@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    user_id = get_user_id(request.session_id)
    save_feedback(user_id, request.message_id, request.feedback_type)
    return {"success": True, "message": "反馈已记录"}

@app.get("/api/admin/eval-report")
async def get_eval_report():
    import json
    import os
    report_path = os.path.join(os.path.dirname(__file__), "../../data/eval_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "评测报告不存在"}

@app.post("/api/admin/run-eval")
async def run_eval():
    import subprocess
    import sys
    script_path = os.path.join(os.path.dirname(__file__), "../../scripts/bubble_eval_runner.py")
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    if result.returncode == 0:
        return {"success": True, "message": "评测完成"}
    return {"success": False, "message": "评测失败", "error": result.stderr}

def main():
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()