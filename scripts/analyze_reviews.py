"""
BubbleMate - 差评数据分析
统计差评类型分布，生成意图识别训练数据
"""

import json
import os
import random

def analyze_reviews():
    """分析差评数据"""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    
    # 加载差评数据
    reviews = json.load(open(os.path.join(base_dir, "real_reviews.json"), "r", encoding="utf-8"))
    
    print("=" * 60)
    print("BubbleMate 差评数据分析报告")
    print("=" * 60)
    
    # 统计差评类型分布
    category_count = {}
    intent_count = {}
    
    for review in reviews:
        cat = review["category"]
        intent = review["intent"]
        category_count[cat] = category_count.get(cat, 0) + 1
        intent_count[intent] = intent_count.get(intent, 0) + 1
    
    print("\n【差评类型分布】")
    for cat, count in sorted(category_count.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}条 ({count/len(reviews)*100:.1f}%)")
    
    print("\n【意图标签分布】")
    for intent, count in sorted(intent_count.items(), key=lambda x: -x[1]):
        print(f"  {intent}: {count}条")
    
    # 关键词统计
    all_keywords = []
    for review in reviews:
        all_keywords.extend(review["keywords"])
    
    keyword_count = {}
    for kw in all_keywords:
        keyword_count[kw] = keyword_count.get(kw, 0) + 1
    
    print("\n【高频关键词TOP10】")
    for kw, count in sorted(keyword_count.items(), key=lambda x: -x[1])[:10]:
        print(f"  {kw}: {count}次")
    
    return reviews, category_count, intent_count

def generate_training_data(reviews):
    """生成意图识别训练数据"""
    training_data = []
    
    # 直接使用真实差评
    for review in reviews:
        training_data.append({
            "text": review["content"],
            "intent": review["intent"],
            "category": review["category"],
            "type": "real"
        })
    
    # 基于真实差评风格生成模拟数据
    templates = {
        "complaint_taste": [
            "太甜了，喝不下去",
            "味道很奇怪，不像之前喝的",
            "酸得没法喝",
            "口感涩涩的",
            "喝起来像兑了水",
            "糖度标注不准，明明点了少糖还是很甜"
        ],
        "complaint_quantity": [
            "冰块太多，饮料都没了",
            "份量比别家少",
            "糯米才几粒",
            "杯子只有一半满",
            "比平时少了一大半"
        ],
        "complaint_service": [
            "打电话没人接",
            "店员态度不好",
            "没按备注做",
            "等了很久没人理",
            "说好的加冰没给"
        ],
        "complaint_delivery": [
            "配送超时一小时",
            "还没开始做就显示超时",
            "送来的饮料撒了一半",
            "骑手找不到地址",
            "预计时间不准"
        ],
        "complaint_price": [
            "这么贵还这么难喝",
            "性价比太低",
            "价格涨了质量没涨",
            "比别家贵一倍"
        ]
    }
    
    # 生成模拟数据
    for intent, texts in templates.items():
        for text in texts:
            training_data.append({
                "text": text,
                "intent": intent,
                "category": intent.replace("complaint_", ""),
                "type": "simulated"
            })
    
    return training_data

def generate_qa_pairs(reviews):
    """生成问答对数据（用于Agent对话训练）"""
    qa_pairs = []
    
    # 加载客服回复
    replies = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "review_replies.json"), "r", encoding="utf-8"))
    
    for reply in replies:
        qa_pairs.append({
            "user": reply["review"],
            "agent": reply["reply"],
            "intent": reviews[reply["review_id"]-1]["intent"],
            "category": reply["category"]
        })
    
    # 补充常见咨询场景
    common_qa = [
        {
            "user": "你们有哪些招牌推荐？",
            "agent": "您好！我们的招牌饮品包括：1)芝芝莓莓 - 鲜草莓搭配芝士奶盖，口感浓郁；2)杨枝甘露 - 椰奶芒果西柚，清爽香甜；3)茉莉绿茶 - 零糖低卡，适合减脂人群。您喜欢什么口味呢？",
            "intent": "query_recommend",
            "category": "菜单咨询"
        },
        {
            "user": "订单什么时候能送到？",
            "agent": "请提供您的订单号，我帮您查询配送状态。正常情况下，门店制作10-15分钟，配送30分钟内到达。高峰期可能稍有延迟。",
            "intent": "query_delivery",
            "category": "订单查询"
        },
        {
            "user": "可以退款吗？",
            "agent": "可以的。请在小程序【我的订单】页面选择该订单，点击【申请售后】，选择退款原因提交即可。退款将在24小时内原路返回。如需人工处理，请提供订单号。",
            "intent": "query_refund",
            "category": "售后咨询"
        },
        {
            "user": "门店营业时间？",
            "agent": "武汉大学门店营业时间：周一至周日 10:00-22:00。银泰创意城店营业至21:30。具体时间可在小程序门店页面查看。",
            "intent": "query_opentime",
            "category": "门店信息"
        },
        {
            "user": "有无糖选项吗？",
            "agent": "有的！我们提供5档糖度选择：标准糖、七分糖、五分糖、三分糖、无糖。建议首次尝试选择五分糖。部分饮品如冰沙系列无法去糖，下单时会有提示。",
            "intent": "query_sugar",
            "category": "饮品定制"
        },
        {
            "user": "附近有门店吗？",
            "agent": "您当前地址附近的门店：1)武汉大学梅园店 - 步行5分钟；2)银泰创意城店 - 步行10分钟；3)街道口1点点店 - 步行8分钟。需要导航吗？",
            "intent": "query_location",
            "category": "门店查询"
        }
    ]
    
    qa_pairs.extend(common_qa)
    
    return qa_pairs

def main():
    reviews, category_count, intent_count = analyze_reviews()
    
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    
    # 生成意图识别训练数据
    training_data = generate_training_data(reviews)
    training_path = os.path.join(base_dir, "intent_training_data.json")
    with open(training_path, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    print(f"\n意图识别训练数据已保存: {training_path} ({len(training_data)}条)")
    
    # 生成问答对数据
    qa_pairs = generate_qa_pairs(reviews)
    qa_path = os.path.join(base_dir, "qa_pairs.json")
    with open(qa_path, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, ensure_ascii=False, indent=2)
    print(f"问答对数据已保存: {qa_path} ({len(qa_pairs)}条)")
    
    print("\n" + "=" * 60)
    print("数据文件清单")
    print("=" * 60)
    print("1. bubble_tea_all.json     - 25家奶茶店信息")
    print("2. real_reviews.json       - 15条真实差评（已标注）")
    print("3. review_replies.json     - 15条客服标准回复")
    print("4. intent_training_data.json - 意图识别训练数据")
    print("5. qa_pairs.json           - 问答对话数据")

if __name__ == "__main__":
    main()