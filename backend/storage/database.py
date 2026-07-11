import sqlite3
import os
import json
import threading
from datetime import datetime
from contextlib import contextmanager
from functools import lru_cache

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/bubblemate.db")

class SQLiteConnectionPool:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._connections = {}
                    cls._instance._connection_lock = threading.Lock()
        return cls._instance
    
    def _create_connection(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False,
            isolation_level=None,
            timeout=30
        )
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def get_connection(self):
        thread_id = threading.current_thread().ident
        with self._connection_lock:
            if thread_id not in self._connections:
                self._connections[thread_id] = self._create_connection()
            conn = self._connections[thread_id]
        try:
            yield conn
        finally:
            pass
    
    def close_all(self):
        with self._connection_lock:
            for conn in self._connections.values():
                conn.close()
            self._connections.clear()

connection_pool = SQLiteConnectionPool()

@contextmanager
def get_db_connection():
    with connection_pool.get_connection() as conn:
        yield conn

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        isolation_level=None,
        timeout=30
    )
    conn.row_factory = sqlite3.Row
    return conn


def _connect_pool():
    thread_id = threading.current_thread().ident
    with connection_pool._connection_lock:
        if thread_id not in connection_pool._connections:
            connection_pool._connections[thread_id] = connection_pool._create_connection()
        conn = connection_pool._connections[thread_id]
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
            session_id TEXT,
            complaint_type TEXT,
            description TEXT,
            status TEXT DEFAULT '待处理',
            knowledge_id INTEGER,
            candidate_id INTEGER,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    try:
        c.execute("ALTER TABLE complaints ADD COLUMN session_id TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE complaints ADD COLUMN status TEXT DEFAULT '待处理'")
    except:
        pass
    try:
        c.execute("ALTER TABLE complaints ADD COLUMN resolved_at TIMESTAMP")
    except:
        pass
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
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT,
            node_type TEXT,
            content TEXT,
            parent_id INTEGER,
            level INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES knowledge_graph(id)
        )
    """)
    try:
        c.execute("SELECT COUNT(*) FROM knowledge")
        if c.fetchone()[0] > 0:
            c.execute("""
                INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level, is_active, created_at)
                SELECT content, node_type, content, parent_id, 1, reviewed, created_at FROM knowledge
            """)
            c.execute("DROP TABLE knowledge")
    except:
        pass
    try:
        c.execute("""
            UPDATE knowledge_graph 
            SET node_type = CASE 
                WHEN node_type IN ('solution', 'compensation', 'issue', 'complaint') THEN node_type
                WHEN parent_id IS NULL THEN 'complaint'
                ELSE 'issue'
            END,
            level = CASE
                WHEN parent_id IS NULL THEN 1
                WHEN node_type = 'solution' OR node_type = 'compensation' THEN 3
                ELSE 2
            END
            WHERE node_type NOT IN ('solution', 'compensation', 'issue', 'complaint')
        """)
    except:
        pass
    try:
        c.execute("""
            WITH duplicates AS (
                SELECT id, node_name, ROW_NUMBER() OVER (PARTITION BY node_name, node_type ORDER BY id) as rn
                FROM knowledge_graph
                WHERE node_type = 'complaint' AND parent_id IS NULL
            )
            SELECT id, node_name FROM duplicates WHERE rn > 1
        """)
        duplicates = c.fetchall()
        for dup in duplicates:
            dup_id, node_name = dup[0], dup[1]
            c.execute("SELECT id FROM knowledge_graph WHERE node_name = ? AND node_type = 'complaint' AND parent_id IS NULL AND id != ? ORDER BY id LIMIT 1", (node_name, dup_id))
            keep_id = c.fetchone()
            if keep_id:
                c.execute("UPDATE knowledge_graph SET parent_id = ? WHERE parent_id = ?", (keep_id[0], dup_id))
                c.execute("UPDATE knowledge_graph SET is_active = 0 WHERE id = ?", (dup_id,))
    except:
        pass

    c.execute("CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON complaints(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_complaints_type ON complaints(complaint_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_complaints_created ON complaints(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_parent ON knowledge_graph(parent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_graph(node_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_candidates_status ON knowledge_candidates(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            location TEXT,
            tel TEXT,
            rating TEXT,
            cost TEXT,
            opentime TEXT,
            business_area TEXT,
            tag TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS menu_items (
            id TEXT PRIMARY KEY,
            shop_id TEXT REFERENCES shops(id),
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            available BOOLEAN DEFAULT 1,
            description TEXT,
            sales INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            shop_id TEXT REFERENCES shops(id),
            items TEXT,
            total REAL,
            status TEXT DEFAULT 'pending',
            address TEXT,
            create_time TEXT,
            delivery_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            shop_id TEXT REFERENCES shops(id),
            menu_item_id TEXT REFERENCES menu_items(id),
            quantity INTEGER DEFAULT 0,
            PRIMARY KEY (shop_id, menu_item_id)
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_shops_name ON shops(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_shops_area ON shops(business_area)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_menu_shop ON menu_items(shop_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_menu_name ON menu_items(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_inventory_shop ON inventory(shop_id)")

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
        SELECT id, complaint_type, description, status, created_at
        FROM complaints WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_complaints():
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.user_id, c.session_id, c.complaint_type, c.description, c.status, c.created_at, c.knowledge_id, c.candidate_id, c.resolved_at, u.preferences
        FROM complaints c LEFT JOIN users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_knowledge(complaint_type, solution, compensation):
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, NULL, 1)", (complaint_type, 'complaint', complaint_type))
    parent_id = c.lastrowid
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, ?, 3)", (solution[:50], 'solution', solution, parent_id))
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, ?, 3)", (compensation[:50], 'compensation', compensation, parent_id))
    conn.commit()
    conn.close()

@lru_cache(maxsize=64)
def get_knowledge_list(reviewed_only=False):
    conn = _connect()
    c = conn.cursor()
    if reviewed_only:
        c.execute("SELECT * FROM knowledge_graph WHERE is_active = 1 ORDER BY created_at DESC")
    else:
        c.execute("SELECT * FROM knowledge_graph ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@lru_cache(maxsize=32)
def get_knowledge_graph():
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT * FROM knowledge_graph WHERE is_active = 1 ORDER BY parent_id NULLS FIRST, id")
    raw_rows = c.fetchall()
    rows = [dict(row) for row in raw_rows]
    conn.close()
    
    nodes = {}
    roots = []
    for row in rows:
        node = {"id": row["id"], "node_name": row["node_name"], "node_type": row["node_type"], "content": row["content"], "level": row["level"], "is_active": row["is_active"], "children": []}
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
    level = 1 if parent_id is None else 3 if node_type in ['solution', 'compensation'] else 2
    c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level) VALUES (?, ?, ?, ?, ?)", (content[:50], node_type, content, parent_id, level))
    conn.commit()
    conn.close()
    return c.lastrowid

def review_knowledge(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        WITH RECURSIVE descendants AS (
            SELECT id FROM knowledge_graph WHERE id = ?
            UNION ALL
            SELECT kg.id FROM knowledge_graph kg JOIN descendants d ON kg.parent_id = d.id
        )
        UPDATE knowledge_graph SET is_active = 1 WHERE id IN (SELECT id FROM descendants)
    """, (id,))
    conn.commit()
    conn.close()

