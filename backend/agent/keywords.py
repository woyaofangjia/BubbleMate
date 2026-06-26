STORE_KEYWORDS = ["光谷", "武汉大学", "街道口", "汉口", "武昌", "汉阳", "银泰", "武大", "群光", "梦时代", "中南", "徐东"]

DRINK_KEYWORDS = ["芝芝莓莓", "杨枝甘露", "珍珠奶茶", "茉莉绿茶", "柠檬茶", "葡萄冰茶", "芝芝芒果", "糯米奶茶", "芝士奶盖", "鲜果茶", "奶绿"]

CATEGORY_KEYWORDS = {"芝士": "芝士系列", "鲜果茶": "鲜果茶系列", "奶茶": "奶茶系列", "纯茶": "纯茶系列", "果茶": "果茶系列", "奶盖": "奶盖系列"}

INGREDIENT_KEYWORDS = ["珍珠", "糯米", "芝士", "芒果", "草莓", "椰奶"]

SUGAR_MAP = {"无糖": ["无糖", "零糖", "不加糖", "不要糖"], "三分糖": ["三分糖", "少糖", "低糖"], "五分糖": ["五分糖", "半糖"], "七分糖": ["七分糖"], "正常糖": ["正常糖", "标准糖", "全糖", "多糖"]}

ICE_MAP = {"热": ["热饮", "热的", "加热", "温的"], "温": ["温饮", "常温"], "去冰": ["去冰", "不加冰", "不要冰"], "少冰": ["少冰", "微冰"], "正常冰": ["正常冰", "加冰"]}

COMPLAINT_TYPE_MAP = {"口感": "taste", "味道": "taste", "甜": "taste", "酸": "taste", "苦": "taste", "难喝": "taste",
                      "份量": "quantity", "分量": "quantity", "料": "quantity", "冰块": "quantity",
                      "服务": "service", "态度": "service",
                      "配送": "delivery", "送": "delivery", "超时": "delivery",
                      "价格": "price", "贵": "price"}

COMPLAINT_CATEGORY_MAP = {"口感": "口味", "味道": "口味", "甜": "口味", "酸": "口味", "苦": "口味",
                          "份量": "份量", "分量": "份量", "料": "份量", "冰块": "份量",
                          "服务": "服务", "态度": "服务",
                          "配送": "配送", "送": "配送", "超时": "配送",
                          "价格": "价格", "贵": "价格"}

ALLERGEN_MAP = {"牛奶": ["牛奶", "乳糖", "乳清"], "坚果": ["坚果", "花生", "核桃", "杏仁"], "水果": ["芒果", "草莓", "葡萄", "西柚"], "茶": ["茶", "咖啡因"]}

PRICE_MAP = {"high": ["太贵", "太贵了", "不值", "性价比低"], "medium": ["价格适中", "还可以", "不贵"], "low": ["便宜", "划算", "性价比高"]}

INTENT_KEYWORDS = {
    "complaint_taste": ["太甜", "太酸", "太苦", "难喝", "不好喝", "口感", "味道怪", "喝不下"],
    "complaint_quantity": ["份量", "分量", "冰块太多", "配料少", "珍珠少"],
    "complaint_service": ["服务差", "态度差", "电话打不通", "备注没按"],
    "complaint_delivery": ["配送慢", "超时", "送得晚", "等太久"],
    "complaint_price": ["太贵", "价格高", "不值"],
    "query_recommend": ["推荐", "招牌", "热门", "特色", "好喝"],
    "query_menu": ["菜单", "饮品", "有什么"],
    "query_order": ["订单", "单号", "配送", "送到"],
    "query_refund": ["退款", "退钱", "售后"],
    "query_opentime": ["营业时间", "开门", "关门"],
    "query_location": ["门店", "地址", "附近", "在哪"],
    "query_sugar": ["糖度", "甜度", "无糖", "少糖"],
    "query_price": ["多少钱", "价格"],
    "query_temp": ["热", "冰", "温度"],
    "query_delivery": ["外卖", "配送"],
    "query_promo": ["优惠", "活动", "折扣"],
    "query_complaint_status": ["投诉", "处理"],
    "query_member": ["会员", "会员卡"],
    "query_invoice": ["发票", "开票"],
    "place_order": ["点", "买", "下单"],
}

CATEGORY_MAP = {
    "complaint_taste": "口感投诉",
    "complaint_quantity": "份量投诉",
    "complaint_service": "服务投诉",
    "complaint_delivery": "配送投诉",
    "complaint_price": "价格投诉",
    "complaint_taste_refund": "口感投诉",
    "complaint_taste_price": "口感投诉",
    "query_recommend": "推荐查询",
    "query_menu": "菜单查询",
    "query_order": "订单查询",
    "query_refund": "退款查询",
    "query_opentime": "营业时间查询",
    "query_location": "门店查询",
    "query_sugar": "糖度查询",
    "query_price": "价格查询",
    "query_temp": "温度查询",
    "query_delivery": "配送查询",
    "query_promo": "优惠查询",
    "query_complaint_status": "投诉状态",
    "query_member": "会员查询",
    "query_invoice": "发票查询",
    "place_order": "下单",
    "order_create": "创建订单",
    "order_modify": "修改订单",
    "general": "通用",
}