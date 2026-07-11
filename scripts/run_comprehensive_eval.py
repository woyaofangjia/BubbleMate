import json
import os
import sys
import time
import sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import recognize_intent, process_message, create_memory_store

def run_intent_eval(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    correct = 0
    total = len(samples)
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        predicted = result['name']
        
        if predicted == expected:
            correct += 1
    
    return {
        'accuracy': round(correct / total * 100, 2),
        'correct': correct,
        'total': total
    }

def run_classification_report(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    from collections import defaultdict
    
    y_true = []
    y_pred = []
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        predicted = result['name']
        
        y_true.append(expected)
        y_pred.append(predicted)
    
    all_intents = sorted(set(y_true + y_pred))
    
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    
    for true, pred in zip(y_true, y_pred):
        if true == pred:
            tp[true] += 1
        else:
            fp[pred] += 1
            fn[true] += 1
    
    intent_stats = {}
    for intent in all_intents:
        precision = tp[intent] / (tp[intent] + fp[intent]) if (tp[intent] + fp[intent]) > 0 else 0
        recall = tp[intent] / (tp[intent] + fn[intent]) if (tp[intent] + fn[intent]) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        support = tp[intent] + fn[intent]
        
        intent_stats[intent] = {
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'support': support,
            'tp': tp[intent],
            'fp': fp[intent],
            'fn': fn[intent]
        }
    
    macro_precision = sum(v['precision'] for v in intent_stats.values()) / len(intent_stats) if intent_stats else 0
    macro_recall = sum(v['recall'] for v in intent_stats.values()) / len(intent_stats) if intent_stats else 0
    macro_f1 = sum(v['f1_score'] for v in intent_stats.values()) / len(intent_stats) if intent_stats else 0
    
    weighted_precision = sum(v['precision'] * v['support'] for v in intent_stats.values()) / len(y_true) if y_true else 0
    weighted_recall = sum(v['recall'] * v['support'] for v in intent_stats.values()) / len(y_true) if y_true else 0
    weighted_f1 = sum(v['f1_score'] * v['support'] for v in intent_stats.values()) / len(y_true) if y_true else 0
    
    worst_intents = sorted(intent_stats.items(), key=lambda x: x[1]['f1_score'])[:3]
    
    confusion_matrix = []
    for true_intent in all_intents:
        row = []
        for pred_intent in all_intents:
            count = sum(1 for t, p in zip(y_true, y_pred) if t == true_intent and p == pred_intent)
            row.append(count)
        confusion_matrix.append(row)
    
    return {
        'intent_stats': intent_stats,
        'macro_avg': {
            'precision': round(macro_precision, 4),
            'recall': round(macro_recall, 4),
            'f1_score': round(macro_f1, 4),
            'support': len(y_true)
        },
        'weighted_avg': {
            'precision': round(weighted_precision, 4),
            'recall': round(weighted_recall, 4),
            'f1_score': round(weighted_f1, 4),
            'support': len(y_true)
        },
        'worst_intents': [{'intent': k, **v} for k, v in worst_intents],
        'confusion_matrix': {
            'labels': all_intents,
            'matrix': confusion_matrix
        },
        'total_samples': len(y_true)
    }

def run_rule_coverage(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    rule_hits = 0
    llm_fallback = 0
    cache_hits = 0
    total = 0
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        
        if not text:
            continue
        
        result = recognize_intent(text)
        confidence = result['confidence']
        
        if confidence >= 0.5:
            rule_hits += 1
        else:
            llm_fallback += 1
        total += 1
    
    return {
        'total_requests': total,
        'rule_hits': rule_hits,
        'llm_fallback': llm_fallback,
        'rule_coverage': round(rule_hits / total * 100, 2) if total > 0 else 0,
        'llm_fallback_rate': round(llm_fallback / total * 100, 2) if total > 0 else 0
    }

def run_tool_eval():
    test_cases = [
        {'query': '订单12345', 'expected_tool': 'query_order', 'expected_clarify': False},
        {'query': '查询订单', 'expected_tool': 'query_order', 'expected_clarify': True},
        {'query': '光谷附近的店', 'expected_tool': 'query_stores', 'expected_clarify': False},
        {'query': '附近有店吗', 'expected_tool': 'query_stores', 'expected_clarify': True},
        {'query': '推荐一款', 'expected_tool': 'query_menu', 'expected_clarify': False},
        {'query': '看看菜单', 'expected_tool': 'query_menu', 'expected_clarify': False},
        {'query': '奶茶太甜了', 'expected_tool': 'log_complaint', 'expected_clarify': False},
        {'query': '退款', 'expected_tool': 'query_order', 'expected_clarify': True},
        {'query': '', 'expected_tool': '', 'expected_clarify': True},
    ]
    
    memory_store = create_memory_store(window_size=5)
    passed = 0
    
    for case in test_cases:
        result = recognize_intent(case['query'])
        response, _ = process_message(case['query'], 'eval-test', memory_store)
        
        tool_map = {
            'query_order': ['query_order'],
            'query_refund': ['query_order'],
            'query_location': ['query_stores'],
            'query_store': ['query_stores'],
            'query_menu': ['query_menu'],
            'query_recommend': ['query_menu'],
            'complaint_taste': ['log_complaint'],
            'complaint_quantity': ['log_complaint'],
            'complaint_service': ['log_complaint'],
            'complaint_delivery': ['log_complaint'],
            'complaint_price': ['log_complaint'],
            'complaint_refund': ['log_complaint'],
            'complaint_sarcasm': [],
            'complaint_vague': [],
            'general': [],
            'unknown': [],
            'unclear': [],
        }
        
        predicted_tools = tool_map.get(result['name'], [])
        has_clarify = '?' in response or '请问' in response or '提供' in response
        
        tool_ok = (case['expected_tool'] in predicted_tools) if case['expected_tool'] else (len(predicted_tools) == 0)
        clarify_ok = has_clarify == case['expected_clarify']
        
        if tool_ok and clarify_ok:
            passed += 1
    
    return {
        'accuracy': round(passed / len(test_cases) * 100, 2),
        'passed': passed,
        'total': len(test_cases)
    }

def run_confidence_calibration(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    buckets = {}
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        predicted = result['name']
        confidence = result['confidence']
        
        bucket = round(confidence * 10) / 10
        if bucket not in buckets:
            buckets[bucket] = {'correct': 0, 'total': 0}
        buckets[bucket]['total'] += 1
        if predicted == expected:
            buckets[bucket]['correct'] += 1
    
    calibration = []
    for bucket in sorted(buckets.keys()):
        stats = buckets[bucket]
        accuracy = stats['correct'] / stats['total'] * 100
        calibration.append({
            'confidence_bucket': bucket,
            'accuracy': round(accuracy, 2),
            'samples': stats['total']
        })
    
    return calibration

def run_bad_case_mining(dataset_path, threshold=0.6):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    bad_cases = []
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        predicted = result['name']
        confidence = result['confidence']
        
        issues = []
        if confidence < threshold:
            issues.append('低置信度(<0.6)')
        if predicted != expected:
            issues.append('意图识别错误')
        
        if issues:
            bad_cases.append({
                'text': text,
                'expected': expected,
                'predicted': predicted,
                'confidence': round(confidence, 2),
                'issues': issues
            })
    
    bad_cases.sort(key=lambda x: x['confidence'])
    return bad_cases

def run_five_fold_cv(dataset_path):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    import random
    random.shuffle(samples)
    
    fold_size = len(samples) // 5
    fold_results = []
    
    for i in range(5):
        start = i * fold_size
        end = start + fold_size
        if i == 4:
            end = len(samples)
        
        test_set = samples[start:end]
        
        correct = 0
        for sample in test_set:
            text = sample.get('user_query', sample.get('query', sample.get('text', '')))
            expected = sample.get('intent', '')
            if not text or not expected:
                continue
            result = recognize_intent(text)
            if result['name'] == expected:
                correct += 1
        
        fold_results.append({
            'fold': i + 1,
            'accuracy': round(correct / len(test_set) * 100, 2),
            'correct': correct,
            'total': len(test_set)
        })
    
    avg_accuracy = sum(r['accuracy'] for r in fold_results) / len(fold_results)
    return {
        'fold_results': fold_results,
        'avg_accuracy': round(avg_accuracy, 2)
    }

def run_adversarial_eval():
    adversarial_cases = [
        {'text': '呵呵，你们这服务绝了', 'intent': 'complaint_sarcasm'},
        {'text': '那个', 'intent': 'unclear'},
        {'text': '上次那个', 'intent': 'unclear'},
        {'text': '跟之前一样的', 'intent': 'unclear'},
        {'text': '还行吧', 'intent': 'unclear'},
        {'text': '这味道跟上次差太多了', 'intent': 'complaint_taste'},
        {'text': '呵呵，这包装也是绝了', 'intent': 'complaint_sarcasm'},
        {'text': '你们是不是换配方了', 'intent': 'complaint_taste'},
        {'text': '感觉被坑了', 'intent': 'complaint_price'},
        {'text': '一言难尽', 'intent': 'complaint_sarcasm'},
        {'text': '太坑了', 'intent': 'complaint_sarcasm'},
        {'text': '这也太离谱了吧', 'intent': 'complaint_sarcasm'},
    ]
    
    correct = 0
    for case in adversarial_cases:
        result = recognize_intent(case['text'])
        if result['name'] == case['intent']:
            correct += 1
    
    return {
        'accuracy': round(correct / len(adversarial_cases) * 100, 2),
        'correct': correct,
        'total': len(adversarial_cases)
    }

def check_db_indexes():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'bubblemate.db')
    if not os.path.exists(db_path):
        return {'error': 'Database not found'}
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    tables = ['shops', 'menu_items', 'orders', 'inventory']
    indexes = {}
    
    for table in tables:
        c.execute(f"SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
        idx_result = c.fetchall()
        indexes[table] = [idx[1] for idx in idx_result]
    
    conn.close()
    return indexes

def generate_html_report(all_results):
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BubbleMate 综合测试报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #1a1a2e; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; }}
.header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
.header p {{ opacity: 0.9; font-size: 1.1rem; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 30px 20px; }}
.card {{ background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 24px; margin-bottom: 24px; }}
.card-title {{ font-size: 1.3rem; color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0; }}
.dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
.stat-box {{ background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 8px; padding: 20px; text-align: center; }}
.stat-box .value {{ font-size: 2.5rem; font-weight: bold; color: #667eea; }}
.stat-box .label {{ font-size: 0.9rem; color: #666; margin-top: 5px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f8f9fa; font-weight: 600; }}
.progress-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 8px 0; }}
.progress-fill {{ height: 100%; border-radius: 10px; }}
.progress-fill.high {{ background: #28a745; }}
.progress-fill.medium {{ background: #ffc107; }}
.progress-fill.low {{ background: #dc3545; }}
.level-header {{ background: #667eea; color: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; }}
.level-header h2 {{ font-size: 1.5rem; }}
</style>
</head>
<body>
<div class="header">
<h1>BubbleMate 综合测试报告</h1>
<p>生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
</div>
<div class="container">"""

    html += f"""<div class="card">
<h2 class="card-title">总体评测仪表盘</h2>
<div class="dashboard">
<div class="stat-box"><div class="value">{all_results['intent_eval_200']['accuracy']}%</div><div class="label">意图识别准确率 (200条)</div></div>
<div class="stat-box"><div class="value">{all_results['tool_eval']['accuracy']}%</div><div class="label">工具调用准确率 (9场景)</div></div>
<div class="stat-box"><div class="value">{all_results['heldout_eval']['accuracy']}%</div><div class="label">Held-out准确率 (30条)</div></div>
<div class="stat-box"><div class="value">{all_results['adversarial_eval']['accuracy']}%</div><div class="label">对抗样本通过率</div></div>
<div class="stat-box"><div class="value">{all_results['five_fold']['avg_accuracy']}%</div><div class="label">5-Fold平均准确率</div></div>
<div class="stat-box"><div class="value">{len(all_results['bad_cases'])}个</div><div class="label">Bad Case数量</div></div>
</div>
</div>"""

    html += f"""<div class="level-header"><h2>第一层：离线评测</h2></div>"""

    html += f"""<div class="card">
<h2 class="card-title">意图识别准确率评测 (200条测试集)</h2>
<div class="progress-bar"><div class="progress-fill {'high' if all_results['intent_eval_200']['accuracy'] >= 80 else 'medium' if all_results['intent_eval_200']['accuracy'] >= 60 else 'low'}" style="width:{all_results['intent_eval_200']['accuracy']}%">准确率: {all_results['intent_eval_200']['accuracy']}%</div></div>
<p style="color:#666;">正确数: {all_results['intent_eval_200']['correct']} / {all_results['intent_eval_200']['total']}</p>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">工具调用准确率评测 (9个异常场景)</h2>
<p style="color:#666;">总体准确率: {all_results['tool_eval']['accuracy']}% ({all_results['tool_eval']['passed']}/{all_results['tool_eval']['total']})</p>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">置信度校准</h2>
<table>
<thead><tr><th>置信度区间</th><th>实际准确率</th><th>样本数</th></tr></thead>
<tbody>"""
    for bucket in all_results['confidence_calibration']:
        html += f"""<tr><td>{bucket['confidence_bucket']}-{round(bucket['confidence_bucket']+0.1,1)}</td><td>{bucket['accuracy']}%</td><td>{bucket['samples']}</td></tr>"""
    html += f"""</tbody></table>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">Bad Case挖掘 (置信度<0.6)</h2>
<p style="color:#666;">共发现 {len(all_results['bad_cases'])} 个Bad Case</p>
</div>"""

    html += f"""<div class="level-header"><h2>第二层：泛化评测</h2></div>"""

    html += f"""<div class="card">
<h2 class="card-title">Held-out验证 (30条未见样本)</h2>
<div class="progress-bar"><div class="progress-fill {'high' if all_results['heldout_eval']['accuracy'] >= 80 else 'medium' if all_results['heldout_eval']['accuracy'] >= 60 else 'low'}" style="width:{all_results['heldout_eval']['accuracy']}%">准确率: {all_results['heldout_eval']['accuracy']}%</div></div>
<p style="color:#666;">正确数: {all_results['heldout_eval']['correct']} / {all_results['heldout_eval']['total']}</p>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">5-Fold交叉验证</h2>
<table>
<thead><tr><th>Fold</th><th>准确率</th><th>正确数</th><th>总样本</th></tr></thead>
<tbody>"""
    for fold in all_results['five_fold']['fold_results']:
        html += f"""<tr><td>Fold {fold['fold']}</td><td>{fold['accuracy']}%</td><td>{fold['correct']}</td><td>{fold['total']}</td></tr>"""
    html += f"""</tbody></table>
<p style="color:#666;">平均准确率: {all_results['five_fold']['avg_accuracy']}%</p>
</div>"""

    html += f"""<div class="card">
<h2 class="card-title">对抗样本集评测</h2>
<div class="progress-bar"><div class="progress-fill {'high' if all_results['adversarial_eval']['accuracy'] >= 80 else 'medium' if all_results['adversarial_eval']['accuracy'] >= 60 else 'low'}" style="width:{all_results['adversarial_eval']['accuracy']}%">通过率: {all_results['adversarial_eval']['accuracy']}%</div></div>
<p style="color:#666;">正确数: {all_results['adversarial_eval']['correct']} / {all_results['adversarial_eval']['total']}</p>
</div>"""

    html += f"""<div class="level-header"><h2>第三层：性能评测</h2></div>"""

    html += f"""<div class="card">
<h2 class="card-title">数据库索引检查</h2>
<table>
<thead><tr><th>表名</th><th>索引列表</th></tr></thead>
<tbody>"""
    for table, idx_list in all_results['db_indexes'].items():
        html += f"""<tr><td>{table}</td><td>{', '.join(idx_list) if idx_list else '无索引'}</td></tr>"""
    html += f"""</tbody></table>
</div>"""

    html += f"""</div></body></html>"""
    return html

def main():
    print("=" * 70)
    print("BubbleMate 综合测试报告生成")
    print("=" * 70)
    
    results = {}
    
    print("\n【第一层：离线评测】")
    print("1. 意图识别准确率评测...")
    results['intent_eval_200'] = run_intent_eval('data/test_set_200.json')
    print(f"   ✓ 200条测试集: {results['intent_eval_200']['accuracy']}%")
    
    print("2. 工具调用准确率评测...")
    results['tool_eval'] = run_tool_eval()
    print(f"   ✓ 9场景: {results['tool_eval']['accuracy']}%")
    
    print("3. 置信度校准...")
    results['confidence_calibration'] = run_confidence_calibration('data/test_set_200.json')
    print("   ✓ 完成")
    
    print("4. Bad Case挖掘...")
    results['bad_cases'] = run_bad_case_mining('data/test_set_200.json')
    print(f"   ✓ 发现 {len(results['bad_cases'])} 个Bad Case")
    
    print("5. 分类报告(Precision/Recall/F1)...")
    results['classification_report'] = run_classification_report('data/test_set_200.json')
    print(f"   ✓ 加权F1-Score: {results['classification_report']['weighted_avg']['f1_score']}")
    
    print("6. 规则覆盖率统计...")
    results['rule_coverage'] = run_rule_coverage('data/test_set_200.json')
    print(f"   ✓ 规则覆盖率: {results['rule_coverage']['rule_coverage']}%")
    
    print("\n【第二层：泛化评测】")
    print("1. Held-out验证...")
    results['heldout_eval'] = run_intent_eval('data/heldout_test_set_v4.json')
    print(f"   ✓ 30条未见样本: {results['heldout_eval']['accuracy']}%")
    
    print("2. 5-Fold交叉验证...")
    results['five_fold'] = run_five_fold_cv('data/test_set_200.json')
    print(f"   ✓ 平均准确率: {results['five_fold']['avg_accuracy']}%")
    
    print("3. 对抗样本集评测...")
    results['adversarial_eval'] = run_adversarial_eval()
    print(f"   ✓ 对抗样本: {results['adversarial_eval']['accuracy']}%")
    
    print("\n【第三层：性能评测】")
    print("1. 数据库索引检查...")
    results['db_indexes'] = check_db_indexes()
    print("   ✓ 完成")
    
    print("\n【生成HTML报告...】")
    html_report = generate_html_report(results)
    report_path = 'data/comprehensive_eval_report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"   ✓ 报告已保存: {report_path}")
    
    print("\n【保存JSON报告到reports/eval_report.json...】")
    os.makedirs('reports', exist_ok=True)
    json_report = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'level1_offline': {
            'intent_accuracy_200': results['intent_eval_200'],
            'tool_accuracy': results['tool_eval'],
            'confidence_calibration': results['confidence_calibration'],
            'bad_cases_count': len(results['bad_cases']),
            'classification_report': results['classification_report'],
            'rule_coverage': results['rule_coverage']
        },
        'level2_generalization': {
            'heldout_eval': results['heldout_eval'],
            'five_fold_cv': results['five_fold'],
            'adversarial_eval': results['adversarial_eval']
        },
        'level3_performance': {
            'db_indexes': results['db_indexes']
        }
    }
    with open('reports/eval_report.json', 'w', encoding='utf-8') as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print("   ✓ JSON报告已保存: reports/eval_report.json")
    
    print("\n" + "=" * 70)
    print("综合测试完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()