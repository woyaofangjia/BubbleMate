"""
BubbleMate Agent V2 - 增强版ReAct Agent
- 使用增强版意图识别器
- 改进回复生成逻辑
- 更好的工具调用集成
"""

import json
import os
import re
from typing import List, Dict, Optional, Callable
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

class ReActAgentV2:
    """增强版ReAct Agent"""
    
    def __init__(self, tools: Dict[str, Callable], intent_recognizer, memory_manager=None):
        self.tools = tools
        self.intent_recognizer = intent_recognizer
        self.memory_manager = memory_manager
        
        self.system_prompt = """你是BubbleMate奶茶店智能客服Agent。

你的职责：
1. 回答顾客关于奶茶、订单、门店的问题
2. 处理顾客投诉（口感、份量、服务、配送等）
3. 提供饮品推荐和点单建议

你可以使用以下工具（根据意图自动选择）：

📍 query_stores（门店查询）：
   - 当用户问：附近门店、最近门店、门店位置、地址、哪里有奶茶店时调用
   - 输入：位置名称（如"光谷广场"、"武汉大学"）
   - 如果用户没说位置，先反问："请问您在哪个位置/商圈？"

📋 query_menu（菜单查询）：
   - 当用户问：有什么饮品、推荐、菜单、价格、某饮品有没有时调用
   - 输入：门店名称（可选）、关键词（可选）
   - 不指定门店时返回所有门店的热门推荐

📦 query_order（订单查询）：
   - 当用户问：订单状态、订单进度、什么时候送到时调用
   - 输入：用户手机号、订单号（可选）
   - 如果用户没说手机号，先反问："请提供您的手机号以便查询"

📊 check_stock（库存查询）：
   - 当用户问：某饮品有没有货、库存时调用
   - 输入：饮品名称

🛠️ log_complaint（投诉处理）：
   - 当用户投诉时调用
   - 输入：投诉内容、投诉类型（口味/服务/配送）

回复原则：
- 先识别意图，再决定是否需要调用工具
- 工具参数不全时，主动反问用户补充
- 语气友好、专业，回复简洁明了
- 不确定时，承认并建议人工客服介入

回复格式：
【思考】分析用户意图（意图类别）+ 是否需要调用工具 + 参数是否完整
【行动】调用工具（如需要）或直接回复
【回复】最终回复内容
"""
    
    def process(self, user_input: str, session_id: str = "default") -> str:
        """处理用户输入"""
        intent = self.intent_recognizer.recognize(user_input)
        
        context = ""
        if self.memory_manager:
            context = self.memory_manager.get_context(session_id)
        
        response = self._react_loop(user_input, intent, context)
        
        if self.memory_manager:
            self.memory_manager.save_message(session_id, user_input, response)
        
        return response
    
    def _react_loop(self, user_input: str, intent, context: str) -> str:
        """ReAct循环（增强版）"""
        # 根据意图类别选择处理策略
        if intent.name.startswith("complaint"):
            return self._handle_complaint(user_input, intent)
        elif intent.name.startswith("query"):
            return self._handle_query(user_input, intent)
        elif intent.name.startswith("order") or intent.name == "place_order":
            return self._handle_order(user_input, intent)
        else:
            return self._handle_general(user_input, intent)
    
    def _handle_complaint(self, user_input: str, intent) -> str:
        """处理投诉（增强版）"""
        # 提取关键信息
        order_id = self._extract_order_id(user_input)
        
        # 根据投诉类型获取回复
        complaint_templates = {
            "complaint_taste": f"您好，非常抱歉饮品口感不符合您的预期。{'订单' + order_id + '已记录' if order_id else ''}我们核实后会为您重新制作或办理退款，预计24小时内处理完成。",
            "complaint_quantity": f"您好，非常抱歉饮品份量不足。{'订单' + order_id + '已记录' if order_id else ''}我们会核查门店制作标准，为您提供补偿。",
            "complaint_service": f"您好，非常抱歉服务态度不佳。{'订单' + order_id + '已记录' if order_id else ''}我们已通知门店整改，并会为您安排专属客服跟进。",
            "complaint_delivery": f"您好，非常抱歉配送超时。{'订单' + order_id + '已记录' if order_id else ''}我们会为您申请超时赔付，预计24小时内到账。",
            "complaint_price": f"您好，非常抱歉价格问题给您带来困扰。{'订单' + order_id + '已记录' if order_id else ''}我们会核实定价，并为您提供优惠券补偿。",
        }
        
        response = complaint_templates.get(intent.name, 
            "非常抱歉给您带来不好的体验。请提供您的订单号，我们核实后会为您处理退款或补偿。")
        
        return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}
