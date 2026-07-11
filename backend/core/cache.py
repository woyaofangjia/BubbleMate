import os
import json
import time
import hashlib
from collections import defaultdict
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class RedisCache:
    _instance = None
    _lock = __import__('threading').Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._redis = None
                    cls._instance._init_redis()
                    cls._instance._fallback_cache = defaultdict(dict)
                    cls._instance._cache_hits = 0
                    cls._instance._cache_misses = 0
                    cls._instance._stats_lock = __import__('threading').Lock()
        return cls._instance
    
    def _init_redis(self):
        if not REDIS_AVAILABLE:
            return
        
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        try:
            self._redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self._redis.ping()
        except Exception as e:
            self._redis = None
    
    def _get_key_hash(self, key):
        if isinstance(key, str):
            return hashlib.md5(key.strip().encode('utf-8')).hexdigest()
        return hashlib.md5(json.dumps(key, sort_keys=True).encode('utf-8')).hexdigest()
    
    def get(self, prefix, key):
        key_hash = self._get_key_hash(key)
        cache_key = f"cache:{prefix}:{key_hash}"
        
        if self._redis is not None:
            try:
                value = self._redis.get(cache_key)
                if value is not None:
                    with self._stats_lock:
                        self._cache_hits += 1
                    return json.loads(value)
            except Exception:
                pass
        
        if cache_key in self._fallback_cache:
            cached = self._fallback_cache[cache_key]
            if time.time() - cached.get("timestamp", 0) < cached.get("ttl", 3600):
                with self._stats_lock:
                    self._cache_hits += 1
                return cached.get("value")
        
        with self._stats_lock:
            self._cache_misses += 1
        return None
    
    def set(self, prefix, key, value, ttl=3600):
        key_hash = self._get_key_hash(key)
        cache_key = f"cache:{prefix}:{key_hash}"
        
        if self._redis is not None:
            try:
                self._redis.set(cache_key, json.dumps(value), ex=ttl)
            except Exception:
                pass
        
        self._fallback_cache[cache_key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl
        }
        
        if len(self._fallback_cache) > 1000:
            oldest_key = min(self._fallback_cache.keys(), 
                           key=lambda k: self._fallback_cache[k].get("timestamp", 0))
            del self._fallback_cache[oldest_key]
    
    def delete(self, prefix, key):
        key_hash = self._get_key_hash(key)
        cache_key = f"cache:{prefix}:{key_hash}"
        
        if self._redis is not None:
            try:
                self._redis.delete(cache_key)
            except Exception:
                pass
        
        if cache_key in self._fallback_cache:
            del self._fallback_cache[cache_key]
    
    def clear(self, prefix=None):
        if prefix:
            if self._redis is not None:
                try:
                    keys = self._redis.keys(f"cache:{prefix}:*")
                    if keys:
                        self._redis.delete(*keys)
                except Exception:
                    pass
            
            keys_to_delete = [k for k in self._fallback_cache.keys() 
                            if k.startswith(f"cache:{prefix}:")]
            for k in keys_to_delete:
                del self._fallback_cache[k]
        else:
            if self._redis is not None:
                try:
                    self._redis.flushdb()
                except Exception:
                    pass
            
            self._fallback_cache.clear()
    
    def get_stats(self):
        stats = {"redis_available": self._redis is not None}
        
        if self._redis is not None:
            try:
                info = self._redis.info()
                stats["redis_keys"] = info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)
                stats["redis_hits"] = info.get("keyspace_hits", 0)
            except Exception:
                pass
        
        stats["fallback_keys"] = len(self._fallback_cache)
        
        with self._stats_lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total * 100 if total > 0 else 0
            stats["cache_hits"] = self._cache_hits
            stats["cache_misses"] = self._cache_misses
            stats["cache_hit_rate"] = round(hit_rate, 2)
        
        return stats
    
    def reset_stats(self):
        with self._stats_lock:
            self._cache_hits = 0
            self._cache_misses = 0

cache = RedisCache()

def cache_decorator(prefix, ttl=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
            cached = cache.get(prefix, key)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            cache.set(prefix, key, result, ttl)
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
            cached = cache.get(prefix, key)
            if cached is not None:
                return cached
            
            result = await func(*args, **kwargs)
            cache.set(prefix, key, result, ttl)
            return result
        
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        return wrapper
    
    return decorator