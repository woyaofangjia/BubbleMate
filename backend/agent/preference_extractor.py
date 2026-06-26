"""
BubbleMate Preference Extractor - 用户偏好抽取模块
设计用户偏好字段并使用LLM结构化提取
字段定义：
- sugar_level: 甜度偏好（无糖/三分糖/五分糖/七分糖/正常糖）
- ice_level: 冰量偏好（热/温/去冰/少冰/正常冰）
- favorite_drinks: 喜欢的饮品列表
- complaint_history: 投诉历史（类型+描述）
- allergens: 过敏原（牛奶/坚果/水果等）
- price_sensitivity: 价格敏感度（高/中/低）
- preferred_store: 偏好门店
- last_order_id: 最近订单号
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class UserPreferences:
    """用户偏好数据结构"""
    user_id: str
    sugar_level: Optional[str] = None
    ice_level: Optional[str] = None
    favorite_drinks: List[str] = field(default_factory=list)
    complaint_history: List[Dict] = field(default_factory=list)
    allergens: List[str] = field(default_factory=list)
    price_sensitivity: Optional[str] = None
    preferred_store: Optional[str] = None
    last_order_id: Optional[str] = None
    frequency: str = "regular"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "sugar_level": self.sugar_level,
            "ice_level": self.ice_level,
            "favorite_drinks": self.favorite_drinks,
            "complaint_history": self.complaint_history,
            "allergens": self.allergens,
            "price_sensitivity": self.price_sensitivity,
            "preferred_store": self.preferred_store,
            "last_order_id": self.last_order_id,
            "frequency": self.frequency
        }

    def merge(self, other: 'UserPreferences'):
        """合并另一组偏好"""
        if other.sugar_level:
            self.sugar_level = other.sugar_level
        if other.ice_level:
            self.ice_level = other.ice_level
        for drink in other.favorite_drinks:
            if drink not in self.favorite_drinks:
                self.favorite_drinks.append(drink)
        for complaint in other.complaint_history:
            self.complaint_history.append(complaint)
        for allergen in other.allergens:
            if allergen not in self.allergens:
                self.allergens.append(allergen)
        if other.price_sensitivity:
            self.price_sensitivity = other.price_sensitivity
        if other.preferred_store:
            self.preferred_store = other.preferred_store
        if other.last_order_id:
            self.last_order_id = other.last_order_id


class PreferenceExtractor:
    """用户偏好抽取器"""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.llm_client = None

        if use_llm:
            try:
                from backend.core.zhipu_client import call_llm
                self.llm_client = call_llm
            except Exception as e:
                print(f"LLM初始化失败，使用纯规则模式: {e}")
                self.use_llm = False

        self.sugar_patterns = {
            "无糖": [r"无糖", r"零糖", r"不加糖", r"不要糖"],
            "三分糖": [r"三分糖", r"少糖", r"低糖"],
            "五分糖": [r"五分糖", r"半糖"],
            "七分糖": [r"七分糖"],
            "正常糖": [r"正常糖", r"标准糖", r"全糖", r"多糖"]
        }

        self.ice_patterns = {
            "热": [r"热饮", r"热的", r"加热", r"温的"],
            "温": [r"温饮", r"常温"],
            "去冰": [r"去冰", r"不加冰", r"不要冰"],
            "少冰": [r"少冰", r"微冰"],
            "正常冰": [r"正常冰", r"加冰"]
        }

        self.drink_keywords = ["芝芝莓莓", "杨枝甘露", "珍珠奶茶", "茉莉绿茶",
                               "柠檬茶", "葡萄冰茶", "芝芝芒果", "糯米奶茶",
                               "芝士奶盖", "鲜果茶", "奶绿"]

        self.store_keywords = ["武汉大学梅园店", "银泰创意城店", "街道口店",
                               "武汉大学", "银泰", "街道口", "光谷", "武大",
                               "群光", "梦时代"]

        self.allergen_patterns = {
            "牛奶": [r"牛奶", r"乳糖", r"乳清"],
            "坚果": [r"坚果", r"花生", r"核桃", r"杏仁"],
            "水果": [r"芒果", r"草莓", r"葡萄", r"西柚"],
            "茶": [r"茶", r"咖啡因"]
        }

        self.price_patterns = {
            "high": [r"太贵", r"太贵了", r"不值", r"性价比低"],
            "medium": [r"价格适中", r"还可以", r"不贵"],
            "low": [r"便宜", r"划算", r"性价比高"]
        }

    def extract(self, user_message: str, context: str = "") -> UserPreferences:
        """提取用户偏好"""
        preferences = UserPreferences(user_id="")

        self._extract_sugar(user_message, preferences)
        self._extract_ice(user_message, preferences)
        self._extract_drinks(user_message, preferences)
        self._extract_stores(user_message, preferences)
        self._extract_allergens(user_message, preferences)
        self._extract_price(user_message, preferences)
        self._extract_order(user_message, preferences)
        self._extract_complaint(user_message, preferences)

        if context:
            self._extract_from_context(context, preferences)

        if self.use_llm and self.llm_client:
            llm_preferences = self._extract_with_llm(user_message, context)
            if llm_preferences:
                preferences.merge(llm_preferences)

        return preferences

    def _extract_sugar(self, text: str, pref: UserPreferences):
        """提取甜度偏好"""
        for level, patterns in self.sugar_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    pref.sugar_level = level
                    return

    def _extract_ice(self, text: str, pref: UserPreferences):
        """提取冰量偏好"""
        for level, patterns in self.ice_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    pref.ice_level = level
                    return

    def _extract_drinks(self, text: str, pref: UserPreferences):
        """提取喜欢的饮品"""
        for keyword in self.drink_keywords:
            if keyword in text:
                if keyword not in pref.favorite_drinks:
                    pref.favorite_drinks.append(keyword)

    def _extract_stores(self, text: str, pref: UserPreferences):
        """提取偏好门店"""
        for keyword in self.store_keywords:
            if keyword in text:
                pref.preferred_store = keyword
                return

    def _extract_allergens(self, text: str, pref: UserPreferences):
        """提取过敏原"""
        for allergen, patterns in self.allergen_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text) and "过敏" in text:
                    if allergen not in pref.allergens:
                        pref.allergens.append(allergen)

    def _extract_price(self, text: str, pref: UserPreferences):
        """提取价格敏感度"""
        for sensitivity, patterns in self.price_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    pref.price_sensitivity = sensitivity
                    return

    def _extract_order(self, text: str, pref: UserPreferences):
        """提取订单号"""
        match = re.search(r"(\d{5,})", text)
        if match:
            pref.last_order_id = match.group(1)

    def _extract_complaint(self, text: str, pref: UserPreferences):
        """提取投诉信息"""
        complaint_type_map = {
            "taste": ["口感", "味道", "甜", "酸", "苦", "难喝"],
            "quantity": ["份量", "分量", "料", "冰块"],
            "service": ["服务", "态度"],
            "delivery": ["配送", "送", "超时"],
            "price": ["价格", "贵"]
        }

        complaint_type = None
        for code, keywords in complaint_type_map.items():
            if any(kw in text for kw in keywords):
                complaint_type = code
                break

        if complaint_type:
            pref.complaint_history.append({
                "type": complaint_type,
                "description": text,
                "timestamp": text
            })

    def _extract_from_context(self, context: str, pref: UserPreferences):
        """从上下文中提取偏好"""
        if not pref.sugar_level:
            self._extract_sugar(context, pref)
        if not pref.ice_level:
            self._extract_ice(context, pref)
        if not pref.preferred_store:
            self._extract_stores(context, pref)
        if not pref.last_order_id:
            self._extract_order(context, pref)

        self._extract_drinks(context, pref)

    def _extract_with_llm(self, user_message: str, context: str) -> Optional[UserPreferences]:
        """使用LLM结构化提取偏好"""
        try:
            prompt = f"""你是一个奶茶店用户偏好提取器。请从以下对话中提取用户偏好信息。

