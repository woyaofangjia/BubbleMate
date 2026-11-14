import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import bubble_agent
from backend.core.prompt_loader import render_prompt
from backend.core.zhipu_client import DEFAULT_MODEL, LLM_PROVIDER, call_llm, is_available
from scripts.token_cost_analysis import count_tokens

DATASETS = {
    "test_set_200": ROOT / "data" / "test_set_200.json",
    "heldout_30": ROOT / "data" / "heldout_test_set_v4.json",
    "fallback_18": ROOT / "data" / "prompt_fallback_test_set.json",
}
PRICE_PER_1K_TOKENS = 0.002


def load_samples(path, max_samples=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = data.get("samples", []) if isinstance(data, dict) else data
    normalized = []
    for sample in samples:
        text = sample.get("user_query", sample.get("query", sample.get("text", "")))
        if text and sample.get("intent"):
            normalized.append({"text": text, "intent": sample["intent"]})
    return normalized[:max_samples] if max_samples else normalized


def new_metrics():
    return {"total": 0, "correct": 0, "llm_calls": 0, "llm_failures": 0,
            "latencies": [], "tokens": 0, "errors": []}


def finalize(metrics):
    latencies = sorted(metrics.pop("latencies"))
    total = metrics["total"]
    metrics["accuracy"] = round(metrics["correct"] / total * 100, 2) if total else 0
    metrics["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2) if latencies else 0
    p95_index = max(0, math.ceil(len(latencies) * 0.95) - 1)
    metrics["p95_latency_ms"] = round(latencies[p95_index], 2) if latencies else 0
    metrics["estimated_total_tokens"] = metrics.pop("tokens")
    metrics["estimated_cost"] = round(metrics["estimated_total_tokens"] / 1000 * PRICE_PER_1K_TOKENS, 6)
    return metrics


def evaluate_prompt(samples, version):
    metrics = new_metrics()
    for sample in samples:
        prompt = render_prompt(version=version, name="intent_classify", text=sample["text"],
                               intent_list=", ".join(bubble_agent.INTENT_KEYWORDS.keys()))
        start = time.perf_counter()
        response = ""
        try:
            response = call_llm([{"role": "user", "content": prompt}], model=DEFAULT_MODEL,
                                max_tokens=20, temperature=0.1)
            predicted = response.strip().strip("'\"")
            metrics["correct"] += predicted == sample["intent"]
        except Exception as exc:
            metrics["llm_failures"] += 1
            if len(metrics["errors"]) < 10:
                metrics["errors"].append(str(exc))
        metrics["llm_calls"] += 1
        metrics["latencies"].append((time.perf_counter() - start) * 1000)
        metrics["tokens"] += count_tokens(prompt) + count_tokens(response)
        metrics["total"] += 1
    return finalize(metrics)


def evaluate_hybrid(samples):
    metrics = new_metrics()
    original_call = bubble_agent.zhipu_client.call_llm

    def measured_call(messages, model=None, max_tokens=500, temperature=0.7):
        response = ""
        try:
            response = original_call(messages, model=model, max_tokens=max_tokens, temperature=temperature)
            return response
        except Exception as exc:
            metrics["llm_failures"] += 1
            if len(metrics["errors"]) < 10:
                metrics["errors"].append(str(exc))
            raise
        finally:
            metrics["llm_calls"] += 1
            metrics["tokens"] += count_tokens("\n".join(m["content"] for m in messages)) + count_tokens(response)

    bubble_agent.zhipu_client.call_llm = measured_call
    try:
        for sample in samples:
            bubble_agent.clear_intent_cache()
            start = time.perf_counter()
            result = bubble_agent.recognize_intent(sample["text"])
            metrics["latencies"].append((time.perf_counter() - start) * 1000)
            metrics["correct"] += result["name"] == sample["intent"]
            metrics["total"] += 1
    finally:
        bubble_agent.zhipu_client.call_llm = original_call
    return finalize(metrics)


def main():
    parser = argparse.ArgumentParser(description="当前模型prompt与混合链路基线")
    parser.add_argument("--max-samples", type=int, help="每个数据集最多运行的样本数，用于冒烟验证")
    parser.add_argument("--output", help="自定义报告路径")
    args = parser.parse_args()
    if not is_available():
        raise SystemExit("LLM客户端不可用，请检查LLM_PROVIDER、LLM_MODEL和API Key")

    version = os.getenv("PROMPT_VERSION", "v1")
    results = {}
    for name, path in DATASETS.items():
        samples = load_samples(path, args.max_samples)
        if not samples:
            raise ValueError(f"数据集为空或字段无法识别: {path}")
        print(f"[{name}] prompt直测 {len(samples)} 条")
        prompt_metrics = evaluate_prompt(samples, version)
        print(f"[{name}] 混合链路 {len(samples)} 条")
        hybrid_metrics = evaluate_hybrid(samples)
        results[name] = {"sample_count": len(samples), "prompt": prompt_metrics, "hybrid": hybrid_metrics}
        print(f"  prompt={prompt_metrics['accuracy']}%, hybrid={hybrid_metrics['accuracy']}%, "
              f"hybrid_llm_calls={hybrid_metrics['llm_calls']}")

    report = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "provider": LLM_PROVIDER,
              "model": DEFAULT_MODEL, "prompt_name": "intent_classify", "prompt_version": version,
              "token_and_cost_note": "Token为字符估算，成本按每千Token 0.002元估算",
              "results": results}
    safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "_", DEFAULT_MODEL)
    output = Path(args.output) if args.output else ROOT / "reports" / f"baseline_{time.strftime('%Y%m%d')}_{safe_model}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已保存: {output}")
    failures = sum(metrics["llm_failures"] for result in results.values()
                   for metrics in (result["prompt"], result["hybrid"]))
    if failures:
        raise SystemExit(f"基线存在 {failures} 次LLM调用失败，请查看报告errors")


if __name__ == "__main__":
    main()
