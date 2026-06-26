"""
生成200条训练集数据
覆盖15+意图类型，3种难度（Easy/Medium/Hard）
"""

import json
import random

# 武汉本地场景词汇
WUHAN_LOCATIONS = ["光谷", "江汉路", "街道口", "汉街", "武广", "武大", "街道口", "中南", "徐东", "汉口", "武昌", "汉阳", "银泰", "群光", "梦时代"]
DRINKS = ["幽兰拿铁", "声声乌龙", "多肉葡萄", "芝芝莓莓", "杨枝甘露", "抹茶菩提", "茉莉绿茶", "柠檬茶", "珍珠奶茶", "糯米奶茶", "芋泥波波", "冰沙"]
SUGAR_LEVELS = ["无糖", "零糖", "三分糖", "少糖", "五分糖", "半糖", "七分糖", "正常糖", "全糖"]
ICE_LEVELS = ["热", "温", "去冰", "少冰", "常温", "正常冰"]

# 意图分布
INTENT_DISTRIBUTION = {
    "complaint_taste": 30,
    "complaint_quantity": 25,
    "complaint_service": 20,
    "complaint_delivery": 15,
    "complaint_price": 10,
    "complaint_general": 15,
    "complaint_hygiene": 5,
    "complaint_accessory": 5,
    "query_menu": 20,
    "query_recommend": 15,
    "query_store": 15,
    "query_order": 10,
    "query_price": 10,
    "query_promotion": 10,
    "query_hours": 5,
    "query_invoice": 5,
    "query_member": 5,
    "place_order": 5,
    "unclear": 5
}

# 模板库
TEMPLATES = {
    "complaint_taste": [
        "这个{0}也太{1}了吧，我要的{2}啊",
        "{0}喝起来{1}，跟上次味道差好多",
        "{0}怎么这么{1}，是不是坏了",
        "太{1}了，喝不下去",
        "这杯{0}的{1}受不了",
        "我要的{2}，结果还是{1}",
        "{0}的{1}味太重了",
        "你们家的{0}怎么越做越{1}",
        "{1}死了，这杯{0}没法喝",
        "说好的{2}呢，{1}成这样"
    ],
    "complaint_quantity": [
        "{0}少得可怜，别的店都满满一碗",
        "冰块太多了，{0}都没多少",
        "这糯米也太少了吧",
        "{0}怎么就这一点",
        "给你们差评，份量太少了",
        "珍珠少一半，怎么喝",
        "料都不满，太坑了",
        "{0}就这么点，不厚道",
        "一杯就这点，饿着肚子",
        "半杯都是冰，{0}呢"
    ],
    "complaint_service": [
        "打了电话没人接，什么服务",
        "等了半天没人理",
        "服务态度太差了",
        "你们店员爱答不理的",
        "说了不要冰，结果还是加了",
        "备注不看，太不专业了",
        "催单催了三次才有人理",
        "店家态度恶劣",
        "问个问题半天不回",
        "等了半小时没人接待"
    ],
    "complaint_delivery": [
        "超时{mins}分钟了，还没送到",
        "等了一个多小时，饭都凉了",
        "配送太慢了",
        "说好的半小时呢",
        "送餐洒了一半",
        "包装都破了",
        "骑手态度不好",
        "迟迟不取餐",
        "送错了，我点的{0}",
        "超时{mins}分钟，奶茶都化了"
    ],
    "complaint_price": [
        "这价格太贵了吧",
        "比别的店贵很多",
        "性价比太低",
        "{0}要{price}，抢钱呢",
        "这定价不合理",
        "贵成这样，谁买啊",
        "就这点东西卖这么贵",
        "不值这个价"
    ],
    "complaint_hygiene": [
        "{0}酸到发抖，是不是坏了",
        "喝到异物了",
        "这奶茶味道不对",
        "杯子有异味",
        "怎么感觉不新鲜"
    ],
    "complaint_accessory": [
        "吸管给错了，细吸管怎么喝冰沙",
        "勺子都没给",
        "包装袋破了",
        "杯子漏了",
        "保温袋没给"
    ],
    "complaint_general": [
        "我要投诉",
        "太不满意了",
        "给你们差评",
        "这体验太差了",
        "问题很严重",
        "我要举报",
        "你们怎么回事",
        "太失望了",
        "必须投诉",
        "这事没完"
    ],
    "query_menu": [
        "你们有什么{0}",
        "把菜单发来看看",
        "都有些什么饮品",
        "招牌推荐一下",
        "有什么新品吗",
        "热天喝什么好",
        "适合女生的有哪些",
        "无糖的有哪些"
    ],
    "query_recommend": [
        "推荐一款好喝的",
        "你们家什么最好喝",
        "第一次来，有什么必点的",
        "帮我挑一杯",
        "有选择困难症，帮我推荐",
        "最近流行什么",
        "爆款是哪款",
        "你们店特色是什么"
    ],
    "query_store": [
        "{0}附近有店吗",
        "离我最近的门店在哪",
        "怎么去你们店",
        "{0}店几点关门",
        "门店地址发一下",
        "有几家店",
        "哪家人少一点",
        "{0}那边有吗"
    ],
    "query_order": [
        "帮我查下订单{order_id}",
        "我的订单到哪了",
        "{order_id}什么时候能送到",
        "催一下我的订单",
        "订单{mins}分钟了",
        "帮我改一下订单",
        "取消订单",
        "加一杯到订单里"
    ],
    "query_price": [
        "{0}多少钱",
        "这杯{0}价格多少",
        "菜单有价格表吗",
        "性价比高的是哪个",
        "最便宜的多少钱",
        "最贵的是哪款",
        "第二杯半价吗",
        "有什么优惠"
    ],
    "query_promotion": [
        "今天有什么优惠",
        "有活动吗",
        "会员有什么权益",
        "积分能当钱用吗",
        "怎么成为会员",
        "充值有优惠吗",
        "生日有折扣吗",
        "新人有什么福利"
    ],
    "query_hours": [
        "营业时间是",
        "几点开门关门",
        "可以外送到几点",
        "周末营业吗",
        "晚上最晚几点",
        "24小时营业吗"
    ],
    "query_invoice": [
        "可以开发票吗",
        "发票怎么开",
        "能开增值税发票吗",
        "发票抬头怎么写"
    ],
    "query_member": [
        "会员卡怎么办理",
        "会员有什么优惠",
        "积分怎么用",
        "怎么成为VIP"
    ],
    "place_order": [
        "来一杯{0}",
        "帮我下单",
        "要一杯{0}，{1}",
        "下单{0}两杯",
        "急，来一杯{0}"
    ],
    "unclear": [
        "那个",
        "嗯",
        "你好啊",
        "在吗",
        "有事咨询"
    ]
}

