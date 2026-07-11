import time
import threading
import requests
import json

results = []
lock = threading.Lock()

def test_request(message, session_id):
    start = time.time()
    try:
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json={"message": message, "session_id": session_id},
            timeout=10
        )
        latency = (time.time() - start) * 1000
        with lock:
            results.append({
                "status": response.status_code,
                "latency": latency,
                "intent": response.json().get("intent", {}).get("name", "unknown")
            })
    except Exception as e:
        latency = (time.time() - start) * 1000
        with lock:
            results.append({"status": 0, "latency": latency, "intent": "error"})

print("=== 预热阶段 ===")
for msg in ["hello", "推荐一下", "订单查询"]:
    test_request(msg, "warmup")
print("预热完成，结果:", [f"{r['latency']:.2f}ms" for r in results])
results.clear()

print("\n=== 单请求测试 ===")
test_request("推荐一下", "test_single")
print(f"单请求延迟: {results[0]['latency']:.2f}ms")
results.clear()

print("\n=== 5并发测试 ===")
threads = []
for i in range(5):
    t = threading.Thread(target=test_request, args=("推荐一下", f"test_5_{i}"))
    t.start()
    threads.append(t)
for t in threads:
    t.join()

latencies = [r["latency"] for r in results]
print(f"并发数: 5")
print(f"平均延迟: {sum(latencies)/len(latencies):.2f}ms")
print(f"最小延迟: {min(latencies):.2f}ms")
print(f"最大延迟: {max(latencies):.2f}ms")
print(f"意图分布: {[r['intent'] for r in results]}")
results.clear()

print("\n=== 10并发测试 ===")
threads = []
for i in range(10):
    t = threading.Thread(target=test_request, args=("推荐一下", f"test_10_{i}"))
    t.start()
    threads.append(t)
for t in threads:
    t.join()

latencies = [r["latency"] for r in results]
print(f"并发数: 10")
print(f"平均延迟: {sum(latencies)/len(latencies):.2f}ms")
print(f"最小延迟: {min(latencies):.2f}ms")
print(f"最大延迟: {max(latencies):.2f}ms")
results.clear()

print("\n=== 吞吐量测试 (30秒) ===")
stop_event = threading.Event()
def worker():
    while not stop_event.is_set():
        test_request("推荐一下", "throughput")

threads = []
for i in range(20):
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()
    threads.append(t)

time.sleep(30)
stop_event.set()
time.sleep(1)

total_requests = len(results)
success_requests = sum(1 for r in results if r["status"] == 200)
latencies = [r["latency"] for r in results if r["status"] == 200]

print(f"总请求数: {total_requests}")
print(f"成功请求: {success_requests}")
print(f"成功率: {success_requests/total_requests*100:.2f}%")
print(f"吞吐量: {total_requests/30:.2f} req/s")
print(f"平均延迟: {sum(latencies)/len(latencies):.2f}ms")
print(f"最小延迟: {min(latencies):.2f}ms")
print(f"最大延迟: {max(latencies):.2f}ms")

latencies.sort()
n = len(latencies)
print(f"P50延迟: {latencies[int(n*0.5)]:.2f}ms")
print(f"P95延迟: {latencies[int(n*0.95)]:.2f}ms")
print(f"P99延迟: {latencies[int(n*0.99)]:.2f}ms")