"""
BubbleMate Agent - ReAct Agent核心循环
实现 Thought -> Action -> Observation 循环
"""

import json
import os
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import urllib.request
import urllib.parse

@dataclass
class Message:
    """消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    tool_calls: Optional[List[Dict]] = None

@dataclass
class ToolCall:
    """工具调用"""
    name: str
    arguments: Dict
    result: Optional[str] = None

class ReActAgent:
    """ReAct Agent"""
    
    def __init__(self, tools: Dict[str, Callable], intent_recognizer, memory_manager=None):
        self.tools = tools
        self.intent_recognizer = intent_recognizer
        self.memory_manager = memory_manager
        
        # 系统提示
        self.system_prompt = """你是BubbleMate奶茶店智能客服Agent。

你的职责：
1. 回答顾客关于奶茶、订单、门店的问题
2. 处理顾客投诉（口感、份量、服务、配送等）
3. 提供饮品推荐和点单建议

你可以使用的工具：
- query_order: 查询订单状态
- query_shop: 查询门店信息
- query_menu: 查询菜单/饮品信息
- handle_complaint: 处理投诉

回复原则：
- 语气友好、专业
- 遇到投诉先安抚，再提供解决方案
- 工具调用失败时，引导用户提供更多信息
- 不确定时，承认并建议人工客服介入

回复格式（思考过程）：
【思考】分析用户意图
【行动】选择工具或直接回复
【回复】最终回复内容
"""
    
    def process(self, user_input: str, session_id: str = "default") -> str:
        """处理用户输入"""
        # 1. 意图识别
        intent = self.intent_recognizer.recognize(user_input)
        
        # 2. 获取上下文记忆
        context = ""
        if self.memory_manager:
            context = self.memory_manager.get_context(session_id)
        
        # 3. 构建输入
        full_input = self._build_input(user_input, intent, context)
        
        # 4. ReAct循环
        response = self._react_loop(full_input, session_id)
        
        # 5. 保存记忆
        if self.memory_manager:
            self.memory_manager.save_message(session_id, user_input, response)
        
        return response
    
    def _build_input(self, user_input: str, intent, context: str) -> str:
        """构建完整输入"""
        parts = []
        
        if context:
            parts.append(f"[历史对话]\n{context}\n")
        
        parts.append(f"[意图识别] {intent.name} (置信度: {intent.confidence:.2f})")
        parts.append(f"[用户消息] {user_input}")
        
        return "\n".join(parts)
    
    def _react_loop(self, input_text: str, session_id: str) -> str:
        """ReAct循环"""
        # 简化版：基于意图直接路由
        intent = self.intent_recognizer.recognize(input_text.split("[用户消息]")[-1].strip())
        
        # 根据意图选择处理方式
        if intent.name.startswith("complaint"):
            return self._handle_complaint(input_text, intent)
        elif intent.name.startswith("query"):
            return self._handle_query(input_text, intent, session_id)
        elif intent.name.startswith("order"):
            return self._handle_order(input_text, intent)
        else:
            return self._handle_general(input_text)
    
    def _handle_complaint(self, input_text: str, intent) -> str:
        """处理投诉"""
        user_msg = input_text.split("[用户消息]")[-1].strip()
        
        # 获取对应回复模板
        response = self._get_complaint_response(user_msg, intent)
        
        return f"""【思考】用户意图: {intent.name}, 类别: {intent.category}
【行动】匹配投诉处理模板
【回复】{response}"""
    
    def _handle_query(self, input_text: str, intent, session_id: str) -> str:
        """处理查询"""
        user_msg = input_text.split("[用户消息]")[-1].strip()
        
        # 根据意图调用工具
        tool_name = self._map_intent_to_tool(intent.name)
        
        if tool_name and tool_name in self.tools:
            # 调用工具
            tool_result = self.tools[tool_name](user_msg, session_id)
            
            return f"""【思考】用户意图: {intent.name}, 需要查询信息
【行动】调用工具: {tool_name}
【工具结果】{tool_result}
【回复】根据查询结果，{self._format_tool_response(tool_name, tool_result)}"""
        else:
            # 直接回复
            return self._get_query_response(intent)
    
    def _handle_order(self, input_text: str, intent) -> str:
        """处理订单"""
        return """【思考】用户意图: 订单相关操作
【行动】引导用户提供订单信息
【回复】请提供您的订单号或手机号，我帮您查询订单详情。"""
    
    def _handle_general(self, input_text: str) -> str:
        """处理通用对话"""
        return """【思考】无法明确识别意图