用户当前消息：{user_message}

历史对话：{context[:500] if context else '无'}

请提取以下字段（只输出JSON，不要其他文字）：
{{
    "sugar_level": "无糖/三分糖/五分糖/七分糖/正常糖/None",
    "ice_level": "热/温/去冰/少冰/正常冰/None",
    "favorite_drinks": ["饮品名1", "饮品名2"],
    "complaint_history": [{{"type": "taste/quantity/service/delivery/price", "description": "投诉内容"}}],
    "allergens": ["过敏原1", "过敏原2"],
    "price_sensitivity": "high/medium/low/None",
    "preferred_store": "门店名/None",
    "last_order_id": "订单号/None"
}}

注意：
- 如果没有相关信息，对应字段设为null或空数组
- sugar_level和ice_level只能从给定选项中选择
- favorite_drinks只填具体的饮品名称
- complaint_history中type只能从给定选项中选择"""

            response = self.llm_client([{"role": "user", "content": prompt}],
                                       max_tokens=300, temperature=0.1)

            if response:
                response = response.strip()
                start = response.find("{")
                end = response.rfind("}") + 1

                if start >= 0 and end > start:
                    json_str = response[start:end]
                    data = json.loads(json_str)

                    preferences = UserPreferences(user_id="")
                    preferences.sugar_level = data.get("sugar_level")
                    preferences.ice_level = data.get("ice_level")
                    preferences.favorite_drinks = data.get("favorite_drinks", [])
                    preferences.complaint_history = data.get("complaint_history", [])
                    preferences.allergens = data.get("allergens", [])
                    preferences.price_sensitivity = data.get("price_sensitivity")
                    preferences.preferred_store = data.get("preferred_store")
                    preferences.last_order_id = data.get("last_order_id")

                    return preferences

        except Exception as e:
            print(f"LLM偏好提取失败: {e}")

        return None

    def extract_batch(self, messages: List[str], contexts: List[str] = None) -> List[UserPreferences]:
        """批量提取偏好"""
        results = []
        contexts = contexts or ["" for _ in messages]

        for message, context in zip(messages, contexts):
            results.append(self.extract(message, context))

        return results

    def format_for_prompt(self, preferences: UserPreferences) -> str:
        """将偏好格式化为Prompt上下文"""
        parts = []

        if preferences.sugar_level:
            parts.append(f"甜度偏好: {preferences.sugar_level}")
        if preferences.ice_level:
            parts.append(f"冰量偏好: {preferences.ice_level}")
        if preferences.favorite_drinks:
            parts.append(f"喜欢的饮品: {', '.join(preferences.favorite_drinks)}")
        if preferences.preferred_store:
            parts.append(f"偏好门店: {preferences.preferred_store}")
        if preferences.allergens:
            parts.append(f"过敏原: {', '.join(preferences.allergens)}")
        if preferences.price_sensitivity:
            parts.append(f"价格敏感度: {preferences.price_sensitivity}")
        if preferences.last_order_id:
            parts.append(f"最近订单: {preferences.last_order_id}")
        if preferences.complaint_history:
            parts.append(f"投诉次数: {len(preferences.complaint_history)}次")

        return " | ".join(parts) if parts else ""


def test_preference_extractor():
    """测试用户偏好提取器"""
    extractor = PreferenceExtractor(use_llm=False)

    print("\n" + "=" * 60)
    print("用户偏好提取器测试")
    print("=" * 60)

    test_cases = [
        ("给我来一杯无糖去冰的芝芝莓莓", ""),
        ("太甜了，下次要三分糖", "用户: 点了杨枝甘露\n客服: 好的"),
        ("对牛奶过敏，有没有不含奶的饮品", ""),
        ("武汉大学店的珍珠奶茶太贵了", ""),
        ("上次的订单12345口感不好，投诉", ""),
        ("少冰的茉莉绿茶，送到街道口", ""),
    ]

    for message, context in test_cases:
        pref = extractor.extract(message, context)
        prompt_format = extractor.format_for_prompt(pref)

        print(f"\n用户消息: {message}")
        print(f"提取结果:")
        print(f"  甜度: {pref.sugar_level}")
        print(f"  冰量: {pref.ice_level}")
        print(f"  喜欢的饮品: {pref.favorite_drinks}")
        print(f"  偏好门店: {pref.preferred_store}")
        print(f"  过敏原: {pref.allergens}")
        print(f"  价格敏感度: {pref.price_sensitivity}")
        print(f"  最近订单: {pref.last_order_id}")
        print(f"  投诉历史: {pref.complaint_history}")
        print(f"  Prompt格式: {prompt_format}")


if __name__ == "__main__":
    test_preference_extractor()