import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/bubblemate.db")

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            preferences TEXT DEFAULT '{}',
            complaint_history TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            message_id TEXT,
            feedback_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            complaint_type TEXT,
            description TEXT,
            resolved BOOLEAN DEFAULT 0,
            knowledge_id INTEGER,
            candidate_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    try:
        c.execute("ALTER TABLE complaints ADD COLUMN knowledge_id INTEGER")
    except:
        pass
    try:
        c.execute("ALTER TABLE complaints ADD COLUMN candidate_id INTEGER")
    except:
        pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            complaint_type TEXT,
            proposed_solution TEXT,
            proposed_compensation TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_type TEXT,
            content TEXT,
            parent_id INTEGER,
            reviewed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES knowledge(id)
        )
    """)
    conn.commit()
    conn.close()

def _upsert_user(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def save_user_preference(user_id, key, value):
    _upsert_user(user_id)
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT preferences FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    prefs = json.loads(row["preferences"]) if row else {}
    prefs[key] = value
    c.execute("UPDATE users SET preferences = ? WHERE user_id = ?", (json.dumps(prefs), user_id))
    conn.commit()
    conn.close()

def get_user_preferences(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT preferences FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row["preferences"]) if row else {}

def save_complaint(user_id, complaint_data):
    _upsert_user(user_id)
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT complaint_history FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    history = json.loads(row["complaint_history"]) if row else []
    history.append(complaint_data)
    c.execute("UPDATE users SET complaint_history = ? WHERE user_id = ?", (json.dumps(history), user_id))
    conn.commit()
    conn.close()

def get_complaint_history(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT complaint_history FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row["complaint_history"]) if row else []

def save_complaint_db(user_id, complaint_type, description):
    _upsert_user(user_id)
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO complaints (user_id, complaint_type, description)
        VALUES (?, ?, ?)
    """, (user_id, complaint_type, description))
    conn.commit()
    conn.close()

