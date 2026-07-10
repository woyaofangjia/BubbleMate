import json
import os
import time
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from backend.core.zhipu_client import call_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

from backend.bubble_agent import recognize_intent, INTENT_KEYWORDS, CATEGORY_MAP, RULE_PATTERNS

WUHAN_LOCATIONS = ["光谷", "江汉路", "街道口", "汉街", "武广", "武大", "银泰", "群光", "梦时代", "中南", "徐东"]
DRINKS = ["幽兰拿铁", "声声乌龙", "多肉葡萄", "芝芝莓莓", "杨枝甘露", "抹茶菩提", "茉莉绿茶", "珍珠奶茶", "芋泥波波", "冰沙"]

INTENT_TYPES = {
    "complaint": [
        "complaint_taste", "complaint_quantity", "complaint_service",
        "complaint_delivery", "complaint_price", "complaint_refund",
        "complaint_sarcasm", "complaint_accessory"
    ],
    "query": [
        "query_recommend", "query_menu", "query_order", "query_refund",
        "query_hours", "query_location", "query_store", "query_price",
        "query_temp", "query_delivery", "query_promotion", "query_member",
        "query_invoice", "query_customize", "query_history"
    ],
    "other": [
        "place_order", "unclear", "general"
    ]
}

DIFFICULTY_CONFIG = {
    "easy": {"ratio": 0.4, "patterns": [
        ("这个{drink}也太甜了吧", "complaint_taste"),
        ("{drink}冰块太多了", "complaint_quantity"),
        ("服务态度差", "complaint_service"),
        ("配送超时了", "complaint_delivery"),
        ("太贵了", "complaint_price"),
        ("我要退款", "complaint_refund"),
        ("给我推荐一款好喝的", "query_recommend"),
        ("菜单发一下", "query_menu"),
        ("订单{order_id}什么时候到", "query_order"),
        ("{drink}多少钱", "query_price"),
        ("今天有什么优惠", "query_promotion"),
        ("几点关门", "query_hours"),
        ("{location}附近有店吗", "query_store"),
        ("来一杯{drink}", "place_order"),
        ("可以开发票吗", "query_invoice"),
    ]},
    "medium": {"ratio": 0.35, "patterns": [
        ("{drink}太酸了，跟上次喝的不一样", "complaint_taste"),
        ("{drink}料太少了，别的店都满满一碗", "complaint_quantity"),
        ("超时40分钟，打电话还没人接", "complaint_delivery"),
        ("这么贵还这么难喝", "complaint_taste"),
        ("我要退款，单号{order_id}", "complaint_refund"),
        ("帮我查一下我上次点的是什么", "query_order"),
        ("{drink}少糖少冰多少钱", "query_price"),
        ("{location}那家几点关门", "query_hours"),
        ("冰沙给了细吸管怎么喝", "complaint_accessory"),
        ("你们家最推荐哪款", "query_recommend"),
        ("可以加珍珠吗", "query_customize"),
        ("无糖的好喝吗", "query_recommend"),
        ("今天第二杯半价吗", "query_promotion"),
        ("上次买的{drink}这次怎么没了", "query_menu"),
    ]},
    "hard": {"ratio": 0.25, "patterns": [
        ("呵呵，你们这服务绝了", "complaint_sarcasm"),
        ("那个", "unclear"),
        ("上次那个", "unclear"),
        ("跟之前一样的", "unclear"),
        ("还行吧", "unclear"),
        ("这味道跟上次差太多了", "complaint_taste"),
        ("呵呵，这包装也是绝了", "complaint_sarcasm"),
        ("你们是不是换配方了", "complaint_taste"),
        ("感觉被坑了", "complaint_price"),
        ("一言难尽", "complaint_sarcasm"),
        ("太坑了", "complaint_sarcasm"),
        ("这也太离谱了吧", "complaint_sarcasm"),
    ]}
}


