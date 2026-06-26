"""
BubbleMate Tool Router - 渐进式工具调用路由
实现意图→工具映射 + 参数完整性检查 + 自动反问机制
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ParameterSchema:
    name: str
    type: str
    description: str
    required: bool = False


@dataclass
class ToolSchema:
    name: str
    summary: str
    description: str
    parameters: List[ParameterSchema] = field(default_factory=list)
    intent_mapping: List[str] = field(default_factory=list)
    clarification_prompt: str = ""

    @property
    def required_params(self) -> List[str]:
        return [p.name for p in self.parameters if p.required]

    @property
    def param_dict(self) -> Dict[str, ParameterSchema]:
        return {p.name: p for p in self.parameters}


class ToolRouter:
    """渐进式工具调用路由器"""

    def __init__(self):
        self.tools: Dict[str, ToolSchema] = {}
        self.intent_tool_map: Dict[str, str] = {}
        self._register_all_tools()

    def _register_all_tools(self):
        """注册5个核心工具的结构化Schema"""

        tools = [
            ToolSchema(
                name="query_stores",
                summary="查询附近奶茶门店",
                description="""查询奶茶店门店信息，支持按位置关键词搜索。
当用户询问附近门店、门店地址、哪里有奶茶店、最近的店等场景时调用此工具。
输入参数：location（位置关键词，如"光谷广场"、"武汉大学"）
输出：匹配的门店列表，包含店名、地址、距离信息。""",
                parameters=[
                    ParameterSchema(
                        name="location",
                        type="string",
                        description="位置关键词（如商圈名、学校名、地标名）",
                        required=True
                    )
                ],
                intent_mapping=["query_location"],
                clarification_prompt="请问您在哪个位置/商圈？比如'光谷广场'或'武汉大学'"
            ),
            ToolSchema(
                name="query_menu",
                summary="查询饮品菜单",
                description="""查询奶茶店菜单和饮品信息，支持按类别或关键词搜索。
当用户询问菜单、饮品推荐、价格、某款饮品信息等场景时调用此工具。
输入参数：category（饮品类别，可选）、keyword（关键词，可选）
输出：匹配的饮品列表，包含名称、价格、描述。""",
                parameters=[
                    ParameterSchema(
                        name="category",
                        type="string",
                        description="饮品类别（如芝士系列、鲜果茶系列）",
                        required=False
                    ),
                    ParameterSchema(
                        name="keyword",
                        type="string",
                        description="搜索关键词（如饮品名、配料名）",
                        required=False
                    )
                ],
                intent_mapping=["query_menu", "query_recommend", "query_price"],
                clarification_prompt="请问您想了解哪个系列或哪款饮品？"
            ),
            ToolSchema(
                name="query_order",
                summary="查询订单状态",
                description="""查询奶茶订单的配送状态和进度。
当用户询问订单状态、配送进度、什么时候送到等场景时调用此工具。
输入参数：order_id（订单号，必填）、phone_number（手机号，可选）
输出：订单状态、饮品信息、预计送达时间、门店信息。""",
                parameters=[
                    ParameterSchema(
                        name="order_id",
                        type="string",
                        description="订单编号（5位以上数字）",
                        required=True
                    ),
                    ParameterSchema(
                        name="phone_number",
                        type="string",
                        description="手机号码（11位数字）",
                        required=False
                    )
                ],
                intent_mapping=["query_order"],
                clarification_prompt="请提供您的订单号（如12345），我帮您查询订单状态"
            ),
            ToolSchema(
                name="check_stock",
                summary="查询原料库存",
                description="""查询门店原料库存情况，判断饮品是否可制作。
