import json
import time
from typing import List, Dict, Optional
from collections import deque

from .keywords import SUGAR_MAP, ICE_MAP, DRINK_KEYWORDS, STORE_KEYWORDS, ALLERGEN_MAP, PRICE_MAP, COMPLAINT_TYPE_MAP

class MemoryManagerV2:
    """增强版会话记忆管理器"""
    
    def __init__(self, window_size: int = 5, use_redis: bool = False, 
                 session_timeout: int = 3600):
        self.window_size = window_size
        self.use_redis = use_redis
        self.session_timeout = session_timeout
        
        # 本地存储
        self.local_store: Dict[str, deque] = {}
        self.full_history: Dict[str, List] = {}
        self.session_timestamps: Dict[str, float] = {}
        
        # 用户偏好（从对话中提取）
        self.user_preferences: Dict[str, Dict] = {}
        
        # Redis客户端
        self.redis_client = None
        if use_redis:
            self._init_redis()
    
    def _init_redis(self):
        """初始化Redis连接（连接池模式）"""
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
    
    def _extract_preferences(self, user_message: str, agent_message: str):
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
        
        for code, keywords in COMPLAINT_TYPE_MAP.items():
            if any(kw in user_message for kw in keywords):
                preferences.setdefault("complaint_history", []).append({"type": code, "description": user_message})
                break
        
        return preferences
    
    def format_preferences(self, session_id: str) -> str:
        pref = self.get_user_preferences(session_id)
        parts = []
        if pref.get("sugar_level"):
            parts.append(f"甜度偏好: {pref['sugar_level']}")
        if pref.get("ice_level"):
            parts.append(f"冰量偏好: {pref['ice_level']}")
        if pref.get("favorite_drinks"):
            parts.append(f"喜欢的饮品: {', '.join(pref['favorite_drinks'])}")
        if pref.get("preferred_store"):
            parts.append(f"偏好门店: {pref['preferred_store']}")
        if pref.get("allergens"):
            parts.append(f"过敏原: {', '.join(pref['allergens'])}")
        if pref.get("price_sensitivity"):
            parts.append(f"价格敏感度: {pref['price_sensitivity']}")
        if pref.get("last_order_id"):
            parts.append(f"最近订单: {pref['last_order_id']}")
        if pref.get("complaint_history"):
            parts.append(f"投诉次数: {len(pref['complaint_history'])}次")
        return " | ".join(parts) if parts else ""
    
    def save_message(self, session_id: str, user_message: str, agent_message: str):
        """保存对话消息（增强版）"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        epoch_timestamp = time.time()
        
        # 更新会话时间戳（用于超时清理）
        self.session_timestamps[session_id] = epoch_timestamp
        
        # 提取用户偏好
        new_preferences = self._extract_preferences(user_message, agent_message)
        if new_preferences:
            if session_id not in self.user_preferences:
                self.user_preferences[session_id] = {}
            self.user_preferences[session_id].update(new_preferences)
        
        message_pair = {
            "user": user_message,
            "agent": agent_message,
            "timestamp": timestamp,
            "epoch": epoch_timestamp
        }
        
        if self.use_redis and self.redis_client:
            key = f"session:{session_id}"
            
            try:
                # Redis存储
                self.redis_client.rpush(key, json.dumps(message_pair))
                
                # 更新超时时间
                self.redis_client.expire(key, self.session_timeout)
                
                # 更新用户偏好
                if new_preferences:
                    pref_key = f"session:{session_id}:preferences"
                    self.redis_client.set(pref_key, json.dumps(self.user_preferences[session_id]))
                    self.redis_client.expire(pref_key, self.session_timeout)
                
                # 保持滑动窗口
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
            # 本地存储
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
        """获取对话上下文（包含用户偏好）"""
        context_parts = []
        
        # 获取用户偏好
        preferences = self.get_user_preferences(session_id)
        if preferences:
            pref_str = ", ".join([f"{k}: {v}" for k, v in preferences.items()])
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
    
    def get_user_preferences(self, session_id: str) -> Dict:
        """获取用户偏好"""
        if self.use_redis and self.redis_client:
            try:
                pref_key = f"session:{session_id}:preferences"
                pref_json = self.redis_client.get(pref_key)
                if pref_json:
                    return json.loads(pref_json)
            except Exception as e:
                print(f"Redis读取偏好失败: {e}")
        
        return self.user_preferences.get(session_id, {})
    
    def _summarize_messages(self, messages: List[Dict], session_id: str) -> str:
        """高级摘要：提取关键信息"""
        topics = []
        order_ids = []
        complaints = []
        
        for msg in messages:
            user_msg = msg.get("user", "")
            agent_msg = msg.get("agent", "")
            
            # 提取主题
            if "投诉" in user_msg or "不好" in user_msg or "差" in user_msg:
                complaints.append("投诉")
            elif "订单" in user_msg or "配送" in user_msg:
                topics.append("订单查询")
                # 提取订单号
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
        
        # 添加用户偏好
        preferences = self.user_preferences.get(session_id, {})
        if preferences:
            pref_str = "; ".join([f"{k}={v}" for k, v in preferences.items()])
            summary_parts.append(f"偏好: {pref_str}")
        
        if summary_parts:
            return " | ".join(summary_parts)
        else:
            return f"之前有{len(messages)}轮对话"
    
    def clear_expired_sessions(self):
        """清理过期会话"""
        now = time.time()
        expired_count = 0
        
        # 本地存储清理
        expired_sessions = [sid for sid, ts in self.session_timestamps.items() 
                           if now - ts > self.session_timeout]
        
        for sid in expired_sessions:
            self.clear_session(sid)
            expired_count += 1
        
        # Redis清理（通过TTL自动处理）
        
        return expired_count
    
    def clear_session(self, session_id: str):
        """清除会话"""
        if self.use_redis and self.redis_client:
            try:
                keys = [
                    f"session:{session_id}",
                    f"session:{session_id}:summary",
                    f"session:{session_id}:preferences"
                ]
                self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Redis删除失败: {e}")
        
        self.local_store.pop(session_id, None)
        self.full_history.pop(session_id, None)
        self.session_timestamps.pop(session_id, None)
        self.user_preferences.pop(session_id, None)
    
    def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计（增强版）"""
        message_count = 0
        has_summary = False
        has_preferences = False
        
        if self.use_redis and self.redis_client:
            try:
                key = f"session:{session_id}"
                message_count = self.redis_client.llen(key)
                has_summary = self.redis_client.exists(f"session:{session_id}:summary")
                has_preferences = self.redis_client.exists(f"session:{session_id}:preferences")
            except Exception as e:
                print(f"Redis统计失败: {e}")
        else:
            if session_id in self.full_history:
                history = self.full_history[session_id]
                message_count = len(history)
                has_summary = "summary" in history[0] if history else False
                has_preferences = bool(self.user_preferences.get(session_id))
        
        return {
            "message_count": message_count,
            "has_summary": bool(has_summary),
            "has_preferences": has_preferences,
            "window_size": self.window_size,
            "session_timeout": self.session_timeout
        }
    
    def get_global_stats(self) -> Dict:
        """获取全局统计"""
        session_count = len(self.local_store) if not self.use_redis else 0
        
        if self.use_redis and self.redis_client:
            try:
                keys = self.redis_client.keys("session:*")
                session_count = len(set(k.split(":")[1] for k in keys if ":" in k))
            except Exception as e:
                print(f"Redis全局统计失败: {e}")
        
        return {
            "session_count": session_count,
            "active_connections": self.redis_client.ping() if self.use_redis and self.redis_client else False,
            "window_size": self.window_size,
            "session_timeout": self.session_timeout
        }


