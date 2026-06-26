"""
BubbleMate - 纯LLM Baseline测试
对比：纯大模型（Zero-shot）vs 完整Agent
"""

import json
import os
import time
from typing import Dict, List, Tuple

# 尝试导入智谱AI
try:
    from backend.core.zhipu_client import call_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    print("警告: 智谱AI未配置，使用模拟模式")

# 测试数据集
TEST_CASES = [
    {"id": "TC-001", "query": "这个杨枝甘露也太甜了吧，我要的少糖啊", "intent": "complaint_taste", "expected_keywords": ["道歉", "补偿", "下次调整"]},
    {"id": "TC-002", "query": "糯米少得可怜，别的店都满满一碗", "intent": "complaint_quantity", "expected_keywords": ["道歉", "份量", "核实"]},
    {"id": "TC-003", "query": "超时40分钟，打电话还没人接", "intent": "complaint_delivery", "expected_keywords": ["超时", "道歉", "补偿"]},
    {"id": "TC-004", "query": "给我推荐一款不甜的好喝的", "intent": "query_recommend", "expected_keywords": ["推荐", "无糖", "低糖"]},
    {"id": "TC-005", "query": "退款", "intent": "complaint_refund", "expected_keywords": ["订单号", "退款"]},
    {"id": "TC-006", "query": "芝芝莓莓太酸了", "intent": "complaint_taste", "expected_keywords": ["道歉", "酸", "退款"]},
    {"id": "TC-007", "query": "光谷附近有店吗", "intent": "query_store", "expected_keywords": ["光谷", "门店", "地址"]},
    {"id": "TC-008", "query": "你们家最贵的是哪个", "intent": "query_price", "expected_keywords": ["价格", "最贵"]},
    {"id": "TC-009", "query": "送达时洒了一半", "intent": "complaint_delivery", "expected_keywords": ["洒", "道歉", "退款"]},
    {"id": "TC-010", "query": "请问你们几点关门啊", "intent": "query_hours", "expected_keywords": ["营业", "关门", "时间"]},
    {"id": "TC-011", "query": "葡萄汁酸到发抖，是不是坏掉了", "intent": "complaint_hygiene", "expected_keywords": ["停止饮用", "安全", "补偿"]},
    {"id": "TC-012", "query": "你们家最近有第二杯半价吗", "intent": "query_promotion", "expected_keywords": ["优惠", "第二杯半价", "活动"]},
    {"id": "TC-013", "query": "上次买了幽兰拿铁，这次怎么没有了", "intent": "query_menu", "expected_keywords": ["下架", "售罄", "推荐"]},
    {"id": "TC-014", "query": "能不能帮我查一下我上次点的是什么", "intent": "query_order", "expected_keywords": ["订单号", "手机号", "查询"]},
    {"id": "TC-015", "query": "少糖的杨枝甘露多少钱", "intent": "query_price", "expected_keywords": ["价格", "杨枝甘露"]},
    {"id": "TC-016", "query": "门店在哪", "intent": "query_store", "expected_keywords": ["门店", "地址", "位置"]},
    {"id": "TC-017", "query": "冰块太多了", "intent": "complaint_quantity", "expected_keywords": ["冰块", "份量", "道歉"]},
    {"id": "TC-018", "query": "可以开发票吗", "intent": "query_invoice", "expected_keywords": ["发票", "开票"]},
    {"id": "TC-019", "query": "会员卡怎么办理", "intent": "query_member", "expected_keywords": ["会员", "办理", "积分"]},
    {"id": "TC-020", "query": "投诉", "intent": "complaint_general", "expected_keywords": ["投诉", "订单号", "描述"]},
]

def call_pure_llm(query: str) -> str:
    """直接调用LLM，不使用任何工具或意图识别"""
    if not HAS_LLM:
        # 模拟LLM回复
        return "您好，请问有什么可以帮助您的？"

    prompt = f"""你是一个奶茶店客服。用户说："{query}"

请直接回复用户的问题。如果用户投诉，要道歉并承诺处理。如果用户咨询，要提供准确信息。不要说"我可以帮您..."，直接回答。"""

    try:
        response = call_llm([{"role": "user", "content": prompt}], max_tokens=200, temperature=0.7)
        return response
    except Exception as e:
        print(f"LLM调用失败: {e}")
        return "抱歉，系统暂时无法处理您的请求。"