当用户询问某款饮品有没有货、原料是否充足等场景时调用此工具。
输入参数：store_id（门店名称，必填）、ingredient（原料名称，可选）
输出：原料库存状态（充足/紧张/缺货）。""",
                parameters=[
                    ParameterSchema(
                        name="store_id",
                        type="string",
                        description="门店名称或ID",
                        required=True
                    ),
                    ParameterSchema(
                        name="ingredient",
                        type="string",
                        description="原料名称（如珍珠、糯米、芝士）",
                        required=False
                    )
                ],
                intent_mapping=["query_inventory"],
                clarification_prompt="请提供门店名称（如武汉大学店、银泰店）"
            ),
            ToolSchema(
                name="log_complaint",
                summary="处理顾客投诉",
                description="""记录和处理顾客投诉，支持多种投诉类型。
当用户表达不满、投诉口感/份量/服务/配送/价格等问题时调用此工具。
输入参数：complaint_type（投诉类型，必填）、order_id（订单号，可选）、description（投诉描述）
输出：投诉受理状态、投诉单号、处理建议。""",
                parameters=[
                    ParameterSchema(
                        name="complaint_type",
                        type="string",
                        description="投诉类型：taste(口感)/quantity(份量)/service(服务)/delivery(配送)/price(价格)",
                        required=True
                    ),
                    ParameterSchema(
                        name="order_id",
                        type="string",
                        description="订单编号",
                        required=False
                    ),
                    ParameterSchema(
                        name="description",
                        type="string",
                        description="投诉详细描述",
                        required=False
                    )
                ],
                intent_mapping=["complaint_taste", "complaint_quantity", "complaint_service",
                               "complaint_delivery", "complaint_price"],
                clarification_prompt="请提供订单号（如有），方便我为您快速处理"
            )
        ]

        for tool in tools:
            self.tools[tool.name] = tool
            for intent in tool.intent_mapping:
                self.intent_tool_map[intent] = tool.name

    def route(self, intent_name: str) -> Optional[ToolSchema]:
        """根据意图路由到工具"""
        tool_name = self.intent_tool_map.get(intent_name)
        if tool_name:
            return self.tools.get(tool_name)
        return None

    def extract_params(self, user_input: str, tool_schema: ToolSchema) -> Dict[str, Any]:
        """从用户输入中提取参数"""
        params = {}

        for param in tool_schema.parameters:
            if param.name == "location":
                location_keywords = ["光谷", "武汉大学", "街道口", "汉口", "武昌", "汉阳",
                                    "银泰", "武大", "群光", "梦时代", "中南", "徐东"]
                for kw in location_keywords:
                    if kw in user_input:
                        params["location"] = kw
                        break
                if "location" not in params:
                    match = re.search(r"(在|附近|周边)(.+?)(店|门店|奶茶|的)", user_input)
                    if match:
                        params["location"] = match.group(2).strip()

            elif param.name == "order_id":
                match = re.search(r"(\d{5,})", user_input)
                if match:
                    params["order_id"] = match.group(1)

            elif param.name == "phone_number":
                match = re.search(r"(\d{11})", user_input)
                if match:
                    params["phone_number"] = match.group(1)

            elif param.name == "category":
                categories = ["芝士", "鲜果茶", "奶茶", "纯茶", "果茶", "奶盖"]
                for cat in categories:
                    if cat in user_input:
                        params["category"] = cat + "系列" if cat != "奶茶" else "奶茶系列"
                        break

            elif param.name == "keyword":
                drink_keywords = ["芝芝莓莓", "杨枝甘露", "珍珠奶茶", "茉莉绿茶",
                                  "柠檬茶", "葡萄", "芒果", "草莓", "芝士", "糯米"]
                for kw in drink_keywords:
                    if kw in user_input:
                        params["keyword"] = kw
                        break

            elif param.name == "store_id":
                store_keywords = ["武汉大学", "武大", "银泰", "街道口", "光谷"]
                for kw in store_keywords:
                    if kw in user_input:
                        params["store_id"] = kw
                        break

            elif param.name == "ingredient":
                ingredient_keywords = ["珍珠", "糯米", "芝士", "芒果", "草莓", "椰奶"]
                for kw in ingredient_keywords:
                    if kw in user_input:
                        params["ingredient"] = kw
                        break

            elif param.name == "complaint_type":
                complaint_map = {
                    "口感": "taste",
                    "味道": "taste",
                    "甜": "taste",
                    "酸": "taste",
                    "苦": "taste",
                    "份量": "quantity",
                    "分量": "quantity",
                    "料": "quantity",
                    "冰块": "quantity",
                    "服务": "service",
                    "态度": "service",
                    "配送": "delivery",
                    "送": "delivery",
                    "超时": "delivery",
                    "价格": "price",
                    "贵": "price"
                }
                for keyword, complaint_type in complaint_map.items():
                    if keyword in user_input:
                        params["complaint_type"] = complaint_type
                        break

            elif param.name == "description":
                params["description"] = user_input

        return params

    def check_params(self, user_input: str, tool_schema: ToolSchema) -> Dict:
        """
        渐进式参数检查
        返回：需要补充的参数列表或已提取的完整参数
        """
        extracted = self.extract_params(user_input, tool_schema)
        required = tool_schema.required_params

        missing = [p for p in required if p not in extracted or not extracted[p]]

        if missing:
            return {
                "status": "incomplete",
                "tool_name": tool_schema.name,
                "missing_params": missing,
                "extracted_params": extracted,
                "clarification_prompt": tool_schema.clarification_prompt,
                "suggestion": self._generate_clarification(missing, tool_schema)
            }

        return {
            "status": "complete",
            "tool_name": tool_schema.name,
            "params": extracted,
            "tool_schema": tool_schema
        }

    def _generate_clarification(self, missing_params: List[str], tool_schema: ToolSchema) -> str:
        """生成针对性的反问提示"""
        param_descriptions = []
        for param_name in missing_params:
            param = tool_schema.param_dict.get(param_name)
            if param:
                param_descriptions.append(f"{param.description}")

        if len(missing_params) == 1:
            return f"我需要您提供{param_descriptions[0]}，才能帮您查询。"

        return f"我需要以下信息才能帮您查询：\n" + "\n".join([f"- {desc}" for desc in param_descriptions])

    def list_tools(self) -> List[Dict]:
        """列出所有工具的结构化描述（给LLM用）"""
        result = []
        for tool in self.tools.values():
            params_info = []
            for param in tool.parameters:
                params_info.append({
                    "name": param.name,
                    "type": param.type,
                    "description": param.description,
                    "required": param.required
                })
            result.append({
                "name": tool.name,
                "summary": tool.summary,
                "description": tool.description,
                "parameters": params_info
            })
        return result

    def get_tool_by_name(self, name: str) -> Optional[ToolSchema]:
        """按名称获取工具Schema"""
        return self.tools.get(name)


def test_tool_router():
    """测试工具路由器"""
    router = ToolRouter()

    print("\n" + "=" * 60)
    print("渐进式工具调用路由测试")
    print("=" * 60)

    test_cases = [
        ("附近有门店吗？", "query_location"),
        ("光谷附近有门店吗？", "query_location"),
        ("订单12345什么时候能送到？", "query_order"),
        ("我的订单什么时候能到？", "query_order"),
        ("珍珠奶茶多少钱？", "query_price"),
        ("你们有什么推荐？", "query_recommend"),
        ("太甜了，投诉", "complaint_taste"),
        ("武大店珍珠还有吗？", "query_inventory"),
    ]

    for user_input, intent_name in test_cases:
        print(f"\n用户输入: {user_input}")
        print(f"意图: {intent_name}")

        tool = router.route(intent_name)
        if tool:
            print(f"匹配工具: {tool.name}")
            check_result = router.check_params(user_input, tool)
            print(f"参数状态: {check_result['status']}")

            if check_result["status"] == "incomplete":
                print(f"缺失参数: {check_result['missing_params']}")
                print(f"反问提示: {check_result['suggestion']}")
            else:
                print(f"提取参数: {check_result['params']}")
        else:
            print("未匹配到工具")


if __name__ == "__main__":
    test_tool_router()