def test_memory_v2():
    """测试增强版记忆管理器"""
    manager = MemoryManagerV2(window_size=5, use_redis=False, session_timeout=3600)
    
    session_id = "test_v2"
    print("\n" + "=" * 60)
    print("增强版记忆管理器测试")
    print("=" * 60)
    
    test_messages = [
        ("给我推荐一款无糖的饮品", "推荐茉莉绿茶，零糖低卡..."),
        ("太甜了，喝不下去，我要投诉", "抱歉，已记录投诉，将为您处理..."),
        ("订单12345什么时候能送到？", "订单配送中，预计15分钟..."),
        ("附近有门店吗？", "附近有武汉大学梅园店..."),
        ("少冰的珍珠奶茶多少钱？", "珍珠奶茶12元，少冰免费..."),
        ("下次帮我记住少糖去冰", "已记录您的偏好：少糖去冰..."),
    ]
    
    for user_msg, agent_msg in test_messages:
        manager.save_message(session_id, user_msg, agent_msg)
        
        context = manager.get_context(session_id)
        stats = manager.get_session_stats(session_id)
        prefs = manager.get_user_preferences(session_id)
        
        print(f"\n用户: {user_msg}")
        print(f"记忆状态: {stats}")
        print(f"用户偏好: {prefs}")
        print(f"上下文长度: {len(context)}字符")
    
    final_context = manager.get_context(session_id)
    print("\n" + "=" * 60)
    print("最终上下文:")
    print(final_context)
    
    # 测试过期清理
    print("\n" + "=" * 60)
    print("全局统计:", manager.get_global_stats())
    
    # 清理会话
    manager.clear_session(session_id)
    print("\n会话已清除")
    print("全局统计:", manager.get_global_stats())

if __name__ == "__main__":
    test_memory_v2()
