"""
BubbleMate Memory - 会话记忆管理
实现滑动窗口 + 摘要压缩
"""

import json
import time
from typing import List, Dict, Optional
from collections import deque

class MemoryManager:
    """会话记忆管理器"""
    
    def __init__(self, window_size: int = 5, use_redis: bool = False):
        self.window_size = window_size
        self.use_redis = use_redis
        
        # 本地存储（替代Redis）
        self.local_store: Dict[str, deque] = {}
        self.full_history: Dict[str, List] = {}
        
        # Redis客户端（可选）
        self.redis_client = None
        if use_redis:
            self._init_redis()
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
        except ImportError:
            print("Redis未安装，使用本地存储替代")
            self.use_redis = False
    
    def save_message(self, session_id: str, user_message: str, agent_message: str):
        """保存对话消息"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        message_pair = {
            "user": user_message,
            "agent": agent_message,
            "timestamp": timestamp
        }
        
        if self.use_redis and self.redis_client:
            # Redis存储
            key = f"session:{session_id}"
            self.redis_client.rpush(key, json.dumps(message_pair))
            
            # 保持滑动窗口
            length = self.redis_client.llen(key)
            if length > self.window_size:
                # 对旧消息进行摘要
                old_messages = [json.loads(self.redis_client.lindex(key, i)) 
                               for i in range(length - self.window_size)]
                summary = self._summarize_messages(old_messages)
                
                # 删除旧消息，保存摘要
                for _ in range(length - self.window_size):
                    self.redis_client.lpop(key)
                
                self.redis_client.set(f"session:{session_id}:summary", summary)
        else:
            # 本地存储
            if session_id not in self.local_store:
                self.local_store[session_id] = deque(maxlen=self.window_size)
                self.full_history[session_id] = []
            
            self.local_store[session_id].append(message_pair)
            self.full_history[session_id].append(message_pair)
            
            # 超过窗口时压缩
            if len(self.full_history[session_id]) > self.window_size:
                old_messages = self.full_history[session_id][:len(self.full_history[session_id]) - self.window_size]
                summary = self._summarize_messages(old_messages)
                
                # 保存摘要（简化版）
                self.full_history[session_id] = [{"summary": summary}] + \
                    self.full_history[session_id][-self.window_size:]
    
    def get_context(self, session_id: str) -> str:
        """获取对话上下文"""
        if self.use_redis and self.redis_client:
            # 从Redis获取
            key = f"session:{session_id}"
            messages = self.redis_client.lrange(key, 0, -1)
            summary = self.redis_client.get(f"session:{session_id}:summary")
            
            context_parts = []
            if summary:
                context_parts.append(f"[历史摘要] {summary}")
            
            for msg_json in messages:
                msg = json.loads(msg_json)
                context_parts.append(f"用户: {msg['user']}")
                context_parts.append(f"客服: {msg['agent']}")
            
            return "\n".join(context_parts)
        else:
            # 从本地存储获取
            if session_id not in self.local_store:
                return ""
            
            context_parts = []
            
            # 检查是否有摘要
            if self.full_history.get(session_id):
                first_item = self.full_history[session_id][0]
                if "summary" in first_item:
                    context_parts.append(f"[历史摘要] {first_item['summary']}")
            
            # 最近对话
            for msg in self.local_store[session_id]:
                context_parts.append(f"用户: {msg['user']}")
                context_parts.append(f"客服: {msg['agent']}")
            
            return "\n".join(context_parts)
    
    def _summarize_messages(self, messages: List[Dict]) -> str:
        """摘要旧消息"""
        # 简化版摘要：提取关键主题
        topics = []
        
        for msg in messages:
            user_msg = msg.get("user", "")
            
            # 提取关键词
            if "投诉" in user_msg or "不好" in user_msg or "差" in user_msg:
                topics.append("投诉处理")
            elif "订单" in user_msg or "配送" in user_msg:
                topics.append("订单查询")
            elif "推荐" in user_msg or "菜单" in user_msg:
                topics.append("菜单咨询")
            elif "门店" in user_msg or "地址" in user_msg:
                topics.append("门店查询")
        
        if topics:
            return f"之前讨论过: {', '.join(set(topics))}"
        else:
            return f"之前有{len(messages)}轮对话"
    
    def clear_session(self, session_id: str):
        """清除会话"""
        if self.use_redis and self.redis_client:
            self.redis_client.delete(f"session:{session_id}")
            self.redis_client.delete(f"session:{session_id}:summary")
        else:
            self.local_store.pop(session_id, None)
            self.full_history.pop(session_id, None)
    
    def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计"""
        if session_id not in self.full_history:
            return {"message_count": 0, "has_summary": False}
        
        history = self.full_history[session_id]
        has_summary = "summary" in history[0] if history else False
        
        return {
            "message_count": len(history),
            "has_summary": has_summary,
            "window_size": self.window_size
        }


def test_memory_manager():
    """测试记忆管理"""
    manager = MemoryManager(window_size=5, use_redis=False)
    
    session_id = "test_session"
    
    print("\n会话记忆测试:")
    print("-" * 50)
    
    # 模拟对话
    test_messages = [
        ("你们有什么推荐？", "我们的招牌包括芝芝莓莓、杨枝甘露..."),
        ("太甜了，喝不下去", "抱歉，下次建议选择三分糖..."),
        ("订单12345什么时候能送到？", "订单配送中，预计15分钟..."),
        ("附近有门店吗？", "附近门店包括武汉大学梅园店..."),
        ("可以退款吗？", "可以的，请在小程序申请售后..."),
        ("门店营业时间？", "营业时间10:00-22:00..."),  # 第6轮，触发压缩
    ]
    
    for user_msg, agent_msg in test_messages:
        manager.save_message(session_id, user_msg, agent_msg)
        
        context = manager.get_context(session_id)
        stats = manager.get_session_stats(session_id)
        
        print(f"用户: {user_msg}")
        print(f"记忆状态: {stats}")
        print(f"上下文长度: {len(context)}字符")
        print("-" * 50)
    
    # 最终上下文
    final_context = manager.get_context(session_id)
    print("\n最终对话上下文:")
    print(final_context)

if __name__ == "__main__":
    test_memory_manager()