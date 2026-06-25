"""
BubbleMate Agent - 意图识别系统
使用规则匹配 + 轻量分类器的混合方案
"""

import re
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Intent:
    """意图结果"""
    name: str
    confidence: float
    category: str
    keywords: List[str]
    source: str  # "rule" | "classifier" | "llm"

class IntentRecognizer:
    """意图识别器"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.rule_patterns = self._build_rule_patterns()
        self.training_data = self._load_training_data()
    
    def _build_rule_patterns(self) -> Dict[str, List[re.Pattern]]:
        """构建规则匹配模式"""
        patterns = {
            # 投诉类意图
            "complaint_taste": [
                re.compile(r"(太甜|太酸|太苦|难喝|不好喝|口感不好|味道怪|涩|掺水)", re.I),
                re.compile(r"(糖度|甜度).*?(甜|酸|苦)", re.I),
            ],
            "complaint_quantity": [
                re.compile(r"(份量|分量|量).*?(少|小|不够)", re.I),
                re.compile(r"(冰块).*?(太多|全是)", re.I),
                re.compile(r"(糯米|珍珠|配料).*?(少|没|不够)", re.I),
            ],
            "complaint_service": [
                re.compile(r"(服务|态度).*?(差|不好)", re.I),
                re.compile(r"(电话).*?(打不通|没人接)", re.I),
                re.compile(r"(备注).*?(没按|不给|没给)", re.I),
            ],
            "complaint_delivery": [
                re.compile(r"(配送|送达|送).*?(慢|超时|晚)", re.I),
                re.compile(r"(等).*?(久|长|慢)", re.I),
            ],
            "complaint_price": [
                re.compile(r"(贵|价格|性价比).*?(高|低|不好)", re.I),
            ],
            
            # 查询类意图
            "query_recommend": [
                re.compile(r"(推荐|招牌|热门|特色).*?(饮品|奶茶|茶)", re.I),
                re.compile(r"(有什么|哪些).*?(好喝|推荐)", re.I),
            ],
            "query_menu": [
                re.compile(r"(菜单|饮品|有什么).*?(列出|看看|查询)", re.I),
                re.compile(r"(价格|多少钱)", re.I),
            ],
            "query_order": [
                re.compile(r"(订单|配送).*?(查询|状态|进度)", re.I),
                re.compile(r"(我的|查询).*?(订单)", re.I),
            ],
            "query_refund": [
                re.compile(r"(退款|退钱|退货|售后)", re.I),
            ],
            "query_opentime": [
                re.compile(r"(营业时间|开门|关门|营业)", re.I),
            ],
            "query_location": [
                re.compile(r"(门店|地址|位置).*?(查询|在哪|附近)", re.I),
            ],
            "query_sugar": [
                re.compile(r"(糖度|无糖|少糖|糖).*?(选择|选项|有)", re.I),
            ],
            
            # 点单类意图
            "order_create": [
                re.compile(r"(点|买|要).*?(一杯|奶茶|饮品)", re.I),
                re.compile(r"(下单|购买)", re.I),
            ],
            "order_modify": [
                re.compile(r"(修改|改).*?(订单|饮品)", re.I),
                re.compile(r"(取消|退).*?(订单)", re.I),
            ],
        }
        return patterns
    
    def _load_training_data(self) -> List[Dict]:
        """加载训练数据"""
        path = os.path.join(self.data_dir, "intent_training_data.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def recognize(self, text: str) -> Intent:
        """识别意图"""
        # 1. 规则匹配优先（最快）
        intent = self._rule_match(text)
        if intent and intent.confidence > 0.8:
            return intent
        
        # 2. 关键词匹配（中等）
        intent = self._keyword_match(text)
        if intent and intent.confidence > 0.6:
            return intent
        
        # 3. 默认返回通用意图
        return Intent(
            name="general",
            confidence=0.3,
            category="通用",
            keywords=[],
            source="default"
        )
    
    def _rule_match(self, text: str) -> Optional[Intent]:
        """规则匹配"""
        for intent_name, patterns in self.rule_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    # 提取匹配的关键词
                    match = pattern.search(text)
                    matched_text = match.group() if match else ""
                    
                    return Intent(
                        name=intent_name,
                        confidence=0.85,
                        category=self._get_category(intent_name),
                        keywords=[matched_text],
                        source="rule"
                    )
        return None
    
    def _keyword_match(self, text: str) -> Optional[Intent]:
        """关键词匹配"""
        # 从训练数据中查找相似文本
        best_match = None
        best_score = 0
        
        for item in self.training_data:
            # 计算关键词重叠度
            score = self._calculate_similarity(text, item["text"])
            if score > best_score:
                best_score = score
                best_match = item
        
        if best_match and best_score > 0.3:
            return Intent(
                name=best_match["intent"],
                confidence=best_score,
                category=best_match["category"],
                keywords=best_match.get("keywords", []),
                source="keyword"
            )
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简单关键词匹配）"""
        # 提取关键词
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0
    
    def _get_category(self, intent_name: str) -> str:
        """获取意图类别"""
        category_map = {
            "complaint_taste": "口感投诉",
            "complaint_quantity": "份量投诉",
            "complaint_service": "服务投诉",
            "complaint_delivery": "配送投诉",
            "complaint_price": "价格投诉",
            "query_recommend": "推荐查询",
            "query_menu": "菜单查询",
            "query_order": "订单查询",
            "query_refund": "退款查询",
            "query_opentime": "营业时间查询",
            "query_location": "门店查询",
            "query_sugar": "糖度查询",
            "order_create": "创建订单",
            "order_modify": "修改订单",
        }
        return category_map.get(intent_name, "通用")


def test_intent_recognizer():
    """测试意图识别"""
    recognizer = IntentRecognizer("data")
    
    test_texts = [
        "太甜了，喝不下去",
        "冰块太多，饮料都没了",
        "你们有什么招牌推荐？",
        "配送超时一小时",
        "订单什么时候能送到？",
        "可以退款吗？",
        "门店营业时间？",
    ]
    
    print("\n意图识别测试:")
    print("-" * 50)
    for text in test_texts:
        intent = recognizer.recognize(text)
        print(f"输入: {text}")
        print(f"意图: {intent.name} (置信度: {intent.confidence:.2f})")
        print(f"类别: {intent.category} | 来源: {intent.source}")
        print("-" * 50)

if __name__ == "__main__":
    test_intent_recognizer()