import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import recognize_intent

def analyze_low_confidence_samples(dataset_path, min_conf=0.2, max_conf=0.3):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    low_conf_samples = []
    intent_distribution = {}
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        confidence = result['confidence']
        predicted = result['name']
        
        if min_conf <= confidence < max_conf:
            low_conf_samples.append({
                'text': text,
                'expected_intent': expected,
                'predicted_intent': predicted,
                'confidence': round(confidence, 2),
                'correct': predicted == expected
            })
            
            if expected not in intent_distribution:
                intent_distribution[expected] = {'count': 0, 'correct': 0}
            intent_distribution[expected]['count'] += 1
            if predicted == expected:
                intent_distribution[expected]['correct'] += 1
    
    sorted_intents = sorted(intent_distribution.items(), key=lambda x: x[1]['count'], reverse=True)
    
    analysis = {
        'total_low_confidence': len(low_conf_samples),
        'confidence_range': f'{min_conf}-{max_conf}',
        'intent_distribution': [],
        'top_failed_intents': [],
        'samples': low_conf_samples
    }
    
    for intent, stats in sorted_intents:
        accuracy = round(stats['correct'] / stats['count'] * 100, 2)
        analysis['intent_distribution'].append({
            'intent': intent,
            'count': stats['count'],
            'correct': stats['correct'],
            'accuracy': accuracy,
            'failed': stats['count'] - stats['correct']
        })
        
        if stats['correct'] == 0:
            analysis['top_failed_intents'].append({
                'intent': intent,
                'count': stats['count']
            })
    
    return analysis

def analyze_confidence_range(dataset_path, min_conf, max_conf, label=""):
    if not os.path.exists(dataset_path):
        return None
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        samples = data.get('samples', [])
    else:
        samples = data
    
    range_samples = []
    intent_distribution = {}
    error_patterns = {}
    
    for sample in samples:
        text = sample.get('user_query', sample.get('query', sample.get('text', '')))
        expected = sample.get('intent', '')
        
        if not text or not expected:
            continue
        
        result = recognize_intent(text)
        confidence = result['confidence']
        predicted = result['name']
        
        if min_conf <= confidence < max_conf:
            range_samples.append({
                'text': text,
                'expected_intent': expected,
                'predicted_intent': predicted,
                'confidence': round(confidence, 2),
                'correct': predicted == expected
            })
            
            if expected not in intent_distribution:
                intent_distribution[expected] = {'count': 0, 'correct': 0, 'misclassified_as': {}}
            intent_distribution[expected]['count'] += 1
            if predicted == expected:
                intent_distribution[expected]['correct'] += 1
            else:
                if predicted not in intent_distribution[expected]['misclassified_as']:
                    intent_distribution[expected]['misclassified_as'][predicted] = 0
                intent_distribution[expected]['misclassified_as'][predicted] += 1
                
                error_key = f"{expected} -> {predicted}"
                if error_key not in error_patterns:
                    error_patterns[error_key] = {'count': 0, 'examples': []}
                error_patterns[error_key]['count'] += 1
                if len(error_patterns[error_key]['examples']) < 5:
                    error_patterns[error_key]['examples'].append(text)
    
    sorted_intents = sorted(intent_distribution.items(), key=lambda x: x[1]['count'], reverse=True)
    sorted_errors = sorted(error_patterns.items(), key=lambda x: x[1]['count'], reverse=True)
    
    analysis = {
        'total_samples': len(range_samples),
        'confidence_range': f'{min_conf}-{max_conf}',
        'label': label,
        'intent_distribution': [],
        'top_failed_intents': [],
        'error_patterns': [],
        'samples': range_samples
    }
    
    for intent, stats in sorted_intents:
        accuracy = round(stats['correct'] / stats['count'] * 100, 2)
        analysis['intent_distribution'].append({
            'intent': intent,
            'count': stats['count'],
            'correct': stats['correct'],
            'accuracy': accuracy,
            'failed': stats['count'] - stats['correct'],
            'misclassified_as': stats['misclassified_as']
        })
        
        if stats['correct'] == 0:
            analysis['top_failed_intents'].append({
                'intent': intent,
                'count': stats['count']
            })
    
    for error_key, stats in sorted_errors:
        analysis['error_patterns'].append({
            'pattern': error_key,
            'count': stats['count'],
            'examples': stats['examples']
        })
    
    return analysis

def main():
    print("=" * 70)
    print("Bad Case分析 - 0.7-0.8置信度区间")
    print("=" * 70)
    
    analysis = analyze_confidence_range('data/test_set_200.json', 0.7, 0.8, '中等置信度区间')
    
    if not analysis:
        print("错误: 无法加载测试数据")
        return
    
    print(f"\n【样本总数】: {analysis['total_samples']}")
    print(f"【置信度区间】: {analysis['confidence_range']}")
    
    total_correct = sum(i['correct'] for i in analysis['samples'])
    accuracy = round(total_correct / analysis['total_samples'] * 100, 2)
    print(f"【区间准确率】: {accuracy}% ({total_correct}/{analysis['total_samples']})")
    
    print("\n【意图分布统计】")
    print(f"{'意图':<25} {'数量':<6} {'正确':<6} {'准确率':<10} {'失败':<6}")
    print("-" * 60)
    for item in analysis['intent_distribution']:
        print(f"{item['intent']:<25} {item['count']:<6} {item['correct']:<6} {item['accuracy']:<10}% {item['failed']:<6}")
    
    print("\n【错误模式分析】")
    if analysis['error_patterns']:
        for i, pattern in enumerate(analysis['error_patterns'][:10]):
            print(f"\n  {i+1}. {pattern['pattern']} ({pattern['count']}次)")
            for j, example in enumerate(pattern['examples'][:3]):
                print(f"     {j+1}. '{example}'")
    else:
        print("  无错误模式")
    
    print("\n【Top10失败样本】")
    failed_samples = [s for s in analysis['samples'] if not s['correct']][:10]
    for i, sample in enumerate(failed_samples):
        print(f"  {i+1}. '{sample['text']}'")
        print(f"     期望: {sample['expected_intent']}, 预测: {sample['predicted_intent']}, 置信度: {sample['confidence']}")
    
    output_path = 'reports/bad_case_analysis_07_08.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"\n【分析报告已保存】: {output_path}")

if __name__ == '__main__':
    main()