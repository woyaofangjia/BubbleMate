"""
BubbleMate Query Rewriter - 查询改写模块
定义5种改写规则：
1. 代词消解 - 将"它"、"这个"等代词替换为具体实体
2. 省略补全 - 补全省略的主语或宾语
3. 复合意图拆分 - 将复合问题拆分为多个简单问题
4. 口语化修正 - 将口语化表达转换为标准表达
5. 上下文关联 - 结合历史对话补全当前查询
"""

import re
from typing import List, Dict, Optional, Any


class QueryRewriter:
    """查询改写器 - 基于规则的渐进式改写"""

    def __init__(self):
        self.pronoun_map = {
            "它": ["饮品", "奶茶", "订单", "门店"],
            "这个": ["饮品", "价格", "门店", "订单"],
            "那个": ["饮品", "门店"],
            "它的": ["饮品的", "门店的", "订单的"],
            "这个的": ["饮品的", "价格的"],
            "那": ["那家店", "那款饮品"],
            "这": ["这家店", "这款饮品"],
        }

        self.ellipsis_patterns = [
            (re.compile(r"多少钱\?"), "这款饮品多少钱？"),
            (re.compile(r"好喝吗\?"), "这款饮品好喝吗？"),
            (re.compile(r"有吗\?"), "这款饮品有吗？"),
            (re.compile(r"在哪\?"), "这家门店在哪？"),
            (re.compile(r"几点开门\?"), "这家门店几点开门？"),
            (re.compile(r"可以做热的吗\?"), "这款饮品可以做热的吗？"),
            (re.compile(r"能退款吗\?"), "这个订单能退款吗？"),
            (re.compile(r"什么时候送到\?"), "这个订单什么时候送到？"),
            (re.compile(r"太甜了"), "这款饮品太甜了"),
            (re.compile(r"不好喝"), "这款饮品不好喝"),
            (re.compile(r"份量太少"), "这款饮品份量太少"),
        ]

        self.spoken_patterns = [
            (re.compile(r"啥"), "什么"),
            (re.compile(r"咋"), "怎么"),
            (re.compile(r"为啥"), "为什么"),
            (re.compile(r"呗"), ""),
            (re.compile(r"嘛"), ""),
            (re.compile(r"哒"), "的"),
            (re.compile(r"捏"), ""),
            (re.compile(r"吼"), "哦"),
            (re.compile(r"辣"), "那"),
            (re.compile(r"emmm"), ""),
            (re.compile(r"呃"), ""),
            (re.compile(r"那个"), ""),
            (re.compile(r"就是说"), ""),
            (re.compile(r"其实"), ""),
            (re.compile(r"然后"), ""),
            (re.compile(r"啊"), ""),
            (re.compile(r"呢"), ""),
            (re.compile(r"吧"), ""),
            (re.compile(r"啊"), ""),
            (re.compile(r"！"), "？"),
            (re.compile(r"\.{2,}"), "。"),
            (re.compile(r"\?{2,}"), "？"),
        ]

        self.compound_split_patterns = [
            re.compile(r"(.+?)，(.+?)"),
            re.compile(r"(.+?)和(.+?)"),
            re.compile(r"(.+?)还有(.+?)"),
            re.compile(r"(.+?)以及(.+?)"),
            re.compile(r"(.+?)、(.+?)"),
        ]

        self.drink_keywords = ["芝芝莓莓", "杨枝甘露", "珍珠奶茶", "茉莉绿茶",
                               "柠檬茶", "葡萄冰茶", "芝芝芒果", "糯米奶茶",
                               "芝士系列", "鲜果茶系列", "奶茶系列", "纯茶系列"]
        self.store_keywords = ["武汉大学梅园店", "银泰创意城店", "街道口店",
                               "武汉大学", "银泰", "街道口", "光谷", "武大"]
        self.order_keywords = ["订单", "单号", "配送"]

    def rewrite(self, user_input: str, context: str = "", intent: str = "") -> Dict[str, Any]:
        """
        渐进式查询改写
        返回：改写后的查询、改写类型、原始查询
        """
        original = user_input
        rewritten = user_input
        rewrite_types = []

        rewritten, changed = self._correct_spoken(rewritten)
        if changed:
            rewrite_types.append("口语化修正")

        rewritten, changed = self._resolve_pronouns(rewritten, context, intent)
        if changed:
            rewrite_types.append("代词消解")

        rewritten, changed = self._complete_ellipsis(rewritten, context, intent)
        if changed:
            rewrite_types.append("省略补全")

        rewritten, changed = self._contextualize(rewritten, context)
        if changed:
            rewrite_types.append("上下文关联")

        compound_queries = self._split_compound(rewritten)
        if compound_queries and len(compound_queries) > 1:
            rewrite_types.append("复合意图拆分")

        result = {
            "original": original,
            "rewritten": rewritten,
            "rewrite_types": rewrite_types,
            "compound_queries": compound_queries if compound_queries else None,
            "has_rewritten": rewritten != original or bool(rewrite_types)
        }

        return result

    def _correct_spoken(self, text: str) -> tuple:
        """口语化修正 - 将口语化表达转换为标准表达"""
        rewritten = text
        changed = False

        for pattern, replacement in self.spoken_patterns:
            if pattern.search(text):
                rewritten = pattern.sub(replacement, rewritten)
                changed = True

        rewritten = rewritten.strip()
        return rewritten, changed

    def _resolve_pronouns(self, text: str, context: str, intent: str) -> tuple:
        """代词消解 - 将代词替换为具体实体"""
        rewritten = text
        changed = False

        context_drinks = self._extract_drinks(context)
        context_stores = self._extract_stores(context)
        context_orders = self._extract_orders(context)

        for pronoun, candidates in self.pronoun_map.items():
            if pronoun in rewritten:
                replacement = self._find_best_replacement(
                    pronoun, intent, context_drinks, context_stores, context_orders
                )

                if replacement:
                    rewritten = rewritten.replace(pronoun, replacement)
                    changed = True

        return rewritten, changed

    def _find_best_replacement(self, pronoun: str, intent: str,
                                drinks: List[str], stores: List[str], orders: List[str]) -> Optional[str]:
        """根据意图和上下文找到最佳代词替换"""
        intent_category = intent.split("_")[0] if "_" in intent else intent

        if intent_category == "query_menu" or intent_category == "query_recommend":
            if drinks:
                return drinks[-1]
            return "饮品"

        if intent_category == "query_location":
            if stores:
                return stores[-1]
            return "门店"

        if intent_category == "query_order":
            if orders:
                return orders[-1]
            return "订单"

        if intent_category.startswith("complaint"):
            if drinks:
                return drinks[-1]
            if orders:
                return orders[-1]
            return "饮品"

        if drinks:
            return drinks[-1]
        if stores:
            return stores[-1]

        return None

    def _extract_drinks(self, context: str) -> List[str]:
        """从上下文中提取饮品名"""
        found = []
        for keyword in self.drink_keywords:
            if keyword in context:
                found.append(keyword)
        return found

    def _extract_stores(self, context: str) -> List[str]:
        """从上下文中提取门店名"""
        found = []
        for keyword in self.store_keywords:
            if keyword in context:
                found.append(keyword)
        return found

    def _extract_orders(self, context: str) -> List[str]:
        """从上下文中提取订单号"""
        orders = re.findall(r"(\d{5,})", context)
        return orders

    def _complete_ellipsis(self, text: str, context: str, intent: str) -> tuple:
        """省略补全 - 补全省略的主语或宾语"""
        rewritten = text
        changed = False

        context_drinks = self._extract_drinks(context)
        context_stores = self._extract_stores(context)

        for pattern, template in self.ellipsis_patterns:
            if pattern.search(text):
                replacement = template
                if context_drinks:
                    replacement = replacement.replace("这款饮品", context_drinks[-1])
                if context_stores:
                    replacement = replacement.replace("这家门店", context_stores[-1])

                rewritten = pattern.sub(replacement, rewritten)
                changed = True
                break

        return rewritten, changed

    def _contextualize(self, text: str, context: str) -> tuple:
        """上下文关联 - 结合历史对话补全当前查询"""
        rewritten = text
        changed = False

        context_drinks = self._extract_drinks(context)
        context_stores = self._extract_stores(context)

        if "多少钱" in text and context_drinks and any(d not in text for d in context_drinks):
            rewritten = context_drinks[-1] + " " + text
            changed = True

        elif "在哪" in text and context_stores and any(s not in text for s in context_stores):
            rewritten = context_stores[-1] + " " + text
            changed = True

        elif "好喝吗" in text and context_drinks and any(d not in text for d in context_drinks):
            rewritten = context_drinks[-1] + " " + text
            changed = True

        elif "有吗" in text and context_drinks and any(d not in text for d in context_drinks):
            rewritten = context_drinks[-1] + " " + text
            changed = True

        return rewritten, changed

    def _split_compound(self, text: str) -> Optional[List[str]]:
        """复合意图拆分 - 将复合问题拆分为多个简单问题"""
        for pattern in self.compound_split_patterns:
            match = pattern.search(text)
            if match:
                parts = []
                for i in range(1, pattern.groups + 1):
                    part = match.group(i).strip()
                    if part and len(part) > 2:
                        if not part.endswith("？") and not part.endswith("。"):
                            part += "？"
                        parts.append(part)

                remaining = pattern.sub("", text).strip()
                if remaining and len(remaining) > 2:
                    if not remaining.endswith("？") and not remaining.endswith("。"):
                        remaining += "？"
                    parts.append(remaining)

                if len(parts) >= 2:
                    return parts

        return None

    def batch_rewrite(self, queries: List[str], contexts: List[str] = None) -> List[Dict]:
        """批量改写查询"""
        results = []
        contexts = contexts or ["" for _ in queries]

        for query, context in zip(queries, contexts):
            results.append(self.rewrite(query, context))

        return results


