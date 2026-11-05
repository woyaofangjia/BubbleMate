import json
import os
from typing import Optional, Dict, Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
SESSION_TTL = int(os.getenv("SESSION_TTL", 604800))

class SessionStore:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._use_redis = REDIS_AVAILABLE
            cls._instance._redis_client = None
            cls._instance._memory_store = {}
            
            if cls._instance._use_redis:
                try:
                    cls._instance._redis_client = redis.Redis(
                        host=REDIS_HOST,
                        port=REDIS_PORT,
                        db=REDIS_DB,
                        decode_responses=True,
                        socket_timeout=5,
                        socket_connect_timeout=5
                    )
                    cls._instance._redis_client.ping()
                except Exception as e:
                    cls._instance._use_redis = False
                    cls._instance._redis_client = None
        return cls._instance

    @staticmethod
    def _key(user_id: Optional[str], session_id: str) -> str:
        """会话按用户命名空间存储，避免同 session_id 跨用户串数据。"""
        if user_id:
            return f"user:{user_id}:session:{session_id}"
        return f"session:{session_id}"

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        key = self._key(user_id, session_id)
        if self._use_redis and self._redis_client:
            try:
                data = self._redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception:
                return self._memory_store.get(key)
        return self._memory_store.get(key)
    
    def save_session(self, session_id: str, data: Dict[str, Any], user_id: Optional[str] = None):
        key = self._key(user_id, session_id)
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.setex(key, SESSION_TTL, json.dumps(data))
                return
            except Exception:
                pass
        
        self._memory_store[key] = data
    
    def delete_session(self, session_id: str, user_id: Optional[str] = None):
        keys = [self._key(user_id, session_id)]
        # 兼容升级前的旧键
        if user_id:
            keys.append(f"session:{session_id}")
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.delete(*keys)
                return
            except Exception:
                pass
        
        for key in keys:
            self._memory_store.pop(key, None)
    
    def get_all_sessions(self, user_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        pattern = f"user:{user_id}:session:*" if user_id else "session:*"
        if self._use_redis and self._redis_client:
            try:
                keys = self._redis_client.keys(pattern)
                result = {}
                for key in keys:
                    data = self._redis_client.get(key)
                    if data:
                        result[key] = json.loads(data)
                return result
            except Exception:
                return dict(self._memory_store)
        return dict(self._memory_store)
    
    def is_using_redis(self) -> bool:
        return self._use_redis and self._redis_client is not None

session_store = SessionStore()