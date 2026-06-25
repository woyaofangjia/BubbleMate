"""
BubbleMate Agent - 增强版意图识别系统
优化规则模式 + 增强关键词匹配 + 多维度特征提取
"""

import re
import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Intent:
    """意图结果"""
    name: str
    confidence: float
    category: str
    keywords: List[str]
    source: str

class IntentRecognizerV2:
    """增强版意图识别器"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.rule_patterns = self._build_rule_patterns()
        self.training_data = self._load_training_data()
        
        # 意图类别映射
        self.category_map = {
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
    
    def _build_rule_patterns(self) -> Dict[str, List[re.Pattern]]:
        """构建增强版规则匹配模式"""
        patterns = {
            # 投诉类意图
            "complaint_taste": [
                re.compile(r"(太甜|太酸|太苦|难喝|不好喝|口感不好|味道怪|涩|掺水|不正宗)", re.I),
                re.compile(r"(糖度|甜度).*?(甜|酸|苦|淡)", re.I),
                re.compile(r"(味道).*?(差|怪|不好)", re.I),
                re.compile(r"(喝不下|喝不下去)", re.I),
                re.compile(r"(重做|重新做)", re.I),
            ],
            "complaint_quantity": [
                re.compile(r"(份量|分量|量).*?(少|小|不够|不足)", re.I),
                re.compile(r"(冰块).*?(太多|全是|太多了)", re.I),
                re.compile(r"(糯米|珍珠|配料|料).*?(少|没|不够|不足)", re.I),
                re.compile(r"(饮料).*?(没了|没多少)", re.I),
            ],
            "complaint_service": [
                re.compile(r"(服务|态度).*?(差|不好|恶劣)", re.I),
                re.compile(r"(电话).*?(打不通|没人接|打了没人接)", re.I),
                re.compile(r"(备注).*?(没按|不给|没给|没照做)", re.I),
                re.compile(r"(差评|投诉服务)", re.I),
            ],
            "complaint_delivery": [
                re.compile(r"(配送|送达|送).*?(慢|超时|晚|迟迟不到)", re.I),
                re.compile(r"(等).*?(久|长|慢|很久)", re.I),
                re.compile(r"(超时)", re.I),
            ],
            "complaint_price": [
                re.compile(r"(贵|价格|性价比).*?(高|低|不好|不值)", re.I),
                re.compile(r"(这么贵|太贵)", re.I),
            ],
            
            # 查询类意图 - 增强版
            "query_recommend": [
                re.compile(r"(推荐|招牌|热门|特色|新品).*?(饮品|奶茶|茶|喝什么)", re.I),
                re.compile(r"(有什么|哪些).*?(好喝|推荐|招牌)", re.I),
                re.compile(r"(帮我|给我).*?(推荐|选)", re.I),
            ],
            "query_menu": [
                re.compile(r"(菜单|饮品|有什么).*?(列出|看看|查询|都有)", re.I),
                re.compile(r"(有什么).*?(喝的|饮品)", re.I),
            ],
            "query_order": [
                re.compile(r"(订单|单号).*?(查询|状态|进度|到哪了)", re.I),
                re.compile(r"(我的|查询).*?(订单)", re.I),
                re.compile(r"(订单).*?(什么时候|能送到)", re.I),
                re.compile(r"(\d{5,}).*?(订单)", re.I),
            ],
            "query_refund": [
                re.compile(r"(退款|退钱|退货|售后)", re.I),
                re.compile(r"(要求退款)", re.I),
            ],
            "query_opentime": [
                re.compile(r"(营业时间|开门|关门|营业|几点开门)", re.I),
            ],
            "query_location": [
                re.compile(r"(门店|地址|位置|附近).*?(查询|在哪|有没有)", re.I),
                re.compile(r"(附近).*?(店|门店)", re.I),
            ],
            "query_sugar": [
                re.compile(r"(糖度|无糖|少糖|正常糖|糖).*?(选择|选项|有)", re.I),
                re.compile(r"(甜度).*?(几种|多少种)", re.I),
            ],
            "query_price": [
                re.compile(r"(多少钱|价格|贵不贵)", re.I),
                re.compile(r"(.*?)多少钱", re.I),
            ],
            "query_temp": [
                re.compile(r"(热|冰|温度).*?(可以|能做|选择)", re.I),
                re.compile(r"(热的|冰的|温的)", re.I),
            ],
            "query_delivery": [
                re.compile(r"(外卖|配送|送餐).*?(有|可以|支持)", re.I),
                re.compile(r"(能送|送到)", re.I),
            ],
            "query_promo": [
                re.compile(r"(优惠|活动|折扣|券).*?(有|今天|现在)", re.I),
                re.compile(r"(打折|特价)", re.I),
            ],
            "query_complaint_status": [
                re.compile(r"(投诉).*?(处理|进度|结果)", re.I),
                re.compile(r"(上次).*?(投诉)", re.I),
            ],
            "query_member": [
                re.compile(r"(会员|会员卡|积分).*?(办|怎么|查询)", re.I),
            ],
            "query_invoice": [
                re.compile(r"(发票|开票).*?(能|可以|怎么)", re.I),
            ],
            
            # 点单类意图
            "place_order": [
                re.compile(r"(点|买|要).*?(一杯|奶茶|饮品)", re.I),
                re.compile(r"(下单|购买|订购)", re.I),
                re.compile(r"(我要)", re.I),
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
        """识别意图（增强版）"""
        # 1. 规则匹配（最高优先级）
        intent = self._rule_match(text)
        if intent and intent.confidence > 0.8:
            return intent
        
        # 2. 多关键词匹配
        intent = self._multi_keyword_match(text)
        if intent and intent.confidence > 0.5:
            return intent
        
        # 3. 训练数据匹配
        intent = self._training_data_match(text)
        if intent and intent.confidence > 0.4:
            return intent
        
        # 4. 默认通用意图
        return Intent(
            name="general",
            confidence=0.2,
            category="通用",
            keywords=[],
            source="default"
        )
    
    def _rule_match(self, text: str) -> Optional[Intent]:
        """规则匹配（增强版）"""
        matched_patterns = []
        
        for intent_name, patterns in self.rule_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    matched_text = match.group()
                    matched_patterns.append((intent_name, matched_text))
        
        # 如果有多个匹配，选择最具体的
        if matched_patterns:
            # 优先选择投诉类和查询类中更具体的意图
            priority_order = [
                "complaint_taste", "complaint_quantity", "complaint_service", 
                "complaint_delivery", "complaint_price",
                "query_order", "query_refund", "query_location",
                "query_recommend", "query_menu",
            ]
            
            for priority in priority_order:
                for intent_name, matched_text in matched_patterns:
                    if intent_name == priority:
                        return Intent(
                            name=intent_name,
                            confidence=0.85,
                            category=self.category_map.get(intent_name, "通用"),
                            keywords=[matched_text],
                            source="rule"
                        )
            
            # 默认返回第一个匹配
            intent_name, matched_text = matched_patterns[0]
            return Intent(
                name=intent_name,
                confidence=0.85,
                category=self.category_map.get(intent_name, "通用"),
                keywords=[matched_text],
                source="rule"
            )
        
        return None
    
    def _multi_keyword_match(self, text: str) -> Optional[Intent]:
        """多关键词匹配（增强版）"""
        keyword_intent_map = {
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
        
        best_match = None
        best_score = 0
        
        for intent_name, keywords in keyword_intent_map.items():
            matched_count = sum(1 for kw in keywords if kw in text)
            if matched_count > 0:
                # 计算得分：匹配关键词数 / 该意图总关键词数
                score = matched_count / len(keywords)
                # 如果匹配多个关键词，增加置信度
                if matched_count >= 2:
                    score = min(score * 1.2, 0.95)
                
                if score > best_score:
                    best_score = score
                    best_match = intent_name
        
        if best_match and best_score >= 0.3:
            return Intent(
                name=best_match,
                confidence=min(best_score + 0.2, 0.9),
                category=self.category_map.get(best_match, "通用"),
                keywords=[],
                source="multi_keyword"
            )
        
        return None
    
    def _training_data_match(self, text: str) -> Optional[Intent]:
        """训练数据匹配（增强版）"""
        best_match = None
        best_score = 0
        
        for item in self.training_data:
            score = self._calculate_similarity(text, item["text"])
            if score > best_score:
                best_score = score
                best_match = item
        
        if best_match and best_score > 0.3:
            return Intent(
                name=best_match["intent"],
                confidence=best_score * 0.8 + 0.2,
                category=best_match["category"],
                keywords=best_match.get("keywords", []),
                source="training"
            )
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（增强版）"""
        # 提取2-gram
        def get_ngrams(s: str, n: int = 2) -> set:
            s = s.replace(" ", "")
            return set(s[i:i+n] for i in range(len(s) - n + 1))
        
        ngrams1 = get_ngrams(text1)
        ngrams2 = get_ngrams(text2)
        
        if not ngrams1 or not ngrams2:
            return 0
        
        intersection = ngrams1 & ngrams2
        union = ngrams1 | ngrams2
        
        return len(intersection) / len(union) if union else 0