def generate_samples():
    samples = []
    sample_id = 1

    for intent, count in INTENT_DISTRIBUTION.items():
        for i in range(count):
            # 选择模板
            templates = TEMPLATES[intent]
            template = random.choice(templates)

            # 填充模板参数
            drink = random.choice(DRINKS)
            location = random.choice(WUHAN_LOCATIONS)
            sugar = random.choice(SUGAR_LEVELS)
            ice = random.choice(ICE_LEVELS)
            mins = random.randint(30, 90)
            order_id = f"{random.randint(10000, 99999)}"
            price = random.choice(["18", "22", "25", "28", "32"])

            # 根据意图类型选择填充词
            if intent == "complaint_taste":
                words = ["太甜", "太酸", "太苦", "味道怪", "怪怪的"]
                params = [drink, random.choice(words), sugar]
            elif intent == "complaint_quantity":
                params = [drink]
            elif intent == "complaint_delivery":
                params = [str(mins)]
            elif intent == "query_store":
                params = [location]
            elif intent == "query_order":
                params = [order_id]
            elif intent == "query_price":
                params = [drink, price]
            elif intent == "place_order":
                params = [drink, f"{sugar}{ice}"]
            else:
                params = []

            # 尝试填充模板
            try:
                if "{0}" in template:
                    query = template.format(*params)
                elif "{mins}" in template:
                    query = template.replace("{mins}", str(mins))
                elif "{order_id}" in template:
                    query = template.replace("{order_id}", order_id)
                elif "{price}" in template:
                    query = template.replace("{price}", price)
                else:
                    query = template
            except:
                query = template

            # 确定难度
            if intent in ["unclear", "complaint_hygiene"] or "呵呵" in query:
                difficulty = "hard"
            elif intent in ["complaint_service", "complaint_delivery"] or "跟上次" in query or "上次" in query:
                difficulty = "medium"
            else:
                difficulty = "easy"

            # 期望动作
            expected_actions = {
                "complaint_taste": ["道歉", "确认糖度标准", "提供补偿"],
                "complaint_quantity": ["道歉", "核实份量", "记录投诉"],
                "complaint_service": ["道歉", "查询情况", "改进服务"],
                "complaint_delivery": ["查询订单", "道歉", "超时赔付"],
                "complaint_price": ["解释定价", "提供优惠"],
                "complaint_hygiene": ["高度重视", "建议停止饮用", "补偿"],
                "complaint_accessory": ["道歉", "补偿"],
                "query_menu": ["返回菜单列表", "推荐饮品"],
                "query_recommend": ["推荐3款热门", "询问口味偏好"],
                "query_store": ["返回门店地址", "返回营业时间"],
                "query_order": ["查询订单状态", "返回配送进度"],
                "query_price": ["返回价格信息"],
                "query_promotion": ["返回优惠活动"],
                "query_hours": ["返回营业时间"],
                "query_invoice": ["说明开票流程"],
                "query_member": ["说明会员权益"],
                "place_order": ["确认订单", "返回下单结果"],
                "unclear": ["询问具体需求"]
            }

            sample = {
                "id": f"TRAIN-{sample_id:03d}",
                "user_query": query,
                "intent": intent,
                "difficulty": difficulty,
                "expected_action": random.sample(expected_actions.get(intent, []), min(2, len(expected_actions.get(intent, [])))),
                "keywords": [drink, location] if intent in ["query_store", "query_order", "place_order"] else [drink],
                "tool_calls": get_tool_calls(intent),
                "requires_clarification": intent in ["unclear", "complaint_general"],
                "category": intent.replace("_", " ").title()
            }

            samples.append(sample)
            sample_id += 1

    return samples

