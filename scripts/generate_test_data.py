"""
生成200条测试集数据
分层采样：Easy 50%, Medium 30%, Hard 20%
包含对抗样本（讽刺、指代不明、信息缺失）
"""

import json
import random

# 武汉本地场景
WUHAN_LOCATIONS = ["光谷", "江汉路", "街道口", "汉街", "武广", "武大", "银泰", "群光", "梦时代", "中南", "徐东"]
DRINKS = ["幽兰拿铁", "声声乌龙", "多肉葡萄", "芝芝莓莓", "杨枝甘露", "抹茶菩提", "茉莉绿茶", "珍珠奶茶", "芋泥波波", "冰沙"]

# 难度分层配置
DIFFICULTY_CONFIG = {
    "easy": {
        "count": 100,  # 50%
        "characteristics": ["直接表达", "单一意图", "关键词明确", "无需澄清"]
    },
    "medium": {
        "count": 60,  # 30%
        "characteristics": ["隐含意图", "复合情绪", "上下文依赖", "需要追问"]
    },
    "hard": {
        "count": 40,  # 20%
        "characteristics": ["讽刺语气", "指代不明", "信息严重缺失", "历史对比", "复杂场景"]
    }
}

# 测试集模板
TEST_TEMPLATES = {
    "easy": [
        {"query": "这个杨枝甘露也太甜了吧", "intent": "complaint_taste", "keywords": ["杨枝甘露", "太甜"]},
        {"query": "糯米少得可怜", "intent": "complaint_quantity", "keywords": ["糯米", "少"]},
        {"query": "超时40分钟了", "intent": "complaint_delivery", "keywords": ["超时"]},
        {"query": "退款", "intent": "complaint_refund", "keywords": ["退款"]},
        {"query": "给我推荐一款好喝的", "intent": "query_recommend", "keywords": ["推荐"]},
        {"query": "光谷附近有店吗", "intent": "query_store", "keywords": ["光谷", "店"]},
        {"query": "订单12345什么时候到", "intent": "query_order", "keywords": ["订单", "12345"]},
        {"query": "珍珠奶茶多少钱", "intent": "query_price", "keywords": ["珍珠奶茶", "钱"]},
        {"query": "你们有什么优惠", "intent": "query_promotion", "keywords": ["优惠"]},
        {"query": "几点关门", "intent": "query_hours", "keywords": ["关门"]},
        {"query": "可以开发票吗", "intent": "query_invoice", "keywords": ["发票"]},
        {"query": "会员卡怎么办", "intent": "query_member", "keywords": ["会员"]},
        {"query": "来一杯幽兰拿铁", "intent": "place_order", "keywords": ["幽兰拿铁"]},
        {"query": "菜单发一下", "intent": "query_menu", "keywords": ["菜单"]},
        {"query": "太贵了", "intent": "complaint_price", "keywords": ["贵"]},
        {"query": "冰块太多了", "intent": "complaint_quantity", "keywords": ["冰块", "多"]},
        {"query": "服务态度差", "intent": "complaint_service", "keywords": ["服务", "差"]},
        {"query": "包装破了", "intent": "complaint_delivery", "keywords": ["包装"]},
        {"query": "酸死了", "intent": "complaint_taste", "keywords": ["酸"]},
        {"query": "这家店在哪", "intent": "query_store", "keywords": ["在哪"]},
    ],
    "medium": [
        {"query": "上次买的幽兰拿铁这次怎么没了", "intent": "query_menu", "keywords": ["上次", "没了"], "requires_history": True},
        {"query": "芝芝莓莓太酸了，跟上次喝的不一样", "intent": "complaint_taste", "keywords": ["芝芝莓莓", "太酸", "上次"], "requires_history": True},
        {"query": "超时40分钟，打电话还没人接", "intent": "complaint_delivery", "keywords": ["超时", "电话"], "compound": True},
        {"query": "糯米少得可怜，别的店都满满一碗", "intent": "complaint_quantity", "keywords": ["糯米", "别的店"], "comparison": True},
        {"query": "你们的服务真是一言难尽", "intent": "complaint_service", "keywords": ["服务"], "emotion": "negative"},
        {"query": "这么贵还这么难喝", "intent": "complaint_taste", "keywords": ["贵", "难喝"], "compound": True},
        {"query": "我要退款，单号45678", "intent": "complaint_refund", "keywords": ["退款", "45678"]},
        {"query": "帮我查一下我上次点的是什么", "intent": "query_order", "keywords": ["上次", "点什么"], "requires_history": True},
        {"query": "杨枝甘露少糖少冰多少钱", "intent": "query_price", "keywords": ["杨枝甘露", "少糖少冰"]},
        {"query": "街道口那家几点关门", "intent": "query_hours", "keywords": ["街道口", "关门"]},
        {"query": "冰沙给了细吸管怎么喝", "intent": "complaint_accessory", "keywords": ["冰沙", "吸管"]},
        {"query": "你们家最推荐哪款", "intent": "query_recommend", "keywords": ["推荐"]},
        {"query": "可以加珍珠吗", "intent": "query_customize", "keywords": ["加珍珠"]},
        {"query": "无糖的好喝吗", "intent": "query_recommend", "keywords": ["无糖", "好喝"]},
        {"query": "今天第二杯半价吗", "intent": "query_promotion", "keywords": ["第二杯半价"]},
    ],
    "hard": [
        {"query": "呵呵，你们这服务绝了", "intent": "complaint_sarcasm", "keywords": ["呵呵", "服务"], "adversarial": "sarcasm"},
        {"query": "那个", "intent": "unclear", "keywords": ["那个"], "adversarial": "vague"},
        {"query": "上次那个", "intent": "unclear", "keywords": ["上次"], "adversarial": "reference"},
        {"query": "我点的那个饮料呢", "intent": "unclear", "keywords": ["那个"], "adversarial": "reference"},
        {"query": "还行吧", "intent": "unclear", "keywords": ["还行"], "adversarial": "neutral"},
        {"query": "跟之前一样的", "intent": "unclear", "keywords": ["之前", "一样"], "adversarial": "reference", "requires_history": True},
        {"query": "这味道跟上次差太多了", "intent": "complaint_taste", "keywords": ["上次", "差"], "adversarial": "history_comparison", "requires_history": True},
        {"query": "呵呵，这包装也是绝了", "intent": "complaint_sarcasm", "keywords": ["呵呵", "包装"], "adversarial": "sarcasm"},
        {"query": "你们是不是换配方了", "intent": "complaint_taste", "keywords": ["换配方"], "adversarial": "implied_complaint"},
        {"query": "感觉被坑了", "intent": "complaint_price", "keywords": ["坑"], "adversarial": "implied"},
    ]
}

