"""复合意图专项测试。

验证“复合识别”落到有答案的合并意图，并且回复覆盖两个子诉求，
不能退化成通用兜底话术。
"""

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.bubble_agent import (  # noqa: E402
    CATEGORY_MAP,
    COMPOSITE_PATTERNS,
    DEFAULT_COMPENSATIONS,
    DEFAULT_SOLUTIONS,
    DIRECT_RESPONSES,
    INTENT_KEYWORDS,
    INTENT_TO_CATEGORY,
    build_response,
    clear_intent_cache,
    clear_response_cache,
    create_memory_store,
    process_message,
    recognize_intent,
)

GENERIC_FALLBACKS = [
    "您好，有什么可以帮助您的？",
    "请告诉我具体查询内容。",
]

MERGED_INTENTS = {
    "complaint_taste_price",
    "complaint_quantity_taste",
    "query_recommend_price",
    "place_order_promotion",
}

# expected_intent + required_keywords 全部命中才算通过；required_keywords 用于确认回复覆盖两个子诉求
CASES = [
    {"id": "taste_price_1", "text": "太甜了还这么贵", "intent": "complaint_taste_price",
     "sub_intents": ["complaint_taste", "complaint_price"], "keywords": ["口味", "价格"]},
    {"id": "taste_price_2", "text": "太甜了又这么贵", "intent": "complaint_taste_price",
     "sub_intents": ["complaint_taste", "complaint_price"], "keywords": ["口味", "价格"]},
    {"id": "taste_price_3", "text": "太甜了而且还这么贵", "intent": "complaint_taste_price",
     "sub_intents": ["complaint_taste", "complaint_price"], "keywords": ["口味", "价格"]},
    {"id": "quantity_taste_1", "text": "料太少了还这么甜", "intent": "complaint_quantity_taste",
     "sub_intents": ["complaint_quantity", "complaint_taste"], "keywords": ["份量", "口味"]},
    {"id": "quantity_taste_2", "text": "这料太少又这么甜", "intent": "complaint_quantity_taste",
     "sub_intents": ["complaint_quantity", "complaint_taste"], "keywords": ["份量", "口味"]},
    {"id": "quantity_taste_3", "text": "料太少了还甜得发腻", "intent": "complaint_quantity_taste",
     "sub_intents": ["complaint_quantity", "complaint_taste"], "keywords": ["份量", "口味"]},
    {"id": "recommend_price_1", "text": "好喝吗多少钱", "intent": "query_recommend_price",
     "sub_intents": ["query_recommend", "query_price"], "keywords": ["招牌", "价格"]},
    {"id": "recommend_price_2", "text": "这个好喝吗价格多少", "intent": "query_recommend_price",
     "sub_intents": ["query_recommend", "query_price"], "keywords": ["招牌", "价格"]},
    {"id": "recommend_price_3", "text": "这个好喝吗多少钱一杯", "intent": "query_recommend_price",
     "sub_intents": ["query_recommend", "query_price"], "keywords": ["招牌", "价格"]},
    {"id": "order_promotion_1", "text": "点一杯有什么优惠", "intent": "place_order_promotion",
     "sub_intents": ["place_order", "query_promotion"], "keywords": ["点", "优惠"]},
    {"id": "order_promotion_2", "text": "下单有活动吗", "intent": "place_order_promotion",
     "sub_intents": ["place_order", "query_promotion"], "keywords": ["点", "优惠"]},
    {"id": "order_promotion_3", "text": "我想点一杯，现在有什么优惠活动吗", "intent": "place_order_promotion",
     "sub_intents": ["place_order", "query_promotion"], "keywords": ["点", "优惠"]},
    # 预定义合并意图，行为需保持不变
    {"id": "predefined_taste_price", "text": "又苦又贵不值这个价", "intent": "complaint_taste_price",
     "sub_intents": [], "keywords": ["口味", "价格", "补偿"]},
]