【行动】使用通用回复
【回复】您好，我是BubbleMate奶茶店客服。请问有什么可以帮助您的？您可以咨询菜单推荐、订单状态、门店信息等问题。"""
    
    def _get_complaint_response(self, user_msg: str, intent) -> str:
        """获取投诉回复"""
        # 加载回复模板
        replies_path = os.path.join("data", "review_replies.json")
        if os.path.exists(replies_path):
            with open(replies_path, "r", encoding="utf-8") as f:
                replies = json.load(f)
            
            # 寻找相似回复
            for reply in replies:
                if intent.name in reply.get("category", "") or \
                   any(kw in user_msg for kw in ["甜", "酸", "冰", "慢", "少", "服务", "配送"]):
                    return reply["reply"]
        
        # 默认回复
        return "非常抱歉给您带来不好的体验。请提供您的订单号，我们核实后会为您处理退款或补偿。"
    
    def _get_query_response(self, intent) -> str:
        """获取查询回复"""
        responses = {
            "query_recommend": "您好！我们的招牌饮品包括：1)芝芝莓莓 - 鲜草莓搭配芝士奶盖；2)杨枝甘露 - 椰奶芒果西柚；3)茉莉绿茶 - 零糖低卡。您喜欢什么口味？",
            "query_menu": "我们菜单分为：芝士系列、鲜果茶系列、纯茶系列、奶茶系列。人均价格8-20元。具体饮品可在小程序查看。",
            "query_opentime": "武汉大学门店营业时间：10:00-22:00；银泰创意城店：10:00-21:30。",
            "query_location": "附近门店：1)武汉大学梅园店 - 步行5分钟；2)银泰创意城店 - 步行10分钟；3)街道口1点点店 - 步行8分钟。",
            "query_sugar": "我们提供5档糖度：标准糖、七分糖、五分糖、三分糖、无糖。建议首次选择五分糖。",
            "query_order": "请提供订单号，我帮您查询订单状态和配送进度。",
            "query_refund": "请在小程序【我的订单】申请售后，或提供订单号人工处理。",
        }
        return responses.get(intent.name, "请告诉我您想查询的具体内容。")
    
    def _map_intent_to_tool(self, intent_name: str) -> Optional[str]:
        """映射意图到工具"""
        mapping = {
            "query_order": "query_order",
            "query_location": "query_shop",
            "query_menu": "query_menu",
            "query_recommend": "query_menu",
        }
        return mapping.get(intent_name)
    
    def _format_tool_response(self, tool_name: str, result: str) -> str:
        """格式化工具回复"""
        return f"{result}"

# 简化版工具实现
def create_tools() -> Dict[str, Callable]:
    """创建工具集"""
    
    def query_order(user_input: str, session_id: str) -> str:
        """查询订单"""
        # Mock数据
        orders = {
            "12345": {"status": "配送中", "drink": "芝芝莓莓", "eta": "15分钟"},
            "67890": {"status": "制作中", "drink": "杨枝甘露", "eta": "25分钟"},
        }
        
        # 简单提取订单号
        for order_id in orders:
            if order_id in user_input:
                order = orders[order_id]
                return f"订单{order_id}：状态-{order['status']}, 饮品-{order['drink']}, 预计到达-{order['eta']}"
        
        return "未找到订单，请提供正确的订单号（如：12345）"
    
    def query_shop(user_input: str, session_id: str) -> str:
        """查询门店"""
        # 加载门店数据
        shops_path = os.path.join("data", "bubble_tea_all.json")
        if os.path.exists(shops_path):
            with open(shops_path, "r", encoding="utf-8") as f:
                shops = json.load(f)
            
            # 返回前3家
            shop_list = shops[:3]
            result = "附近门店：\n"
            for shop in shop_list:
                result += f"- {shop['name']} ({shop['address']})\n"
            return result
        
        return "门店数据暂不可用"
    
    def query_menu(user_input: str, session_id: str) -> str:
        """查询菜单"""
        return """招牌推荐：
1. 芝芝莓莓 - ¥20 - 鲜草莓芝士奶盖
2. 杨枝甘露 - ¥18 - 椰奶芒果西柚
3. 茉莉绿茶 - ¥15 - 零糖低卡
4. 蜜雪冰城柠檬水 - ¥9 - 清爽解暑"""
    
    def handle_complaint(user_input: str, session_id: str) -> str:
        """处理投诉"""
        return "已记录您的投诉，客服将在24小时内联系您处理。"
    
    return {
        "query_order": query_order,
        "query_shop": query_shop,
        "query_menu": query_menu,
        "handle_complaint": handle_complaint,
    }


def test_agent():
    """测试Agent"""
    from .intent_recognizer import IntentRecognizer
    
    intent_recognizer = IntentRecognizer("data")
    tools = create_tools()
    agent = ReActAgent(tools, intent_recognizer)
    
    test_inputs = [
        "太甜了，喝不下去",
        "你们有什么招牌推荐？",
        "订单12345什么时候能送到？",
        "附近有门店吗？",
    ]
    
    print("\nAgent测试:")
    print("=" * 60)
    for input_text in test_inputs:
        response = agent.process(input_text)
        print(f"用户: {input_text}")
        print(f"Agent: {response}")
        print("=" * 60)

if __name__ == "__main__":
    test_agent()