def generate_test_samples():
    samples = []
    sample_id = 1

    # 按分层采样
    for difficulty, config in DIFFICULTY_CONFIG.items():
        count = config["count"]
        templates = TEST_TEMPLATES[difficulty]

        for i in range(count):
            # 从模板库中选择
            template = templates[i % len(templates)]

            # 添加变体
            location = random.choice(WUHAN_LOCATIONS)
            drink = random.choice(DRINKS)
            order_id = f"{random.randint(10000, 99999)}"

            query = template["query"]
            if location not in query and any(loc in query for loc in WUHAN_LOCATIONS):
                query = query.replace("那家", f"{location}那家").replace("街道口", location)

            # 意图和工具映射
            intent = template["intent"]
            tool_map = {
                "complaint_taste": ["query_order", "log_complaint"],
                "complaint_quantity": ["query_order", "log_complaint"],
                "complaint_delivery": ["query_order", "log_complaint"],
                "complaint_service": ["log_complaint"],
                "complaint_price": ["query_menu", "log_complaint"],
                "complaint_refund": ["query_order", "log_complaint"],
                "complaint_sarcasm": ["log_complaint"],
                "complaint_accessory": ["query_order", "log_complaint"],
                "query_menu": ["query_menu"],
                "query_recommend": ["query_menu"],
                "query_store": ["query_stores"],
                "query_order": ["query_order"],
                "query_price": ["query_menu"],
                "query_promotion": ["query_menu"],
                "query_hours": ["query_stores"],
                "query_customize": ["query_menu"],
                "query_member": [],
                "query_invoice": [],
                "place_order": ["place_order"],
                "unclear": []
            }

            sample = {
                "id": f"TEST-{sample_id:03d}",
                "user_query": query,
                "intent": intent,
                "difficulty": difficulty,
                "layer": difficulty,
                "expected_action": get_expected_action(intent),
                "keywords": template["keywords"],
                "tool_calls": tool_map.get(intent, []),
                "requires_clarification": difficulty in ["medium", "hard"] or template.get("requires_history", False),
                "adversarial_type": template.get("adversarial", None),
                "category": intent.replace("_", " ").title()
            }

            samples.append(sample)
            sample_id += 1

    # 打乱顺序
    random.shuffle(samples)

    # 重新编号
    for i, sample in enumerate(samples):
        sample["id"] = f"TEST-{i+1:03d}"

    return samples

