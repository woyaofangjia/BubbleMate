"""
BubbleMate Agent V3 - 集成版ReAct Agent
- 集成三层记忆系统（Redis+MySQL+ChromaDB）
- 集成查询改写模块（Query Rewrite）
- 集成用户偏好提取模块
- 使用ToolRouter进行渐进式工具调用
- 使用ToolRegistryV2进行工具注册和调用
"""

import json
import os
import re
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None


@dataclass
class ToolCall:
    name: str
    arguments: Dict
    result: Optional[str] = None


class ReActAgentV3:
    """集成版ReAct Agent"""

    def __init__(self):
        from .intent_recognizer_v2 import IntentRecognizerV2
        from .memory_three_layer import ThreeLayerMemory
        from .query_rewriter import QueryRewriter
        from .preference_extractor import PreferenceExtractor
        from .tool_router import ToolRouter
        from .tools.tool_registry_v2 import tool_registry_v2, register_all_tools_v2

        self.intent_recognizer = IntentRecognizerV2("data")
        self.memory_manager = ThreeLayerMemory(window_size=5, session_timeout=3600)
        self.query_rewriter = QueryRewriter()
        self.preference_extractor = PreferenceExtractor(use_llm=False)
        self.tool_router = ToolRouter()
        self.tool_registry = tool_registry_v2

        register_all_tools_v2()

        self.system_prompt = """你是BubbleMate奶茶店智能客服Agent。

你的职责：
1. 回答顾客关于奶茶、订单、门店的问题
2. 处理顾客投诉（口感、份量、服务、配送等）
3. 提供饮品推荐和点单建议

可用工具：
- query_stores: 查询附近门店，需要位置关键词
- query_menu: 查询菜单饮品，支持按类别或关键词搜索
- query_order: 查询订单状态，需要订单号
- check_stock: 查询原料库存，需要门店名和原料名
- log_complaint: 处理投诉，需要投诉类型

回复原则：
- 先识别意图，再决定是否需要调用工具
- 工具参数不全时，主动反问用户补充
- 结合用户偏好提供个性化服务
- 语气友好、专业，回复简洁明了
- 不确定时，承认并建议人工客服介入

回复格式：
【思考】分析用户意图 + 是否需要调用工具 + 参数是否完整
【行动】调用工具或直接回复
【回复】最终回复内容"""

    def process(self, user_input: str, session_id: str = "default", user_id: str = "") -> str:
        """处理用户输入（完整流程）"""
        context = self.memory_manager.get_context(session_id, user_id)

        rewrite_result = self.query_rewriter.rewrite(user_input, context)
        rewritten_input = rewrite_result["rewritten"]

        intent = self.intent_recognizer.recognize(rewritten_input)

        preferences = self.preference_extractor.extract(user_input, context)
        pref_context = self.preference_extractor.format_for_prompt(preferences)

        response = self._react_loop(rewritten_input, intent, context, pref_context)

        self.memory_manager.save_message(session_id, user_id, user_input, response, intent.name)

        return response

    def _react_loop(self, user_input: str, intent, context: str, pref_context: str) -> str:
        """ReAct循环（集成版）"""
        if intent.name.startswith("complaint"):
            return self._handle_complaint(user_input, intent, pref_context)
        elif intent.name.startswith("query"):
            return self._handle_query(user_input, intent, context)
        elif intent.name.startswith("order") or intent.name == "place_order":
            return self._handle_order(user_input, intent)
        else:
            return self._handle_general(user_input, intent)

    def _handle_complaint(self, user_input: str, intent, pref_context: str) -> str:
        """处理投诉（集成版）"""
        tool = self.tool_router.route(intent.name)
        if tool:
            check_result = self.tool_router.check_params(user_input, tool)

            if check_result["status"] == "incomplete":
                return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}, 参数缺失
