"""
BubbleMate - 银泰、群光、武商梦时代 奶茶店数据爬虫
"""

import os
import json
import urllib.request
import urllib.parse
from typing import List, Dict

# 高德地图配置
AMAP_KEY = os.getenv("AMAP_KEY", "679f279b17eb4669837bb1d31a83a2a9")
AMAP_GEO_URL = "https://restapi.amap.com/v3/geocode/geocode"
AMAP_AROUND_URL = "https://restapi.amap.com/v3/place/around"

def geocode(address: str, city: str = "武汉") -> str:
    """获取地址坐标"""
    params = {
        "key": AMAP_KEY,
        "address": address,
        "city": city
    }
    try:
        query_string = urllib.parse.urlencode(params)
        url = f"{AMAP_GEO_URL}?{query_string}"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("status") == "1" and data.get("geocodes"):
            return data["geocodes"][0].get("location", "")
        return ""
    except Exception as e:
        print(f"地理编码失败: {e}")
        return ""

def search_nearby_shops(location: str, keywords: str = "奶茶,茶饮", radius: int = 1000) -> List[Dict]:
    """搜索附近奶茶店"""
    params = {
        "key": AMAP_KEY,
        "location": location,
        "keywords": keywords,
        "radius": radius,
        "offset": 20,
        "page": 1,
        "extensions": "all"
    }
    try:
        query_string = urllib.parse.urlencode(params)
        url = f"{AMAP_AROUND_URL}?{query_string}"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("status") == "1" and data.get("pois"):
            return data["pois"]
        return []
    except Exception as e:
        print(f"周边搜索失败: {e}")
        return []

def filter_bubble_tea(pois: List[Dict]) -> List[Dict]:
    """过滤奶茶相关店铺"""
    bubble_keywords = ["奶茶", "茶饮", "饮品", "奶盖", "果茶", "柠檬", "贡茶", "一点点", "CoCo", "书亦", "茶颜", "茉莉", "甘茶", "tea"]
    filtered = []
    for poi in pois:
        name = poi.get("name", "")
        tag = poi.get("tag", "")
        address = poi.get("address", "")
        
        # tag可能是列表，转字符串
        if isinstance(tag, list):
            tag = ",".join(tag)
        if isinstance(address, list):
            address = ",".join(address)
        
        combined = name + tag + address
        if any(kw in combined for kw in bubble_keywords):
            filtered.append(poi)
    return filtered

def main():
    # 目标商场（名称 + 已知坐标）
    # 银泰百货(珞喻路店): 珞喻路6号
    # 群光广场: 珞喻路6号（靠近武大）
    # 武商梦时代: 武昌区宝通寺路
    malls = [
        ("银泰", "114.3521,30.5278"),
        ("群光", "114.3506,30.5298"),
        ("武商梦时代", "114.2956,30.5454")
    ]
    
    all_shops = []
    
    print("=" * 60)
    print("BubbleMate - 商场奶茶店数据爬虫")
    print("=" * 60)
    
    for name, location in malls:
        print(f"\n[{name}] 坐标: {location}")
        
        # 搜索周边奶茶店
        pois = search_nearby_shops(location, radius=1000)
        print(f"  获取到 {len(pois)} 条数据")
        
        # 过滤
        bubble_shops = filter_bubble_tea(pois)
        print(f"  过滤后 {len(bubble_shops)} 家奶茶店")
        
        # 添加来源标记
        for shop in bubble_shops:
            shop["source_mall"] = name
        
        all_shops.extend(bubble_shops)
    
    print("\n" + "=" * 60)
    print(f"总计获取 {len(all_shops)} 家奶茶店")
    print("=" * 60)
    
    # 去重（根据店铺名）
    seen = set()
    unique_shops = []
    for shop in all_shops:
        name = shop.get("name", "")
        if name not in seen:
            seen.add(name)
            unique_shops.append(shop)
    
    print(f"去重后 {len(unique_shops)} 家")
    
    # 保存
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "mall_bubble_tea_shops.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_shops, f, ensure_ascii=False, indent=2)
    print(f"\n数据已保存到: {output_path}")
    
    # 打印样例
    print("\n" + "=" * 60)
    print("数据样例:")
    print("=" * 60)
    for shop in unique_shops[:5]:
        print(f"\n[{shop.get('source_mall')}] {shop.get('name')}")
        print(f"  地址: {shop.get('address', '未知')}")
        print(f"  评分: {shop.get('biz_ext', {}).get('rating', '无')}")
        print(f"  人均: {shop.get('biz_ext', {}).get('cost', '未知')}")

if __name__ == "__main__":
    main()
