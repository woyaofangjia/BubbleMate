import time
import threading
import requests
import json
from collections import defaultdict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

results = []
lock = threading.Lock()

TEST_MESSAGES = [
    ("推荐一下", "推荐"),
    ("我的订单", "订单查询"),
    ("有什么优惠", "优惠查询"),
    ("怎么自定义奶茶", "自定义"),
    ("配送时间", "配送"),
    ("投诉服务态度", "投诉服务"),
    ("退款", "退款"),
    ("营业时间", "营业时间"),
    ("hello", "通用"),
    ("附近门店", "门店查询"),
    ("新品上市", "新品"),
    ("会员权益", "会员"),
    ("外卖配送范围", "配送范围"),
    ("能不能便宜点", "议价"),
    ("这个好喝吗", "评价"),
    ("无糖奶茶", "定制"),
    ("打包带走", "打包"),
    ("等了很久", "等待"),
    ("味道不好", "味道"),
    ("能不能换口味", "更换"),
]

def create_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=retry)
    session.mount("http://", adapter)
    return session

session = create_session()

def test_request(message, label):
    start = time.time()
    try:
        response = session.post(
            "http://127.0.0.1:8000/chat",
            json={"message": message, "session_id": f"test_{label}"},
            timeout=30
        )
        latency = (time.time() - start) * 1000
        with lock:
            results.append({
                "status": response.status_code,
                "latency": latency,
                "label": label,
                "intent": response.json().get("intent", {}).get("name", "unknown")
            })
    except Exception as e:
        latency = (time.time() - start) * 1000
        with lock:
            results.append({"status": 0, "latency": latency, "label": label, "intent": "error"})

print("=== 全链路性能测试 ===")
print("测试请求类型：缓存命中、规则匹配、LLM调用")
print("=" * 60)

print("\n--- 阶段1：预热缓存（3次） ---")
for i in range(3):
    for msg, label in TEST_MESSAGES:
        test_request(msg, label)
print(f"预热完成，共发送 {len(results)} 个请求")
results.clear()

print("\n--- 阶段2：单请求延迟测试（每种类型2次） ---")
all_latencies = []
for msg, label in TEST_MESSAGES:
    latencies = []
    for i in range(2):
        start = time.time()
        response = session.post(
            "http://127.0.0.1:8000/chat",
            json={"message": msg, "session_id": f"single_{label}_{i}"},
            timeout=30
        )
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        intent = response.json().get("intent", {}).get("name", "unknown")
        all_latencies.append({"label": label, "latency": latency, "intent": intent})
    avg_latency = sum(latencies) / len(latencies)
    print(f"  {label:10s}: 平均 {avg_latency:6.2f}ms, 最小 {min(latencies):6.2f}ms, 最大 {max(latencies):6.2f}ms")

print("\n--- 阶段3：并发测试（10并发，混合请求） ---")
threads = []
for i in range(10):
    msg, label = TEST_MESSAGES[i % len(TEST_MESSAGES)]
    t = threading.Thread(target=test_request, args=(msg, label))
    t.start()
    threads.append(t)
for t in threads:
    t.join()

print(f"  并发数: 10")
latencies = [r["latency"] for r in results]
print(f"  平均延迟: {sum(latencies)/len(latencies):.2f}ms")
print(f"  最小延迟: {min(latencies):.2f}ms")
print(f"  最大延迟: {max(latencies):.2f}ms")
latencies.sort()
n = len(latencies)
print(f"  P50延迟: {latencies[int(n*0.5)]:.2f}ms")
print(f"  P95延迟: {latencies[int(n*0.95)]:.2f}ms")
print(f"  P99延迟: {latencies[int(n*0.99)]:.2f}ms")
results.clear()

print("\n--- 阶段4：吞吐量测试（30秒，30并发，混合请求） ---")
stop_event = threading.Event()
sessions = [create_session() for _ in range(30)]

def worker(worker_id):
    sess = sessions[worker_id]
    while not stop_event.is_set():
        msg, label = TEST_MESSAGES[int(time.time() * 10) % len(TEST_MESSAGES)]
        start = time.time()
        try:
            response = sess.post(
                "http://127.0.0.1:8000/chat",
                json={"message": msg, "session_id": f"worker_{worker_id}"},
                timeout=30
            )
            latency = (time.time() - start) * 1000
            with lock:
                results.append({
                    "status": response.status_code,
                    "latency": latency,
                    "label": label,
                    "intent": response.json().get("intent", {}).get("name", "unknown")
                })
        except:
            latency = (time.time() - start) * 1000
            with lock:
                results.append({"status": 0, "latency": latency, "label": label, "intent": "error"})

threads = []
for i in range(30):
    t = threading.Thread(target=worker, args=(i,))
    t.daemon = True
    threads.append(t)
    t.start()

time.sleep(30)
stop_event.set()
time.sleep(1)

total_requests = len(results)
success_requests = sum(1 for r in results if r["status"] == 200)
latencies = [r["latency"] for r in results if r["status"] == 200]

intent_counts = defaultdict(int)
for r in results:
    if r["status"] == 200:
        intent_counts[r["intent"]] += 1

print(f"  总请求数: {total_requests}")
print(f"  成功请求: {success_requests}")
print(f"  成功率: {success_requests/total_requests*100:.2f}%")
print(f"  吞吐量: {total_requests/30:.2f} req/s")
print(f"  平均延迟: {sum(latencies)/len(latencies):.2f}ms")
print(f"  最小延迟: {min(latencies):.2f}ms")
print(f"  最大延迟: {max(latencies):.2f}ms")
latencies.sort()
n = len(latencies)
print(f"  P50延迟: {latencies[int(n*0.5)]:.2f}ms")
print(f"  P95延迟: {latencies[int(n*0.95)]:.2f}ms")
print(f"  P99延迟: {latencies[int(n*0.99)]:.2f}ms")

print("\n  意图分布:")
for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
    print(f"    {intent}: {count}")

print("\n" + "=" * 60)
print("全链路性能测试完成")