"""
BubbleMate Three-Layer Memory - 三层记忆系统
Hot Layer: Redis - 短期会话窗口（最近5轮）
Warm Layer: MySQL - 长期用户画像（用户偏好、投诉历史）
Cold Layer: ChromaDB - 语义检索知识库（菜单、门店、常见问题）
"""

import json
import time
import os
from typing import List, Dict, Optional, Any
from collections import deque


class ThreeLayerMemory:
    """三层记忆系统 - Hot/Warm/Cold架构"""

    def __init__(self, window_size: int = 5, session_timeout: int = 3600):
        self.window_size = window_size
        self.session_timeout = session_timeout

        self._init_hot_layer()
        self._init_warm_layer()
        self._init_cold_layer()

    def _init_hot_layer(self):
        """初始化Hot层 - Redis短期会话窗口"""
        self.hot_client = None
        self.local_hot_store: Dict[str, deque] = {}
        self.local_full_history: Dict[str, List] = {}
        self.session_timestamps: Dict[str, float] = {}

        try:
            import redis
            from redis import ConnectionPool

            pool = ConnectionPool(
                host='localhost',
                port=6379,
                decode_responses=True,
                max_connections=10,
                socket_timeout=2,
                socket_connect_timeout=1,
                protocol=3
            )
            self.hot_client = redis.Redis(connection_pool=pool)

            try:
                self.hot_client.ping()
                print("Hot Layer: Redis连接成功")
            except Exception as ping_e:
                print(f"Hot Layer: Redis ping失败 ({ping_e})，使用本地存储")
                self.hot_client = None
        except ImportError:
            print("Hot Layer: Redis未安装，使用本地存储")
        except Exception as e:
            print(f"Hot Layer: Redis连接失败 ({e})，使用本地存储")

    def _init_warm_layer(self):
        """初始化Warm层 - MySQL长期用户画像"""
        self.warm_client = None
        self.local_user_profiles: Dict[str, Dict] = {}
        self._create_tables()

        try:
            import pymysql

            self.warm_client = pymysql.connect(
                host='localhost',
                user='root',
                password='',
                database='bubblemate',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5
            )
            print("Warm Layer: MySQL连接成功")
        except ImportError:
            print("Warm Layer: pymysql未安装，使用本地存储")
        except Exception as e:
            print(f"Warm Layer: MySQL连接失败 ({e})，使用本地存储")

    def _create_tables(self):
        """创建MySQL表结构（如果不存在）"""
        if not self.warm_client:
            return

        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id VARCHAR(64) PRIMARY KEY,
            sugar_level VARCHAR(20),
            ice_level VARCHAR(20),
            favorite_drinks JSON,
            complaint_history JSON,
            allergens JSON,
            price_sensitivity VARCHAR(20),
            last_order_id VARCHAR(32),
            preferred_store VARCHAR(64),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS session_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(64),
            user_id VARCHAR(64),
            user_message TEXT,
            agent_message TEXT,
            intent VARCHAR(64),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_session (session_id),
            INDEX idx_user (user_id),
            INDEX idx_time (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS complaint_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            complaint_id VARCHAR(32) UNIQUE,
            user_id VARCHAR(64),
            order_id VARCHAR(32),
            complaint_type VARCHAR(20),
            description TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME NULL,
            INDEX idx_user (user_id),
            INDEX idx_type (complaint_type),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        try:
            with self.warm_client.cursor() as cursor:
                for sql in create_tables_sql.split(';'):
                    sql = sql.strip()
                    if sql:
                        cursor.execute(sql)
            self.warm_client.commit()
            print("Warm Layer: 表结构创建完成")
        except Exception as e:
            print(f"Warm Layer: 创建表失败 ({e})")

    def _init_cold_layer(self):
        """初始化Cold层 - ChromaDB语义检索知识库"""
        self.cold_client = None
        self.cold_collection = None

        try:
            import chromadb

            persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chromadb")
            os.makedirs(persist_dir, exist_ok=True)

            self.cold_client = chromadb.PersistentClient(path=persist_dir)
            self.cold_collection = self.cold_client.get_or_create_collection(name="bubblemate_knowledge")

            self._init_knowledge_base()
            print("Cold Layer: ChromaDB初始化成功")
        except ImportError:
            print("Cold Layer: chromadb未安装，跳过")
        except Exception as e:
            print(f"Cold Layer: ChromaDB初始化失败 ({e})")

    def _init_knowledge_base(self):
        """初始化知识库（菜单、门店、常见问题）"""
        if not self.cold_collection:
            return

        existing_count = self.cold_collection.count()
        if existing_count > 0:
            print(f"Cold Layer: 知识库已有{existing_count}条记录，跳过初始化")
            return

        menu_docs = [
            {"id": "menu_1", "content": "芝芝莓莓：鲜草莓搭配芝士奶盖，价格20元，推荐甜度：三分糖", "category": "menu"},
            {"id": "menu_2", "content": "杨枝甘露：椰奶芒果西柚，价格18元，推荐甜度：五分糖", "category": "menu"},
            {"id": "menu_3", "content": "珍珠奶茶：经典珍珠奶茶，价格12元，推荐甜度：正常糖", "category": "menu"},
            {"id": "menu_4", "content": "茉莉绿茶：零糖低卡，价格15元，适合减肥人群", "category": "menu"},
            {"id": "menu_5", "content": "柠檬茶：清爽柠檬，价格10元，推荐去冰", "category": "menu"},
        ]

        store_docs = [
            {"id": "store_1", "content": "武汉大学梅园店：地址在武汉大学梅园食堂旁，营业时间10:00-22:00", "category": "store"},
            {"id": "store_2", "content": "银泰创意城店：地址在街道口银泰创意城负一楼，营业时间10:00-21:30", "category": "store"},
            {"id": "store_3", "content": "街道口店：地址在街道口地铁站B出口旁，营业时间09:30-22:30", "category": "store"},
        ]

        faq_docs = [
            {"id": "faq_1", "content": "甜度选择：提供无糖、三分糖、五分糖、七分糖、正常糖五种选择", "category": "faq"},
            {"id": "faq_2", "content": "温度选择：提供热、温、冰三种温度", "category": "faq"},
            {"id": "faq_3", "content": "外卖配送：支持美团、饿了么、小程序下单，满20元免配送费", "category": "faq"},
            {"id": "faq_4", "content": "会员卡：小程序免费办理，首单立减5元，消费积分可兑换饮品", "category": "faq"},
            {"id": "faq_5", "content": "投诉处理：提供24小时客服热线，投诉后24小时内处理完成", "category": "faq"},
        ]

        all_docs = menu_docs + store_docs + faq_docs

        self.cold_collection.add(
            ids=[doc["id"] for doc in all_docs],
            documents=[doc["content"] for doc in all_docs],
            metadatas=[{"category": doc["category"]} for doc in all_docs]
        )

        print(f"Cold Layer: 知识库初始化完成，共{len(all_docs)}条记录")

    def save_message(self, session_id: str, user_id: str, user_message: str, agent_message: str, intent: str = ""):
        """保存消息到三层记忆"""
        timestamp = time.time()
        self.session_timestamps[session_id] = timestamp

        message_pair = {
            "user": user_message,
            "agent": agent_message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "epoch": timestamp,
            "intent": intent
        }

        self._save_to_hot(session_id, message_pair)
        self._save_to_warm(session_id, user_id, user_message, agent_message, intent)

    def _save_to_hot(self, session_id: str, message_pair: Dict):
        """保存到Hot层（Redis/本地）"""
        if self.hot_client:
            try:
                key = f"session:{session_id}"
                self.hot_client.rpush(key, json.dumps(message_pair))
                self.hot_client.expire(key, self.session_timeout)

                length = self.hot_client.llen(key)
                if length > self.window_size:
                    old_messages = [json.loads(self.hot_client.lindex(key, i))
                                   for i in range(length - self.window_size)]
                    summary = self._summarize_messages(old_messages)

                    for _ in range(length - self.window_size):
                        self.hot_client.lpop(key)

                    summary_key = f"session:{session_id}:summary"
                    self.hot_client.set(summary_key, summary)
                    self.hot_client.expire(summary_key, self.session_timeout)

            except Exception as e:
                print(f"Hot Layer保存失败: {e}")
        else:
            if session_id not in self.local_hot_store:
                self.local_hot_store[session_id] = deque(maxlen=self.window_size)
                self.local_full_history[session_id] = []

            self.local_hot_store[session_id].append(message_pair)
            self.local_full_history[session_id].append(message_pair)

            if len(self.local_full_history[session_id]) > self.window_size:
                old_messages = self.local_full_history[session_id][:len(self.local_full_history[session_id]) - self.window_size]
                summary = self._summarize_messages(old_messages)
                self.local_full_history[session_id] = [{"summary": summary}] + \
                    self.local_full_history[session_id][-self.window_size:]

    def _save_to_warm(self, session_id: str, user_id: str, user_message: str, agent_message: str, intent: str):
        """保存到Warm层（MySQL/本地）"""
        if self.warm_client:
            try:
                with self.warm_client.cursor() as cursor:
                    sql = """
                    INSERT INTO session_history (session_id, user_id, user_message, agent_message, intent)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (session_id, user_id, user_message, agent_message, intent))
                self.warm_client.commit()

                self._extract_and_save_profile(user_id, user_message)

            except Exception as e:
                print(f"Warm Layer保存失败: {e}")
        else:
            if user_id not in self.local_user_profiles:
                self.local_user_profiles[user_id] = {}

    def _extract_and_save_profile(self, user_id: str, user_message: str):
        """从对话中提取用户偏好并保存到Warm层"""
        if not self.warm_client:
            return

        profile = self._get_user_profile_from_warm(user_id)

        sugar_map = {
            "无糖": "无糖", "零糖": "无糖",
            "三分糖": "三分糖",
            "五分糖": "五分糖",
            "少糖": "三分糖",
            "正常糖": "正常糖",
            "七分糖": "七分糖",
            "多糖": "正常糖"
        }

        ice_map = {
            "去冰": "去冰",
            "少冰": "少冰",
            "正常冰": "正常冰",
            "热饮": "热",
            "热的": "热",
            "温的": "温"
        }

        for keyword, value in sugar_map.items():
            if keyword in user_message:
                profile["sugar_level"] = value
                break

        for keyword, value in ice_map.items():
            if keyword in user_message:
                profile["ice_level"] = value
                break

        drink_keywords = ["芝芝莓莓", "杨枝甘露", "珍珠奶茶", "茉莉绿茶",
                          "柠檬茶", "葡萄冰茶", "芝芝芒果", "糯米奶茶"]
        for kw in drink_keywords:
            if kw in user_message:
                favorite_drinks = json.loads(profile.get("favorite_drinks", "[]"))
                if kw not in favorite_drinks:
                    favorite_drinks.append(kw)
                    profile["favorite_drinks"] = json.dumps(favorite_drinks)
                break

        order_match = re.search(r"(\d{5,})", user_message)
        if order_match:
            profile["last_order_id"] = order_match.group(1)

        try:
            with self.warm_client.cursor() as cursor:
                sql = """
                INSERT INTO user_profiles (user_id, sugar_level, ice_level, favorite_drinks, last_order_id)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    sugar_level = COALESCE(VALUES(sugar_level), sugar_level),
                    ice_level = COALESCE(VALUES(ice_level), ice_level),
                    favorite_drinks = COALESCE(VALUES(favorite_drinks), favorite_drinks),
                    last_order_id = COALESCE(VALUES(last_order_id), last_order_id),
                    updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (
                    user_id,
                    profile.get("sugar_level"),
                    profile.get("ice_level"),
                    profile.get("favorite_drinks"),
                    profile.get("last_order_id")
                ))
            self.warm_client.commit()
        except Exception as e:
            print(f"Warm Layer保存偏好失败: {e}")

    def _get_user_profile_from_warm(self, user_id: str) -> Dict:
        """从Warm层获取用户画像"""
        if self.warm_client:
            try:
                with self.warm_client.cursor() as cursor:
                    sql = "SELECT * FROM user_profiles WHERE user_id = %s"
                    cursor.execute(sql, (user_id,))
                    result = cursor.fetchone()
                    return result if result else {}
            except Exception as e:
                print(f"Warm Layer读取失败: {e}")
                return {}
        return self.local_user_profiles.get(user_id, {})

    def get_context(self, session_id: str, user_id: str = "") -> str:
        """获取完整上下文（三层融合）"""
        context_parts = []

        user_profile = self.get_user_profile(user_id)
        if user_profile:
            pref_items = []
            if user_profile.get("sugar_level"):
                pref_items.append(f"甜度偏好: {user_profile['sugar_level']}")
            if user_profile.get("ice_level"):
                pref_items.append(f"冰量偏好: {user_profile['ice_level']}")
            if user_profile.get("favorite_drinks"):
                pref_items.append(f"喜欢的饮品: {user_profile['favorite_drinks']}")
            if pref_items:
                context_parts.append(f"[用户偏好] {', '.join(pref_items)}")

        if self.hot_client:
            try:
                key = f"session:{session_id}"
                messages = self.hot_client.lrange(key, 0, -1)
                summary = self.hot_client.get(f"session:{session_id}:summary")

                if summary:
                    context_parts.append(f"[历史摘要] {summary}")

                for msg_json in messages:
                    msg = json.loads(msg_json)
                    context_parts.append(f"用户: {msg['user']}")
                    context_parts.append(f"客服: {msg['agent']}")

            except Exception as e:
                print(f"Hot Layer读取失败: {e}")
        else:
            if session_id in self.local_full_history:
                first_item = self.local_full_history[session_id][0]
                if "summary" in first_item:
                    context_parts.append(f"[历史摘要] {first_item['summary']}")

            if session_id in self.local_hot_store:
                for msg in self.local_hot_store[session_id]:
                    context_parts.append(f"用户: {msg['user']}")
                    context_parts.append(f"客服: {msg['agent']}")

        return "\n".join(context_parts)

    def get_user_profile(self, user_id: str) -> Dict:
        """获取用户完整画像"""
        profile = self._get_user_profile_from_warm(user_id)

        if self.warm_client:
            try:
                with self.warm_client.cursor() as cursor:
                    sql = "SELECT COUNT(*) as complaint_count FROM complaint_records WHERE user_id = %s"
                    cursor.execute(sql, (user_id,))
                    result = cursor.fetchone()
                    if result:
                        profile["complaint_count"] = result["complaint_count"]
            except Exception as e:
                print(f"Warm Layer读取投诉统计失败: {e}")

        return profile

    def search_knowledge(self, query: str, top_k: int = 3) -> List[Dict]:
        """从Cold层检索知识库"""
        if not self.cold_collection:
            return []

        try:
            results = self.cold_collection.query(
                query_texts=[query],
                n_results=top_k
            )

            matches = []
            for i in range(len(results['ids'][0])):
                matches.append({
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "score": results['distances'][0][i],
                    "category": results['metadatas'][0][i].get('category', '')
                })

            return matches
        except Exception as e:
            print(f"Cold Layer检索失败: {e}")
            return []

    def add_knowledge(self, content: str, category: str = "faq"):
        """向Cold层添加知识"""
        if not self.cold_collection:
            return

        try:
            doc_id = f"{category}_{int(time.time())}"
            self.cold_collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[{"category": category}]
            )
            print(f"Cold Layer: 新增知识 {doc_id}")
        except Exception as e:
            print(f"Cold Layer添加失败: {e}")

    def save_complaint(self, user_id: str, order_id: str, complaint_type: str, description: str):
        """保存投诉记录到Warm层"""
        if self.warm_client:
            try:
                complaint_id = f"CP-{int(time.time())}"
                with self.warm_client.cursor() as cursor:
                    sql = """
                    INSERT INTO complaint_records (complaint_id, user_id, order_id, complaint_type, description)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (complaint_id, user_id, order_id, complaint_type, description))
                self.warm_client.commit()
                return complaint_id
            except Exception as e:
                print(f"Warm Layer保存投诉失败: {e}")
                return None
        return None

    def _summarize_messages(self, messages: List[Dict]) -> str:
        """生成历史摘要"""
        topics = []
        order_ids = []
        complaints = []

        for msg in messages:
            user_msg = msg.get("user", "")
            intent = msg.get("intent", "")

            if intent.startswith("complaint"):
                complaints.append(intent.replace("complaint_", ""))
            elif intent.startswith("query_order"):
                topics.append("订单查询")
                import re
                order_match = re.search(r"(\d{5,})", user_msg)
                if order_match:
                    order_ids.append(order_match.group(1))
            elif intent.startswith("query_menu") or intent.startswith("query_recommend"):
                topics.append("菜单咨询")
            elif intent.startswith("query_location"):
                topics.append("门店查询")
            elif intent.startswith("query_refund"):
                topics.append("退款咨询")

        summary_parts = []
        if complaints:
            summary_parts.append(f"投诉({len(complaints)}次)")
        if topics:
            summary_parts.append(f"咨询: {', '.join(set(topics))}")
        if order_ids:
            summary_parts.append(f"订单: {', '.join(order_ids)}")

        return " | ".join(summary_parts) if summary_parts else f"{len(messages)}轮对话"

    def clear_session(self, session_id: str):
        """清除会话"""
        if self.hot_client:
            try:
                keys = [f"session:{session_id}", f"session:{session_id}:summary"]
                self.hot_client.delete(*keys)
            except Exception as e:
                print(f"Hot Layer清除失败: {e}")

        self.local_hot_store.pop(session_id, None)
        self.local_full_history.pop(session_id, None)
        self.session_timestamps.pop(session_id, None)

    def clear_expired_sessions(self) -> int:
        """清理过期会话"""
        now = time.time()
        expired_count = 0

        expired_sessions = [sid for sid, ts in self.session_timestamps.items()
                           if now - ts > self.session_timeout]

        for sid in expired_sessions:
            self.clear_session(sid)
            expired_count += 1

        return expired_count

    def get_global_stats(self) -> Dict:
        """获取全局统计"""
        hot_count = len(self.local_hot_store) if not self.hot_client else 0

        if self.hot_client:
            try:
                keys = self.hot_client.keys("session:*")
                hot_count = len(set(k.split(":")[1] for k in keys if ":" in k))
            except Exception as e:
                print(f"Hot Layer统计失败: {e}")

        cold_count = self.cold_collection.count() if self.cold_collection else 0

        warm_count = 0
        if self.warm_client:
            try:
                with self.warm_client.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as count FROM user_profiles")
                    result = cursor.fetchone()
                    warm_count = result["count"] if result else 0
            except Exception as e:
                print(f"Warm Layer统计失败: {e}")

        return {
            "hot_layer_sessions": hot_count,
            "warm_layer_users": warm_count,
            "cold_layer_knowledge": cold_count,
            "window_size": self.window_size,
            "session_timeout": self.session_timeout,
            "hot_connected": self.hot_client is not None,
            "warm_connected": self.warm_client is not None,
            "cold_connected": self.cold_client is not None
        }


import re


def test_three_layer_memory():
    """测试三层记忆系统"""
    memory = ThreeLayerMemory(window_size=5, session_timeout=3600)

    session_id = "test_three_layer"
    user_id = "user_001"

    print("\n" + "=" * 60)
    print("三层记忆系统测试")
    print("=" * 60)

    test_messages = [
        ("给我推荐一款无糖的饮品", "推荐茉莉绿茶，零糖低卡...", "query_recommend"),
        ("太甜了，喝不下去，我要投诉", "抱歉，已记录投诉...", "complaint_taste"),
        ("订单12345什么时候能送到？", "订单配送中，预计15分钟...", "query_order"),
        ("附近有门店吗？", "附近有武汉大学梅园店...", "query_location"),
        ("少冰的珍珠奶茶多少钱？", "珍珠奶茶12元，少冰免费...", "query_price"),
        ("下次帮我记住少糖去冰", "已记录您的偏好：少糖去冰...", "general"),
    ]

    for user_msg, agent_msg, intent in test_messages:
        memory.save_message(session_id, user_id, user_msg, agent_msg, intent)
        print(f"\n用户: {user_msg}")
        print(f"意图: {intent}")

    context = memory.get_context(session_id, user_id)
    print(f"\n上下文长度: {len(context)}字符")

    profile = memory.get_user_profile(user_id)
    print(f"\n用户画像: {profile}")

    knowledge = memory.search_knowledge("甜度选择")
    print(f"\n知识库检索('甜度选择'): {len(knowledge)}条匹配")
    for item in knowledge:
        print(f"  - {item['content']}")

    stats = memory.get_global_stats()
    print(f"\n全局统计: {stats}")

    memory.clear_session(session_id)
    print("\n会话已清除")


if __name__ == "__main__":
    test_three_layer_memory()