def delete_knowledge(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        WITH RECURSIVE descendants AS (
            SELECT id FROM knowledge_graph WHERE id = ?
            UNION ALL
            SELECT kg.id FROM knowledge_graph kg JOIN descendants d ON kg.parent_id = d.id
        )
        UPDATE knowledge_graph SET is_active = 0 WHERE id IN (SELECT id FROM descendants)
    """, (id,))
    conn.commit()
    conn.close()

def update_knowledge_parent(child_id, parent_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE knowledge_graph SET parent_id = ? WHERE id = ?", (parent_id, child_id))
    conn.commit()
    conn.close()

def get_knowledge_graph_aggregated():
    conn = _connect()
    c = conn.cursor()
    
    c.execute("SELECT * FROM knowledge_graph WHERE is_active = 1 ORDER BY id")
    rows = c.fetchall()
    knowledge_list = [dict(row) for row in rows]
    
    c.execute("SELECT * FROM complaints")
    complaint_rows = c.fetchall()
    complaints = [dict(row) for row in complaint_rows]
    
    conn.close()
    
    complaint_types = {}
    issues = {}
    solutions = {}
    compensations = {}
    links = []
    
    node_id_counter = 1
    
    for k in knowledge_list:
        if k['node_type'] == 'complaint':
            ct_key = k['node_name']
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
        elif k['node_type'] == 'issue':
            issue_key = k['node_name']
            if issue_key not in issues:
                issues[issue_key] = {
                    'id': f'issue_{node_id_counter}',
                    'name': k['node_name'],
                    'type': 'issue',
                    'content': k['content'],
                    'original_id': k['id'],
                    'parent_id': k['parent_id'],
                    'children': []
                }
                node_id_counter += 1
        elif k['node_type'] == 'solution':
            sol_key = k['content'][:100]
            if sol_key not in solutions:
                solutions[sol_key] = {
                    'id': f'solution_{node_id_counter}',
                    'name': k['node_name'],
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
                    'name': k['node_name'],
                    'type': 'compensation',
                    'content': k['content'],
                    'original_id': k['id'],
                    'parent_id': k['parent_id']
                }
                node_id_counter += 1
    
    ct_id_map = {}
    for ct_key, ct_node in complaint_types.items():
        ct_id_map[ct_node['original_id']] = ct_node
    
    issue_id_map = {}
    for issue_key, issue_node in issues.items():
        issue_id_map[issue_node['original_id']] = issue_node
    
    for k in knowledge_list:
        if k['node_type'] == 'issue' and k['parent_id'] is not None and k['parent_id'] in ct_id_map:
            ct_node = ct_id_map[k['parent_id']]
            issue_key = k['node_name']
            if issue_key in issues:
                issue_node = issues[issue_key]
                if issue_node['id'] not in [c['id'] for c in ct_node['children']]:
                    ct_node['children'].append(issue_node)
                    links.append({'source': ct_node['id'], 'target': issue_node['id']})
        elif k['node_type'] == 'solution' and k['parent_id'] is not None:
            parent_node = ct_id_map.get(k['parent_id']) or issue_id_map.get(k['parent_id'])
            if parent_node:
                sol_key = k['content'][:100]
                if sol_key in solutions:
                    sol_node = solutions[sol_key]
                    if sol_node['id'] not in [c['id'] for c in parent_node['children']]:
                        parent_node['children'].append(sol_node)
                        links.append({'source': parent_node['id'], 'target': sol_node['id']})
        elif k['node_type'] == 'compensation' and k['parent_id'] is not None:
            parent_node = ct_id_map.get(k['parent_id']) or issue_id_map.get(k['parent_id'])
            if parent_node:
                comp_key = k['content'][:100]
                if comp_key in compensations:
                    comp_node = compensations[comp_key]
                    if comp_node['id'] not in [c['id'] for c in parent_node['children']]:
                        parent_node['children'].append(comp_node)
                        links.append({'source': parent_node['id'], 'target': comp_node['id']})
    
    all_nodes = list(complaint_types.values())
    
    ct_count = len(complaint_types)
    issue_count = len(issues)
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
    c.execute("UPDATE complaints SET status = '已解决', resolved_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
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
        SELECT COUNT(*) FROM complaints WHERE status = '已解决'
    """)
    resolved_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM complaints")
    total_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM knowledge_candidates WHERE status = 'pending'")
    pending_candidates = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM knowledge_graph WHERE is_active = 1")
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
    
    c.execute("""
        SELECT k.id FROM knowledge_graph k 
        WHERE k.node_name = ? AND k.node_type = 'complaint' AND k.is_active = 1
    """, (complaint_type,))
    existing_node = c.fetchone()
    
    solution = f"非常抱歉给您带来不好的体验，关于{complaint_type}问题我们会尽快处理。"
    compensation = "请联系客服处理"
    
    if existing_node:
        c.execute("""
            SELECT content FROM knowledge_graph 
            WHERE parent_id = ? AND node_type = 'solution' AND is_active = 1
        """, (existing_node[0],))
        sol_row = c.fetchone()
        if sol_row:
            solution = sol_row[0]
        
        c.execute("""
            SELECT content FROM knowledge_graph 
            WHERE parent_id = ? AND node_type = 'compensation' AND is_active = 1
        """, (existing_node[0],))
        comp_row = c.fetchone()
        if comp_row:
            compensation = comp_row[0]
    
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
    try:
        conn.execute("BEGIN")
        c.execute("SELECT * FROM knowledge_candidates WHERE id = ?", (candidate_id,))
        candidate = c.fetchone()
        if not candidate:
            conn.execute("ROLLBACK")
            conn.close()
            return False
        
        candidate_dict = dict(candidate)
        complaint_type = candidate_dict["complaint_type"]
        solution = candidate_dict["proposed_solution"]
        compensation = candidate_dict["proposed_compensation"]
        
        c.execute("SELECT id FROM knowledge_graph WHERE node_name = ? AND node_type = 'complaint' AND is_active = 1", (complaint_type,))
        complaint_row = c.fetchone()
        if complaint_row:
            complaint_id = complaint_row[0]
        else:
            c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level, is_active) VALUES (?, ?, ?, NULL, 1, 1)", (complaint_type, 'complaint', complaint_type))
            complaint_id = c.lastrowid
        
        issue_name = complaint_type + "问题"
        c.execute("SELECT id FROM knowledge_graph WHERE node_name = ? AND node_type = 'issue' AND parent_id = ? AND is_active = 1", (issue_name, complaint_id))
        issue_row = c.fetchone()
        if issue_row:
            issue_id = issue_row[0]
        else:
            c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level, is_active) VALUES (?, ?, ?, ?, 2, 1)", (issue_name, 'issue', '用户反馈' + complaint_type + '相关问题', complaint_id))
            issue_id = c.lastrowid
        
        c.execute("SELECT id FROM knowledge_graph WHERE node_name = ? AND node_type = 'solution' AND parent_id = ? AND is_active = 1", (solution[:50], issue_id))
        sol_row = c.fetchone()
        if not sol_row:
            c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level, is_active) VALUES (?, ?, ?, ?, 3, 1)", (solution[:50], 'solution', solution, issue_id))
        
        c.execute("SELECT id FROM knowledge_graph WHERE node_name = ? AND node_type = 'compensation' AND parent_id = ? AND is_active = 1", (compensation[:50], issue_id))
        comp_row = c.fetchone()
        if not comp_row:
            c.execute("INSERT INTO knowledge_graph (node_name, node_type, content, parent_id, level, is_active) VALUES (?, ?, ?, ?, 3, 1)", (compensation[:50], 'compensation', compensation, issue_id))
        
        c.execute("UPDATE knowledge_candidates SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?", (candidate_id,))
        c.execute("UPDATE complaints SET knowledge_id = ?, candidate_id = NULL, status = '已解决', resolved_at = CURRENT_TIMESTAMP WHERE candidate_id = ?", (issue_id, candidate_id))
        
        conn.execute("COMMIT")
        conn.close()
        return True
    except Exception as e:
        conn.execute("ROLLBACK")
        conn.close()
        return False

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