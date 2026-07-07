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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_type TEXT,
            solution TEXT,
            compensation TEXT,
            reviewed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        SELECT c.id, c.user_id, c.complaint_type, c.description, c.resolved, c.created_at, u.preferences
        FROM complaints c LEFT JOIN users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_knowledge(complaint_type, solution, compensation):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO knowledge (complaint_type, solution, compensation)
        VALUES (?, ?, ?)
    """, (complaint_type, solution, compensation))
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

def review_knowledge(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE knowledge SET reviewed = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def delete_knowledge(id):
    conn = _connect()
    c = conn.cursor()
    c.execute("DELETE FROM knowledge WHERE id = ?", (id,))
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
    conn.close()
    return {
        "by_type": type_stats,
        "today_count": today_count,
        "resolved_count": resolved_count,
        "total_count": total_count
    }

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