def get_tool_calls(intent):
    tool_map = {
        "complaint_taste": ["query_order", "log_complaint"],
        "complaint_quantity": ["query_order", "log_complaint"],
        "complaint_service": ["log_complaint"],
        "complaint_delivery": ["query_order", "log_complaint"],
        "complaint_price": ["query_menu", "log_complaint"],
        "complaint_hygiene": ["query_order", "log_complaint"],
        "complaint_accessory": ["query_order", "log_complaint"],
        "query_menu": ["query_menu"],
        "query_recommend": ["query_menu"],
        "query_store": ["query_stores"],
        "query_order": ["query_order"],
        "query_price": ["query_menu"],
        "query_promotion": ["query_menu"],
        "query_hours": ["query_stores"],
        "query_invoice": [],
        "query_member": [],
        "place_order": ["place_order"],
        "unclear": []
    }
    return tool_map.get(intent, [])

def main():
    # 生成数据
    samples = generate_samples()

    # 统计
    intent_stats = {}
    for s in samples:
        intent = s["intent"]
        if intent not in intent_stats:
            intent_stats[intent] = 0
        intent_stats[intent] += 1

    difficulty_stats = {}
    for s in samples:
        diff = s["difficulty"]
        if diff not in difficulty_stats:
            difficulty_stats[diff] = 0
        difficulty_stats[diff] += 1

    # 创建数据集
    dataset = {
        "dataset_name": "BubbleMate_Training_Set",
        "total": len(samples),
        "version": "1.0",
        "generated_at": "2026-06-26",
        "description": "BubbleMate奶茶店客服Agent训练数据集，覆盖15+意图类型",
        "intent_distribution": intent_stats,
        "difficulty_distribution": difficulty_stats,
        "samples": samples
    }

    # 保存
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/training_set_200.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("BubbleMate 训练数据集生成完成")
    print("=" * 60)
    print(f"总样本数: {len(samples)}")
    print()
    print("意图分布:")
    for intent, count in sorted(intent_stats.items()):
        print(f"  {intent}: {count}")
    print()
    print("难度分布:")
    for diff, count in sorted(difficulty_stats.items()):
        print(f"  {diff}: {count}")
    print()
    print("已保存: data/training_set_200.json")

if __name__ == "__main__":
    main()