def evaluate_response(query: str, response: str, expected_keywords: List[str]) -> Dict:
    """评估LLM回复质量"""
    response_lower = response.lower()

    # 检查关键词匹配
    matched_keywords = [kw for kw in expected_keywords if kw.lower() in response_lower]
    keyword_match_rate = len(matched_keywords) / len(expected_keywords) if expected_keywords else 0

    # 检查是否为合理回复（不是默认回复）
    is_reasonable = keyword_match_rate > 0 or len(response) > 20

    # 检查是否包含道歉（投诉类）
    has_apology = any(word in response for word in ["抱歉", "对不起", "非常抱歉", "不好意思"])

    # 基础评估
    score = 0
    if keyword_match_rate >= 0.5:
        score = 1  # 良好
    elif keyword_match_rate >= 0.3:
        score = 0.5  # 一般
    else:
        score = 0  # 较差

    return {
        "matched_keywords": matched_keywords,
        "keyword_match_rate": round(keyword_match_rate, 2),
        "is_reasonable": is_reasonable,
        "has_apology": has_apology,
        "score": score,
        "is_correct": score >= 0.5
    }

def run_baseline_test():
    """运行纯LLM Baseline测试"""
    print("=" * 60)
    print("BubbleMate - 纯LLM Baseline测试")
    print("对比: 纯大模型(Zero-shot) vs 完整Agent")
    print("=" * 60)

    if not HAS_LLM:
        print("⚠️  警告: 智谱AI未配置，使用模拟数据")
    else:
        print(f"✅ 智谱AI已配置: glm-4-flash")

    print()

    results = []
    correct = 0
    total = len(TEST_CASES)

    for tc in TEST_CASES:
        print(f"测试 [{tc['id']}] {tc['query']}")

        # 调用纯LLM
        start_time = time.time()
        response = call_pure_llm(tc['query'])
        elapsed = (time.time() - start_time) * 1000

        # 评估回复
        eval_result = evaluate_response(tc['query'], response, tc['expected_keywords'])

        status = "✓" if eval_result['is_correct'] else "✗"
        print(f"  {status} 意图: {tc['intent']}, 匹配率: {eval_result['keyword_match_rate']:.0%}, 耗时: {elapsed:.0f}ms")
        if not eval_result['is_correct']:
            print(f"     期望关键词: {tc['expected_keywords']}")
            print(f"     匹配关键词: {eval_result['matched_keywords']}")
            print(f"     LLM回复: {response[:50]}...")

        results.append({
            "id": tc['id'],
            "query": tc['query'],
            "intent": tc['intent'],
            "response": response,
            **eval_result,
            "elapsed_ms": round(elapsed, 2)
        })

        if eval_result['is_correct']:
            correct += 1

        print()

    # 汇总统计
    accuracy = correct / total * 100
    avg_keyword_rate = sum(r['keyword_match_rate'] for r in results) / total
    avg_time = sum(r['elapsed_ms'] for r in results) / total

    print("=" * 60)
    print("Baseline测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {total}")
    print(f"正确数: {correct}")
    print(f"准确率: {accuracy:.1f}%")
    print(f"平均关键词匹配率: {avg_keyword_rate:.1%}")
    print(f"平均响应时间: {avg_time:.0f}ms")

    # 按意图分组统计
    intent_stats = {}
    for r in results:
        intent = r['intent']
        if intent not in intent_stats:
            intent_stats[intent] = {"total": 0, "correct": 0}
        intent_stats[intent]["total"] += 1
        if r['is_correct']:
            intent_stats[intent]["correct"] += 1

    print()
    print("按意图分组:")
    for intent, stats in intent_stats.items():
        rate = stats['correct'] / stats['total'] * 100
        print(f"  {intent}: {rate:.0f}% ({stats['correct']}/{stats['total']})")

    # 保存结果
    report = {
        "test_type": "pure_llm_baseline",
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 2),
        "avg_keyword_match_rate": round(avg_keyword_rate, 2),
        "avg_response_time_ms": round(avg_time, 2),
        "intent_stats": intent_stats,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    }

    os.makedirs("data", exist_ok=True)
    with open("data/llm_baseline_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print()
    print(f"报告已保存: data/llm_baseline_report.json")

    return report

if __name__ == "__main__":
    report = run_baseline_test()
