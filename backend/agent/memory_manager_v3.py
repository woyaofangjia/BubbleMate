import json
import time
from typing import List, Dict, Optional, Any
from collections import deque
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.agent.keywords import SUGAR_MAP, ICE_MAP, DRINK_KEYWORDS, STORE_KEYWORDS, ALLERGEN_MAP, PRICE_MAP, COMPLAINT_TYPE_MAP, CATEGORY_MAP
except ImportError:
    from .keywords import SUGAR_MAP, ICE_MAP, DRINK_KEYWORDS, STORE_KEYWORDS, ALLERGEN_MAP, PRICE_MAP, COMPLAINT_TYPE_MAP, CATEGORY_MAP

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'memory_schema.json')
KNOWLEDGE_GRAPH_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'knowledge_graph.json')

class MemoryManagerV3:
    """增强版会话记忆管理器（带结构化记忆 + 知识沉淀）"""
    
    def __init__(self, window_size: int = 5, use_redis: bool = False, 
                 session_timeout: int = 3600):
        self.window_size = window_size
        self.use_redis = use_redis
        self.session_timeout = session_timeout
        
        self.local_store: Dict[str, deque] = {}
        self.full_history: Dict[str, List] = {}
        self.session_timestamps: Dict[str, float] = {}
        
        self.user_profiles: Dict[str, Dict] = {}
        
        self.redis_client = None
        if use_redis:
            self._init_redis()
        
        self._load_schema()
        self._load_knowledge_graph()
    
    def _init_redis(self):
        try:
            import redis
            from redis import ConnectionPool
            
            pool = ConnectionPool(
                host='localhost',
                port=6379,
                decode_responses=True,
                max_connections=10,
                socket_timeout=2,
                socket_connect_timeout=1
            )
            self.redis_client = redis.Redis(connection_pool=pool)
            print("Redis连接池初始化成功")
        except ImportError:
            print("Redis未安装，使用本地存储替代")
            self.use_redis = False
        except Exception as e:
            print(f"Redis连接失败: {e}")
            self.use_redis = False
    
    def _load_schema(self):
        try:
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
            print(f"用户偏好Schema加载成功")
        except Exception as e:
            print(f"Schema加载失败: {e}")
            self.schema = {}
    
    def _load_knowledge_graph(self):
        try:
            if os.path.exists(KNOWLEDGE_GRAPH_PATH):
                with open(KNOWLEDGE_GRAPH_PATH, 'r', encoding='utf-8') as f:
                    self.knowledge_graph = json.load(f)
            else:
                self.knowledge_graph = {
                    "complaint_patterns": {},
                    "solutions": {},
                    "compensation_strategies": {},
                    "case_count": 0
                }
                self._save_knowledge_graph()
            print(f"知识图谱加载成功，包含{self.knowledge_graph['case_count']}条案例")
        except Exception as e:
            print(f"知识图谱加载失败: {e}")
            self.knowledge_graph = {
                "complaint_patterns": {},
                "solutions": {},
                "compensation_strategies": {},
                "case_count": 0
            }
    
    def _save_knowledge_graph(self):
        try:
            with open(KNOWLEDGE_GRAPH_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_graph, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"知识图谱保存失败: {e}")
    
    def _extract_preferences(self, user_message: str, agent_message: str) -> Dict[str, Any]:
        preferences = {}
        import re
        
        for level, patterns in SUGAR_MAP.items():
            for pattern in patterns:
                if re.search(pattern, user_message):
                    preferences["sugar_level"] = level
                    break
        
        for level, patterns in ICE_MAP.items():
            for pattern in patterns:
                if re.search(pattern, user_message):
                    preferences["ice_level"] = level
                    break
        
        for keyword in DRINK_KEYWORDS:
            if keyword in user_message:
                preferences.setdefault("favorite_drinks", []).append(keyword)
        
        for keyword in STORE_KEYWORDS:
            if keyword in user_message:
                preferences["preferred_store"] = keyword
                break
        
        for allergen, patterns in ALLERGEN_MAP.items():
            for pattern in patterns:
                if re.search(pattern, user_message) and "过敏" in user_message:
                    preferences.setdefault("allergens", []).append(allergen)
        
        for sensitivity, patterns in PRICE_MAP.items():
            for pattern in patterns:
                if re.search(pattern, user_message):
                    preferences["price_sensitivity"] = sensitivity
                    break
        
        match = re.search(r"(\d{5,})", user_message)
        if match:
            preferences["last_order_id"] = match.group(1)
        
        return preferences
    
    def _extract_complaint(self, user_message: str) -> Optional[Dict]:
        import re
        
        complaint_keywords = {
            "taste": ["太甜", "太酸", "太苦", "难喝", "不好喝", "口感", "味道怪", "喝不下", "酸死了", "换配方", "跟上次不一样", "味道差"],
            "quantity": ["份量", "分量", "冰块太多", "配料少", "珍珠少", "料少", "少得可怜", "饮料没了"],
            "service": ["服务差", "态度差", "电话打不通", "备注没按", "服务不好", "态度恶劣"],
            "delivery": ["配送慢", "超时", "送得晚", "等太久", "包装破了", "送错"],
            "price": ["太贵", "价格高", "不值", "太贵了", "被坑了"],
            "refund": ["退款", "退钱", "要求退款"],
            "sarcasm": ["呵呵", "绝了", "也是绝了", "真是"],
            "accessory": ["吸管", "冰沙"]
        }
        
        complaint_intent_map = {
            "taste": "口感投诉",
            "quantity": "份量投诉",
            "service": "服务投诉",
            "delivery": "配送投诉",
            "price": "价格投诉",
            "refund": "退款投诉",
            "sarcasm": "讽刺投诉",
            "accessory": "配件投诉"
        }
        
        for code, keywords in complaint_keywords.items():
            if any(kw in user_message for kw in keywords):
                return {
                    "complaint_type": code,
                    "complaint_category": complaint_intent_map[code],
                    "description": user_message,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "resolved": False,
                    "solution": ""
                }
        
        return None
    
    def update_preference(self, session_id: str, user_message: str, agent_message: str):
        if session_id not in self.user_profiles:
            self.user_profiles[session_id] = {
                "user_id": session_id,
                "session_id": session_id,
                "preferences": {},
                "complaint_history": [],
                "interaction_stats": {
                    "total_interactions": 0,
                    "total_orders": 0,
                    "total_complaints": 0,
                    "avg_interaction_duration": 0.0,
                    "last_interaction_time": ""
                },
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        new_preferences = self._extract_preferences(user_message, agent_message)
        if new_preferences:
            self.user_profiles[session_id]["preferences"].update(new_preferences)
            
            drinks = new_preferences.get("favorite_drinks", [])
            if drinks:
                existing = self.user_profiles[session_id]["preferences"].get("favorite_drinks", [])
                self.user_profiles[session_id]["preferences"]["favorite_drinks"] = list(set(existing + drinks))
        
        complaint = self._extract_complaint(user_message)
        if complaint:
            self.user_profiles[session_id]["complaint_history"].append(complaint)
            self.user_profiles[session_id]["interaction_stats"]["total_complaints"] += 1
            
            self._learn_from_complaint(complaint)
        
        if "订单" in user_message or "下单" in user_message or "点" in user_message:
            self.user_profiles[session_id]["interaction_stats"]["total_orders"] += 1
        
        self.user_profiles[session_id]["interaction_stats"]["total_interactions"] += 1
        self.user_profiles[session_id]["interaction_stats"]["last_interaction_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.user_profiles[session_id]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if self.use_redis and self.redis_client:
            try:
                profile_key = f"user:{session_id}:profile"
                self.redis_client.set(profile_key, json.dumps(self.user_profiles[session_id]))
                self.redis_client.expire(profile_key, self.session_timeout * 24 * 7)
            except Exception as e:
                print(f"Redis保存偏好失败: {e}")
    
    def _learn_from_complaint(self, complaint: Dict):
        complaint_type = complaint["complaint_type"]
        description = complaint["description"]
        
        if complaint_type not in self.knowledge_graph["complaint_patterns"]:
            self.knowledge_graph["complaint_patterns"][complaint_type] = []
        
        self.knowledge_graph["complaint_patterns"][complaint_type].append(description)
        
        if complaint_type not in self.knowledge_graph["solutions"]:
            self.knowledge_graph["solutions"][complaint_type] = {
                "default": self._get_default_solution(complaint_type),
                "variants": []
            }
        
        if complaint_type not in self.knowledge_graph["compensation_strategies"]:
            self.knowledge_graph["compensation_strategies"][complaint_type] = {
                "default": self._get_default_compensation(complaint_type),
                "threshold": 3
            }
        
        self.knowledge_graph["case_count"] += 1
        self._save_knowledge_graph()
    
    def _get_default_solution(self, complaint_type: str) -> str:
        solutions = {
            "taste": "非常抱歉给您带来不好的体验，我们会为您重新制作一杯。",
            "quantity": "非常抱歉，我们会为您补做一份配料。",
            "service": "非常抱歉，我们已经将问题反馈给门店经理。",
            "delivery": "非常抱歉，我们会为您加急配送。",
            "price": "非常抱歉，我们可以为您提供优惠券作为补偿。",
            "refund": "非常抱歉，我们已经为您发起退款申请。",
            "sarcasm": "非常抱歉，我们会认真对待您的反馈。",
            "accessory": "非常抱歉，我们会为您补发吸管。"
        }
        return solutions.get(complaint_type, "非常抱歉，我们会尽快处理您的问题。")
    
    def _get_default_compensation(self, complaint_type: str) -> str:
        compensations = {
            "taste": "免费重做 + 5元优惠券",
            "quantity": "补配料 + 3元优惠券",
            "service": "10元优惠券",
            "delivery": "免配送费 + 5元优惠券",
            "price": "5元优惠券",
            "refund": "全额退款",
            "sarcasm": "5元优惠券",
            "accessory": "补发配件"
        }
        return compensations.get(complaint_type, "5元优惠券")
    
    def query_knowledge(self, complaint_type: str) -> Dict:
        result = {
            "solution": "",
            "compensation": "",
            "case_count": 0,
            "confidence": 0.0
        }
        
        if complaint_type in self.knowledge_graph["solutions"]:
            result["solution"] = self.knowledge_graph["solutions"][complaint_type]["default"]
        
        if complaint_type in self.knowledge_graph["compensation_strategies"]:
            result["compensation"] = self.knowledge_graph["compensation_strategies"][complaint_type]["default"]
        
        if complaint_type in self.knowledge_graph["complaint_patterns"]:
            result["case_count"] = len(self.knowledge_graph["complaint_patterns"][complaint_type])
            result["confidence"] = min(result["case_count"] * 0.2, 1.0)
        
        return result
    
    def get_user_profile(self, session_id: str) -> Dict:
        if self.use_redis and self.redis_client:
            try:
                profile_key = f"user:{session_id}:profile"
                profile_json = self.redis_client.get(profile_key)
                if profile_json:
                    return json.loads(profile_json)
            except Exception as e:
                print(f"Redis读取用户画像失败: {e}")
        
        return self.user_profiles.get(session_id, {})
    
    def format_preferences_for_prompt(self, session_id: str) -> str:
        profile = self.get_user_profile(session_id)
        preferences = profile.get("preferences", {})
        
        if not preferences:
            return ""
        
        parts = []
        if preferences.get("sugar_level"):
            parts.append(f"糖度偏好: {preferences['sugar_level']}")
        if preferences.get("ice_level"):
            parts.append(f"冰量偏好: {preferences['ice_level']}")
        if preferences.get("favorite_drinks"):
            parts.append(f"常点饮品: {', '.join(preferences['favorite_drinks'])}")
        if preferences.get("preferred_store"):
            parts.append(f"偏好门店: {preferences['preferred_store']}")
        if preferences.get("allergens"):
            parts.append(f"过敏原: {', '.join(preferences['allergens'])}")
        if preferences.get("price_sensitivity"):
            parts.append(f"价格敏感度: {preferences['price_sensitivity']}")
        if preferences.get("last_order_id"):
            parts.append(f"最近订单: {preferences['last_order_id']}")
        
        complaint_count = len(profile.get("complaint_history", []))
        if complaint_count > 0:
            parts.append(f"历史投诉: {complaint_count}次")
        
        return " | ".join(parts)
    
    def save_message(self, session_id: str, user_message: str, agent_message: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        epoch_timestamp = time.time()
        
        self.session_timestamps[session_id] = epoch_timestamp
        
        self.update_preference(session_id, user_message, agent_message)
        
        message_pair = {
            "user": user_message,
            "agent": agent_message,
            "timestamp": timestamp,
            "epoch": epoch_timestamp
        }
        
        if self.use_redis and self.redis_client:
            key = f"session:{session_id}"
            try:
                self.redis_client.rpush(key, json.dumps(message_pair))
                self.redis_client.expire(key, self.session_timeout)
                
                length = self.redis_client.llen(key)
                if length > self.window_size:
                    old_messages = [json.loads(self.redis_client.lindex(key, i)) 
                                   for i in range(length - self.window_size)]
                    summary = self._summarize_messages(old_messages, session_id)
                    
                    for _ in range(length - self.window_size):
                        self.redis_client.lpop(key)
                    
                    summary_key = f"session:{session_id}:summary"
                    self.redis_client.set(summary_key, summary)
                    self.redis_client.expire(summary_key, self.session_timeout)
            
            except Exception as e:
                print(f"Redis操作失败: {e}")
        
        else:
            if session_id not in self.local_store:
                self.local_store[session_id] = deque(maxlen=self.window_size)
                self.full_history[session_id] = []
            
            self.local_store[session_id].append(message_pair)
            self.full_history[session_id].append(message_pair)
            
            if len(self.full_history[session_id]) > self.window_size:
                old_messages = self.full_history[session_id][:len(self.full_history[session_id]) - self.window_size]
                summary = self._summarize_messages(old_messages, session_id)
                
                self.full_history[session_id] = [{"summary": summary}] + \
                    self.full_history[session_id][-self.window_size:]
    
    def get_context(self, session_id: str) -> str:
        context_parts = []
        
        pref_str = self.format_preferences_for_prompt(session_id)
        if pref_str:
            context_parts.append(f"[用户偏好] {pref_str}")
        
        if self.use_redis and self.redis_client:
            key = f"session:{session_id}"
            try:
                messages = self.redis_client.lrange(key, 0, -1)
                summary = self.redis_client.get(f"session:{session_id}:summary")
                
                if summary:
                    context_parts.append(f"[历史摘要] {summary}")
                
                for msg_json in messages:
                    msg = json.loads(msg_json)
                    context_parts.append(f"用户: {msg['user']}")
                    context_parts.append(f"客服: {msg['agent']}")
            
            except Exception as e:
                print(f"Redis读取失败: {e}")
        
        else:
            if session_id not in self.local_store:
                return ""
            
            if self.full_history.get(session_id):
                first_item = self.full_history[session_id][0]
                if "summary" in first_item:
                    context_parts.append(f"[历史摘要] {first_item['summary']}")
            
            for msg in self.local_store[session_id]:
                context_parts.append(f"用户: {msg['user']}")
                context_parts.append(f"客服: {msg['agent']}")
        
        return "\n".join(context_parts)
    
    def _summarize_messages(self, messages: List[Dict], session_id: str) -> str:
        topics = []
        order_ids = []
        complaints = []
        
        for msg in messages:
            user_msg = msg.get("user", "")
            agent_msg = msg.get("agent", "")
            
            if "投诉" in user_msg or "不好" in user_msg or "差" in user_msg:
                complaints.append("投诉")
            elif "订单" in user_msg or "配送" in user_msg:
                topics.append("订单查询")
                import re
                order_match = re.search(r"(\d{5,})", user_msg)
                if order_match:
                    order_ids.append(order_match.group(1))
            elif "推荐" in user_msg or "菜单" in user_msg or "喝什么" in user_msg:
                topics.append("菜单咨询")
            elif "门店" in user_msg or "地址" in user_msg or "附近" in user_msg:
                topics.append("门店查询")
            elif "退款" in user_msg or "售后" in user_msg:
                topics.append("退款/售后")
        
        summary_parts = []
        
        if complaints:
            summary_parts.append(f"投诉问题({len(complaints)}次)")
        
        if topics:
            summary_parts.append(f"咨询: {', '.join(set(topics))}")
        
        if order_ids:
            summary_parts.append(f"涉及订单: {', '.join(order_ids)}")
        
        pref_str = self.format_preferences_for_prompt(session_id)
        if pref_str:
            summary_parts.append(f"偏好: {pref_str}")
        
        if summary_parts:
            return " | ".join(summary_parts)
        else:
            return f"之前有{len(messages)}轮对话"
    
    def clear_expired_sessions(self):
        now = time.time()
        expired_count = 0
        
        expired_sessions = [sid for sid, ts in self.session_timestamps.items() 
                           if now - ts > self.session_timeout]
        
        for sid in expired_sessions:
            self.clear_session(sid)
            expired_count += 1
        
        return expired_count
    
    def clear_session(self, session_id: str):
        if self.use_redis and self.redis_client:
            try:
                keys = [
                    f"session:{session_id}",
                    f"session:{session_id}:summary",
                    f"session:{session_id}:preferences",
                    f"user:{session_id}:profile"
                ]
                self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Redis删除失败: {e}")
        
        self.local_store.pop(session_id, None)
        self.full_history.pop(session_id, None)
        self.session_timestamps.pop(session_id, None)
        self.user_profiles.pop(session_id, None)
    
    def get_session_stats(self, session_id: str) -> Dict:
        message_count = 0
        has_summary = False
        has_preferences = False
        
        if self.use_redis and self.redis_client:
            try:
                key = f"session:{session_id}"
                message_count = self.redis_client.llen(key)
                has_summary = self.redis_client.exists(f"session:{session_id}:summary")
                has_preferences = self.redis_client.exists(f"user:{session_id}:profile")
            except Exception as e:
                print(f"Redis统计失败: {e}")
        else:
            if session_id in self.full_history:
                history = self.full_history[session_id]
                message_count = len(history)
                has_summary = "summary" in history[0] if history else False
                has_preferences = bool(self.user_profiles.get(session_id))
        
        return {
            "message_count": message_count,
            "has_summary": bool(has_summary),
            "has_preferences": has_preferences,
            "window_size": self.window_size,
            "session_timeout": self.session_timeout
        }
    
    def get_global_stats(self) -> Dict:
        session_count = len(self.local_store) if not self.use_redis else 0
        
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys("session:*")
                session_count = len(set(k.split(":")[1] for k in keys if ":" in k))
            except Exception as e:
                print(f"Redis全局统计失败: {e}")
        
        return {
            "session_count": session_count,
            "knowledge_case_count": self.knowledge_graph.get("case_count", 0),
            "active_connections": self.redis_client.ping() if self.use_redis and self.redis_client else False,
            "window_size": self.window_size,
            "session_timeout": self.session_timeout
        }


def test_memory_v3():
    manager = MemoryManagerV3(window_size=5, use_redis=False)
    
    session_id = "test_v3"
    print("\n" + "=" * 60)
    print("结构化记忆管理器V3测试")
    print("=" * 60)
    
    test_messages = [
        ("给我推荐一款无糖的饮品", "推荐茉莉绿茶，零糖低卡..."),
        ("太甜了，喝不下去，我要投诉", "抱歉，已记录投诉，将为您处理..."),
        ("订单12345什么时候能送到？", "订单配送中，预计15分钟..."),
        ("附近有门店吗？", "附近有武汉大学梅园店..."),
        ("少冰的珍珠奶茶多少钱？", "珍珠奶茶12元，少冰免费..."),
        ("下次帮我记住少糖去冰", "已记录您的偏好：少糖去冰..."),
        ("还是太甜了，重做一杯", "非常抱歉，立即为您重做..."),
        ("给我来一杯七分糖正常冰的杨枝甘露", "好的，杨枝甘露七分糖正常冰..."),
    ]
    
    for user_msg, agent_msg in test_messages:
        manager.save_message(session_id, user_msg, agent_msg)
        
        profile = manager.get_user_profile(session_id)
        stats = manager.get_session_stats(session_id)
        
        print(f"\n用户: {user_msg}")
        print(f"记忆状态: {stats}")
        print(f"用户偏好: {profile.get('preferences', {})}")
        print(f"投诉次数: {len(profile.get('complaint_history', []))}")
        print(f"交互统计: {profile.get('interaction_stats', {})}")
    
    final_context = manager.get_context(session_id)
    print("\n" + "=" * 60)
    print("最终上下文:")
    print(final_context)
    
    print("\n" + "=" * 60)
    print("知识图谱查询测试:")
    taste_knowledge = manager.query_knowledge("taste")
    print(f"口感投诉知识: {taste_knowledge}")
    
    quantity_knowledge = manager.query_knowledge("quantity")
    print(f"份量投诉知识: {quantity_knowledge}")
    
    print("\n" + "=" * 60)
    print("全局统计:", manager.get_global_stats())
    
    manager.clear_session(session_id)
    print("\n会话已清除")

if __name__ == "__main__":
    test_memory_v3()