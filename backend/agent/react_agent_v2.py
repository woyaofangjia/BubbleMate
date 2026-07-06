import re
from typing import Dict, Optional, Any, Callable

from .tool_router import route, check_params, get_tool_name

COMPLAINT_TEMPLATES = {
    "complaint_taste": "您好，非常抱歉饮品口感不符合您的预期。我们核实后会为您重新制作或办理退款，预计24小时内处理完成。",
    "complaint_quantity": "您好，非常抱歉饮品份量不足。我们会核查门店制作标准，为您提供补偿。",
    "complaint_service": "您好，非常抱歉服务态度不佳。我们已通知门店整改，并会为您安排专属客服跟进。",
    "complaint_delivery": "您好，非常抱歉配送超时。我们会为您申请超时赔付，预计24小时内到账。",
    "complaint_price": "您好，非常抱歉价格问题给您带来困扰。我们会核实定价，并为您提供优惠券补偿。",
}

DIRECT_RESPONSES = {
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
    "query_promotion": "今日优惠：新品第二杯半价，会员9折。",
    "query_member": "会员卡免费办理，首单立减5元。",
    "query_invoice": "支持电子发票，在小程序申请。",
    "query_complaint_status": "请提供投诉单号或订单号查询进度。",
}

class ReActAgentV2:
    def __init__(self, tools: Dict[str, Callable], intent_recognizer, memory_manager=None):
        self.tools = tools
        self.intent_recognizer = intent_recognizer
        self.memory_manager = memory_manager

    def process(self, user_input: str, session_id: str = "default") -> str:
        context = self.memory_manager.get_context(session_id) if self.memory_manager else ""
        intent = self.intent_recognizer.recognize(user_input)
        response = self._react_loop(user_input, intent, context)
        if self.memory_manager:
            self.memory_manager.save_message(session_id, user_input, response)
        return response

    def _react_loop(self, user_input: str, intent, context: str) -> str:
        if intent.name.startswith("complaint"):
            return self._handle_complaint(user_input, intent)
        elif intent.name.startswith("query"):
            return self._handle_query(user_input, intent)
        elif intent.name.startswith("order") or intent.name == "place_order":
            return self._handle_order(user_input, intent)
        else:
            return self._handle_general(user_input, intent)

    def _handle_complaint(self, user_input: str, intent) -> str:
        tool_schema = route(intent.name)
        if tool_schema:
            check_result = check_params(user_input, tool_schema)
            if check_result["status"] == "incomplete":
                return f"""【思考】用户意图: {intent.name}, 参数缺失
【行动】引导用户补充信息
【回复】{check_result['suggestion']}"""
            tool_name = get_tool_name(intent.name)
            tool_result = self.tools[tool_name](**check_result["params"]) if tool_name in self.tools else {"success": False}
            if tool_result["success"]:
                return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}
【行动】调用工具: {tool_name}
【工具结果】成功
【回复】{tool_result.get('response', '')}"""
            else:
                return f"""【思考】用户意图: {intent.name}, 工具调用失败
【行动】使用预设回复
【回复】{tool_result.get('response', '抱歉，投诉处理失败，请稍后再试。')}"""
        response = COMPLAINT_TEMPLATES.get(intent.name, "非常抱歉给您带来不好的体验。请提供您的订单号，我们核实后会为您处理退款或补偿。")
        return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}
【行动】匹配投诉处理模板
【回复】{response}"""

    def _handle_query(self, user_input: str, intent) -> str:
        tool_schema = route(intent.name)
        if tool_schema:
            check_result = check_params(user_input, tool_schema)
            if check_result["status"] == "incomplete":
                return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}, 工具参数缺失
【行动】引导用户补充信息
【回复】{check_result['suggestion']}"""
            tool_name = get_tool_name(intent.name)
            if tool_name and tool_name in self.tools:
                tool_result = self.tools[tool_name](**check_result["params"])
                if tool_result["success"]:
                    return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}, 需要查询信息
【行动】调用工具: {tool_name}({check_result['params']})
【工具结果】成功
【回复】{tool_result.get('response', str(tool_result))}"""
                else:
                    return f"""【思考】用户意图: {intent.name}, 工具调用失败
【行动】使用预设回复
【回复】{tool_result.get('response', '抱歉，查询失败，请稍后再试。')}"""
        return self._get_direct_response(intent)

    def _handle_order(self, user_input: str, intent) -> str:
        order_id = self._extract_order_id(user_input)
        if order_id and "query_order" in self.tools:
            tool_result = self.tools["query_order"](user_id="", order_id=order_id)
            if tool_result["success"]:
                return f"""【思考】用户意图: {intent.name}, 已有订单号
【行动】调用订单查询工具
【回复】{tool_result.get('response', str(tool_result))}"""
        return f"""【思考】用户意图: {intent.name}, 需要订单信息
【行动】引导用户提供订单号
【回复】请提供您的订单号或手机号，我帮您查询订单详情。"""

    def _handle_general(self, user_input: str, intent) -> str:
        response = DIRECT_RESPONSES.get(intent.name, "您好，我是BubbleMate奶茶店客服。请问有什么可以帮助您的？您可以咨询菜单推荐、订单状态、门店信息等问题。")
        return f"""【思考】用户意图: {intent.name}, 直接回复
【行动】使用预设回复模板
【回复】{response}"""

    def _extract_order_id(self, text: str) -> str:
        match = re.search(r"(\d{5,})", text)
        return match.group(1) if match else ""

    def _get_direct_response(self, intent) -> str:
        return f"""【思考】用户意图: {intent.name}
【行动】直接回复
【回复】{DIRECT_RESPONSES.get(intent.name, '请告诉我您想查询的具体内容。')}"""