【行动】引导用户补充信息
【回复】{check_result['suggestion']}"""

            tool_result = self.tool_registry.call(tool.name, check_result["params"])

            if tool_result["success"]:
                response = f"{tool_result.get('response', '')}\n\n"
                if pref_context:
                    response += f"根据您的偏好，后续订单我们会为您默认设置：{pref_context}。"
                return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}
【行动】调用工具: {tool.name}
【工具结果】成功
【回复】{response}"""
            else:
                return f"""【思考】用户意图: {intent.name}, 工具调用失败
【行动】使用预设回复
【回复】{tool_result.get('response', '抱歉，投诉处理失败，请稍后再试。')}"""

        complaint_templates = {
            "complaint_taste": "您好，非常抱歉饮品口感不符合您的预期。我们核实后会为您重新制作或办理退款，预计24小时内处理完成。",
            "complaint_quantity": "您好，非常抱歉饮品份量不足。我们会核查门店制作标准，为您提供补偿。",
            "complaint_service": "您好，非常抱歉服务态度不佳。我们已通知门店整改，并会为您安排专属客服跟进。",
            "complaint_delivery": "您好，非常抱歉配送超时。我们会为您申请超时赔付，预计24小时内到账。",
            "complaint_price": "您好，非常抱歉价格问题给您带来困扰。我们会核实定价，并为您提供优惠券补偿。",
        }

        response = complaint_templates.get(intent.name,
                                           "非常抱歉给您带来不好的体验。请提供您的订单号，我们核实后会为您处理退款或补偿。")

        if pref_context:
            response += f"\n\n根据您的偏好，后续订单我们会为您默认设置：{pref_context}。"

        return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}
【行动】匹配投诉处理模板
【回复】{response}"""

    def _handle_query(self, user_input: str, intent, context: str) -> str:
        """处理查询（集成版）"""
        tool = self.tool_router.route(intent.name)

        if tool:
            check_result = self.tool_router.check_params(user_input, tool)

            if check_result["status"] == "incomplete":
                return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}, 工具参数缺失
【行动】引导用户补充信息
【回复】{check_result['suggestion']}"""

            tool_result = self.tool_registry.call(tool.name, check_result["params"])

            if tool_result["success"]:
                return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}, 需要查询信息
【行动】调用工具: {tool.name}({check_result['params']})
【工具结果】成功
【回复】{tool_result.get('response', str(tool_result))}"""
            else:
                return f"""【思考】用户意图: {intent.name}, 工具调用失败
【行动】使用预设回复
【回复】{tool_result.get('response', '抱歉，查询失败，请稍后再试。')}"""

        return self._get_direct_query_response(intent)

    def _handle_order(self, user_input: str, intent) -> str:
        """处理订单（集成版）"""
        order_id = self._extract_order_id(user_input)

        if order_id:
            tool = self.tool_router.route("query_order")
            if tool:
                check_result = self.tool_router.check_params(user_input, tool)
                if check_result["status"] == "complete":
                    tool_result = self.tool_registry.call(tool.name, check_result["params"])
                    if tool_result["success"]:
                        return f"""【思考】用户意图: {intent.name}, 已有订单号
【行动】调用订单查询工具
【回复】{tool_result.get('response', str(tool_result))}"""

        return f"""【思考】用户意图: {intent.name}, 需要订单信息
