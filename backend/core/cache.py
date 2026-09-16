import os
import json
import time
import hashlib
from difflib import SequenceMatcher
from collections import defaultdict
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

PREFIX_CAPACITY = {"intent": 500}
DEFAULT_CAPACITY = 1000

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
                    cls._instance._fallback_index = defaultdict(dict)
                    cls._instance._cache_hits = 0
                    cls._instance._similar_hits = 0
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
        now = time.time()
        idx_key = f"cache:idx:{prefix}"
        idx_value = json.dumps({"k": key, "ts": now}, ensure_ascii=False)

        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.set(cache_key, json.dumps(value), ex=ttl)
                pipe.hset(idx_key, key_hash, idx_value)
                pipe.execute()
                self._trim_redis_index(prefix, idx_key)
            except Exception:
                pass

        self._fallback_cache[cache_key] = {
            "value": value,
            "timestamp": now,
            "ttl": ttl
        }
        self._fallback_index[prefix][key_hash] = {"k": key, "ts": now}
        self._trim_fallback_index(prefix)

    def _trim_redis_index(self, prefix, idx_key):
        cap = PREFIX_CAPACITY.get(prefix, DEFAULT_CAPACITY)
        try:
            if self._redis.hlen(idx_key) <= cap:
                return
            entries = self._redis.hgetall(idx_key)
            ordered = sorted(entries.items(), key=lambda kv: json.loads(kv[1]).get("ts", 0))
            for key_hash, _ in ordered[:len(ordered) - cap]:
                self._redis.hdel(idx_key, key_hash)
                self._redis.delete(f"cache:{prefix}:{key_hash}")
        except Exception:
            pass

    def _trim_fallback_index(self, prefix):
        cap = PREFIX_CAPACITY.get(prefix, DEFAULT_CAPACITY)
        idx = self._fallback_index[prefix]
        while len(idx) > cap:
            oldest_hash = min(idx, key=lambda h: idx[h]["ts"])
            idx.pop(oldest_hash)
            self._fallback_cache.pop(f"cache:{prefix}:{oldest_hash}", None)

    def get_similar(self, prefix, key, threshold=0.8):
        exact = self.get(prefix, key)
        if exact is not None:
            return {"value": exact, "match": "exact", "score": 1.0}

        key_hash = self._get_key_hash(key)
        candidates = {}
        if self._redis is not None:
            try:
                for h, raw in self._redis.hgetall(f"cache:idx:{prefix}").items():
                    candidates[h] = json.loads(raw)
            except Exception:
                pass
        for h, meta in self._fallback_index.get(prefix, {}).items():
            candidates.setdefault(h, meta)
        candidates.pop(key_hash, None)

        key_norm = key.strip()
        best_score, best_hash, best_text = 0.0, None, None
        for h, meta in candidates.items():
            score = SequenceMatcher(None, key_norm, str(meta.get("k", "")).strip()).ratio()
            if score > best_score:
                best_score, best_hash, best_text = score, h, meta.get("k")

        if best_hash and best_score >= threshold:
            value = self._get_by_hash(prefix, best_hash)
            if value is not None:
                with self._stats_lock:
                    self._similar_hits += 1
                return {"value": value, "match": "similar", "score": round(best_score, 3), "matched_text": best_text}
        return None

    def _get_by_hash(self, prefix, key_hash):
        cache_key = f"cache:{prefix}:{key_hash}"
        if self._redis is not None:
            try:
                raw = self._redis.get(cache_key)
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                pass
        cached = self._fallback_cache.get(cache_key)
        if cached and time.time() - cached.get("timestamp", 0) < cached.get("ttl", 3600):
            return cached.get("value")
        return None
    
    def delete(self, prefix, key):
        key_hash = self._get_key_hash(key)
        cache_key = f"cache:{prefix}:{key_hash}"

        if self._redis is not None:
            try:
                self._redis.delete(cache_key)
                self._redis.hdel(f"cache:idx:{prefix}", key_hash)
            except Exception:
                pass

        self._fallback_cache.pop(cache_key, None)
        self._fallback_index.get(prefix, {}).pop(key_hash, None)

    def clear(self, prefix=None):
        if prefix:
            if self._redis is not None:
                try:
                    keys = self._redis.keys(f"cache:{prefix}:*")
                    if keys:
                        self._redis.delete(*keys)
                    self._redis.delete(f"cache:idx:{prefix}")
                except Exception:
                    pass

            keys_to_delete = [k for k in self._fallback_cache.keys()
                            if k.startswith(f"cache:{prefix}:")]
            for k in keys_to_delete:
                del self._fallback_cache[k]
            self._fallback_index.pop(prefix, None)
        else:
            if self._redis is not None:
                try:
                    self._redis.flushdb()
                except Exception:
                    pass

            self._fallback_cache.clear()
            self._fallback_index.clear()

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
        stats["fallback_index_keys"] = sum(len(v) for v in self._fallback_index.values())

        with self._stats_lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total * 100 if total > 0 else 0
            stats["cache_hits"] = self._cache_hits
            stats["similar_hits"] = self._similar_hits
            stats["cache_misses"] = self._cache_misses
            stats["cache_hit_rate"] = round(hit_rate, 2)

        return stats

    def reset_stats(self):
        with self._stats_lock:
            self._cache_hits = 0
            self._similar_hits = 0
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