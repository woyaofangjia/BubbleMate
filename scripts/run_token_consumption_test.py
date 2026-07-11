import sys
import time
import json
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import process_message, create_memory_store, recognize_intent

unseen_queries = [
    "我想点一杯少糖去冰加珍珠的奶茶",
    "你们家新品有哪些呀",
    "上次买的那个不好喝能退吗",
    "明天开业吗",
    "学生有优惠吗",
    "能送到小区门口吗",
    "可以用支付宝吗",
    "有什么低糖的推荐",
    "上次那个太甜了这次要无糖",
    "外卖多久能到",
    "可以开发票吗",
    "买十杯有折扣吗",
    "有没有热饮推荐",
    "上次那个杯子挺好看的能卖吗",
    "你们几点关门",
    "能帮我送到写字楼楼下吗",
    "有什么季节限定的饮品",
    "上次点的那个还能做吗",
    "可以加双倍珍珠吗",
    "有没有不含咖啡因的",
    "离地铁站近吗",
    "可以堂食吗",
    "生日当天有优惠吗",
    "上次那个水果茶挺不错的再推荐几个",
    "能预约吗",
    "下雨天送得慢吗",
    "有会员日吗",
    "上次买的少给了配料",
    "杯子能回收吗",
    "有什么适合夏天喝的",
]

results = {
    "total_queries": len(unseen_queries),
    "rule_matched": 0,
    "llm_fallback": 0,
    "token_estimates": [],
    "avg_latency_ms": 0,
}

total_latency = 0

print(f"{'='*60}")
print("Token消耗测试 - 未见过的真实问法")
print(f"{'='*60}")

for query in unseen_queries:
    start_time = time.time()
    
    intent = recognize_intent(query)
    response, _ = process_message(query, "token_test")
    
    latency = (time.time() - start_time) * 1000
    total_latency += latency
    
    is_rule_match = intent["confidence"] >= 0.5
    is_llm = "【LLM】" in response or "LLM" in response or intent["confidence"] < 0.5
    
    if is_rule_match:
        results["rule_matched"] += 1
    else:
        results["llm_fallback"] += 1
    
    token_estimate = len(response) * 1.3
    results["token_estimates"].append({
        "query": query,
        "intent": intent["name"],
        "confidence": intent["confidence"],
        "rule_match": is_rule_match,
        "latency_ms": latency,
        "response_length": len(response),
        "estimated_tokens": token_estimate,
    })
    
    status = "规则" if is_rule_match else "LLM"
    print(f"[{status}] {latency:6.2f}ms | {intent['name']:20s} | {query}")

results["avg_latency_ms"] = total_latency / len(unseen_queries)
results["avg_tokens_per_query"] = sum(t["estimated_tokens"] for t in results["token_estimates"]) / len(results["token_estimates"])
results["total_estimated_tokens"] = sum(t["estimated_tokens"] for t in results["token_estimates"])
results["rule_coverage"] = results["rule_matched"] / len(unseen_queries) * 100
results["llm_fallback_rate"] = results["llm_fallback"] / len(unseen_queries) * 100

print(f"\n{'='*60}")
print("测试结果汇总")
print(f"{'='*60}")
print(f"总查询数: {results['total_queries']}")
print(f"规则匹配: {results['rule_matched']} ({results['rule_coverage']:.2f}%)")
print(f"LLM兜底: {results['llm_fallback']} ({results['llm_fallback_rate']:.2f}%)")
print(f"平均延迟: {results['avg_latency_ms']:.2f}ms")
print(f"平均Token/查询: {results['avg_tokens_per_query']:.2f}")
print(f"总Token估算: {results['total_estimated_tokens']:.2f}")

output_path = 'reports/token_consumption_report.json'
os.makedirs('reports', exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到: {output_path}")