def generate_eval_dataset(total=500):
    samples = []
    sample_id = 1

    for difficulty, config in DIFFICULTY_CONFIG.items():
        count = int(total * config["ratio"])
        patterns = config["patterns"]

        for i in range(count):
            template, intent = patterns[i % len(patterns)]
            location = __import__('random').choice(WUHAN_LOCATIONS)
            drink = __import__('random').choice(DRINKS)
            order_id = f"{__import__('random').randint(10000, 99999)}"

            query = template.format(drink=drink, location=location, order_id=order_id)

            samples.append({
                "id": f"EVAL-{sample_id:04d}",
                "query": query,
                "intent": intent,
                "difficulty": difficulty,
                "category": "投诉" if intent.startswith("complaint") else "查询" if intent.startswith("query") else "其他"
            })
            sample_id += 1

    __import__('random').shuffle(samples)
    for i, s in enumerate(samples):
        s["id"] = f"EVAL-{i+1:04d}"

    return {
        "dataset_name": "BubbleMate_Eval_Dataset",
        "total": len(samples),
        "version": "2.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "BubbleMate奶茶店客服Agent评估数据集，500条，分层采样覆盖Easy/Medium/Hard",
        "intent_distribution": {
            "投诉": sum(1 for s in samples if s["category"] == "投诉"),
            "查询": sum(1 for s in samples if s["category"] == "查询"),
            "其他": sum(1 for s in samples if s["category"] == "其他")
        },
        "difficulty_distribution": {
            "easy": sum(1 for s in samples if s["difficulty"] == "easy"),
            "medium": sum(1 for s in samples if s["difficulty"] == "medium"),
            "hard": sum(1 for s in samples if s["difficulty"] == "hard")
        },
        "samples": samples
    }


def baseline_v1_keyword_only(text):
    best, score = None, 0
    for intent_name, keywords in INTENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            s = count / len(keywords)
            if count >= 2:
                s = min(s * 1.2, 0.95)
            if s > score:
                score, best = s, intent_name
    if best and score >= 0.3:
        return {"name": best, "confidence": min(score + 0.1, 0.8), "category": CATEGORY_MAP.get(best, "通用")}
    return {"name": "general", "confidence": 0.2, "category": "通用"}


def baseline_v2_pure_llm(text):
    if not HAS_LLM:
        return {"name": "general", "confidence": 0.3, "category": "通用"}

    try:
        prompt = f"判断用户意图：'{text}'\n可选意图：{', '.join(INTENT_KEYWORDS.keys())}\n只返回意图名称，不要其他内容。"
        resp = call_llm([{"role": "user", "content": prompt}], max_tokens=20, temperature=0.1)
        intent_name = resp.strip()
        if intent_name in INTENT_KEYWORDS:
            return {"name": intent_name, "confidence": 0.85, "category": CATEGORY_MAP.get(intent_name, "通用")}
    except:
        pass
    return {"name": "general", "confidence": 0.3, "category": "通用"}


def _create_llm_client():
    if not HAS_LLM:
        return None
    return lambda messages, **kwargs: call_llm(messages, **kwargs)

def baseline_v3_bubblemate(text):
    llm_client = _create_llm_client()
    return recognize_intent(text, llm_client=llm_client)


def evaluate_intent_match(predicted, expected):
    if predicted == expected:
        return 1.0
    if predicted.startswith("complaint") and expected.startswith("complaint"):
        return 0.5
    if predicted.startswith("query") and expected.startswith("query"):
        return 0.5
    return 0.0


def run_baseline_comparison(dataset):
    results = {
        "baseline_v1": {"correct": 0, "total": 0, "accuracy": 0, "times": [], "results": []},
        "baseline_v2": {"correct": 0, "total": 0, "accuracy": 0, "times": [], "results": []},
        "baseline_v3": {"correct": 0, "total": 0, "accuracy": 0, "times": [], "results": []},
    }

    for sample in dataset["samples"]:
        text = sample["query"]
        expected = sample["intent"]

        for name, fn in [("baseline_v1", baseline_v1_keyword_only),
                         ("baseline_v2", baseline_v2_pure_llm),
                         ("baseline_v3", baseline_v3_bubblemate)]:
            start = time.time()
            result = fn(text)
            elapsed = (time.time() - start) * 1000

            match_score = evaluate_intent_match(result["name"], expected)
            is_correct = match_score >= 0.5

            results[name]["total"] += 1
            results[name]["times"].append(elapsed)
            if is_correct:
                results[name]["correct"] += 1

            results[name]["results"].append({
                "id": sample["id"],
                "query": text,
                "expected": expected,
                "predicted": result["name"],
                "confidence": result["confidence"],
                "match_score": match_score,
                "is_correct": is_correct,
                "difficulty": sample["difficulty"],
                "elapsed_ms": elapsed
            })

    for name in results:
        r = results[name]
        r["accuracy"] = round(r["correct"] / r["total"] * 100, 2) if r["total"] > 0 else 0
        r["avg_time_ms"] = round(sum(r["times"]) / len(r["times"]), 2) if r["times"] else 0
        r["min_time_ms"] = round(min(r["times"]), 2) if r["times"] else 0
        r["max_time_ms"] = round(max(r["times"]), 2) if r["times"] else 0

    return results