def test_query_rewriter():
    """测试查询改写器"""
    rewriter = QueryRewriter()

    print("\n" + "=" * 60)
    print("查询改写模块测试")
    print("=" * 60)

    test_cases = [
        ("它多少钱？", "用户: 芝芝莓莓好喝吗\n客服: 是的，很受欢迎", "query_price"),
        ("这个在哪？", "用户: 武汉大学梅园店\n客服: 在梅园食堂旁", "query_location"),
        ("好喝吗？", "用户: 杨枝甘露\n客服: 这是我们的招牌", "query_recommend"),
        ("啥时候送到？", "用户: 订单12345\n客服: 正在制作", "query_order"),
        ("太甜了，投诉", "用户: 点了珍珠奶茶\n客服: 好的", "complaint_taste"),
        ("芝芝莓莓和杨枝甘露多少钱？", "", "query_price"),
        ("附近有门店吗？还有你们的招牌是什么？", "", "query_location"),
        ("emmm那个... 它的价格是多少呗", "用户: 茉莉绿茶\n客服: 零糖低卡", "query_price"),
        ("几点开门？", "用户: 武汉大学梅园店\n客服: 在梅园食堂旁", "query_opentime"),
        ("可以做热的吗？", "用户: 杨枝甘露\n客服: 这是我们的招牌", "query_temp"),
    ]

    for user_input, context, intent in test_cases:
        result = rewriter.rewrite(user_input, context, intent)

        print(f"\n原始查询: {user_input}")
        print(f"上下文: {context[:50]}{'...' if len(context) > 50 else ''}")
        print(f"改写后: {result['rewritten']}")
        print(f"改写类型: {', '.join(result['rewrite_types']) if result['rewrite_types'] else '无'}")

        if result.get("compound_queries"):
            print(f"拆分查询: {result['compound_queries']}")


if __name__ == "__main__":
    test_query_rewriter()