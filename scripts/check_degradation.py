import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.intent_recognizer_v2 import IntentRecognizerV2

def main():
    recognizer = IntentRecognizerV2('data', use_llm=False)
    
    with open('data/test_set_200.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        samples = data['samples']
    
    errors = []
    for s in samples:
        text = s['user_query']
        expected = s['intent']
        result = recognizer.recognize(text)
        if result.name != expected:
            errors.append({
                'text': text,
                'expected': expected,
                'predicted': result.name,
                'conf': result.confidence,
                'source': result.source
            })
    
    print(f'错误数: {len(errors)}')
    print('前30个错误:')
    for i, e in enumerate(errors[:30], 1):
        print(f'{i}. text: {repr(e["text"])}')
        print(f'   expected: {e["expected"]}, predicted: {e["predicted"]}')
        print(f'   conf: {e["conf"]:.2f}, source: {e["source"]}')
        print()

if __name__ == '__main__':
    main()