# 模板外组合：明确按单意图处理，不报错、不假装复合
SINGLE_INTENT_CASES = [
    {"id": "outside_refund_order", "text": "我要退款，顺便帮我查订单", "allowed": ["complaint_refund", "query_order"]},
    {"id": "outside_service_menu", "text": "服务太差了，你们菜单有什么", "allowed": ["complaint_service", "query_menu"]},
    # 只命中单个诉求时，不能被误判为合并意图
    {"id": "single_taste", "text": "太甜了", "allowed": ["complaint_taste"]},
    {"id": "single_quantity", "text": "料太少了", "allowed": ["complaint_quantity"]},
    {"id": "single_recommend", "text": "好喝吗", "allowed": ["query_recommend"]},
    {"id": "single_promotion", "text": "有优惠吗", "allowed": ["query_promotion"]},
    {"id": "single_price", "text": "多少钱", "allowed": ["query_price"]},
    {"id": "single_order", "text": "点一杯", "allowed": ["place_order"]},
]

# 旧版 composite 缓存的重映射：直接喂 build_response，不经识别层
LEGACY_CASES = [
    {"id": "legacy_taste_price", "text": "太甜了还这么贵", "sub_intents": ["complaint_taste", "complaint_price"],
     "intent": "complaint_taste_price", "keywords": ["口味", "价格"]},
    {"id": "legacy_quantity_taste", "text": "料太少了还这么甜",
     "sub_intents": ["complaint_quantity", "complaint_taste"], "intent": "complaint_quantity_taste",
     "keywords": ["份量", "口味"]},
    {"id": "legacy_recommend_price", "text": "好喝吗多少钱",
     "sub_intents": ["query_recommend", "query_price"], "intent": "query_recommend_price",
     "keywords": ["招牌", "价格"]},
    {"id": "legacy_order_promotion", "text": "点一杯有优惠",
     "sub_intents": ["place_order", "query_promotion"], "intent": "place_order_promotion",
     "keywords": ["点", "优惠"]},
]


def check_registry_consistency():
    """意图登记一致性：防止新增意图漏登记，重新产生孤儿意图。"""
    problems = []

    missing_category = sorted(set(INTENT_KEYWORDS) - set(CATEGORY_MAP))
    if missing_category:
        problems.append(f"INTENT_KEYWORDS 缺少 CATEGORY_MAP 登记: {missing_category}")

    missing_category = sorted(set(INTENT_TO_CATEGORY) - set(CATEGORY_MAP))
    if missing_category:
        problems.append(f"INTENT_TO_CATEGORY 缺少 CATEGORY_MAP 登记: {missing_category}")

    for name in INTENT_KEYWORDS:
        if name.startswith("complaint") and name not in INTENT_TO_CATEGORY:
            problems.append(f"投诉意图缺少知识库分类映射: {name}")

    for _, merged, sub_intents in COMPOSITE_PATTERNS:
        if merged not in CATEGORY_MAP:
            problems.append(f"复合意图缺少分类: {merged}")
        for sub in sub_intents:
            if sub not in CATEGORY_MAP:
                problems.append(f"子意图缺少分类: {sub}")
        if merged.startswith("complaint"):
            category = INTENT_TO_CATEGORY.get(merged)
            if not category:
                problems.append(f"复合投诉意图缺少分类映射: {merged}")
            elif category not in DEFAULT_SOLUTIONS or category not in DEFAULT_COMPENSATIONS:
                problems.append(f"复合投诉意图缺少双诉求答案: {merged} -> {category}")
        elif merged not in DIRECT_RESPONSES:
            problems.append(f"复合意图缺少回复出口: {merged}")

    return {
        "id": "registry_consistency",
        "text": "INTENT_KEYWORDS / CATEGORY_MAP / INTENT_TO_CATEGORY 一致性",
        "expected_intent": "consistent",
        "actual_intent": "consistent" if not problems else "inconsistent",
        "sub_intents": None,
        "response": "",
        "passed": not problems,
        "problems": problems,
    }


