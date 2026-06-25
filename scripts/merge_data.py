"""
BubbleMate - 合并奶茶店数据
合并武汉大学周边 + 三大商场 的奶茶店数据
"""

import os
import json

def load_json(filepath):
    """加载JSON文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def merge_shops():
    """合并所有奶茶店数据"""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    
    # 加载各数据源
    whu_shops = load_json(os.path.join(base_dir, "bubble_tea_shops.json"))
    mall_shops = load_json(os.path.join(base_dir, "mall_bubble_tea_shops.json"))
    
    print(f"武汉大学周边: {len(whu_shops)} 家")
    print(f"三大商场周边: {len(mall_shops)} 家")
    
    # 合并
    all_shops = whu_shops + mall_shops
    
    # 按名称去重
    seen = set()
    unique_shops = []
    for shop in all_shops:
        name = shop.get("name", "")
        if name not in seen:
            seen.add(name)
            # 简化数据，保留关键字段
            simplified = {
                "name": name,
                "address": shop.get("address", ""),
                "tel": shop.get("tel", ""),
                "location": shop.get("location", ""),
                "rating": shop.get("biz_ext", {}).get("rating", ""),
                "cost": shop.get("biz_ext", {}).get("cost", ""),
                "opentime": shop.get("biz_ext", {}).get("opentime2", ""),
                "business_area": shop.get("business_area", ""),
                "tag": shop.get("tag", ""),
                "source": shop.get("source_mall", "武汉大学")
            }
            unique_shops.append(simplified)
    
    # 按评分排序
    unique_shops.sort(key=lambda x: float(x["rating"]) if x["rating"] else 0, reverse=True)
    
    print(f"\n合并后总计: {len(unique_shops)} 家 (去重后)")
    
    # 保存合并数据
    output_path = os.path.join(base_dir, "bubble_tea_all.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_shops, f, ensure_ascii=False, indent=2)
    
    print(f"已保存到: {output_path}")
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("BubbleMate 奶茶店数据库")
    print("=" * 60)
    
    for i, shop in enumerate(unique_shops, 1):
        rating_str = shop["rating"] if shop["rating"] else "无"
        cost_str = f"¥{shop['cost']}" if shop["cost"] else "未知"
        print(f"{i}. {shop['name']}")
        print(f"   地址: {shop['address']}")
        print(f"   评分: {rating_str} | 人均: {cost_str}")
        print()
    
    return unique_shops

if __name__ == "__main__":
    merge_shops()
