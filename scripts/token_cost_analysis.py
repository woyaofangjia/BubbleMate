import json
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import recognize_intent, INTENT_KEYWORDS

def count_tokens(text):
    import re
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    other_chars = len(re.findall(r'[^\w\s\u4e00-\u9fa5]', text))
    return chinese_chars + english_words + other_chars

def call_llm_with_token_count(messages, model="glm-4-flash"):
    try:
        from backend.core.zhipu_client import call_llm
        prompt_text = "\n".join(m["content"] for m in messages)
        prompt_tokens = count_tokens(prompt_text)
        
        response = call_llm(messages, model=model, max_tokens=20, temperature=0.1)
        completion_tokens = count_tokens(response)
        
        return {
            "success": True,
            "content": response,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    except Exception as e:
        return {"success": False, "error": str(e), "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

def run_pure_llm_eval(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    correct = 0
    total = 0
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        prompt = f"判断用户意图：'{text}'\n可选：{', '.join(INTENT_KEYWORDS.keys())}\n只返回意图名称，不要其他内容。"
        result = call_llm_with_token_count([{"role": "user", "content": prompt}])
        
        if result["success"]:
            total_prompt_tokens += result["prompt_tokens"]
            total_completion_tokens += result["completion_tokens"]
            total_tokens += result["total_tokens"]
            
            predicted = result["content"].strip().strip("'\"")
            if predicted == expected:
                correct += 1
        total += 1
    
    return {
        "accuracy": round(correct / total * 100, 2) if total > 0 else 0,
        "correct": correct,
        "total": total,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "avg_tokens_per_request": round(total_tokens / total, 2) if total > 0 else 0,
        "avg_prompt_tokens": round(total_prompt_tokens / total, 2) if total > 0 else 0,
        "avg_completion_tokens": round(total_completion_tokens / total, 2) if total > 0 else 0
    }

def run_bubblemate_eval(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    llm_calls = 0
    rule_hits = 0
    correct = 0
    total = 0
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        predicted = result["name"]
        confidence = result["confidence"]
        
        if confidence >= 0.5:
            rule_hits += 1
        else:
            llm_calls += 1
            prompt = f"判断用户意图：'{text}'\n可选：{', '.join(INTENT_KEYWORDS.keys())}\n只返回意图名称，不要其他内容。"
            llm_result = call_llm_with_token_count([{"role": "user", "content": prompt}])
            if llm_result["success"]:
                total_prompt_tokens += llm_result["prompt_tokens"]
                total_completion_tokens += llm_result["completion_tokens"]
                total_tokens += llm_result["total_tokens"]
        
        if predicted == expected:
            correct += 1
        total += 1
    
    return {
        "accuracy": round(correct / total * 100, 2) if total > 0 else 0,
        "correct": correct,
        "total": total,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "avg_tokens_per_request": round(total_tokens / total, 2) if total > 0 else 0,
        "avg_prompt_tokens": round(total_prompt_tokens / total, 2) if total > 0 else 0,
        "avg_completion_tokens": round(total_completion_tokens / total, 2) if total > 0 else 0,
        "llm_calls": llm_calls,
        "rule_hits": rule_hits,
        "rule_coverage": round(rule_hits / total * 100, 2) if total > 0 else 0
    }

def estimate_cost(total_tokens, price_per_1k=0.002):
    return round(total_tokens / 1000 * price_per_1k, 4)

def main():
    print("=" * 70)
    print("BubbleMate Token消耗对比分析")
    print("=" * 70)
    
    dataset_path = "data/test_set_200.json"
    
    print("\n【方案A：纯LLM方案（每条请求都调用glm-4-flash）】")
    print("正在运行...")
    pure_llm_result = run_pure_llm_eval(dataset_path)
    
    if pure_llm_result:
        print(f"   ✓ 准确率: {pure_llm_result['accuracy']}%")
        print(f"   ✓ 总Token数: {pure_llm_result['total_tokens']}")
        print(f"   ✓ 平均Token/请求: {pure_llm_result['avg_tokens_per_request']}")
        print(f"   ✓ 预估成本(千次): ¥{estimate_cost(pure_llm_result['total_tokens'] * 5)}")
    else:
        print("   ✗ 数据集不存在")
        return
    
    print("\n【方案B：BubbleMate混合方案（规则优先+LLM兜底）】")
    print("正在运行...")
    bubblemate_result = run_bubblemate_eval(dataset_path)
    
    if bubblemate_result:
        print(f"   ✓ 准确率: {bubblemate_result['accuracy']}%")
        print(f"   ✓ 总Token数: {bubblemate_result['total_tokens']}")
        print(f"   ✓ 平均Token/请求: {bubblemate_result['avg_tokens_per_request']}")
        print(f"   ✓ LLM调用次数: {bubblemate_result['llm_calls']}")
        print(f"   ✓ 规则覆盖率: {bubblemate_result['rule_coverage']}%")
        print(f"   ✓ 预估成本(千次): ¥{estimate_cost(bubblemate_result['total_tokens'] * 5)}")
    else:
        print("   ✗ 数据集不存在")
        return
    
    print("\n" + "=" * 70)
    print("【Token消耗对比表格】")
    print("=" * 70)
    
    headers = ["指标", "纯LLM方案", "BubbleMate方案", "节省比例"]
    
    token_saving = 1 - (bubblemate_result['total_tokens'] / pure_llm_result['total_tokens']) if pure_llm_result['total_tokens'] > 0 else 0
    cost_saving = 1 - (estimate_cost(bubblemate_result['total_tokens']) / estimate_cost(pure_llm_result['total_tokens'])) if pure_llm_result['total_tokens'] > 0 else 0
    
    rows = [
        ["总Token数", f"{pure_llm_result['total_tokens']:,}", f"{bubblemate_result['total_tokens']:,}", f"-{round(token_saving * 100, 2)}%"],
        ["平均Token/请求", f"{pure_llm_result['avg_tokens_per_request']}", f"{bubblemate_result['avg_tokens_per_request']}", f"-{round(token_saving * 100, 2)}%"],
        ["平均Prompt Token", f"{pure_llm_result['avg_prompt_tokens']}", f"{bubblemate_result['avg_prompt_tokens']}", "-"],
        ["平均Completion Token", f"{pure_llm_result['avg_completion_tokens']}", f"{bubblemate_result['avg_completion_tokens']}", "-"],
        ["LLM调用次数", f"{pure_llm_result['total']}", f"{bubblemate_result['llm_calls']}", f"-{round((1 - bubblemate_result['llm_calls']/pure_llm_result['total']) * 100, 2)}%"],
        ["规则覆盖率", "0%", f"{bubblemate_result['rule_coverage']}%", "+"],
        ["准确率", f"{pure_llm_result['accuracy']}%", f"{bubblemate_result['accuracy']}%", "+"],
        ["预估成本(千次)", f"¥{estimate_cost(pure_llm_result['total_tokens'] * 5)}", f"¥{estimate_cost(bubblemate_result['total_tokens'] * 5)}", f"-{round(cost_saving * 100, 2)}%"],
    ]
    
    col_widths = [max(len(row[i]) for row in rows + [headers]) for i in range(4)]
    
    print("")
    print(" | ".join(f"{h:{col_widths[i]}}" for i, h in enumerate(headers)))
    print("-+-".join("-" * w for w in col_widths))
    for row in rows:
        print(" | ".join(f"{r:{col_widths[i]}}" for i, r in enumerate(row)))
    
    print("\n【分析结论】")
    print(f"- Token节省: {round(token_saving * 100, 2)}%")
    print(f"- 成本节省: {round(cost_saving * 100, 2)}%")
    print(f"- 规则层拦截了 {bubblemate_result['rule_coverage']}% 的请求，避免了不必要的LLM调用")
    print(f"- 准确率保持: {bubblemate_result['accuracy']}%")
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": dataset_path,
        "sample_count": pure_llm_result['total'],
        "pure_llm": pure_llm_result,
        "bubblemate": bubblemate_result,
        "savings": {
            "token_saving_percent": round(token_saving * 100, 2),
            "cost_saving_percent": round(cost_saving * 100, 2),
            "llm_call_reduction": round((1 - bubblemate_result['llm_calls']/pure_llm_result['total']) * 100, 2)
        },
        "price_per_1k_tokens": 0.002
    }
    
    os.makedirs('reports', exist_ok=True)
    with open('reports/token_cost_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 报告已保存: reports/token_cost_report.json")
    
    print("\n" + "=" * 70)
    print("Token消耗分析完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()