【行动】匹配投诉处理模板
【回复】{response}"""
    
    def _handle_query(self, user_input: str, intent) -> str:
        """处理查询（增强版）"""
        # 映射意图到工具（使用新工具）
        tool_mapping = {
            "query_order": "query_order",
            "query_location": "query_stores",  # 门店查询（高德API）
            "query_menu": "query_menu",         # 菜单查询（本地JSON）
            "query_recommend": "query_menu",    # 推荐→菜单查询
            "query_price": "query_menu",        # 价格→菜单查询
        }
        
        tool_name = tool_mapping.get(intent.name)
        
        if tool_name and tool_name in self.tools:
            try:
                # 根据意图提取参数
                args = self._extract_args_for_tool(user_input, intent.name, tool_name)
                
                # 调用工具
                tool_result = self.tools[tool_name](**args)
                
                # 检查是否需要反问（参数缺失）
                if isinstance(tool_result, dict):
                    if not tool_result.get("success") and tool_result.get("type") == "ask_user":
                        return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}, 工具参数缺失
【行动】引导用户补充信息
【回复】{tool_result.get("response", "请提供更多信息")}"""
                    
                    # 成功调用
                    return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}, 需要查询信息
【行动】调用工具: {tool_name}({args})
【工具结果】成功: {tool_result.get('success')}
【回复】{tool_result.get("response", str(tool_result))}"""
                else:
                    # 字符串结果
                    return f"""【思考】用户意图: {intent.name}, 置信度: {intent.confidence:.2f}
【行动】调用工具: {tool_name}
【回复】{tool_result}"""
            except Exception as e:
                return f"""【思考】工具调用异常: {str(e)}
【行动】降级处理，直接回复
【回复】抱歉，系统暂时无法查询，请稍后再试或联系人工客服。"""
        else:
            # 无工具，直接回复
            return self._get_direct_query_response(intent)
    
    def _extract_args_for_tool(self, user_input: str, intent_name: str, tool_name: str) -> dict:
        """根据意图提取工具参数"""
        args = {}
        
        if tool_name == "query_stores":
            # 提取位置关键词
            location_keywords = ["光谷", "武汉大学", "街道口", "汉口", "武昌", "汉阳", "银泰", "武大"]
            for kw in location_keywords:
                if kw in user_input:
                    args["location"] = kw
                    break
            
            # 如果没提取到位置，返回空结果触发反问
            if not args.get("location"):
                # 尝试从用户输入提取更通用的位置
                import re
                match = re.search(r"(在|附近|周边).*?(?|有|的)(.+?)(店|门店|奶茶)", user_input)
                if match:
                    args["location"] = match.group(3)
                else:
                    args["location"] = None  # 会触发反问
        
        elif tool_name == "query_menu":
            # 提取门店名或关键词
            store_keywords = ["茶颜悦色", "喜茶", "奈雪", "蜜雪冰城"]
            for kw in store_keywords:
                if kw in user_input:
                    args["store_name"] = kw
                    break
            
            # 提取饮品关键词
            drink_keywords = ["拿铁", "奶茶", "果茶", "葡萄", "草莓", "幽兰", "声声", "杨枝甘露"]
            for kw in drink_keywords:
                if kw in user_input:
                    args["keyword"] = kw
                    break
        
        elif tool_name == "query_order":
            # 提取手机号或订单号
            import re
            phone_match = re.search(r"(\d{11})", user_input)
            if phone_match:
                args["user_id"] = phone_match.group(1)
            
            order_match = re.search(r"(ORD-\d+)", user_input)
            if order_match:
                args["order_id"] = order_match.group(1)
        
        return args
    
    def _handle_order(self, user_input: str, intent) -> str:
        """处理订单（增强版）"""
        order_id = self._extract_order_id(user_input)
        
        if order_id:
            # 调用订单查询工具
            if "query_order" in self.tools:
                result = self.tools["query_order"](user_input)
                return f"""【思考】用户意图: {intent.name}, 已有订单号
