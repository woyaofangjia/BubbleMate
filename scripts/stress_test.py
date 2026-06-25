"""
BubbleMate - 压力测试脚本
模拟高并发请求，测试系统性能
"""

import sys
import os
import time
import threading
import queue
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
from backend.agent.react_agent_v2 import ReActAgentV2, create_tools_v2
from backend.agent.memory_manager_v2 import MemoryManagerV2
from backend.utils.performance_monitor import PerformanceMonitor

class StressTester:
    """压力测试器"""
    
    def __init__(self, concurrent_users: int = 10, total_requests: int = 100):
        self.concurrent_users = concurrent_users
        self.total_requests = total_requests
        self.results = []
        self.lock = threading.Lock()
        
        # 初始化Agent
        self.intent_recognizer = IntentRecognizerV2("data")
        self.tools = create_tools_v2()
        self.memory_manager = MemoryManagerV2(window_size=5, use_redis=False)
        self.agent = ReActAgentV2(self.tools, self.intent_recognizer, self.memory_manager)
        
        # 测试请求
        self.test_requests = [
            "太甜了，喝不下去",
            "你们有什么招牌推荐？",
            "订单12345什么时候能送到？",
            "附近有门店吗？",
            "可以退款吗？",
            "门店营业时间？",
            "甜度有几种选择？",
            "有外卖吗？",
            "今天有什么优惠？",
            "会员卡怎么办？",
        ]
    
    def _worker(self, user_id: int, request_queue: queue.Queue, monitor: PerformanceMonitor):
        """工作线程"""
        while not request_queue.empty():
            try:
                request_id = request_queue.get(timeout=1)
                
                # 记录开始时间
                metrics = monitor.start_request(f"req-{request_id}")
                
                # 选择随机请求
                user_input = random.choice(self.test_requests)
                
                # 处理请求
                start_time = time.time()
                response = self.agent.process(user_input, session_id=f"user-{user_id}")
                end_time = time.time()
                
                # 记录结束时间
                latency = end_time - start_time
                success = True
                
                with self.lock:
                    self.results.append({
                        "request_id": request_id,
                        "user_id": user_id,
                        "input": user_input,
                        "latency_ms": latency * 1000,
                        "success": success,
                    })
                
                monitor.end_request(metrics, status="success" if success else "error")
                request_queue.task_done()
                
            except queue.Empty:
                break
            except Exception as e:
                with self.lock:
                    self.results.append({
                        "request_id": request_id,
                        "user_id": user_id,
                        "error": str(e),
                        "success": False,
                    })
    
    def run(self):
        """运行压力测试"""
        print("\n" + "=" * 60)
        print("压力测试开始")
        print(f"并发用户数: {self.concurrent_users}")
        print(f"总请求数: {self.total_requests}")
        print("=" * 60)
        
        monitor = PerformanceMonitor()
        request_queue = queue.Queue()
        
        # 填充请求队列
        for i in range(self.total_requests):
            request_queue.put(i)
        
        # 创建工作线程
        threads = []
        start_time = time.time()
        
        for user_id in range(self.concurrent_users):
            thread = threading.Thread(
                target=self._worker,
                args=(user_id, request_queue, monitor)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 计算统计
        successful = [r for r in self.results if r["success"]]
        latencies = [r["latency_ms"] for r in successful]
        
        print("\n" + "=" * 60)
        print("压力测试结果")
        print("=" * 60)
        
        print(f"\n总耗时: {total_time:.2f}s")
        print(f"吞吐量: {self.total_requests / total_time:.2f} req/s")
        print(f"成功率: {len(successful) / len(self.results) * 100:.2f}%")
        
        if latencies:
            print(f"\n延迟统计(ms):")
            print(f"  平均: {sum(latencies) / len(latencies):.2f}")
            print(f"  最小: {min(latencies):.2f}")
            print(f"  最大: {max(latencies):.2f}")
            print(f"  P95: {sorted(latencies)[int(len(latencies)*0.95)]:.2f}")
            print(f"  P99: {sorted(latencies)[int(len(latencies)*0.99)]:.2f}")
        
        # 性能监控统计
        stats = monitor.get_stats()
        print(f"\n监控指标:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return {
            "total_requests": self.total_requests,
            "concurrent_users": self.concurrent_users,
            "total_time": total_time,
            "throughput": self.total_requests / total_time,
            "success_rate": len(successful) / len(self.results) * 100,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
        }


def run_stress_test():
    """运行多轮压力测试"""
    print("\n" + "=" * 70)
    print("BubbleMate 压力测试")
    print("=" * 70)
    
    test_configs = [
        {"users": 5, "requests": 50},
        {"users": 10, "requests": 100},
        {"users": 20, "requests": 200},
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n--- 测试: {config['users']}并发, {config['requests']}请求 ---")
        tester = StressTester(
            concurrent_users=config["users"],
            total_requests=config["requests"]
        )
        result = tester.run()
        results.append(result)
    
    print("\n" + "=" * 70)
    print("压力测试汇总")
    print("=" * 70)
    
    print(f"\n{'并发数':<8} {'请求数':<8} {'吞吐量':<12} {'成功率':<10} {'平均延迟':<12}")
    print("-" * 50)
    
    for result in results:
        print(f"{result['concurrent_users']:<8} {result['total_requests']:<8} "
              f"{result['throughput']:<12.2f} {result['success_rate']:<10.2f}% "
              f"{result['avg_latency_ms']:<12.2f}")


if __name__ == "__main__":
    run_stress_test()
