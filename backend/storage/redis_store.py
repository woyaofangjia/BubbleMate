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
SESSION_TTL = int(os.getenv("SESSION_TTL", 3600))

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
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._use_redis and self._redis_client:
            try:
                data = self._redis_client.get(f"session:{session_id}")
                if data:
                    return json.loads(data)
                return None
            except Exception:
                return self._memory_store.get(session_id)
        return self._memory_store.get(session_id)
    
    def save_session(self, session_id: str, data: Dict[str, Any]):
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.setex(
                    f"session:{session_id}",
                    SESSION_TTL,
                    json.dumps(data)
                )
                return
            except Exception:
                pass
        
        self._memory_store[session_id] = data
    
    def delete_session(self, session_id: str):
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.delete(f"session:{session_id}")
                return
            except Exception:
                pass
        
        self._memory_store.pop(session_id, None)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        if self._use_redis and self._redis_client:
            try:
                keys = self._redis_client.keys("session:*")
                result = {}
                for key in keys:
                    data = self._redis_client.get(key)
                    if data:
                        session_id = key.replace("session:", "")
                        result[session_id] = json.loads(data)
                return result
            except Exception:
                return dict(self._memory_store)
        return dict(self._memory_store)
    
    def is_using_redis(self) -> bool:
        return self._use_redis and self._redis_client is not None

session_store = SessionStore()