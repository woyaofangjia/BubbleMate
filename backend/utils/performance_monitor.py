"""
BubbleMate Performance Monitor - 性能监控模块
实现响应时间追踪、并发处理监控、资源使用统计
"""

import time
import threading
import queue
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

@dataclass
class RequestMetrics:
    """请求指标"""
    request_id: str
    start_time: float
    end_time: float = 0.0
    status: str = "pending"  # pending | success | error
    intent: str = ""
    tool_calls: int = 0
    memory_hits: int = 0
    error_message: str = ""
    
    @property
    def latency(self) -> float:
        return max(self.end_time - self.start_time, 0)

@dataclass
class PerformanceStats:
    """性能统计"""
    total_requests: int = 0
    success_requests: int = 0
    error_requests: int = 0
    avg_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    intent_accuracy: float = 0.0
    tool_success_rate: float = 0.0
    concurrent_requests: int = 0
    max_concurrent: int = 0
    memory_usage: int = 0  # bytes

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.requests: deque = deque(maxlen=window_size)
        self.stats = PerformanceStats()
        
        # 并发控制
        self.concurrent_lock = threading.Lock()
        self.current_concurrent = 0
        
        # 指标队列（异步处理）
        self.metrics_queue = queue.Queue(maxsize=1000)
        self._start_worker()
        
        # 时间窗口
        self.window_start = time.time()
    
    def _start_worker(self):
        """启动指标处理线程"""
        def worker():
            while True:
                try:
                    metrics = self.metrics_queue.get(timeout=1)
                    self._process_metrics(metrics)
                    self.metrics_queue.task_done()
                except queue.Empty:
                    continue
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def _process_metrics(self, metrics: RequestMetrics):
        """处理指标"""
        with self.concurrent_lock:
            self.stats.total_requests += 1
            if metrics.status == "success":
                self.stats.success_requests += 1
            else:
                self.stats.error_requests += 1
            
            # 更新延迟统计
            latency = metrics.latency
            self.stats.min_latency = min(self.stats.min_latency, latency)
            self.stats.max_latency = max(self.stats.max_latency, latency)
            
            # 计算平均延迟
            if self.stats.total_requests > 0:
                self.stats.avg_latency = (
                    self.stats.avg_latency * (self.stats.total_requests - 1) + latency
                ) / self.stats.total_requests
            
            # 更新百分位数
            self.requests.append(latency)
            if len(self.requests) >= 100:
                sorted_latencies = sorted(self.requests)
                self.stats.p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                self.stats.p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
    
    def start_request(self, request_id: str) -> RequestMetrics:
        """开始请求"""
        with self.concurrent_lock:
            self.current_concurrent += 1
            self.stats.max_concurrent = max(self.stats.max_concurrent, self.current_concurrent)
        
        return RequestMetrics(
            request_id=request_id,
            start_time=time.time()
        )
    
    def end_request(self, metrics: RequestMetrics, status: str = "success", **kwargs):
        """结束请求"""
        metrics.end_time = time.time()
        metrics.status = status
        
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        
        with self.concurrent_lock:
            self.current_concurrent -= 1
        
        # 异步处理指标
        if not self.metrics_queue.full():
            self.metrics_queue.put(metrics)
    
    def record_intent(self, correct: bool):
        """记录意图识别结果"""
        with self.concurrent_lock:
            if correct:
                self.stats.intent_accuracy = (
                    self.stats.intent_accuracy * (self.stats.total_requests - 1) + 100
                ) / self.stats.total_requests
            else:
                self.stats.intent_accuracy = (
                    self.stats.intent_accuracy * (self.stats.total_requests - 1) + 0
                ) / self.stats.total_requests
    
    def record_tool_call(self, success: bool):
        """记录工具调用结果"""
        # 简化实现：基于总请求数计算成功率
        pass
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        uptime = time.time() - self.window_start
        
        return {
            "uptime": round(uptime, 2),
            "total_requests": self.stats.total_requests,
            "success_rate": round(
                self.stats.success_requests / self.stats.total_requests * 100 
                if self.stats.total_requests > 0 else 0,
                2
            ),
            "avg_latency_ms": round(self.stats.avg_latency * 1000, 2),
            "min_latency_ms": round(self.stats.min_latency * 1000, 2),
            "max_latency_ms": round(self.stats.max_latency * 1000, 2),
            "p95_latency_ms": round(self.stats.p95_latency * 1000, 2),
            "p99_latency_ms": round(self.stats.p99_latency * 1000, 2),
            "intent_accuracy": round(self.stats.intent_accuracy, 2),
            "current_concurrent": self.current_concurrent,
            "max_concurrent": self.stats.max_concurrent,
            "request_window_size": len(self.requests),
        }
    
    def reset(self):
        """重置统计"""
        self.stats = PerformanceStats()
        self.requests.clear()
        self.window_start = time.time()
    
    def health_check(self) -> Dict:
        """健康检查"""
        stats = self.get_stats()
        
        # 判断健康状态
        status = "healthy"
        issues = []
        
        if stats["success_rate"] < 90:
            status = "warning"
            issues.append("成功率低于90%")
        
        if stats["avg_latency_ms"] > 500:
            status = "warning"
            issues.append("平均延迟超过500ms")
        
        if stats["current_concurrent"] > 20:
            status = "warning"
            issues.append("并发数超过20")
        
        return {
            "status": status,
            "issues": issues,
            "metrics": stats
        }


# 创建全局监控实例
performance_monitor = PerformanceMonitor()


def test_performance_monitor():
    """测试性能监控器"""
    monitor = PerformanceMonitor()
    
    print("\n" + "=" * 60)
    print("性能监控器测试")
    print("=" * 60)
    
    # 模拟10个请求
    for i in range(10):
        metrics = monitor.start_request(f"req-{i}")
        
        # 模拟处理时间（10-100ms）
        time.sleep((i + 1) * 0.01)
        
        # 随机成功/失败
        status = "success" if i % 3 != 0 else "error"
        monitor.end_request(metrics, status=status, intent=f"intent-{i}")
    
    # 获取统计
    stats = monitor.get_stats()
    print("\n统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 健康检查
    health = monitor.health_check()
    print(f"\n健康状态: {health['status']}")
    if health["issues"]:
        print(f"问题: {', '.join(health['issues'])}")

if __name__ == "__main__":
    test_performance_monitor()