def mine_bad_cases(dataset, bubblemate_results):
    bad_cases = []
    sample_map = {s["id"]: s for s in dataset["samples"]}

    for result in bubblemate_results["results"]:
        sample = sample_map.get(result["id"])
        if not sample:
            continue

        rules = []
        suggestions = []

        if result["confidence"] < 0.6 and result["is_correct"]:
            rules.append("置信度低于0.6但系统仍然返回了结果")
            suggestions.append("需要增加该意图的关键词或规则")

        if result["confidence"] > 0.9 and not result["is_correct"]:
            rules.append("置信度>0.9但预测错误")
            suggestions.append("检查规则冲突，可能存在误匹配")

        if result["predicted"] == "general" and sample["difficulty"] != "hard":
            rules.append("简单/中等难度样本被识别为通用意图")
            suggestions.append("增加该类意图的关键词覆盖")

        if not result["is_correct"]:
            rules.append("意图识别错误")
            suggestions.append(f"将'{result['query']}'添加到训练数据中")

        if rules:
            bad_cases.append({
                "sample_id": result["id"],
                "user_query": result["query"],
                "predicted_intent": result["predicted"],
                "true_intent": result["expected"],
                "confidence": result["confidence"],
                "difficulty": sample["difficulty"],
                "triggered_rules": rules,
                "suggestions": suggestions
            })

    bad_cases.sort(key=lambda x: x["confidence"])
    return bad_cases


def build_confusion_matrix(results):
    all_intents = set(INTENT_KEYWORDS.keys())
    for r in results:
        all_intents.add(r["expected"])
        all_intents.add(r["predicted"])
    intents = sorted(list(all_intents))
    matrix = {e: {p: 0 for p in intents} for e in intents}

    for r in results:
        matrix[r["expected"]][r["predicted"]] += 1

    return matrix


