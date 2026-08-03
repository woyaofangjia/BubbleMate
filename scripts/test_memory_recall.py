import sys
import os
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.bubble_agent import process_message, create_memory_store, clear_response_cache

def load_scenarios(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_scenario(scenario, window_size):
    memory_store = create_memory_store(window_size=window_size)
    session_id = f"recall_{window_size}_{scenario['scenario_id']}"
    
    results = []
    turns = scenario['turns']
    target_turn = scenario['target_turn']
    expected_key = scenario['expected_key']
    
    for i, turn in enumerate(turns):
        user_msg = turn['user']
        response, intent = process_message(user_msg, session_id, memory_store)
        
        turn_result = {
            "turn": turn['turn'],
            "user": user_msg,
            "response": response[:120],
            "intent": intent.get('name', 'unknown'),
            "is_target": (i + 1 == target_turn)
        }
        
        if i + 1 == target_turn:
            is_correct = expected_key in response
            turn_result["expected_key"] = expected_key
            turn_result["correct"] = is_correct
            results.append(turn_result)
            break
        
        results.append(turn_result)
    
    return {
        "scenario_id": scenario['scenario_id'],
        "scenario_name": scenario['scenario_name'],
        "window_size": window_size,
        "correct": results[-1].get("correct", False),
        "expected_key": expected_key,
        "response": results[-1].get("response", ""),
        "turns": results
    }

def run_experiment(scenarios, window_sizes):
    all_results = {}
    
    for ws in window_sizes:
        print(f"\n{'='*60}")
        print(f"窗口大小: {ws} 轮")
        print(f"{'='*60}")
        
        ws_results = []
        correct_count = 0
        total = len(scenarios)
        
        for scenario in scenarios:
            start = time.time()
            result = run_scenario(scenario, ws)
            elapsed = (time.time() - start) * 1000
            result['time_ms'] = elapsed
            ws_results.append(result)
            
            status = "✓" if result['correct'] else "✗"
            correct_count += 1 if result['correct'] else 0
            print(f"  {status} 场景{scenario['scenario_id']} [{scenario['scenario_name']}]: "
                  f"{'命中' if result['correct'] else '未命中'} | "
                  f"耗时 {elapsed:.0f}ms")
            if not result['correct']:
                print(f"     期望关键词: '{scenario['expected_key']}'")
                print(f"     实际回复:   {result['response'][:100]}...")
        
        accuracy = correct_count / total * 100
        all_results[ws] = {
            "accuracy": accuracy,
            "correct": correct_count,
            "total": total,
            "scenarios": ws_results
        }
        
        print(f"\n  准确率: {correct_count}/{total} ({accuracy:.1f}%)")
    
    return all_results

def print_summary(all_results, scenarios):
    window_sizes = sorted(all_results.keys())
    scenario_names = [s['scenario_name'] for s in scenarios]
    
    print(f"\n{'='*80}")
    print(f"{'记忆召回能力实验结果':^70}")
    print(f"{'='*80}")
    
    header = f"{'窗口':<6}"
    for name in scenario_names:
        header += f" {name:^8}"
    header += f" {'准确率':^8}"
    print(header)
    print(f"{'-'* (6 + 10 * len(scenarios) + 10)}")
    
    for ws in window_sizes:
        row = f"{ws:<6}"
        ws_data = all_results[ws]
        for s_result in ws_data['scenarios']:
            mark = "✓" if s_result['correct'] else "✗"
            row += f" {mark:^8}"
        row += f" {ws_data['accuracy']:^7.1f}%"
        print(row)
    
    print(f"{'-'* (6 + 10 * len(scenarios) + 10)}")
    
    print("\n" + "说明:")
    print("  ✓ = Agent回复包含预期关键词（记忆召回成功）")
    print("  ✗ = Agent回复未包含预期关键词（记忆召回失败）")

def save_results(all_results, scenarios, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output = {
        "experiment_info": {
            "name": "记忆召回能力测试",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "window_sizes": sorted(all_results.keys()),
            "scenario_count": len(scenarios)
        },
        "results": {}
    }
    
    for ws, ws_data in all_results.items():
        output["results"][ws] = {
            "accuracy": ws_data['accuracy'],
            "correct": ws_data['correct'],
            "total": ws_data['total'],
            "scenario_details": []
        }
        for s in ws_data['scenarios']:
            output["results"][ws]["scenario_details"].append({
                "scenario_id": s['scenario_id'],
                "scenario_name": s['scenario_name'],
                "correct": s['correct'],
                "expected_key": s['expected_key'],
                "response": s['response'],
                "time_ms": s['time_ms']
            })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存至: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='记忆召回能力测试')
    parser.add_argument('--min-accuracy', type=float, default=100.0,
                        help='最低准确率阈值，低于此值返回非零退出码 (默认: 100.0)')
    parser.add_argument('--ci', action='store_true',
                        help='CI模式：生成JUnit XML报告并返回退出码')
    parser.add_argument('--no-cache-clear', action='store_true',
                        help='不清除响应缓存')
    args = parser.parse_args()

    if not args.no_cache_clear:
        clear_response_cache()

    scenarios_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'memory_test_scenarios.json'
    )
    
    if not os.path.exists(scenarios_path):
        print(f"错误: 测试场景文件不存在: {scenarios_path}")
        print("请先运行第1步生成 memory_test_scenarios.json")
        sys.exit(1)
    
    scenarios = load_scenarios(scenarios_path)
    print(f"已加载 {len(scenarios)} 个测试场景")
    
    window_sizes = [1, 3, 5, 7, 10]
    print(f"将测试窗口大小: {window_sizes}")
    print(f"每个场景对话轮次: 4-8 轮不等")
    
    all_results = run_experiment(scenarios, window_sizes)
    print_summary(all_results, scenarios)
    
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'reports', 'memory_recall_results.json'
    )
    save_results(all_results, scenarios, output_path)

    if args.ci:
        junit_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'reports', 'memory_recall_junit.xml'
        )
        save_junit_report(all_results, scenarios, junit_path)

    min_acc = min(v['accuracy'] for v in all_results.values())
    if min_acc < args.min_accuracy:
        print(f"\n✗ 最低准确率 {min_acc:.1f}% 低于阈值 {args.min_accuracy}%")
        sys.exit(1)
    else:
        print(f"\n✓ 最低准确率 {min_acc:.1f}% 满足阈值 {args.min_accuracy}%")
        sys.exit(0)

