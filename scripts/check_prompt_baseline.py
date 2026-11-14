import argparse
import json
from pathlib import Path


def compare_reports(baseline, current, max_accuracy_drop=2.0, max_p95_regression=20.0):
    failures = []
    if baseline.get("model") != current.get("model"):
        failures.append(f"模型不一致: baseline={baseline.get('model')}, current={current.get('model')}")
    if baseline.get("provider") != current.get("provider"):
        failures.append(f"Provider不一致: baseline={baseline.get('provider')}, current={current.get('provider')}")

    for dataset, base_result in baseline.get("results", {}).items():
        current_result = current.get("results", {}).get(dataset)
        if not current_result:
            failures.append(f"{dataset}: 缺少当前评测结果")
            continue
        if current_result.get("sample_count") != base_result.get("sample_count"):
            failures.append(f"{dataset}: 样本数变化 {base_result.get('sample_count')} -> {current_result.get('sample_count')}")

        for mode in ("prompt", "hybrid"):
            base = base_result[mode]
            now = current_result[mode]
            accuracy_drop = base["accuracy"] - now["accuracy"]
            if accuracy_drop > max_accuracy_drop:
                failures.append(f"{dataset}/{mode}: 准确率下降 {accuracy_drop:.2f}pp "
                                f"({base['accuracy']:.2f}% -> {now['accuracy']:.2f}%)")
            if now.get("llm_failures", 0) != 0:
                failures.append(f"{dataset}/{mode}: LLM失败 {now['llm_failures']} 次")
            if mode == "prompt" and now.get("llm_calls") != now.get("total"):
                failures.append(f"{dataset}/{mode}: prompt未逐条调用 ({now.get('llm_calls')}/{now.get('total')})")

        for mode in ("prompt", "hybrid" if dataset.startswith("fallback") else None):
            if mode is None:
                continue
            base_p95 = base_result[mode].get("p95_latency_ms", 0)
            now_p95 = current_result[mode].get("p95_latency_ms", 0)
            if base_p95 > 0 and now_p95 > base_p95 * (1 + max_p95_regression / 100):
                failures.append(f"{dataset}/{mode}: P95劣化超过{max_p95_regression:.0f}% "
                                f"({base_p95:.2f}ms -> {now_p95:.2f}ms)")
        print(f"{dataset}: prompt {base_result['prompt']['accuracy']:.2f}% -> "
              f"{current_result['prompt']['accuracy']:.2f}%, hybrid "
              f"{base_result['hybrid']['accuracy']:.2f}% -> {current_result['hybrid']['accuracy']:.2f}%")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Prompt评测基线门禁")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--max-accuracy-drop", type=float, default=2.0)
    parser.add_argument("--max-p95-regression", type=float, default=20.0)
    args = parser.parse_args()
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    current = json.loads(Path(args.current).read_text(encoding="utf-8"))
    failures = compare_reports(baseline, current, args.max_accuracy_drop, args.max_p95_regression)
    if failures:
        print("Prompt门禁失败:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("Prompt门禁通过：准确率、LLM成功率和P95均符合阈值")


if __name__ == "__main__":
    main()