def get_expected_action(intent):
    actions = {
        "complaint_taste": "道歉，确认糖度，反馈或退款",
        "complaint_quantity": "道歉，核实份量，记录投诉",
        "complaint_delivery": "查询订单，道歉，超时赔付",
        "complaint_service": "道歉，查询情况，改进服务",
        "complaint_price": "解释定价，提供优惠方案",
        "complaint_refund": "确认订单，办理退款",
        "complaint_sarcasm": "识别讽刺，诚恳道歉，询问具体问题",
        "complaint_accessory": "道歉，补偿下次订单",
        "query_menu": "返回菜单列表或推荐",
        "query_recommend": "推荐3款热门饮品",
        "query_store": "返回门店地址和营业时间",
        "query_order": "查询订单状态和配送进度",
        "query_price": "返回饮品价格信息",
        "query_promotion": "返回当前优惠活动",
        "query_hours": "返回营业时间",
        "query_customize": "返回加料选项",
        "query_member": "说明会员权益",
        "query_invoice": "说明开票流程",
        "place_order": "确认订单，生成订单号",
        "unclear": "礼貌询问具体需求"
    }
    return actions.get(intent, "提供帮助")

def main():
    samples = generate_test_samples()

    # 统计
    difficulty_stats = {}
    intent_stats = {}
    adversarial_count = 0

    for s in samples:
        diff = s["difficulty"]
        intent = s["intent"]
        if diff not in difficulty_stats:
            difficulty_stats[diff] = 0
        difficulty_stats[diff] += 1
        if intent not in intent_stats:
            intent_stats[intent] = 0
        intent_stats[intent] += 1
        if s.get("adversarial_type"):
            adversarial_count += 1

    dataset = {
        "dataset_name": "BubbleMate_Test_Set",
        "total": len(samples),
        "version": "1.0",
        "generated_at": "2026-06-26",
        "description": "BubbleMate奶茶店客服Agent测试数据集，分层采样覆盖Easy/Medium/Hard",
        "layer_distribution": {
            "easy": DIFFICULTY_CONFIG["easy"]["count"],
            "medium": DIFFICULTY_CONFIG["medium"]["count"],
            "hard": DIFFICULTY_CONFIG["hard"]["count"]
        },
        "difficulty_distribution": difficulty_stats,
        "intent_distribution": intent_stats,
        "adversarial_sample_count": adversarial_count,
        "samples": samples
    }

    import os
    os.makedirs("data", exist_ok=True)
    with open("data/test_set_200.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("BubbleMate 测试数据集生成完成")
    print("=" * 60)
    print(f"总样本数: {len(samples)}")
    print()
    print("分层分布:")
    for diff, count in sorted(difficulty_stats.items()):
        pct = count / len(samples) * 100
        print(f"  {diff}: {count} ({pct:.0f}%)")
    print()
    print("对抗样本数:", adversarial_count)
    print()
    print("意图覆盖:", len(intent_stats), "种")
    print()
    print("已保存: data/test_set_200.json")

if __name__ == "__main__":
    main()
