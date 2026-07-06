import re
import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .keywords import INTENT_KEYWORDS, CATEGORY_MAP

@dataclass
class Intent:
    """意图结果"""
    name: str
    confidence: float
    category: str
    keywords: List[str]
    source: str

class IntentRecognizerV2:
    """增强版意图识别器 - 规则 + LLM混合策略"""
    
    def __init__(self, data_dir: str, use_llm: bool = True):
        self.data_dir = data_dir
        self.use_llm = use_llm
        self.rule_patterns = self._build_rule_patterns()
        self.training_data = self._load_training_data()
        
        # LLM兜底识别器（可选）
        if use_llm:
            try:
                from backend.core.zhipu_client import call_llm
                self.llm_client = call_llm
            except Exception as e:
                print(f"LLM初始化失败，使用纯规则模式: {e}")
                self.use_llm = False
                self.llm_client = None
        
        self.category_map = CATEGORY_MAP
    
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
                re.compile(r"(酸死了|换配方|跟上次不一样)", re.I),
            ],
            "complaint_quantity": [
                re.compile(r"(份量|分量|量).*?(少|小|不够|不足)", re.I),
                re.compile(r"(冰块).*?(太多|全是|太多了)", re.I),
                re.compile(r"(糯米|珍珠|配料|料).*?(太少|少了|不够|不足)", re.I),
                re.compile(r"(饮料).*?(没了|没多少)", re.I),
                re.compile(r"(少得可怜)", re.I),
            ],
            "complaint_service": [
                re.compile(r"(服务|态度).*?(差|不好|恶劣)", re.I),
                re.compile(r"(电话).*?(打不通|没人接|打了没人接)", re.I),
                re.compile(r"(备注).*?(没按|不给|没给|没照做)", re.I),
                re.compile(r"(差评|投诉服务)", re.I),
                re.compile(r"(一言难尽)", re.I),
            ],
            "complaint_delivery": [
                re.compile(r"(配送|送达|送).*?(慢|超时|晚|迟迟不到)", re.I),
                re.compile(r"(等).*?(久|长|慢|很久)", re.I),
                re.compile(r"(超时)", re.I),
                re.compile(r"(包装破了|包装坏了)", re.I),
            ],
            "complaint_price": [
                re.compile(r"(贵|价格|性价比).*?(高|低|不好|不值)", re.I),
                re.compile(r"(这么贵|太贵)", re.I),
                re.compile(r"(被坑了)", re.I),
            ],
            "complaint_refund": [
                re.compile(r"(退款|退钱|要求退款|申请退款)", re.I),
                re.compile(r"(我要退款)", re.I),
            ],
            "complaint_sarcasm": [
                re.compile(r"(呵呵|绝了|也是绝了)", re.I),
                re.compile(r"(真是|一言难尽).*?(服务|包装)", re.I),
            ],
            "complaint_accessory": [
                re.compile(r"(吸管).*?(细|怎么喝)", re.I),
                re.compile(r"(冰沙).*?(吸管)", re.I),
            ],
            
            # 查询类意图 - 增强版
            "query_recommend": [
                # 推荐查询 - 大幅扩充
                re.compile(r"(推荐|招牌|热门|特色|新品|必点)", re.I),
                re.compile(r"(有什么|有哪些).*?(好喝|推荐|招牌|热门)", re.I),
                re.compile(r"(帮我|给我).*?(推荐|选|挑)", re.I),
                re.compile(r"(喝什么|点什么|买什么)", re.I),
                re.compile(r"(什么).*?(好喝|好吃)", re.I),
                re.compile(r"(给我推荐一款|最推荐)", re.I),
                re.compile(r"(好喝吗)", re.I),
            ],
            "query_menu": [
                # 菜单查询 - 扩充
                re.compile(r"(菜单|饮品|饮料).*?(列出|看看|查询|都有)", re.I),
                re.compile(r"(有什么).*?(喝的|饮品|饮料)", re.I),
                re.compile(r"(看看).*?(菜单|饮品)", re.I),
                re.compile(r"(价格|多少钱).*?(列表|表)", re.I),
                re.compile(r"(菜单发一下)", re.I),
                re.compile(r"(上次的没了|这次怎么没了)", re.I),
            ],
            "query_order": [
                re.compile(r"(订单|单号).*?(查询|状态|进度|到哪了)", re.I),
                re.compile(r"(我的|查询).*?(订单)", re.I),
                re.compile(r"(订单).*?(什么时候|能送到)", re.I),
                re.compile(r"(\d{5,}).*?(订单)", re.I),
                re.compile(r"(查订单|我的单|订单号)", re.I),
                re.compile(r"(帮我查|我的订单|下单记录)", re.I),
            ],
            "query_refund": [
                re.compile(r"(退款|退钱|退货|售后)", re.I),
                re.compile(r"(要求退款)", re.I),
                re.compile(r"(怎么退款)", re.I),
            ],
            "query_opentime": [
                re.compile(r"(营业时间|开门|关门|营业|几点开门)", re.I),
            ],
            "query_hours": [
                re.compile(r"(几点关门|几点开门)", re.I),
                re.compile(r"(营业时间|开门时间|关门时间)", re.I),
            ],
            "query_location": [
                # 门店/位置查询 - 大幅扩充关键词池
                re.compile(r"(门店|店铺|店|地址|位置)", re.I),
                re.compile(r"(附近|周边|最近).*?(有|店|门店|奶茶)", re.I),
                re.compile(r"(哪里|在哪|怎么走|在哪边).*?(有|买|喝)", re.I),
                re.compile(r"(门店|店).*?(在哪|在哪边|位置|地址)", re.I),
                re.compile(r"(离|距).*?(多远|近|远)", re.I),
                re.compile(r"(附近有门店吗)", re.I),
                re.compile(r"(最近的一家店)", re.I),
            ],
            "query_store": [
                re.compile(r"(门店|店铺|店|地址|位置)", re.I),
                re.compile(r"(附近|周边).*?(有|店)", re.I),
                re.compile(r"(在哪|在哪边).*?(店|门店)", re.I),
                re.compile(r"(这家店在哪|附近有店吗)", re.I),
            ],
            "query_sugar": [
                re.compile(r"(糖度|无糖|少糖|正常糖|糖).*?(选择|选项|有)", re.I),
                re.compile(r"(甜度).*?(几种|多少种)", re.I),
            ],
            "query_price": [
                re.compile(r"(多少钱|价格|贵不贵)", re.I),
                re.compile(r"(\w+)?多少钱$", re.I),
                re.compile(r"(卖|要|买).*?多少钱", re.I),
                re.compile(r"(价位|一杯多少钱|多少钱一杯)", re.I),
                re.compile(r"(.*?)多少钱", re.I),
                re.compile(r"(便宜|最便宜).*?(奶茶|饮品|多少钱|店)", re.I),
                re.compile(r"(哪家|什么).*?(便宜|贵|价格)", re.I),
                re.compile(r"(附近).*?(哪家|什么).*?(便宜|贵)", re.I),
            ],
            "query_temp": [
                re.compile(r"(热|冰|温度).*?(可以|能做|选择)", re.I),
                re.compile(r"(热的|冰的|温的)", re.I),
                re.compile(r"(去冰|少冰)", re.I),
            ],
            "query_delivery": [
                re.compile(r"(外卖|配送|送餐).*?(有|可以|支持)", re.I),
                re.compile(r"(能送|送到)", re.I),
            ],
            "query_promotion": [
                re.compile(r"(优惠|活动|折扣|券).*?(有|今天|现在)", re.I),
                re.compile(r"(有什么).*?(优惠|活动|折扣)", re.I),
                re.compile(r"(打折|特价)", re.I),
                re.compile(r"(第二杯半价|优惠活动|今日优惠)", re.I),
                re.compile(r"(现在有什么优惠)", re.I),
            ],
            "query_complaint_status": [
                re.compile(r"(投诉).*?(处理|进度|结果)", re.I),
                re.compile(r"(上次).*?(投诉)", re.I),
            ],
            "query_member": [
                re.compile(r"(会员|会员卡|积分).*?(办|怎么|查询)", re.I),
                re.compile(r"(会员权益)", re.I),
            ],
            "query_invoice": [
                re.compile(r"(发票|开票).*?(能|可以|怎么)", re.I),
                re.compile(r"(开发票)", re.I),
            ],
            "query_customize": [
                re.compile(r"(加料|配料|料|珍珠|椰果|仙草|芋圆).*?(可以|能加|有哪些|有什么)", re.I),
                re.compile(r"(可以加|能加|加个|加一份).*?(珍珠|椰果|仙草|芋圆|布丁)", re.I),
                re.compile(r"(定制|甜度|温度|糖度|冰度).*?(选择|选项|调整)", re.I),
                re.compile(r"(有什么.*?(料|加料|配料))", re.I),
                re.compile(r"(加珍珠)", re.I),
            ],
            "query_history": [
                re.compile(r"(历史订单|之前.*?(订单|买过)|以前.*?(点|买))", re.I),
                re.compile(r"(我之前|我以前|我上次).*?(点|买|喝|下单)", re.I),
                re.compile(r"(订单记录|购买记录|消费记录)", re.I),
                re.compile(r"(最近.*?(订单|买过|点过))", re.I),
                re.compile(r"(上次买的|之前点的)", re.I),
            ],
            
            # 点单类意图
            "place_order": [
                re.compile(r"(点|买|要).*?(一杯|奶茶|饮品)", re.I),
                re.compile(r"(下单|购买|订购)", re.I),
                re.compile(r"(我要)", re.I),
                re.compile(r"(来一杯).*?", re.I),
            ],
            "order_modify": [
                re.compile(r"(修改|改).*?(订单|饮品)", re.I),
                re.compile(r"(取消|退).*?(订单)", re.I),
            ],
            "unclear": [
                re.compile(r"(那个)$", re.I),
                re.compile(r"(跟之前一样|和上次一样)", re.I),
                re.compile(r"(上次那个)", re.I),
                re.compile(r"(还行吧|还行)", re.I),
                re.compile(r"(我点的那个)", re.I),
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
        """识别意图（规则优先 → 关键词阈值 → LLM兜底）"""
        # 1. 规则匹配（覆盖80%常见问法，最高优先级）
        intent = self._rule_match(text)
        if intent and intent.confidence > 0.7:
            return intent
        
        # 2. 多关键词匹配（阈值保护，防止低质量匹配抢跑）
        intent = self._multi_keyword_match(text)
        if intent and intent.confidence > 0.6:
            return intent
        
        # 3. 训练数据匹配（补充覆盖）
        intent = self._training_data_match(text)
        if intent and intent.confidence > 0.5:
            return intent
        
        # 4. LLM兜底识别（处理剩余20%疑难样本）
        if self.use_llm and self.llm_client:
            intent = self._llm_recognize(text)
            if intent and intent.confidence > 0.5:
                return intent
        
        # 5. 默认通用意图
        return Intent(
            name="general",
            confidence=0.2,
            category="通用",
            keywords=[],
            source="default"
        )
    
    def _llm_recognize(self, text: str) -> Optional[Intent]:
        """使用LLM进行意图识别（针对疑难样本）"""
        try:
            prompt = f"""你是一个奶茶店客服意图识别器。用户说："{text}"

请判断意图类别（从以下选择）：
- query_location: 门店查询
- query_menu: 菜单查询
- query_recommend: 推荐查询
- query_order: 订单查询
- query_refund: 退款查询
- query_promotion: 优惠活动查询
- query_customize: 加料定制查询
- query_history: 历史订单查询
- query_hours: 营业时间查询
- query_store: 门店位置查询
- query_price: 价格查询
- query_member: 会员查询
- query_invoice: 发票查询
- complaint_taste: 口感投诉
- complaint_quantity: 份量投诉
- complaint_service: 服务投诉
- complaint_delivery: 配送投诉
- complaint_price: 价格投诉
- complaint_refund: 退款投诉
- complaint_sarcasm: 讽刺投诉
- complaint_accessory: 配件投诉
- place_order: 下单
- general: 通用/无法识别
- unclear: 不明确

直接输出类别名称，不要其他文字。"""

            response = self.llm_client([{"role": "user", "content": prompt}], max_tokens=20, temperature=0.1)
            
            # 解析响应
            if response and response.strip() in self.category_map:
                return Intent(
                    name=response.strip(),
                    confidence=0.6,  # LLM置信度设为0.6
                    category=self.category_map.get(response.strip(), "通用"),
                    keywords=[],
                    source="llm"
                )
            
            return None
        except Exception as e:
            print(f"LLM意图识别失败: {e}")
            return None
    
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
                "complaint_sarcasm", "complaint_refund", "complaint_accessory",
                "complaint_taste", "complaint_service", "complaint_delivery", 
                "complaint_price", "complaint_quantity",
                "query_order", "query_refund", "query_hours", "query_price",
                "query_store", "query_location", "query_promotion",
                "query_recommend", "query_menu", "query_customize",
                "place_order", "unclear",
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
        best_match = None
        best_score = 0
        
        for intent_name, keywords in INTENT_KEYWORDS.items():
            matched_count = sum(1 for kw in keywords if kw in text)
            if matched_count > 0:
                score = matched_count / len(keywords)
                if matched_count >= 2:
                    score = min(score * 1.2, 0.95)
                
                if score > best_score:
                    best_score = score
                    best_match = intent_name
        
        if best_match and best_score >= 0.4:
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
        ("今天有什么优惠？", "query_promotion"),
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