def run_case(case, store):
    session_id = f"composite_{case['id']}_{int(time.time() * 1000)}"
    started = time.perf_counter()
    response, intent = process_message(case["text"], session_id, store)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    problems = []
    name = intent.get("name")
    if name != case["intent"]:
        problems.append(f"意图={name}，期望={case['intent']}")
    if list(intent.get("sub_intents") or []) != case["sub_intents"]:
        problems.append(f"子意图={intent.get('sub_intents')}，期望={case['sub_intents']}")
    missing = [kw for kw in case["keywords"] if kw not in response]
    if missing:
        problems.append(f"回复缺少关键词={missing}")
    generic = [phrase for phrase in GENERIC_FALLBACKS if phrase in response]
    if generic:
        problems.append(f"回复退化为通用兜底={generic}")

    return {
        "id": case["id"],
        "text": case["text"],
        "expected_intent": case["intent"],
        "actual_intent": name,
        "sub_intents": intent.get("sub_intents"),
        "response": response,
        "elapsed_ms": elapsed_ms,
        "passed": not problems,
        "problems": problems,
    }


def run_single_intent_case(case):
    # 只验证分类边界，不触发工具和外部依赖
    intent = recognize_intent(case["text"])
    name = intent.get("name")
    problems = []
    if name in MERGED_INTENTS:
        problems.append(f"模板外组合被误判为合并意图={name}")
    if name not in case["allowed"]:
        problems.append(f"意图={name}，期望单意图之一={case['allowed']}")
    return {
        "id": case["id"],
        "text": case["text"],
        "expected_intent": "single:" + "/".join(case["allowed"]),
        "actual_intent": name,
        "sub_intents": intent.get("sub_intents"),
        "response": "",
        "passed": not problems,
        "problems": problems,
    }


def run_legacy_case(case):
    """模拟旧缓存里的 composite 结果，验证重映射后仍有正确出口。"""
    response = build_response(
        {"name": "composite", "confidence": 0.85, "category": "复合意图", "sub_intents": case["sub_intents"]},
        case["text"], None, [], "", {},
    )
    problems = []
    if f"【思考】{case['intent']}" not in response:
        problems.append(f"未重映射到 {case['intent']}")
    missing = [kw for kw in case["keywords"] if kw not in response]
    if missing:
        problems.append(f"回复缺少关键词={missing}")
    generic = [phrase for phrase in GENERIC_FALLBACKS if phrase in response]
    if generic:
        problems.append(f"回复退化为通用兜底={generic}")
    return {
        "id": case["id"],
        "text": case["text"],
        "expected_intent": case["intent"],
        "actual_intent": case["intent"] if not problems else "unmapped",
        "sub_intents": case["sub_intents"],
        "response": response,
        "passed": not problems,
        "problems": problems,
    }


def main():
    clear_intent_cache()
    clear_response_cache()
    store = create_memory_store()

    results = [check_registry_consistency()]
    results += [run_case(case, store) for case in CASES]
    results += [run_single_intent_case(case) for case in SINGLE_INTENT_CASES]
    results += [run_legacy_case(case) for case in LEGACY_CASES]

    passed = sum(1 for item in results if item["passed"])
    total = len(results)

    print("=" * 72)
    print("复合意图专项测试")
    print("=" * 72)
    for item in results:
        mark = "PASS" if item["passed"] else "FAIL"
        print(f"[{mark}] {item['id']}: {item['text']} -> {item['actual_intent']}")
        if not item["passed"]:
            for problem in item["problems"]:
                print(f"       - {problem}")
            print(f"       response: {item['response'][:160]}")

    print("-" * 72)
    print(f"通过: {passed}/{total} ({passed / total * 100:.1f}%)")

    output_path = os.path.join(ROOT, "reports", "composite_intent_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "name": "composite_intent_test",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "passed": passed,
            "total": total,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"结果已保存至: {output_path}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