【行动】引导用户提供订单号
【回复】请提供您的订单号或手机号，我帮您查询订单详情。"""

    def _handle_general(self, user_input: str, intent) -> str:
        """处理通用对话（集成版）"""
        knowledge_results = self.memory_manager.search_knowledge(user_input, top_k=2)
        knowledge_hints = []
        for item in knowledge_results:
            if item["score"] < 1.0:
                knowledge_hints.append(item["content"])

        general_responses = {
            "query_temp": "我们提供热、温、冰三种温度选择，您可以根据喜好选择。",
            "query_delivery": "支持外卖配送，美团、饿了么、小程序均可下单，满20元免配送费。",
            "query_promo": "今日优惠：新品第二杯半价，会员享受9折优惠，还有满30减5优惠券可领取。",
            "query_member": "会员卡可在小程序免费办理，首单立减5元，消费积分可兑换饮品。",
            "query_invoice": "支持开具电子发票，在小程序【我的订单】中申请，预计3个工作日内发送到邮箱。",
            "query_complaint_status": "请提供您的投诉单号或订单号，我帮您查询处理进度。",
        }

        response = general_responses.get(intent.name,
                                         "您好，我是BubbleMate奶茶店客服。请问有什么可以帮助您的？您可以咨询菜单推荐、订单状态、门店信息等问题。")

        if knowledge_hints:
            response += "\n\n相关信息：\n" + "\n".join(knowledge_hints)

        return f"""【思考】用户意图: {intent.name}, 直接回复
【行动】使用预设回复模板
【回复】{response}"""

    def _extract_order_id(self, text: str) -> str:
        """提取订单号"""
        match = re.search(r"(\d{5,})", text)
        return match.group(1) if match else ""

    def _get_direct_query_response(self, intent) -> str:
        """获取直接查询回复"""
        responses = {
            "query_recommend": "您好！我们的招牌饮品包括：1)芝芝莓莓 - 鲜草莓搭配芝士奶盖；2)杨枝甘露 - 椰奶芒果西柚；3)茉莉绿茶 - 零糖低卡。您喜欢什么口味？",
            "query_menu": "我们菜单分为：芝士系列、鲜果茶系列、纯茶系列、奶茶系列。人均价格8-20元。具体饮品可在小程序查看。",
            "query_opentime": "武汉大学门店营业时间：10:00-22:00；银泰创意城店：10:00-21:30。",
            "query_location": "附近门店：1)武汉大学梅园店 - 步行5分钟；2)银泰创意城店 - 步行10分钟；3)街道口店 - 步行8分钟。",
            "query_sugar": "我们提供5档糖度：标准糖、七分糖、五分糖、三分糖、无糖。建议首次选择五分糖。",
            "query_order": "请提供订单号，我帮您查询订单状态和配送进度。",
            "query_refund": "请在小程序【我的订单】申请售后，或提供订单号人工处理。",
            "query_price": "饮品价格8-20元不等，具体价格可在菜单中查看。",
            "query_temp": "支持热、温、冰三种温度。",
            "query_delivery": "支持外卖配送，满20元免配送费。",
            "query_promo": "今日优惠：新品第二杯半价，会员9折。",
            "query_member": "会员卡免费办理，首单立减5元。",
            "query_invoice": "支持电子发票，在小程序申请。",
            "query_complaint_status": "请提供投诉单号或订单号查询进度。",
        }
        return f"""【思考】用户意图: {intent.name}
【行动】直接回复
【回复】{responses.get(intent.name, '请告诉我您想查询的具体内容。')}"""

    def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计"""
        return self.memory_manager.get_session_stats(session_id)

    def get_global_stats(self) -> Dict:
        """获取全局统计"""
        return self.memory_manager.get_global_stats()


def test_agent_v3():
    """测试集成版Agent"""
    agent = ReActAgentV3()

    print("\n" + "=" * 60)
    print("集成版Agent测试（V3）")
    print("=" * 60)

    session_id = "test_session_v3"
    user_id = "user_001"

    test_inputs = [
        "太甜了，喝不下去",
        "你们有什么招牌推荐？",
        "订单12345什么时候能送到？",
        "附近有门店吗？",
        "可以退款吗？",
        "门店营业时间？",
        "它多少钱？",
        "少冰的珍珠奶茶",
    ]

    for input_text in test_inputs:
        response = agent.process(input_text, session_id, user_id)
        print(f"用户: {input_text}")
        print(f"Agent:\n{response}")
        print("=" * 60)

    stats = agent.get_global_stats()
    print(f"\n全局统计: {stats}")


if __name__ == "__main__":
    test_agent_v3()