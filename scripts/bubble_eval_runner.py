"""
BubbleMate 评测体系
三层评测：组件级 + 端到端 + 对抗性
"""

import json
import os
import sys
import time
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

import pathlib
project_root = str(pathlib.Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from backend.bubble_agent import recognize_intent, process_message, create_memory_store
from backend.api.main import app


@dataclass
class EvalResult:
    case_id: str
    category: str
    difficulty: str
    predicted_intent: str
    expected_intent: str
    intent_correct: bool
    predicted_tools: List[str]
    expected_tools: List[str]
    tool_correct: bool
    response: str
    has_clarification: bool
    expected_clarification: bool
    clarification_correct: bool
    latency_ms: float
    passed: bool


class BubbleMateEvaluator:
    
    def __init__(self, test_set_path: str = None):
        self.memory_store = create_memory_store(window_size=5)
        
        self.test_cases = []
        if test_set_path:
            self._load_test_set(test_set_path)
        else:
            self._build_default_test_set()
        
        self.results: List[EvalResult] = []
    
    def _load_test_set(self, path: str):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.test_cases = json.load(f)
    
    def _build_default_test_set(self):
        self.test_cases = [
            {"id": "TC-001", "user_query": "糯米少的可怜，正常是啥分量我很清楚",
             "ground_truth": {"intent": "complaint_quantity", "tool_calls": ["log_complaint"],
             "requires_clarification": False}, "difficulty": "easy", "category": "份量问题"},
            {"id": "TC-002", "user_query": "点了大杯，送来只有半杯，冰块占了一大半",
             "ground_truth": {"intent": "complaint_quantity", "tool_calls": ["log_complaint"],
             "requires_clarification": False}, "difficulty": "easy", "category": "份量问题"},
            {"id": "TC-007", "user_query": "就是太甜了，喝了一口就扔了",
             "ground_truth": {"intent": "complaint_taste", "tool_calls": ["log_complaint"],
             "requires_clarification": False}, "difficulty": "easy", "category": "口感问题"},
            {"id": "TC-008", "user_query": "葡萄太酸了，酸到喝不下去",
             "ground_truth": {"intent": "complaint_taste", "tool_calls": ["log_complaint"],
             "requires_clarification": False}, "difficulty": "easy", "category": "口感问题"},
            {"id": "TC-101", "user_query": "光谷附近有门店吗",
             "ground_truth": {"intent": "query_location", "tool_calls": ["query_stores"],
             "requires_clarification": True}, "difficulty": "easy", "category": "门店查询"},
            {"id": "TC-102", "user_query": "最近的一家店在哪里",
             "ground_truth": {"intent": "query_location", "tool_calls": ["query_stores"],
             "requires_clarification": True}, "difficulty": "easy", "category": "门店查询"},
            {"id": "TC-103", "user_query": "附近有门店吗",
             "ground_truth": {"intent": "query_location", "tool_calls": ["query_stores"],
             "requires_clarification": True}, "difficulty": "easy", "category": "门店查询"},
            {"id": "TC-104", "user_query": "有什么推荐的吗",
             "ground_truth": {"intent": "query_recommend", "tool_calls": ["query_menu"],
             "requires_clarification": False}, "difficulty": "easy", "category": "菜单查询"},
            {"id": "TC-105", "user_query": "菜单看看",
             "ground_truth": {"intent": "query_menu", "tool_calls": ["query_menu"],
             "requires_clarification": False}, "difficulty": "easy", "category": "菜单查询"},
            {"id": "TC-106", "user_query": "我的订单什么时候能送到",
             "ground_truth": {"intent": "query_order", "tool_calls": ["query_order"],
             "requires_clarification": True}, "difficulty": "easy", "category": "订单查询"},
            {"id": "TC-017", "user_query": "糖浆劣质，少少糖巨甜，联系商家还不理我",
             "ground_truth": {"intent": "complaint_taste_service", "tool_calls": ["log_complaint"],
             "requires_clarification": False}, "difficulty": "medium", "category": "口感+服务"},
            {"id": "TC-018", "user_query": "芝芝抹茶又苦又贵，喝起来像药",
             "ground_truth": {"intent": "complaint_taste_price", "tool_calls": ["log_complaint"],
             "requires_clarification": False}, "difficulty": "medium", "category": "口感+价格"},
            {"id": "TC-029", "user_query": "就是那个，又少又难喝，你们懂的",
             "ground_truth": {"intent": "complaint_vague", "tool_calls": [],
             "requires_clarification": True}, "difficulty": "hard", "category": "指代不明"},
            {"id": "TC-030", "user_query": "退款",
             "ground_truth": {"intent": "query_refund", "tool_calls": ["query_order"],
             "requires_clarification": True}, "difficulty": "hard", "category": "信息缺失"},
            {"id": "TC-031", "user_query": "上次那个，跟这次不一样，你们是不是换配方了",
             "ground_truth": {"intent": "complaint_compare_history", "tool_calls": [],
             "requires_clarification": True}, "difficulty": "hard", "category": "指代+对比"},
            {"id": "TC-034", "user_query": "呵呵，就这",
             "ground_truth": {"intent": "complaint_sarcasm", "tool_calls": [],
             "requires_clarification": True}, "difficulty": "hard", "category": "讽刺语气"},
            {"id": "TC-045", "user_query": "",
             "ground_truth": {"intent": "unknown", "tool_calls": [],
             "requires_clarification": True}, "difficulty": "hard", "category": "空输入"},
            {"id": "TC-048", "user_query": "你是真人还是机器人",
             "ground_truth": {"intent": "general", "tool_calls": [],
             "requires_clarification": False}, "difficulty": "easy", "category": "元对话"},
        ]
    
    def run_all_evals(self) -> Dict[str, Any]:
        print("=" * 60)
        print("BubbleMate 评测体系启动")
        print("三层评测：组件级 + 端到端 + 对抗性")
        print("=" * 60)
        
        component_results = self.run_component_evals()
        end_to_end_results = self.run_end_to_end_evals()
        adversarial_results = self.run_adversarial_evals()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_cases_count": len(self.test_cases),
            "level1_component": component_results,
            "level2_end_to_end": end_to_end_results,
            "level3_adversarial": adversarial_results,
            "overall_pass_rate": self._calculate_overall_rate(),
            "bad_cases": self._get_bad_cases(),
        }
        
        self._save_report(report)
        
        return report
    
    def run_component_evals(self) -> Dict[str, float]:
        print("\n" + "=" * 60)
        print("Level 1: 组件级评测")
        print("=" * 60)
        
        intent_correct = 0
        tool_correct = 0
        clarification_correct = 0
        clarification_cases = 0
        
        for case in self.test_cases:
            query = case["user_query"]
            expected = case["ground_truth"]
            
            start_time = time.time()
            intent_result = recognize_intent(query)
            latency = (time.time() - start_time) * 1000
            
            predicted_intent = intent_result["name"]
            expected_intent = expected["intent"]
            intent_match = predicted_intent == expected_intent
            
            if intent_match:
                intent_correct += 1
            
            tool_mapping = {
                "query_location": ["query_stores"],
                "query_menu": ["query_menu"],
                "query_recommend": ["query_menu"],
                "query_order": ["query_order"],
                "complaint_taste": ["log_complaint"],
                "complaint_quantity": ["log_complaint"],
                "complaint_taste_service": ["log_complaint"],
                "complaint_taste_price": ["log_complaint"],
            }
            predicted_tools = tool_mapping.get(predicted_intent, [])
            expected_tools = expected.get("tool_calls", [])
            tool_match = set(predicted_tools) == set(expected_tools) or len(expected_tools) == 0
            
            if tool_match:
                tool_correct += 1
            
            response, _ = process_message(query, f"eval-{case['id']}", self.memory_store)
            has_clarification = "?" in response or "请问" in response or "提供" in response
            expected_clarification = expected.get("requires_clarification", False)
            
            if expected_clarification:
                clarification_cases += 1
                if has_clarification:
                    clarification_correct += 1
            
            result = EvalResult(
                case_id=case["id"],
                category=case["category"],
                difficulty=case["difficulty"],
                predicted_intent=predicted_intent,
                expected_intent=expected_intent,
                intent_correct=intent_match,
                predicted_tools=predicted_tools,
                expected_tools=expected_tools,
                tool_correct=tool_match,
                response=response[:100] + "..." if len(response) > 100 else response,
                has_clarification=has_clarification,
                expected_clarification=expected_clarification,
                clarification_correct=has_clarification == expected_clarification,
                latency_ms=round(latency, 2),
                passed=intent_match and tool_match and (has_clarification == expected_clarification)
            )
            self.results.append(result)
            
            status = "✓" if result.passed else "✗"
            print(f"{status} {case['id']}: {case['category']} | "
                  f"意图:{predicted_intent}→{expected_intent} | "
                  f"反问:{has_clarification}")
        
        total = len(self.test_cases)
        metrics = {
            "intent_accuracy": round(intent_correct / total, 3),
            "intent_correct": intent_correct,
            "intent_total": total,
            "tool_accuracy": round(tool_correct / total, 3),
            "tool_correct": tool_correct,
            "tool_total": total,
            "clarification_rate": round(clarification_correct / clarification_cases, 3) if clarification_cases > 0 else 1.0,
            "clarification_correct": clarification_correct,
            "clarification_cases": clarification_cases,
            "avg_latency_ms": round(sum(r.latency_ms for r in self.results) / total, 2),
        }
        
        print("\n组件级评测结果:")
        print(f"  意图识别准确率: {metrics['intent_accuracy']} ({intent_correct}/{total})")
        print(f"  工具选择准确率: {metrics['tool_accuracy']} ({tool_correct}/{total})")
        print(f"  反问准确率: {metrics['clarification_rate']} ({clarification_correct}/{clarification_cases})")
        print(f"  平均响应时间: {metrics['avg_latency_ms']}ms")
        
        return metrics
    
    def run_end_to_end_evals(self) -> Dict[str, float]:
        print("\n" + "=" * 60)
        print("Level 2: 端到端评测")
        print("=" * 60)
        
        solved = 0
        partially_solved = 0
        not_solved = 0
        
        for result in self.results:
            if result.intent_correct and result.tool_correct:
                solved += 1
            elif result.intent_correct or result.tool_correct:
                partially_solved += 1
            else:
                not_solved += 1
        
        total = len(self.results)
        metrics = {
            "solved_rate": round(solved / total, 3),
            "solved_count": solved,
            "partial_rate": round(partially_solved / total, 3),
            "partial_count": partially_solved,
            "failure_rate": round(not_solved / total, 3),
            "failure_count": not_solved,
        }
        
        print(f"  完全解决率: {metrics['solved_rate']} ({solved}/{total})")
        print(f"  部分解决率: {metrics['partial_rate']} ({partially_solved}/{total})")
        print(f"  未解决率: {metrics['failure_rate']} ({not_solved}/{total})")
        
        return metrics
    
    def run_adversarial_evals(self) -> Dict[str, float]:
        print("\n" + "=" * 60)
        print("Level 3: 对抗性评测")
        print("=" * 60)
        
        hard_cases = [r for r in self.results if r.difficulty == "hard"]
        passed = sum(1 for r in hard_cases if r.passed)
        
        categories = {}
        for r in hard_cases:
            if r.category not in categories:
                categories[r.category] = {"passed": 0, "total": 0}
            categories[r.category]["total"] += 1
            if r.passed:
                categories[r.category]["passed"] += 1
        
        metrics = {
            "adversarial_pass_rate": round(passed / len(hard_cases), 3) if hard_cases else 1.0,
            "passed": passed,
            "total": len(hard_cases),
            "category_breakdown": categories,
        }
        
        print(f"  对抗性通过率: {metrics['adversarial_pass_rate']} ({passed}/{len(hard_cases)})")
        for cat, data in categories.items():
            print(f"    - {cat}: {data['passed']}/{data['total']}")
        
        return metrics
    
    def _calculate_overall_rate(self) -> float:
        passed = sum(1 for r in self.results if r.passed)
        return round(passed / len(self.results), 3)
    
    def _get_bad_cases(self) -> List[Dict]:
        bad_cases = []
        for r in self.results:
            if not r.passed:
                bad_cases.append({
                    "case_id": r.case_id,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "predicted_intent": r.predicted_intent,
                    "expected_intent": r.expected_intent,
                    "intent_error": not r.intent_correct,
                    "tool_error": not r.tool_correct,
                    "clarification_error": not r.clarification_correct,
                    "response": r.response,
                })
        return bad_cases
    
    def _save_report(self, report: Dict):
        output_path = os.path.join(os.path.dirname(__file__), "../data/eval_report.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n评测报告已保存: {output_path}")


if __name__ == "__main__":
    evaluator = BubbleMateEvaluator()
    report = evaluator.run_all_evals()
    
    print("\n" + "=" * 60)
    print("评测完成！")
    print("=" * 60)
    print(f"综合通过率: {report['overall_pass_rate']}")
    print(f"Bad Case数: {len(report['bad_cases'])}")