【行动】调用订单查询工具
【回复】{result}"""
        
        return f"""【思考】用户意图: {intent.name}, 需要订单信息
【行动】引导用户提供订单号
【回复】请提供您的订单号或手机号，我帮您查询订单详情。"""
    
    def _handle_general(self, user_input: str, intent) -> str:
        """处理通用对话（增强版）"""
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
        
        return f"""【思考】用户意图: {intent.name}, 直接回复
【行动】使用预设回复模板
【回复】{response}"""
    
    def _extract_order_id(self, text: str) -> str:
        """提取订单号"""
        match = re.search(r"(\d{5,})", text)
        return match.group(1) if match else ""
    
    def _format_query_response(self, intent_name: str, tool_result: str) -> str:
        """格式化查询回复"""
        # 清理工具结果中的JSON格式
        try:
            result_json = json.loads(tool_result.replace("【工具结果】", ""))
            if isinstance(result_json, dict):
                if "error" in result_json:
                    return f"抱歉，{result_json['error']}。{result_json.get('hint', '')}"
                
                if "shops" in result_json:
                    shops = result_json["shops"][:3]
                    lines = []
                    for shop in shops:
                        lines.append(f"- {shop.get('name', '')}: {shop.get('address', '')}")
                    return "\n".join(lines)
                
                if "menu" in result_json or "items" in result_json:
                    return tool_result
                
                return tool_result
        except:
            pass
        
        return tool_result
    
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


def create_tools_v2() -> Dict[str, Callable]:
    """创建增强版工具集"""
    
    def query_order(user_input: str) -> str:
        """查询订单（增强版）"""
        orders = {
            "12345": {"status": "配送中", "drink": "芝芝莓莓", "eta": "15分钟", "store": "武汉大学梅园店"},
            "67890": {"status": "制作中", "drink": "杨枝甘露", "eta": "25分钟", "store": "银泰创意城店"},
            "11111": {"status": "已完成", "drink": "茉莉绿茶", "eta": "已送达", "store": "街道口店"},
        }
        
        order_id = re.search(r"(\d{5,})", user_input)
        if order_id:
            order_id = order_id.group(1)
            if order_id in orders:
                order = orders[order_id]
                return f"订单{order_id}状态：{order['status']}，饮品-{order['drink']}，{order['eta']}，门店-{order['store']}"
            
            return f"抱歉，订单{order_id}不存在，请检查订单号是否正确。"
        
        return "请提供订单号（如：12345），我帮您查询订单状态。"
    
    def query_shop(user_input: str) -> str:
        """查询门店（增强版）"""
        shops_path = os.path.join("data", "bubble_tea_all.json")
        if os.path.exists(shops_path):
            with open(shops_path, "r", encoding="utf-8") as f:
                shops = json.load(f)
            
            # 根据关键词筛选
            keywords = ["武大", "武汉", "银泰", "群光", "梦时代", "街道口"]
            matched_keyword = None
            for kw in keywords:
                if kw in user_input:
                    matched_keyword = kw
                    break
            
            if matched_keyword:
                filtered = [s for s in shops if matched_keyword in s.get("address", "") or matched_keyword in s.get("name", "")]
                if filtered:
                    result = f"找到{len(filtered)}家匹配门店：\n"
                    for shop in filtered[:3]:
                        result += f"- {shop.get('name', '')}: {shop.get('address', '')}\n"
                    return result
                return f"未找到'{matched_keyword}'附近的门店，请尝试其他关键词。"
            
            # 返回前3家
            shop_list = shops[:3]
            result = "附近门店：\n"
            for shop in shop_list:
                result += f"- {shop.get('name', '')}: {shop.get('address', '')}\n"
            return result
        
        return "门店数据暂不可用"
    
    def query_menu(user_input: str) -> str:
        """查询菜单（增强版）"""
        menu = {
            "芝士系列": [
                {"name": "芝芝莓莓", "price": 20, "desc": "鲜草莓芝士奶盖"},
                {"name": "芝芝芒果", "price": 18, "desc": "芒果芝士奶盖"},
            ],
            "鲜果茶系列": [
                {"name": "杨枝甘露", "price": 18, "desc": "椰奶芒果西柚"},
                {"name": "葡萄冰茶", "price": 15, "desc": "新鲜葡萄冰茶"},
            ],
            "奶茶系列": [
                {"name": "珍珠奶茶", "price": 12, "desc": "经典珍珠奶茶"},
                {"name": "糯米奶茶", "price": 14, "desc": "糯米珍珠奶茶"},
            ],
            "纯茶系列": [
                {"name": "茉莉绿茶", "price": 15, "desc": "零糖低卡"},
                {"name": "柠檬茶", "price": 10, "desc": "清爽柠檬"},
            ]
        }
        
        # 检查是否有分类关键词
        for category in menu:
            if category in user_input or category.replace("系列", "") in user_input:
                items = menu[category]
                result = f"{category}：\n"
                for item in items:
                    result += f"- {item['name']} - ¥{item['price']} - {item['desc']}\n"
                return result
        
        # 默认返回推荐
        return """招牌推荐：
