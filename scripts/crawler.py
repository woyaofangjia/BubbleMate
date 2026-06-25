"""
BubbleMate - 武汉大学附近奶茶店数据爬虫
使用高德地图POI接口获取真实数据

使用方法:
1. 去高德地图开放平台申请Key: https://lbs.amap.com/dev/key/app
2. 设置环境变量: set AMAP_KEY=你的KEY
3. 运行: python scripts/crawler.py
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Dict

# 高德地图配置
AMAP_KEY = os.getenv("AMAP_KEY", "你的高德地图Key")
AMAP_POI_SEARCH_URL = "https://restapi.amap.com/v3/place/text"
AMAP_GEO_URL = "https://restapi.amap.com/v3/geocode/geocode"

# 武汉大学坐标
WHU_LOCATION = "114.36612,30.53755"  # 武汉大学信息学部

def get_whu_boundary() -> str:
    """获取武汉大学大致边界范围"""
    # 武汉大学几个主要校门坐标
    # 珞珈门(南门): 114.36612,30.53755
    # 信息学部: 114.34867,30.53134
    # 工学部门: 114.37659,30.54234
    return "114.34,30.52,114.40,30.56"  # 框选整个武汉大学区域

def search_bubble_tea_shops(keywords: str = "奶茶店") -> List[Dict]:
    """
    搜索奶茶店POI数据
    高德地图POI类型码: 饮品店 050200（茶馆是050100）
    """
    params = {
        "key": AMAP_KEY,
        "keywords": keywords,
        "city": "武汉",
        "citylimit": "true",
        "offset": 20,
        "page": 1,
        "extensions": "all",
        "types": "050200"  # 饮品店
    }
    
    try:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{AMAP_POI_SEARCH_URL}?{query_string}"
        
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        if data.get("status") == "1" and data.get("pois"):
            return data["pois"]
        else:
            print(f"API返回异常: {data}")
            return []
    except Exception as e:
        print(f"请求失败: {e}")
        return []

def search_by_radius() -> List[Dict]:
    """
    在武汉大学周边3公里范围内搜索奶茶店
    使用范围查询接口
    """
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        "key": AMAP_KEY,
        "location": WHU_LOCATION,
        "keywords": "奶茶,茶饮,饮品",
        "radius": 3000,  # 3公里
        "offset": 20,
        "page": 1,
        "extensions": "all"
    }
    
    try:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        if data.get("status") == "1" and data.get("pois"):
            return data["pois"]
        else:
            print(f"周边搜索API返回: {data}")
            return []
    except Exception as e:
        print(f"请求失败: {e}")
        return []

def filter_bubble_tea(pois: List[Dict]) -> List[Dict]:
    """过滤出奶茶相关店铺"""
    bubble_keywords = ["奶茶", "茶饮", "饮品", "奶盖", "果茶", "柠檬", "贡茶", "一点点", "CoCo", "书亦"]
    
    filtered = []
    for poi in pois:
        name = poi.get("name", "")
        address = poi.get("address", "")
        tag = poi.get("tag", "")
        
        # 检查是否包含奶茶相关关键词
        if any(kw in name or kw in address or kw in tag for kw in bubble_keywords):
            filtered.append(poi)
    
    return filtered

def save_to_json(data: List[Dict], filename: str = "bubble_tea_shops.json"):
    """保存数据到JSON文件"""
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
    
    # 确保data目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到: {output_path}")
    return output_path

def crawl_reviews(shop_id: str) -> List[Dict]:
    """
    尝试爬取店铺评价（高德地图API不提供此接口，需要其他来源）
    这里用占位符，演示数据结构
    """
    # 高德地图POI搜索不提供评价数据
    # 评价数据需要爬取大众点评或美团
    return []

def main():
    print("=" * 50)
    print("BubbleMate 奶茶店数据爬虫")
    print("=" * 50)
    
    if AMAP_KEY == "你的高德地图Key":
        print("\n⚠️  请先设置高德地图Key:")
        print("   1. 访问 https://lbs.amap.com/dev/key/app")
        print("   2. 创建应用获取Key")
        print("   3. 设置环境变量: set AMAP_KEY=你的KEY")
        print("\n或者直接修改 scripts/crawler.py 中的 AMAP_KEY 变量")
        return
    
    print(f"\n武汉大学坐标: {WHU_LOCATION}")
    print("正在搜索周边奶茶店...\n")
    
    # 1. 周边搜索
    print("方法1: 周边3公里范围搜索")
    pois = search_by_radius()
    
    if not pois:
        # 2. 如果周边搜索没结果，尝试关键词搜索
        print("\n方法2: 关键词搜索")
        pois = search_bubble_tea_shops("奶茶店")
    
    if pois:
        print(f"✓ 获取到 {len(pois)} 条原始数据")
        
        # 3. 过滤奶茶相关店铺
        bubble_shops = filter_bubble_tea(pois)
        print(f"✓ 过滤后保留 {len(bubble_shops)} 条奶茶店数据")
        
        # 4. 保存
        filepath = save_to_json(bubble_shops)
        
        # 5. 打印样例
        print("\n" + "=" * 50)
        print("数据样例:")
        print("=" * 50)
        for shop in bubble_shops[:3]:
            print(f"\n店铺名: {shop.get('name')}")
            print(f"地址: {shop.get('address', '未知')}")
            print(f"坐标: {shop.get('location')}")
            print(f"电话: {shop.get('tel')}")
            print(f"类型: {shop.get('type')}")
    else:
        print("\n⚠️  未获取到数据，请检查:")
        print("   1. Key是否有效")
        print("   2. 网络连接是否正常")

if __name__ == "__main__":
    main()
