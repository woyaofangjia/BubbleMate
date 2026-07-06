"""
BubbleMate - 增强版分层评估系统
支持：Easy/Medium/Hard分层评测，Baseline对比，对抗样本分析
"""

import json
import time
import os
import sys
from typing import Dict, List, Tuple

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入意图识别器
try:
    from backend.agent.intent_recognizer_v2 import IntentRecognizerV2
    HAS_INTENT_RECOGNIZER = True
except ImportError as e:
    HAS_INTENT_RECOGNIZER = False
    print(f"警告: 意图识别器导入失败: {e}")

# 尝试导入完整Agent组件（用于回复质量评估）
try:
    from backend.agent.react_agent_v2 import ReActAgentV2
    from backend.agent.memory_manager_v2 import MemoryManagerV2
    from backend.tools.bubble_tools import TOOL_REGISTRY
    HAS_AGENT = True
except ImportError as e:
    HAS_AGENT = False
    print(f"提示: 完整Agent组件导入失败（缺少requests），仅测试意图识别: {e}")

# 尝试导入LLM
HAS_LLM = False
if os.getenv("ZHIPUAI_API_KEY", ""):
    try:
        from backend.core.zhipu_client import call_llm
        HAS_LLM = True
    except (ImportError, Exception):
        pass

if not HAS_LLM:
    print("提示: 智谱AI未配置或无API Key，使用纯规则模式测试")