def test_intent_recognizer_v2():
    """测试增强版意图识别"""
    recognizer = IntentRecognizerV2("data")
    
    test_cases = [
        ("太甜了，喝不下去", "complaint_taste"),
        ("冰块太多，饮料都没了", "complaint_quantity"),
        ("你们有什么招牌推荐？", "query_recommend"),
        ("配送超时一小时", "complaint_delivery"),
        ("订单12345什么时候能送到？", "query_order"),
        ("可以退款吗？", "query_refund"),
        ("门店营业时间？", "query_opentime"),
        ("附近有门店吗？", "query_location"),
        ("珍珠奶茶多少钱？", "query_price"),
        ("可以做热的吗？", "query_temp"),
        ("甜度有几种选择？", "query_sugar"),
        ("有外卖吗？", "query_delivery"),
        ("今天有什么优惠？", "query_promo"),
        ("上次的投诉处理好了吗？", "query_complaint_status"),
        ("我要下单", "place_order"),
        ("会员卡怎么办？", "query_member"),
        ("能开发票吗？", "query_invoice"),
        ("不好喝，要求退款", "complaint_taste"),
        ("这么贵还这么难喝", "complaint_taste"),
        ("服务太差了", "complaint_service"),
    ]
    
    correct = 0
    total = len(test_cases)
    
    print("\n" + "=" * 60)
    print("增强版意图识别测试")
    print("=" * 60)
    
    for text, expected in test_cases:
        intent = recognizer.recognize(text)
        is_correct = intent.name == expected
        
        status = "✓" if is_correct else "✗"
        print(f"{status} [{intent.name}] {text}")
        
        if is_correct:
            correct += 1
    
    accuracy = correct / total * 100
    print(f"\n准确率: {accuracy:.1f}% ({correct}/{total})")
    
    return accuracy >= 80

if __name__ == "__main__":
    test_intent_recognizer_v2()
