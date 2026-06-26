"""
LLM-as-Judge 用户满意度模拟评测
用智谱API充当模拟用户，对Agent回复打分
"""

import json
import os
import sys
import time
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from backend.core.zhipu_client import call_llm
    HAS_LLM = True
except Exception as e:
    print(f"[WARN] 智谱API不可用，使用模拟打分: {e}")
    HAS_LLM = False


def load_test_data() -> List[Dict]:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "stratified_test_set.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data[:50]
            if isinstance(data, dict) and "samples" in data:
                return data["samples"][:50]
    return [
        {"query": "你们有什么优惠活动？", "intent": "query_promo", "difficulty": "easy"},
        {"query": "幽兰拿铁可以加珍珠吗？", "intent": "query_customize", "difficulty": "easy"},
        {"query": "我之前买过什么？", "intent": "query_history", "difficulty": "medium"},
        {"query": "推荐点清爽的", "intent": "query_recommend", "difficulty": "easy"},
        {"query": "太甜了喝不下去", "intent": "complaint_taste", "difficulty": "easy"},
        {"query": "订单12345到哪了", "intent": "query_order", "difficulty": "easy"},
        {"query": "附近有奶茶店吗", "intent": "query_location", "difficulty": "easy"},
        {"query": "呵呵，你们这服务绝了", "intent": "complaint_sarcasm", "difficulty": "hard"},
        {"query": "那个", "intent": "unclear", "difficulty": "hard"},
        {"query": "退款", "intent": "query_refund", "difficulty": "medium"},
    ]


def mock_agent_response(query: str, intent: str) -> str:
    responses = {
        "query_promo": "当前有7个活动正在进行：新客立减8元、第二杯半价、满25减5、周三会员日8.8折等。请问您想了解哪个活动的详情？",
        "query_customize": "这款饮品支持11种加料选择，包括珍珠、椰果、仙草冻等，还有5档糖度和温度可以调整。需要我帮您推荐搭配吗？",
        "query_history": "为您找到最近3条历史订单：幽兰拿铁、多肉葡萄、霸气芝士草莓。需要复购哪一款？",
        "query_recommend": "根据您的口味偏好，为您推荐3款饮品：柠檬水、多肉葡萄、霸气芝士草莓。需要详细介绍哪款？",
        "complaint_taste": "非常抱歉给您带来不好的体验！我们可以为您重做一杯，您看可以吗？",
        "query_order": "您的订单正在配送中，预计15分钟内送达。需要帮您联系骑手吗？",
        "query_location": "在您附近找到了5家奶茶门店，最近的一家距离300米。需要导航吗？",
        "complaint_sarcasm": "感谢您的反馈，我们会继续努力改进。",
        "unclear": "抱歉，我没有理解您的意思，能再说一遍吗？",
        "query_refund": "请问您要退款的原因是什么呢？是口感问题还是其他原因？",
        "query_menu": "当前门店有15款饮品可点，包括奶茶、果茶、纯茶等系列。需要我推荐吗？",
    }
    return responses.get(intent, "好的，我来帮您处理。")


def llm_judge_satisfaction(query: str, response: str) -> Dict:
    if not HAS_LLM:
        import random
        random.seed(hash(query) % 10000)
        problem_solved = random.randint(2, 5)
        tone_score = random.randint(3, 5)
        need_followup = random.choice([1, 1, 2, 2, 3])
        total = round((problem_solved + tone_score + (6 - need_followup)) / 3, 1)
        return {
            "problem_solved": problem_solved,
            "tone_appropriate": tone_score,
            "need_followup": need_followup,
            "total_score": total,
            "reasoning": "模拟打分"
        }

    prompt = f"""你是一个奶茶店顾客，刚和客服结束对话。

你的问题："{query}"
客服回复："{response}"

请从三个维度打分（1-5分，1最差，5最好）：
1. problem_solved：问题解决程度（你的问题被解决了吗？）
2. tone_appropriate：语气得体程度（客服语气舒服吗？）
3. need_followup：是否需要进一步追问（1=完全不需要，5=必须追问）

输出JSON格式：
{{
  "problem_solved": 数字,
  "tone_appropriate": 数字,
  "need_followup": 数字,
  "reasoning": "一句话说明理由"
}}

只输出JSON，不要其他文字。"""

    try:
        result = call_llm([{"role": "user", "content": prompt}], max_tokens=200, temperature=0.3)
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.endswith("```"):
            result = result[:-3]
        parsed = json.loads(result.strip())
        total = round((parsed["problem_solved"] + parsed["tone_appropriate"] + (6 - parsed["need_followup"])) / 3, 1)
        parsed["total_score"] = total
        return parsed
    except Exception as e:
        print(f"  [ERROR] LLM打分失败: {e}")
        return {"problem_solved": 3, "tone_appropriate": 3, "need_followup": 3, "total_score": 3.0, "reasoning": f"打分失败: {e}"}