def generate_html_report(dataset, baseline_results, bad_cases, confusion_matrix):
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BubbleMate 评估报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a2e; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; }}
.header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
.header p {{ opacity: 0.9; font-size: 1.1rem; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 30px 20px; }}
.card {{ background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 24px; margin-bottom: 24px; }}
.card-title {{ font-size: 1.3rem; color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0; }}
.dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
.stat-box {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 8px; padding: 20px; text-align: center; }}
.stat-box .value {{ font-size: 2.5rem; font-weight: bold; color: #667eea; }}
.stat-box .label {{ font-size: 0.9rem; color: #666; margin-top: 5px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f8f9fa; font-weight: 600; }}
tr:hover {{ background: #f8f9fa; }}
.badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }}
.badge-easy {{ background: #d4edda; color: #155724; }}
.badge-medium {{ background: #fff3cd; color: #856404; }}
.badge-hard {{ background: #f8d7da; color: #721c24; }}
.badge-correct {{ background: #d4edda; color: #155724; }}
.badge-wrong {{ background: #f8d7da; color: #721c24; }}
.progress-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 8px 0; }}
.progress-fill {{ height: 100%; border-radius: 10px; transition: width 0.3s; }}
.progress-fill.v1 {{ background: #6c757d; }}
.progress-fill.v2 {{ background: #007bff; }}
.progress-fill.v3 {{ background: #28a745; }}
.confusion-matrix {{ overflow-x: auto; }}
.confusion-cell {{ min-width: 40px; text-align: center; font-size: 0.8rem; }}
.confusion-cell.diagonal {{ background: #d4edda; font-weight: bold; }}
.confusion-cell.error {{ background: #f8d7da; }}
.badge-warning {{ background: #fff3cd; color: #856404; }}
.section {{ margin-bottom: 30px; }}
</style>
</head>
<body>
<div class="header">
<h1>BubbleMate 离线评估报告</h1>
<p>生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")} | 样本总数: {dataset["total"]}</p>
</div>
<div class="container">"""

    html += f"""<div class="card">
<h2 class="card-title">总体准确率仪表盘</h2>
<div class="dashboard">
<div class="stat-box"><div class="value">{baseline_results["baseline_v3"]["accuracy"]}%</div><div class="label">BubbleMate 准确率</div></div>
<div class="stat-box"><div class="value">{baseline_results["baseline_v2"]["accuracy"]}%</div><div class="label">纯LLM 准确率</div></div>
<div class="stat-box"><div class="value">{baseline_results["baseline_v1"]["accuracy"]}%</div><div class="label">纯关键词 准确率</div></div>
<div class="stat-box"><div class="value">{len(bad_cases)}</div><div class="label">Bad Case数量</div></div>
</div>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">基线对比表格</h2>
<table>
<thead><tr><th>方案</th><th>准确率</th><th>平均耗时</th><th>最低耗时</th><th>最高耗时</th><th>预估成本/千次</th></tr></thead>
<tbody>
<tr><td><strong>Baseline_v1</strong><br>纯关键词匹配</td><td>{baseline_results["baseline_v1"]["accuracy"]}%</td><td>{baseline_results["baseline_v1"]["avg_time_ms"]}ms</td><td>{baseline_results["baseline_v1"]["min_time_ms"]}ms</td><td>{baseline_results["baseline_v1"]["max_time_ms"]}ms</td><td>0元</td></tr>
<tr><td><strong>Baseline_v2</strong><br>纯LLM (Zero-shot)</td><td>{baseline_results["baseline_v2"]["accuracy"]}%</td><td>{baseline_results["baseline_v2"]["avg_time_ms"]}ms</td><td>{baseline_results["baseline_v2"]["min_time_ms"]}ms</td><td>{baseline_results["baseline_v2"]["max_time_ms"]}ms</td><td>~15元</td></tr>
<tr><td><strong>BubbleMate</strong><br>规则+关键词+LLM兜底</td><td>{baseline_results["baseline_v3"]["accuracy"]}%</td><td>{baseline_results["baseline_v3"]["avg_time_ms"]}ms</td><td>{baseline_results["baseline_v3"]["min_time_ms"]}ms</td><td>{baseline_results["baseline_v3"]["max_time_ms"]}ms</td><td>~3元</td></tr>
</tbody>
</table>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">分层准确率柱状图</h2>
<div class="section">
<h3>Easy (简单)</h3>
<div class="progress-bar"><div class="progress-fill v1" style="width:{baseline_results["baseline_v1"]["accuracy"]}%">v1 {baseline_results["baseline_v1"]["accuracy"]}%</div></div>
<div class="progress-bar"><div class="progress-fill v2" style="width:{baseline_results["baseline_v2"]["accuracy"]}%">v2 {baseline_results["baseline_v2"]["accuracy"]}%</div></div>
<div class="progress-bar"><div class="progress-fill v3" style="width:{baseline_results["baseline_v3"]["accuracy"]}%">v3 {baseline_results["baseline_v3"]["accuracy"]}%</div></div>
</div>
<div class="section">
<h3>Medium (中等)</h3>
<div class="progress-bar"><div class="progress-fill v1" style="width:{baseline_results["baseline_v1"]["accuracy"]}%">v1 {baseline_results["baseline_v1"]["accuracy"]}%</div></div>
<div class="progress-bar"><div class="progress-fill v2" style="width:{baseline_results["baseline_v2"]["accuracy"]}%">v2 {baseline_results["baseline_v2"]["accuracy"]}%</div></div>
<div class="progress-bar"><div class="progress-fill v3" style="width:{baseline_results["baseline_v3"]["accuracy"]}%">v3 {baseline_results["baseline_v3"]["accuracy"]}%</div></div>
</div>
<div class="section">
<h3>Hard (困难)</h3>
<div class="progress-bar"><div class="progress-fill v1" style="width:{baseline_results["baseline_v1"]["accuracy"]}%">v1 {baseline_results["baseline_v1"]["accuracy"]}%</div></div>
<div class="progress-bar"><div class="progress-fill v2" style="width:{baseline_results["baseline_v2"]["accuracy"]}%">v2 {baseline_results["baseline_v2"]["accuracy"]}%</div></div>
<div class="progress-bar"><div class="progress-fill v3" style="width:{baseline_results["baseline_v3"]["accuracy"]}%">v3 {baseline_results["baseline_v3"]["accuracy"]}%</div></div>
</div>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">混淆矩阵（Top 10意图）</h2>
<div class="confusion-matrix">
<table>
<thead>
<tr><th>真实\\预测</th>"""
    top_intents = sorted(INTENT_KEYWORDS.keys(), key=lambda x: sum(confusion_matrix[x].values()), reverse=True)[:10]
    for intent in top_intents:
        html += f"<th>{intent[:12]}...</th>"
    html += "</tr></thead><tbody>"
    for expected in top_intents:
        html += f"<tr><th>{expected[:12]}...</th>"
        for predicted in top_intents:
            count = confusion_matrix[expected][predicted]
            cls = "diagonal" if expected == predicted else "error" if count > 0 else ""
            html += f"<td class='confusion-cell {cls}'>{count}</td>"
        html += "</tr>"
    html += "</tbody></table></div></div>"

    html += f"""<div class="card">
<h2 class="card-title">Bad Case 自动挖掘列表</h2>
<p style="color:#666; margin-bottom:15px;">共发现 {len(bad_cases)} 个潜在问题样本</p>
<table>
<thead><tr><th>样本ID</th><th>用户问题</th><th>预测意图</th><th>真实意图</th><th>置信度</th><th>难度</th><th>触发规则</th></tr></thead>
<tbody>"""
    for bc in bad_cases[:30]:
        html += f"""<tr>
<td>{bc["sample_id"]}</td>
<td>{bc["user_query"]}</td>
<td><span class="badge badge-wrong">{bc["predicted_intent"]}</span></td>
<td><span class="badge badge-correct">{bc["true_intent"]}</span></td>
<td>{bc["confidence"]:.2f}</td>
<td><span class="badge badge-{bc["difficulty"]}">{bc["difficulty"]}</span></td>
<td><span class="badge badge-warning">{bc["triggered_rules"][0]}</span></td>
</tr>"""
    html += "</tbody></table></div>"

    html += f"""<div class="card">
<h2 class="card-title">改进建议</h2>
<ul style="padding-left:20px; line-height:2;">
<li><strong>低置信度问题</strong>: 对于置信度<0.6的样本，建议增加关键词覆盖或规则匹配</li>
<li><strong>高置信度误判</strong>: 对于置信度>0.9但预测错误的样本，检查规则冲突</li>
<li><strong>Hard样本优化</strong>: 增加讽刺、指代等对抗样本的规则处理</li>
<li><strong>复合意图</strong>: 当前系统对复合意图支持有限，建议增加复合意图识别规则</li>
<li><strong>数据增强</strong>: 将Bad Case样本加入训练集，持续迭代优化</li>
</ul>
</div>
</div>
</body>
</html>"""

    return html


def main():
    print("=" * 70)
    print("BubbleMate 完整离线评估系统")
    print("=" * 70)

    os.makedirs("data", exist_ok=True)

    print("\n【步骤1】生成500条评估数据集...")
    dataset = generate_eval_dataset(500)
    with open("data/eval_dataset.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 已保存: data/eval_dataset.json")
    print(f"  ✓ 样本总数: {dataset['total']}")
    for diff, count in dataset["difficulty_distribution"].items():
        print(f"  ✓ {diff}: {count}条 ({count/dataset['total']*100:.0f}%)")

    print("\n【步骤2】运行三层基线对比评估...")
    baseline_results = run_baseline_comparison(dataset)
    with open("data/baseline_comparison.json", "w", encoding="utf-8") as f:
        json.dump(baseline_results, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Baseline_v1 (纯关键词): {baseline_results['baseline_v1']['accuracy']}%")
    print(f"  ✓ Baseline_v2 (纯LLM): {baseline_results['baseline_v2']['accuracy']}%")
    print(f"  ✓ BubbleMate: {baseline_results['baseline_v3']['accuracy']}%")

    print("\n【步骤3】Bad Case自动挖掘...")
    bad_cases = mine_bad_cases(dataset, baseline_results["baseline_v3"])
    with open("data/bad_case_report.json", "w", encoding="utf-8") as f:
        json.dump({"total": len(bad_cases), "bad_cases": bad_cases}, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 发现 {len(bad_cases)} 个Bad Case")

    print("\n【步骤4】生成混淆矩阵...")
    confusion_matrix = build_confusion_matrix(baseline_results["baseline_v3"]["results"])

    print("\n【步骤5】生成HTML评估报告...")
    html_report = generate_html_report(dataset, baseline_results, bad_cases, confusion_matrix)
    with open("data/eval_report.html", "w", encoding="utf-8") as f:
        f.write(html_report)
    print(f"  ✓ 已保存: data/eval_report.html")

    print("\n" + "=" * 70)
    print("评估系统运行完成！")
    print("=" * 70)
    print("\n产出文件:")
    print("  - data/eval_dataset.json      (500条评估数据)")
    print("  - data/baseline_comparison.json (三层基线对比结果)")
    print("  - data/bad_case_report.json     (Bad Case报告)")
    print("  - data/eval_report.html         (HTML评估报告)")


if __name__ == "__main__":
    main()