def load_test_data():
    """加载测试数据集"""
    test_path = "data/test_set_200.json"
    if os.path.exists(test_path):
        with open(test_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["samples"]
    return []

def call_pure_llm(query: str) -> str:
    """纯LLM回复（Baseline）"""
    if not HAS_LLM:
        return "模拟回复"

    prompt = f"""你是一个奶茶店客服。用户说："{query}"
直接回复，不要说"我可以帮您..."。"""

    try:
        return call_llm([{"role": "user", "content": prompt}], max_tokens=200, temperature=0.7)
    except:
        return "系统暂时无法处理"

def call_intent_recognizer(query: str, recognizer) -> Dict:
    """调用意图识别器"""
    if not recognizer:
        return {"intent": "unknown", "confidence": 0}
    
    try:
        intent = recognizer.recognize(query)
        return {"intent": intent.name, "confidence": intent.confidence}
    except Exception as e:
        print(f"意图识别错误: {e}")
        return {"intent": "error", "confidence": 0}

def call_agent(query: str, agent=None) -> Tuple[str, Dict]:
    """调用Agent获取回复"""
    if not HAS_AGENT or agent is None:
        return "Agent未配置", {"intent": "unknown", "confidence": 0}

    try:
        response = agent.process(query)
        intent = agent.intent_recognizer.recognize(query)
        return response, {"intent": intent.name, "confidence": intent.confidence}
    except Exception as e:
        return f"Agent错误: {e}", {"intent": "error", "confidence": 0}

def evaluate_intent_match(predicted: str, expected: str) -> float:
    """评估意图匹配"""
    if predicted == expected:
        return 1.0
    # 部分匹配（投诉类）
    if predicted.startswith("complaint") and expected.startswith("complaint"):
        return 0.5
    return 0.0

def evaluate_response(response: str, expected_keywords: List[str]) -> float:
    """评估回复质量"""
    response_lower = response.lower()
    if not expected_keywords:
        return 0.5
    matches = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    return matches / len(expected_keywords)

def run_stratified_evaluation(samples: List[Dict], agent=None, recognizer=None, use_llm_baseline: bool = False) -> Dict:
    """分层评估"""
    results = {
        "total": len(samples),
        "by_difficulty": {"easy": [], "medium": [], "hard": []},
        "by_intent": {},
        "adversarial": [],
        "timestamps": []
    }

    for sample in samples:
        query = sample["user_query"]
        expected_intent = sample["intent"]
        difficulty = sample["difficulty"]
        keywords = sample.get("keywords", [])
        is_adversarial = sample.get("adversarial_type") is not None

        # 优先使用完整Agent，否则使用意图识别器
        if HAS_AGENT and agent:
            agent_response, intent_info = call_agent(query, agent)
            response_score = evaluate_response(agent_response, keywords)
        else:
            intent_info = call_intent_recognizer(query, recognizer)
            response_score = 0.5

        # 意图匹配
        intent_score = evaluate_intent_match(intent_info["intent"], expected_intent)

        # 综合得分
        final_score = intent_score * 0.7 + response_score * 0.3
        is_correct = final_score >= 0.5

        result = {
            "id": sample["id"],
            "query": query,
            "expected_intent": expected_intent,
            "predicted_intent": intent_info["intent"],
            "confidence": intent_info["confidence"],
            "intent_score": intent_score,
            "response_score": response_score,
            "final_score": round(final_score, 2),
            "is_correct": is_correct,
            "requires_clarification": sample.get("requires_clarification", False),
            "adversarial_type": sample.get("adversarial_type")
        }

        # 按难度分组
        results["by_difficulty"][difficulty].append(result)

        # 按意图分组
        if expected_intent not in results["by_intent"]:
            results["by_intent"][expected_intent] = []
        results["by_intent"][expected_intent].append(result)

        # 对抗样本
        if is_adversarial:
            results["adversarial"].append(result)

    # 计算分层统计
    stats = {}
    for diff, items in results["by_difficulty"].items():
        correct = sum(1 for r in items if r["is_correct"])
        total = len(items)
        stats[diff] = {
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0
        }

    # 意图统计
    intent_stats = {}
    for intent, items in results["by_intent"].items():
        correct = sum(1 for r in items if r["is_correct"])
        total = len(items)
        intent_stats[intent] = {
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total > 0 else 0
        }

    # 对抗样本统计
    adversarial_stats = {"total": len(results["adversarial"]), "correct": sum(1 for r in results["adversarial"] if r["is_correct"])}
    adversarial_stats["accuracy"] = round(adversarial_stats["correct"] / adversarial_stats["total"] * 100, 1) if adversarial_stats["total"] > 0 else 0

    # 对抗类型分析
    adversarial_by_type = {}
    for r in results["adversarial"]:
        adv_type = r["adversarial_type"]
        if adv_type not in adversarial_by_type:
            adversarial_by_type[adv_type] = {"total": 0, "correct": 0}
        adversarial_by_type[adv_type]["total"] += 1
        if r["is_correct"]:
            adversarial_by_type[adv_type]["correct"] += 1

    for adv_type, stat in adversarial_by_type.items():
        stat["accuracy"] = round(stat["correct"] / stat["total"] * 100, 1)

    results["stats"] = {
        "overall": {
            "total": len(samples),
            "correct": sum(1 for r in results["by_difficulty"]["easy"] + results["by_difficulty"]["medium"] + results["by_difficulty"]["hard"] if r["is_correct"]),
            "accuracy": 0
        },
        "by_difficulty": stats,
        "by_intent": intent_stats,
        "adversarial": adversarial_stats,
        "adversarial_by_type": adversarial_by_type
    }

    results["stats"]["overall"]["accuracy"] = round(
        results["stats"]["overall"]["correct"] / results["stats"]["overall"]["total"] * 100, 1
    )

    return results

def print_report(results: Dict):
    """打印评估报告"""
    print("=" * 70)
    print("BubbleMate - 增强版分层评估报告")
    print("=" * 70)

    # 整体统计
    overall = results["stats"]["overall"]
    print(f"\n【整体评测】")
    print(f"  测试样本数: {overall['total']}")
    print(f"  正确数: {overall['correct']}")
    print(f"  整体准确率: {overall['accuracy']}%")

    # 分层统计
    print(f"\n【分层评测】")
    for diff in ["easy", "medium", "hard"]:
        stat = results["stats"]["by_difficulty"].get(diff, {})
        emoji = {"easy": "😊", "medium": "😐", "hard": "😰"}[diff]
        print(f"  {emoji} {diff.upper():6s}: {stat.get('accuracy', 0):5.1f}% ({stat.get('correct', 0)}/{stat.get('total', 0)})")

    # 对抗样本统计
    print(f"\n【对抗样本分析】")
    adv_stat = results["stats"]["adversarial"]
    print(f"  对抗样本数: {adv_stat['total']}")
    print(f"  通过数: {adv_stat['correct']}")
    print(f"  通过率: {adv_stat['accuracy']}%")

    if results["stats"]["adversarial_by_type"]:
        print("  按类型:")
        for adv_type, stat in results["stats"]["adversarial_by_type"].items():
            print(f"    - {adv_type}: {stat['accuracy']}% ({stat['correct']}/{stat['total']})")

    # 意图统计（只显示Top 5和Bottom 5）
    print(f"\n【意图准确率 Top 5】")
    sorted_intents = sorted(results["stats"]["by_intent"].items(), key=lambda x: x[1]["accuracy"], reverse=True)
    for intent, stat in sorted_intents[:5]:
        print(f"  ✓ {intent}: {stat['accuracy']}% ({stat['correct']}/{stat['total']})")

    print(f"\n【意图准确率 Bottom 5】")
    for intent, stat in sorted_intents[-5:]:
        print(f"  ✗ {intent}: {stat['accuracy']}% ({stat['correct']}/{stat['total']})")

    # Bad Case示例
    print(f"\n【Bad Case示例】")
    all_results = results["by_difficulty"]["easy"] + results["by_difficulty"]["medium"] + results["by_difficulty"]["hard"]
    bad_cases = [r for r in all_results if not r["is_correct"]][:5]
    for bc in bad_cases:
        print(f"  ✗ [{bc['id']}] {bc['query'][:30]}...")
        print(f"     期望: {bc['expected_intent']}, 预测: {bc['predicted_intent']}, 得分: {bc['final_score']}")

def main():
    print("=" * 70)
    print("BubbleMate 增强版评测系统启动")
    print("=" * 70)

    # 加载测试数据
    samples = load_test_data()
    if not samples:
        print("错误: 无法加载测试数据，请先运行 generate_test_data.py")
        return

    print(f"\n加载测试数据: {len(samples)} 条")

    # 初始化意图识别器（优先）
    recognizer = None
    if HAS_INTENT_RECOGNIZER:
        print("初始化意图识别器...")
        try:
            recognizer = IntentRecognizerV2("data", use_llm=HAS_LLM)
            print(f"意图识别器初始化成功 (LLM模式: {HAS_LLM})")
        except Exception as e:
            print(f"意图识别器初始化失败: {e}")

    # 初始化完整Agent（如果可用）
    agent = None
    if HAS_AGENT:
        print("初始化Agent组件...")
        try:
            tools = {k: v["handler"] for k, v in TOOL_REGISTRY.items()}
            ir = IntentRecognizerV2("data", use_llm=HAS_LLM)
            mm = MemoryManagerV2(use_redis=False)
            agent = ReActAgentV2(tools, ir, mm)
            print("Agent初始化成功")
        except Exception as e:
            print(f"Agent初始化失败: {e}")

    # 运行分层评估
    print("\n运行分层评估...")
    results = run_stratified_evaluation(samples, agent, recognizer)

    # 打印报告
    print_report(results)

    # 保存报告
    report = {
        "test_type": "stratified_evaluation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_samples": len(samples),
        "stats": results["stats"],
        "bad_cases": [r for r in (results["by_difficulty"]["easy"] + results["by_difficulty"]["medium"] + results["by_difficulty"]["hard"]) if not r["is_correct"]]
    }

    os.makedirs("data", exist_ok=True)
    report_path = "data/stratified_eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n评估报告已保存: {report_path}")

    # 对比Baseline
    if HAS_LLM and HAS_AGENT:
        print("\n" + "=" * 70)
        print("【Baseline对比分析】")
        print("=" * 70)
        print("  纯LLM Baseline: ~45-55% (估计值，需配置智谱API)")
        print(f"  完整Agent: {results['stats']['overall']['accuracy']}%")
        improvement = results['stats']['overall']['accuracy'] - 50  # 假设Baseline为50%
        if improvement > 0:
            print(f"  提升: +{improvement:.1f}%")
        print("\n  注: 如需精确Baseline数据，运行 scripts/llm_baseline_test.py")

if __name__ == "__main__":
    main()
