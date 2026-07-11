import sqlite3
import os
import json
from functools import lru_cache
from .database import _connect, DB_PATH

@lru_cache(maxsize=128)
def get_shops(location=None, business_area=None):
    conn = _connect()
    c = conn.cursor()
    if location:
        c.execute("SELECT * FROM shops WHERE status = 'active' AND (name LIKE ? OR address LIKE ?)", 
                  (f'%{location}%', f'%{location}%'))
    elif business_area:
        c.execute("SELECT * FROM shops WHERE status = 'active' AND business_area = ?", (business_area,))
    else:
        c.execute("SELECT * FROM shops WHERE status = 'active'")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@lru_cache(maxsize=256)
def get_shop_by_name(name):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT * FROM shops WHERE name = ? AND status = 'active'", (name,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

@lru_cache(maxsize=128)
def get_menu_items(shop_id=None, keyword=None, category=None):
    conn = _connect()
    c = conn.cursor()
    query = "SELECT * FROM menu_items WHERE available = 1"
    params = []
    if shop_id:
        query += " AND shop_id = ?"
        params.append(shop_id)
    if keyword:
        query += " AND name LIKE ?"
        params.append(f'%{keyword}%')
    if category:
        query += " AND category = ?"
        params.append(category)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@lru_cache(maxsize=32)
def get_hot_menu_items(limit=5):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT * FROM menu_items WHERE available = 1 ORDER BY sales DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_orders(user_id=None, order_id=None):
    conn = _connect()
    c = conn.cursor()
    if order_id:
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        rows = c.fetchall()
    elif user_id:
        c.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY create_time DESC", (user_id,))
        rows = c.fetchall()
    else:
        c.execute("SELECT * FROM orders ORDER BY create_time DESC")
        rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        order = dict(row)
        try:
            order['items'] = json.loads(order['items']) if order['items'] else []
        except:
            order['items'] = []
        result.append(order)
    return result

def get_inventory(shop_id=None, menu_item_id=None):
    conn = _connect()
    c = conn.cursor()
    if shop_id and menu_item_id:
        c.execute("SELECT * FROM inventory WHERE shop_id = ? AND menu_item_id = ?", (shop_id, menu_item_id))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    elif shop_id:
        c.execute("SELECT i.*, m.name as item_name FROM inventory i JOIN menu_items m ON i.menu_item_id = m.id WHERE i.shop_id = ?", (shop_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    conn.close()
    return []

def add_shop(shop_id, name, address=None, location=None, tel=None, rating=None, cost=None, opentime=None, business_area=None, tag=None):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO shops (id, name, address, location, tel, rating, cost, opentime, business_area, tag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shop_id, name, address, location, tel, rating, cost, opentime, business_area, tag))
    conn.commit()
    conn.close()

def add_menu_item(item_id, shop_id, name, category=None, price=None, available=True, description=None, sales=0):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO menu_items (id, shop_id, name, category, price, available, description, sales)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_id, shop_id, name, category, price, available, description, sales))
    conn.commit()
    conn.close()

def add_order(order_id, user_id, shop_id, items, total, status='pending', address=None, create_time=None, delivery_time=None):
    conn = _connect()
    c = conn.cursor()
    items_json = json.dumps(items) if isinstance(items, list) else items
    c.execute("""
        INSERT OR IGNORE INTO orders (id, user_id, shop_id, items, total, status, address, create_time, delivery_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, user_id, shop_id, items_json, total, status, address, create_time, delivery_time))
    conn.commit()
    conn.close()

def add_inventory(shop_id, menu_item_id, quantity=0):
    conn = _connect()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO inventory (shop_id, menu_item_id, quantity)
        VALUES (?, ?, ?)
    """, (shop_id, menu_item_id, quantity))
    conn.commit()
    conn.close()

def get_all_stores():
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT id, name, address, location FROM shops WHERE status = 'active'")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]