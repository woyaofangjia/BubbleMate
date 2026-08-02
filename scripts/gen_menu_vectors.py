"""预生成菜单向量，用于 query_recommend 的语义检索。
运行: python scripts/gen_menu_vectors.py
输出: data/menu_vectors.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from core.zhipu_client import embed_text

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MENU_PATH = os.path.join(DATA_DIR, "menu_data.json")
OUT_PATH = os.path.join(DATA_DIR, "menu_vectors.json")


def main():
    with open(MENU_PATH, "r", encoding="utf-8") as f:
        menu = json.load(f)

    vectors = []
    for store, items in menu.items():
        for item in items:
            if not item.get("available"):
                continue
            text = f"{item['name']} {item['category']} {item.get('description', '')}"
            vec = embed_text(text)
            vectors.append({
                "name": item["name"],
                "store": store,
                "price": item["price"],
                "category": item["category"],
                "description": item.get("description", ""),
                "sales": item.get("sales", 0),
                "vector": vec,
            })
            print(f"  向量化: {item['name']} ({store})")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(vectors, f, ensure_ascii=False)
    print(f"\n完成: 生成 {len(vectors)} 条向量 -> {OUT_PATH}")


if __name__ == "__main__":
    main()