def save_junit_report(all_results, scenarios, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    scenario_names = [s['scenario_name'] for s in scenarios]
    testsuite = f'<testsuite name="memory_recall" tests="{len(all_results) * len(scenarios)}" failures="0">'
    
    testcases = []
    failures = 0
    for ws, ws_data in all_results.items():
        for s_result in ws_data['scenarios']:
            classname = f"window_{ws}"
            name = f"window_{ws}_{s_result['scenario_name']}"
            time_s = s_result['time_ms'] / 1000.0
            if s_result['correct']:
                testcases.append(f'  <testcase classname="{classname}" name="{name}" time="{time_s:.3f}s" />')
            else:
                failures += 1
                testcases.append(f'  <testcase classname="{classname}" name="{name}" time="{time_s:.3f}s">')
                testcases.append(f'    <failure message="Expected key not found">Expected {s_result["expected_key"]!r}</failure>')
                testcases.append(f'  </testcase>')
    
    testsuite = f'<testsuite name="memory_recall" tests="{len(all_results) * len(scenarios)}" failures="{failures}">'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(testsuite + '\n')
        f.write('\n'.join(testcases) + '\n')
        f.write('</testsuite>\n')
    print(f"\nJUnit报告已保存至: {output_path}")

if __name__ == "__main__":
    main()
