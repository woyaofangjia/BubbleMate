import sys
import time
import json
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import process_message, create_memory_store

test_scenarios = [
    {
        "name": "糖度记忆",
        "dialogue": [
            ("我要一杯三分糖的奶茶", "query_recommend"),
            ("甜度是多少", "query_temp"),
        ],
        "check_response": lambda r: "三分糖" in r
    },
    {
        "name": "温度记忆",
        "dialogue": [
            ("来一杯热的珍珠奶茶", "place_order"),
            ("温度是多少", "query_temp"),
        ],
        "check_response": lambda r: "热" in r or "温" in r
    },
    {
        "name": "订单号记忆",
        "dialogue": [
            ("订单号ORD-20260101-001", "query_order"),
            ("这个订单的状态", "query_order"),
        ],
        "check_response": lambda r: "ORD-20260101-001" in r or "订单" in r
    },
    {
        "name": "位置记忆",
        "dialogue": [
            ("光谷附近有门店吗", "query_location"),
            ("距离有多远", "query_location"),
        ],
        "check_response": lambda r: "光谷" in r or "附近" in r or "距离" in r
    },
    {
        "name": "复杂指代记忆",
        "dialogue": [
            ("我上次点的那杯太甜了", "complaint_taste"),
            ("那杯是什么", "query_menu"),
        ],
        "check_response": lambda r: "甜" in r or "上次" in r or "奶茶" in r
    },
    {
        "name": "多轮偏好记忆",
        "dialogue": [
            ("我要少糖去冰的奶茶", "place_order"),
            ("再加一份珍珠", "query_customize"),
            ("甜度和冰量是多少", "query_temp"),
        ],
        "check_response": lambda r: ("少糖" in r or "三分糖" in r) and ("去冰" in r)
    },
    {
        "name": "5轮指代记忆",
        "dialogue": [
            ("推荐一款饮品", "query_recommend"),
            ("这款多少钱", "query_price"),
            ("有优惠吗", "query_promotion"),
            ("可以加珍珠吗", "query_customize"),
            ("刚才那款叫什么", "query_menu"),
        ],
        "check_response": lambda r: "珍珠奶茶" in r or "柠檬水" in r or "葡萄" in r or "推荐" in r
    },
    {
        "name": "7轮上下文记忆",
        "dialogue": [
            ("我在光谷", "query_location"),
            ("附近有什么店", "query_location"),
            ("菜单有什么", "query_menu"),
            ("推荐一款", "query_recommend"),
            ("多少钱", "query_price"),
            ("有优惠吗", "query_promotion"),
            ("光谷那家店有吗", "query_location"),
        ],
        "check_response": lambda r: "光谷" in r or "店" in r
    },
]

window_sizes = [1, 3, 5, 7, 10]

results = {}

for window_size in window_sizes:
    print(f"\n{'='*60}")
    print(f"测试窗口大小: {window_size} 轮")
    print(f"{'='*60}")
    
    total_correct = 0
    total_time = 0
    scenario_results = []
    
    for scenario in test_scenarios:
        memory_store = create_memory_store(window_size=window_size)
        session_id = f"mem_test_{window_size}_{scenario['name']}"
        
        start_time = time.time()
        
        for i, (user_msg, _) in enumerate(scenario["dialogue"]):
            response, _ = process_message(user_msg, session_id, memory_store)
            
            if i == len(scenario["dialogue"]) - 1:
                is_correct = scenario["check_response"](response)
                elapsed = (time.time() - start_time) * 1000
                total_time += elapsed
                total_correct += 1 if is_correct else 0
                
                status = "✓" if is_correct else "✗"
                print(f"{status} {scenario['name']}: {elapsed:.2f}ms - {response[:60]}...")
                
                scenario_results.append({
                    "scenario": scenario["name"],
                    "correct": is_correct,
                    "response": response,
                    "time_ms": elapsed
                })
    
    accuracy = total_correct / len(test_scenarios) * 100
    avg_time = total_time / len(test_scenarios)
    
    print(f"\n窗口大小 {window_size} 轮:")
    print(f"  准确率: {accuracy:.2f}% ({total_correct}/{len(test_scenarios)})")
    print(f"  平均耗时: {avg_time:.2f}ms")
    
    results[window_size] = {
        "accuracy": accuracy,
        "correct": total_correct,
        "total": len(test_scenarios),
        "avg_time_ms": avg_time,
        "scenario_results": scenario_results
    }

print(f"\n{'='*60}")
print("实验结果汇总")
print(f"{'='*60}")
print(f"{'窗口大小':<10} {'准确率':<10} {'平均耗时':<10}")
print(f"{'-'*35}")
for ws in window_sizes:
    r = results[ws]
    print(f"{ws:<10} {r['accuracy']:<10.2f}% {r['avg_time_ms']:<10.2f}ms")

output_path = 'reports/memory_window_experiment.json'
os.makedirs('reports', exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n实验结果已保存到: {output_path}")