import sys
import time
import json
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.zhipu_client import call_llm, is_available

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

system_prompt = """你是一个奶茶店智能客服助手。请回答用户的问题，提供友好、专业的服务。

可用工具：
- query_menu: 查询菜单
- query_stores: 查询门店
- query_order: 查询订单
- query_price: 查询价格
- query_promotion: 查询优惠活动
- query_delivery: 查询配送信息
- query_customize: 查询定制选项
- place_order: 下单
- log_complaint: 记录投诉

请根据用户的问题，直接提供回答或调用相应工具。"""

if not is_available():
    print("LLM客户端不可用，请检查API Key配置")
    sys.exit(1)

results = {
    "total_queries": len(unseen_queries),
    "token_results": [],
    "avg_latency_ms": 0,
    "avg_tokens_per_query": 0,
    "total_tokens": 0,
}

total_latency = 0
total_tokens = 0

print(f"{'='*60}")
print("纯LLM方案 Token消耗测试 (glm-4-flash)")
print(f"{'='*60}")

for i, query in enumerate(unseen_queries, 1):
    start_time = time.time()
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        response = call_llm(messages, model="glm-4-flash", max_tokens=500)
        
        latency = (time.time() - start_time) * 1000
        total_latency += latency
        
        input_tokens = len(system_prompt) + len(query)
        output_tokens = len(response)
        total_query_tokens = input_tokens + output_tokens
        total_tokens += total_query_tokens
        
        print(f"[{i:2d}] {latency:8.2f}ms | 输入:{input_tokens:4d} | 输出:{output_tokens:4d} | 总计:{total_query_tokens:4d} | {query[:30]}...")
        
        results["token_results"].append({
            "query": query,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_query_tokens,
            "latency_ms": latency,
            "response": response[:100] + "..." if len(response) > 100 else response,
        })
        
    except Exception as e:
        print(f"[{i:2d}] ❌ 失败: {str(e)}")
        results["token_results"].append({
            "query": query,
            "error": str(e),
        })

results["avg_latency_ms"] = total_latency / len(unseen_queries)
results["avg_tokens_per_query"] = total_tokens / len(unseen_queries)
results["total_tokens"] = total_tokens
results["estimated_cost_per_k_queries"] = total_tokens / len(unseen_queries) * 1000 * 0.000002

print(f"\n{'='*60}")
print("测试结果汇总")
print(f"{'='*60}")
print(f"总查询数: {results['total_queries']}")
print(f"总Token数: {results['total_tokens']}")
print(f"平均Token/查询: {results['avg_tokens_per_query']:.2f}")
print(f"平均延迟: {results['avg_latency_ms']:.2f}ms")
print(f"预估成本/千次: ¥{results['estimated_cost_per_k_queries']:.4f}")

output_path = 'reports/pure_llm_baseline_report.json'
os.makedirs('reports', exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到: {output_path}")