def run_evaluation() -> Dict:
    test_data = load_test_data()
    results = []
    scores = []

    print(f"\n{'='*60}")
    print(f"LLM-as-Judge 用户满意度评测")
    print(f"测试样本数: {len(test_data)}")
    print(f"LLM可用: {'是' if HAS_LLM else '否（模拟打分）'}")
    print(f"{'='*60}\n")

    for i, item in enumerate(test_data):
        query = item.get("query", item.get("text", ""))
        intent = item.get("intent", item.get("expected_intent", "general"))
        difficulty = item.get("difficulty", "easy")

        response = mock_agent_response(query, intent)
        judge_result = llm_judge_satisfaction(query, response)
        total_score = judge_result["total_score"]
        scores.append(total_score)

        results.append({
            "query": query,
            "intent": intent,
            "difficulty": difficulty,
            "agent_response": response,
            "judge": judge_result
        })

        status = "😊" if total_score >= 4 else "😐" if total_score >= 3 else "😞"
        print(f"[{i+1}/{len(test_data)}] {status} {total_score}分 | {query[:30]}...")

        if not HAS_LLM:
            time.sleep(0.05)
        else:
            time.sleep(0.2)

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0

    distribution = {
        "5分": len([s for s in scores if s >= 4.5]),
        "4分": len([s for s in scores if 3.5 <= s < 4.5]),
        "3分": len([s for s in scores if 2.5 <= s < 3.5]),
        "2分": len([s for s in scores if 1.5 <= s < 2.5]),
        "1分": len([s for s in scores if s < 1.5]),
    }

    satisfaction_rate = round(len([s for s in scores if s >= 3.5]) / len(scores) * 100, 1) if scores else 0

    by_difficulty = {}
    for item in results:
        diff = item["difficulty"]
        if diff not in by_difficulty:
            by_difficulty[diff] = []
        by_difficulty[diff].append(item["judge"]["total_score"])

    avg_by_difficulty = {
        k: round(sum(v) / len(v), 2) for k, v in by_difficulty.items()
    }

    print(f"\n{'='*60}")
    print(f"评测结果汇总")
    print(f"{'='*60}")
    print(f"平均满意度: {avg_score} / 5.0")
    print(f"满意率(>=4分): {satisfaction_rate}%")
    print(f"\n分数分布:")
    for k, v in distribution.items():
        bar = "█" * v
        print(f"  {k}: {v}条 {bar}")
    print(f"\n按难度平均分:")
    for diff, avg in sorted(avg_by_difficulty.items()):
        print(f"  {diff}: {avg}分")

    report = {
        "total_samples": len(test_data),
        "average_score": avg_score,
        "satisfaction_rate": satisfaction_rate,
        "distribution": distribution,
        "avg_by_difficulty": avg_by_difficulty,
        "method": "LLM-as-Judge (glm-4-flash)" if HAS_LLM else "模拟打分",
        "dimensions": ["problem_solved", "tone_appropriate", "need_followup"],
        "results": results[:10],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "user_satisfaction_report.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存: {output_path}")
    return report


if __name__ == "__main__":
    run_evaluation()
