import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2

def main():
    print("=== BubbleMate V3 Held-out 评测 ===")
    
    recognizer = IntentRecognizerV2('data', use_llm=False)
    
    with open('data/heldout_test_set_v4.json', 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    
    correct = 0
    total = len(test_cases)
    errors = []
    
    for case in test_cases:
        text = case['text']
        expected = case['intent']
        result = recognizer.recognize(text)
        
        if result.name == expected:
            correct += 1
            status = "✓"
        else:
            status = "✗"
            errors.append({
                "text": text,
                "expected": expected,
                "predicted": result.name,
                "confidence": result.confidence,
                "source": result.source
            })
        
        print(f"{status} '{text}' -> {result.name} (confidence: {result.confidence:.2f})")
    
    accuracy = round(correct / total * 100, 1)
    print(f"\n=== 评测结果 ===")
    print(f"总样本数: {total}")
    print(f"正确数: {correct}")
    print(f"准确率: {accuracy}%")
    
    if errors:
        print(f"\n=== 错误分析 ({len(errors)}条) ===")
        for err in errors:
            print(f"文本: '{err['text']}'")
            print(f"  期望: {err['expected']}")
            print(f"  预测: {err['predicted']} (confidence: {err['confidence']:.2f}, source: {err['source']})")
            print()
    
    return accuracy

if __name__ == '__main__':
    main()
