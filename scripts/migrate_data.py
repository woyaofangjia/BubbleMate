import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.storage.database import init_db
from backend.storage.data_access import add_shop, add_menu_item, add_order, add_inventory

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')

def migrate_shops():
    print("=== 迁移门店数据 ===")
    path = os.path.join(DATA_DIR, 'bubble_tea_all.json')
    if not os.path.exists(path):
        print(f"  文件不存在: {path}")
        return 0
    
    with open(path, 'r', encoding='utf-8') as f:
        shops = json.load(f)
    
    count = 0
    for shop in shops:
        shop_id = f"SHOP-{hash(shop['name']) % 100000:05d}"
        tel = shop.get('tel', '')
        if isinstance(tel, list):
            tel = ';'.join(tel)
        cost = shop.get('cost')
        if isinstance(cost, list):
            cost = cost[0] if cost else None
        tag = shop.get('tag')
        if isinstance(tag, list):
            tag = ','.join(tag)
        add_shop(
            shop_id=shop_id,
            name=shop['name'],
            address=shop.get('address'),
            location=shop.get('location'),
            tel=tel,
            rating=shop.get('rating'),
            cost=cost,
            opentime=shop.get('opentime'),
            business_area=shop.get('business_area'),
            tag=tag
        )
        count += 1
    print(f"  迁移完成: {count} 个门店")
    return count

def migrate_menu():
    print("=== 迁移菜单数据 ===")
    path = os.path.join(DATA_DIR, 'menu_data.json')
    if not os.path.exists(path):
        print(f"  文件不存在: {path}")
        return 0
    
    with open(path, 'r', encoding='utf-8') as f:
        menu_data = json.load(f)
    
    from backend.storage.data_access import get_shop_by_name
    
    count = 0
    for shop_name, items in menu_data.items():
        shop = get_shop_by_name(shop_name)
        if not shop:
            shop_id = f"SHOP-{hash(shop_name) % 100000:05d}"
            add_shop(shop_id=shop_id, name=shop_name)
            print(f"  创建门店: {shop_name}")
        else:
            shop_id = shop['id']
        
        for item in items:
            item_id = f"MENU-{hash(shop_name + item['name']) % 100000:05d}"
            add_menu_item(
                item_id=item_id,
                shop_id=shop_id,
                name=item['name'],
                category=item.get('category'),
                price=item.get('price'),
                available=item.get('available', True),
                description=item.get('description'),
                sales=item.get('sales', 0)
            )
            add_inventory(shop_id, item_id, quantity=50 if item.get('available', True) else 0)
            count += 1
    print(f"  迁移完成: {count} 个菜单项目")
    return count

def migrate_orders():
    print("=== 迁移订单数据 ===")
    path = os.path.join(DATA_DIR, 'orders_mock.json')
    if not os.path.exists(path):
        print(f"  文件不存在: {path}")
        return 0
    
    with open(path, 'r', encoding='utf-8') as f:
        orders_data = json.load(f)
    
    from backend.storage.data_access import get_shop_by_name
    
    count = 0
    for user_id, orders in orders_data.items():
        for order in orders:
            shop = get_shop_by_name(order.get('store', ''))
            shop_id = shop['id'] if shop else None
            
            add_order(
                order_id=order['order_id'],
                user_id=user_id.replace('user_', '').replace('user_session_', ''),
                shop_id=shop_id,
                items=order.get('items', []),
                total=order.get('total'),
                status=order.get('status', 'pending'),
                address=order.get('address'),
                create_time=order.get('create_time'),
                delivery_time=order.get('delivery_time')
            )
            count += 1
    print(f"  迁移完成: {count} 个订单")
    return count

def main():
    print("=== 初始化数据库 ===")
    init_db()
    
    print("\n开始数据迁移...")
    total = 0
    
    total += migrate_shops()
    total += migrate_menu()
    total += migrate_orders()
    
    print(f"\n=== 迁移完成 ===")
    print(f"  共迁移 {total} 条数据")
    print(f"  原JSON文件保留作为备份")

if __name__ == '__main__':
    main()