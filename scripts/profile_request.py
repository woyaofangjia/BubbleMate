import sys
sys.path.insert(0, '.')

import time
import requests

def profile_request(url, message, session_id):
    print(f"\n=== 请求分析: {message} ===")
    
    start = time.time()
    response = requests.post(url, json={"message": message, "session_id": session_id}, timeout=30)
    total_time = time.time() - start
    
    print(f"总耗时: {total_time*1000:.2f}ms")
    
    if response.status_code == 200:
        data = response.json()
        intent_name = data["intent"]["name"]
        print(f"意图: {intent_name}")
        print(f"响应长度: {len(data['response'])}")
    else:
        print(f"状态码: {response.status_code}")
    
    return total_time, response.status_code

url = "http://localhost:8000/chat"

print("=== 预热阶段 ===")
for i in range(3):
    t, code = profile_request(url, "推荐一下", f"warmup_{i}")
    print(f"预热{i+1}: {t*1000:.2f}ms")

print("\n=== 测试阶段 ===")
times = []
for i in range(10):
    t, code = profile_request(url, "推荐一下", f"test_{i}")
    times.append(t)

print(f"\n=== 统计结果 ===")
print(f"请求数: {len(times)}")
print(f"平均延迟: {sum(times)/len(times)*1000:.2f}ms")
print(f"最小延迟: {min(times)*1000:.2f}ms")
print(f"最大延迟: {max(times)*1000:.2f}ms")
print(f"P50: {sorted(times)[int(len(times)*0.5)]*1000:.2f}ms")
print(f"P90: {sorted(times)[int(len(times)*0.9)]*1000:.2f}ms")