1. 芝芝莓莓 - ¥20 - 鲜草莓芝士奶盖
2. 杨枝甘露 - ¥18 - 椰奶芒果西柚
3. 茉莉绿茶 - ¥15 - 零糖低卡
4. 珍珠奶茶 - ¥12 - 经典珍珠奶茶"""
    
    def handle_complaint(user_input: str) -> str:
        """处理投诉（增强版）"""
        complaint_types = {
            "口感": "taste",
            "份量": "quantity", 
            "服务": "service",
            "配送": "delivery",
            "价格": "price",
        }
        
        complaint_type = None
        for name, code in complaint_types.items():
            if name in user_input:
                complaint_type = code
                break
        
        if complaint_type:
            order_id = re.search(r"(\d{5,})", user_input)
            order_str = f"订单{order_id.group(1)}" if order_id else "您的投诉"
            return f"{order_str}已受理，客服将在24小时内联系您处理。"
        
        return "请说明投诉类型（口感/份量/服务/配送/价格），我帮您处理。"
    
    return {
        "query_order": query_order,
        "query_shop": query_shop,
        "query_menu": query_menu,
        "handle_complaint": handle_complaint,
    }


def test_agent_v2():
    """测试增强版Agent"""
    from .intent_recognizer_v2 import IntentRecognizerV2
    from .memory_manager_v2 import MemoryManagerV2
    
    intent_recognizer = IntentRecognizerV2("data")
    tools = create_tools_v2()
    memory_manager = MemoryManagerV2(window_size=5, use_redis=False)
    agent = ReActAgentV2(tools, intent_recognizer, memory_manager)
    
    test_inputs = [
        "太甜了，喝不下去",
        "你们有什么招牌推荐？",
        "订单12345什么时候能送到？",
        "附近有门店吗？",
        "可以退款吗？",
        "门店营业时间？",
    ]
    
    print("\n" + "=" * 60)
    print("增强版Agent测试")
    print("=" * 60)
    
    session_id = "test_session"
    for input_text in test_inputs:
        response = agent.process(input_text, session_id)
        print(f"用户: {input_text}")
        print(f"Agent:\n{response}")
        print("=" * 60)

if __name__ == "__main__":
    test_agent_v2()
