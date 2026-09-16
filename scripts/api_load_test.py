import asyncio
import aiohttp
import time
import json
import sys

async def make_request(session, url, payload):
    start = time.time()
    try:
        async with session.post(url, json=payload) as response:
            status = response.status
            elapsed = time.time() - start
            return status, elapsed
    except Exception as e:
        elapsed = time.time() - start
        return 0, elapsed

MESSAGES = [
    "你们有什么招牌推荐？", "菜单有什么喝的", "珍珠奶茶多少钱",
    "附近有门店吗", "今天有什么优惠", "营业时间几点",
    "可以加料吗", "怎么办会员", "能开发票吗", "支持外卖吗",
]

async def load_test(url, concurrency, duration, mixed=False):
    results = []
    counter = 0
    end_time = time.time() + duration

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=concurrency * 2),
        timeout=aiohttp.ClientTimeout(total=60),
    ) as session:
        async def worker(worker_id):
            nonlocal counter
            seq = 0
            while time.time() < end_time:
                if mixed:
                    counter += 1
                    message = f"{MESSAGES[(counter + worker_id) % len(MESSAGES)]}编号{counter}"
                else:
                    message = MESSAGES[0]
                payload = {"message": message, "session_id": f"load_{worker_id}"}
                status, elapsed = await make_request(session, url, payload)
                results.append((status, elapsed))
                seq += 1

        await asyncio.gather(*(worker(i) for i in range(concurrency)))

    return results

def main():
    url = "http://localhost:8000/chat"
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    mixed = len(sys.argv) > 3 and sys.argv[3] == "mixed"
    report_path = "reports/load_test_report_mixed.json" if mixed else "reports/load_test_report.json"

    print(f"开始压测: {url}")
    print(f"并发数: {concurrency}, 持续时间: {duration}秒, 口径: {'全链路(缓存miss)' if mixed else '热点缓存路径'}")
    print("-" * 50)
    
    results = asyncio.run(load_test(url, concurrency, duration, mixed))
    
    total_requests = len(results)
    successful_requests = sum(1 for s, _ in results if s == 200)
    elapsed_times = [t for _, t in results]
    
    throughput = total_requests / duration
    avg_latency = sum(elapsed_times) / len(elapsed_times) * 1000
    p50 = sorted(elapsed_times)[int(len(elapsed_times) * 0.5)] * 1000
    p95 = sorted(elapsed_times)[int(len(elapsed_times) * 0.95)] * 1000
    p99 = sorted(elapsed_times)[int(len(elapsed_times) * 0.99)] * 1000
    max_latency = max(elapsed_times) * 1000
    min_latency = min(elapsed_times) * 1000
    success_rate = (successful_requests / total_requests) * 100
    
    print(f"\n压测结果:")
    print(f"总请求数: {total_requests}")
    print(f"成功请求: {successful_requests}")
    print(f"成功率: {success_rate:.2f}%")
    print(f"吞吐量: {throughput:.2f} req/s")
    print(f"\n延迟统计(ms):")
    print(f"  平均: {avg_latency:.2f}")
    print(f"  最小: {min_latency:.2f}")
    print(f"  最大: {max_latency:.2f}")
    print(f"  P50:  {p50:.2f}")
    print(f"  P95:  {p95:.2f}")
    print(f"  P99:  {p99:.2f}")
    
    report = {
        "url": url,
        "concurrency": concurrency,
        "duration": duration,
        "mode": "mixed_cache_miss" if mixed else "cached_hot_path",
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "success_rate": success_rate,
        "throughput": throughput,
        "latency_ms": {
            "avg": avg_latency,
            "min": min_latency,
            "max": max_latency,
            "p50": p50,
            "p95": p95,
            "p99": p99
        }
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存到: {report_path}")

if __name__ == "__main__":
    main()