def get_complaints(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        SELECT id, complaint_type, description, resolved, created_at
        FROM complaints WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_complaints():
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.user_id, c.complaint_type, c.description, c.resolved, c.created_at, c.knowledge_id, c.candidate_id, u.preferences
        FROM complaints c LEFT JOIN users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_knowledge(complaint_type, solution, compensation):
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT INTO knowledge (node_type, content, parent_id) VALUES (?, ?, NULL)", (complaint_type, complaint_type))
    parent_id = c.lastrowid
    c.execute("INSERT INTO knowledge (node_type, content, parent_id) VALUES ('solution', ?, ?)", (solution, parent_id))
    c.execute("INSERT INTO knowledge (node_type, content, parent_id) VALUES ('compensation', ?, ?)", (compensation, parent_id))
    conn.commit()
    conn.close()

def get_knowledge_list(reviewed_only=False):
    conn = _connect()
    c = conn.cursor()
    if reviewed_only:
        c.execute("SELECT * FROM knowledge WHERE reviewed = 1 ORDER BY created_at DESC")
    else:
        c.execute("SELECT * FROM knowledge ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_knowledge_graph():
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT * FROM knowledge ORDER BY parent_id NULLS FIRST, id")
    raw_rows = c.fetchall()
    rows = [dict(row) for row in raw_rows]
    conn.close()
    
    nodes = {}
    roots = []
    for row in rows:
        node = {"id": row["id"], "node_type": row["node_type"], "content": row["content"], "reviewed": row["reviewed"], "children": []}
        nodes[row["id"]] = node
        if row["parent_id"] is None:
            roots.append(node)
        else:
            if row["parent_id"] in nodes:
                nodes[row["parent_id"]]["children"].append(node)
    return roots

def add_knowledge_node(node_type, content, parent_id=None):
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT INTO knowledge (node_type, content, parent_id) VALUES (?, ?, ?)", (node_type, content, parent_id))
    conn.commit()
    conn.close()
    return c.lastrowid

def review_knowledge(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE knowledge SET reviewed = 1 WHERE id = ? OR parent_id = ?", (id, id))
    conn.commit()
    conn.close()

def delete_knowledge(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("DELETE FROM knowledge WHERE id = ? OR parent_id = ?", (id, id))
    conn.commit()
    conn.close()

def update_knowledge_parent(child_id, parent_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE knowledge SET parent_id = ? WHERE id = ?", (parent_id, child_id))
    conn.commit()
    conn.close()

def get_knowledge_graph_aggregated():
    conn = _connect()
    c = conn.cursor()
    
    c.execute("SELECT * FROM knowledge WHERE reviewed = 1 ORDER BY id")
    rows = c.fetchall()
    knowledge_list = [dict(row) for row in rows]
    
    c.execute("SELECT * FROM complaints")
    complaint_rows = c.fetchall()
    complaints = [dict(row) for row in complaint_rows]
    
    conn.close()
    
    complaint_types = {}
    solutions = {}
    compensations = {}
    links = []
    
    node_id_counter = 1
    
    for k in knowledge_list:
        if k['node_type'] not in ('solution', 'compensation'):
            ct_key = k['node_type']
            if ct_key not in complaint_types:
                ct_count = sum(1 for c in complaints if c['complaint_type'] == ct_key)
                complaint_types[ct_key] = {
                    'id': f'complaint_{node_id_counter}',
                    'name': ct_key,
                    'type': 'complaint',
                    'content': k['content'],
                    'original_id': k['id'],
                    'complaint_count': ct_count,
                    'children': []
                }
                node_id_counter += 1
        elif k['node_type'] == 'solution':
            sol_key = k['content'][:100]
            if sol_key not in solutions:
                solutions[sol_key] = {
                    'id': f'solution_{node_id_counter}',
                    'name': k['content'][:30] + '...' if len(k['content']) > 30 else k['content'],
                    'type': 'solution',
                    'content': k['content'],
                    'original_id': k['id'],
                    'parent_id': k['parent_id']
                }
                node_id_counter += 1
        elif k['node_type'] == 'compensation':
            comp_key = k['content'][:100]
            if comp_key not in compensations:
                compensations[comp_key] = {
                    'id': f'compensation_{node_id_counter}',
                    'name': k['content'][:30] + '...' if len(k['content']) > 30 else k['content'],
                    'type': 'compensation',
                    'content': k['content'],
                    'original_id': k['id'],
                    'parent_id': k['parent_id']
                }
                node_id_counter += 1
    
    ct_id_map = {}
    for ct_key, ct_node in complaint_types.items():
        ct_id_map[ct_node['original_id']] = ct_node
    
    for k in knowledge_list:
        if k['node_type'] not in ('solution', 'compensation'):
            continue
        if k['parent_id'] is not None and k['parent_id'] in ct_id_map:
            ct_node = ct_id_map[k['parent_id']]
            if k['node_type'] == 'solution':
                sol_key = k['content'][:100]
                if sol_key in solutions:
                    sol_node = solutions[sol_key]
                    if sol_node['id'] not in [c['id'] for c in ct_node['children']]:
                        ct_node['children'].append(sol_node)
                        links.append({'source': ct_node['id'], 'target': sol_node['id']})
            elif k['node_type'] == 'compensation':
                comp_key = k['content'][:100]
                if comp_key in compensations:
                    comp_node = compensations[comp_key]
                    if comp_node['id'] not in [c['id'] for c in ct_node['children']]:
                        ct_node['children'].append(comp_node)
                        links.append({'source': ct_node['id'], 'target': comp_node['id']})
    
    all_nodes = list(complaint_types.values())
    
    ct_count = len(complaint_types)
    issue_count = 0
    sol_count = len(solutions)
    comp_count = len(compensations)
    
    return {
        'nodes': all_nodes,
        'links': links,
        'statistics': {
            'total_complaint_types': ct_count,
            'total_issues': issue_count,
            'total_solutions': sol_count,
            'total_compensations': comp_count
        }
    }

def resolve_complaint(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE complaints SET resolved = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def get_complaint_stats():
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        SELECT complaint_type, COUNT(*) as count
        FROM complaints GROUP BY complaint_type ORDER BY count DESC
    """)
    rows = c.fetchall()
    type_stats = [dict(row) for row in rows]
    c.execute("""
        SELECT COUNT(*) FROM complaints WHERE DATE(created_at) = DATE('now')
    """)
    today_count = c.fetchone()[0]
    c.execute("""
        SELECT COUNT(*) FROM complaints WHERE resolved = 1
    """)
    resolved_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM complaints")
    total_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM knowledge_candidates WHERE status = 'pending'")
    pending_candidates = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM knowledge WHERE reviewed = 1")
    reviewed_knowledge = c.fetchone()[0]
    conn.close()
    return {
        "by_type": type_stats,
        "today_count": today_count,
        "resolved_count": resolved_count,
        "total_count": total_count,
        "pending_candidates": pending_candidates,
        "reviewed_knowledge": reviewed_knowledge
    }

def save_complaint_with_candidate(user_id, complaint_type, description):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO complaints (user_id, complaint_type, description)
        VALUES (?, ?, ?)
    """, (user_id, complaint_type, description))
    complaint_id = c.lastrowid
    
    solution_templates = {
        "口味": "非常抱歉您对口味不满意，我们会尽快为您处理。",
        "份量": "非常抱歉份量不足，我们会为您补发或补偿。",
        "服务": "非常抱歉服务态度不佳，我们已通知门店整改。",
        "配送": "非常抱歉配送超时，我们会申请超时赔付。",
        "价格": "非常抱歉价格问题，核实后提供优惠券补偿。",
        "退款": "非常抱歉，我们会为您办理退款。",
        "讽刺": "非常抱歉给您带来不好的体验，请问具体是什么问题？",
        "配件": "非常抱歉配件缺失，我们会为您补发。",
    }
    compensation_templates = {
        "口味": "免费重做或退款",
        "份量": "补发配料或5元优惠券",
        "服务": "赠送饮品券",
        "配送": "超时赔付或免单",
        "价格": "优惠券补偿",
        "退款": "全额退款",
        "讽刺": "请告知具体问题",
        "配件": "补发配件",
    }
    
    solution = solution_templates.get(complaint_type, f"非常抱歉给您带来不好的体验，关于{complaint_type}问题我们会尽快处理。")
    compensation = compensation_templates.get(complaint_type, "请联系客服处理")
    
    c.execute("""
        INSERT INTO knowledge_candidates (complaint_id, complaint_type, proposed_solution, proposed_compensation)
        VALUES (?, ?, ?, ?)
    """, (complaint_id, complaint_type, solution, compensation))
    candidate_id = c.lastrowid
    
    c.execute("UPDATE complaints SET candidate_id = ? WHERE id = ?", (candidate_id, complaint_id))
    conn.commit()
    conn.close()
    return complaint_id, candidate_id

def get_knowledge_candidates(status=None):
    conn = _connect()
    c = conn.cursor()
    if status:
        c.execute("""
            SELECT kc.*, c.description as complaint_description, c.user_id
            FROM knowledge_candidates kc LEFT JOIN complaints c ON kc.complaint_id = c.id
            WHERE kc.status = ? ORDER BY kc.created_at DESC
        """, (status,))
    else:
        c.execute("""
            SELECT kc.*, c.description as complaint_description, c.user_id
            FROM knowledge_candidates kc LEFT JOIN complaints c ON kc.complaint_id = c.id
            ORDER BY kc.created_at DESC
        """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def approve_candidate(candidate_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT * FROM knowledge_candidates WHERE id = ?", (candidate_id,))
    candidate = c.fetchone()
    if not candidate:
        conn.close()
        return False
    
    candidate_dict = dict(candidate)
    complaint_type = candidate_dict["complaint_type"]
    solution = candidate_dict["proposed_solution"]
    compensation = candidate_dict["proposed_compensation"]
    
    c.execute("INSERT INTO knowledge (node_type, content, parent_id, reviewed) VALUES (?, ?, NULL, 1)", (complaint_type, complaint_type))
    parent_id = c.lastrowid
    c.execute("INSERT INTO knowledge (node_type, content, parent_id, reviewed) VALUES ('solution', ?, ?, 1)", (solution, parent_id))
    c.execute("INSERT INTO knowledge (node_type, content, parent_id, reviewed) VALUES ('compensation', ?, ?, 1)", (compensation, parent_id))
    
    c.execute("UPDATE knowledge_candidates SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?", (candidate_id,))
    c.execute("UPDATE complaints SET knowledge_id = ?, candidate_id = NULL WHERE candidate_id = ?", (parent_id, candidate_id))
    
    conn.commit()
    conn.close()
    return True

def reject_candidate(candidate_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE knowledge_candidates SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?", (candidate_id,))
    c.execute("UPDATE complaints SET candidate_id = NULL WHERE candidate_id = ?", (candidate_id,))
    conn.commit()
    conn.close()
    return True

def get_complaint_knowledge(complaint_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        SELECT c.knowledge_id, k.node_type, k.content, k.parent_id, k.reviewed
        FROM complaints c LEFT JOIN knowledge k ON c.knowledge_id = k.id
        WHERE c.id = ?
    """, (complaint_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_knowledge_complaints(knowledge_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.complaint_type, c.description, c.resolved, c.created_at
        FROM complaints c WHERE c.knowledge_id = ? ORDER BY c.created_at DESC
    """, (knowledge_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_session(session_id, user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO sessions (session_id, user_id, last_active)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (session_id, user_id))
    conn.commit()
    conn.close()

def get_user_by_session(session_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    return row["user_id"] if row else None

def save_feedback(user_id, message_id, feedback_type):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO feedback (user_id, message_id, feedback_type)
        VALUES (?, ?, ?)
    """, (user_id, message_id, feedback_type))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT complaint_history FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    history = json.loads(row["complaint_history"]) if row else []
    c.execute("SELECT COUNT(*) FROM feedback WHERE user_id = ?", (user_id,))
    feedback_count = c.fetchone()[0]
    conn.close()
    return {
        "total_complaints": len(history),
        "total_feedback": feedback_count,
        "preferences_count": len(get_user_preferences(user_id))
    }

init_db()