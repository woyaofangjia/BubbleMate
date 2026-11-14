import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import clear_intent_cache, clear_response_cache
from backend.core.cache import cache


def main():
    before = cache.get_stats()
    clear_intent_cache()
    clear_response_cache()
    after = cache.get_stats()
    print(json.dumps({
        "success": True,
        "cleared": ["intent", "response"],
        "redis_available": before["redis_available"],
        "fallback_keys_before": before["fallback_keys"],
        "fallback_keys_after": after["fallback_keys"],
    }, ensure_ascii=False, indent=2))
    print("注意：其他正在运行的后端进程仍有进程内缓存；完整回滚请重启所有后端worker。")


if __name__ == "__main__":
    main()
