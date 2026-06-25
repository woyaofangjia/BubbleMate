"""
BubbleMate Tools - 工具异常处理包装器
实现参数验证、异常捕获、反问逻辑、重试机制
"""

import json
import time
from typing import Dict, Callable, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class ToolStatus(Enum):
    """工具调用状态"""
    PENDING = "pending"
    VALIDATING = "validating"
    CALLING = "calling"
    RETRYING = "retrying"
    SUCCESS = "success"
    FAILED = "failed"
    MISSING_PARAM = "missing_param"  # 参数缺失，需要反问

@dataclass
class ToolResult:
    """工具调用结果"""
    status: ToolStatus
    result: Any = None
    error: Optional[str] = None
    missing_params: Optional[List[str]] = None
    retry_count: int = 0
    response: str = ""  # 给用户的回复

class ToolWrapper:
    """工具包装器"""
    
    def __init__(self, max_retries: int = 2, timeout: float = 5.0):
        self.max_retries = max_retries
        self.timeout = timeout
        self.call_history: List[Dict] = []
    
    def validate_params(self, tool_config: Dict, arguments: Dict) -> ToolResult:
        """
        验证参数
        如果必填参数缺失，返回MISSING_PARAM状态并提示用户
        """
        required = tool_config.get("parameters", {}).get("required", [])
        properties = tool_config.get("parameters", {}).get("properties", {})
        
        missing = []
        for param in required:
            if param not in arguments or not arguments[param]:
                missing.append(param)
        
        if missing:
            # 构建反问提示
            missing_descriptions = []
            for param in missing:
                desc = properties.get(param, {}).get("description", param)
                missing_descriptions.append(f"  - {param}: {desc}")
            
            return ToolResult(
                status=ToolStatus.MISSING_PARAM,
                missing_params=missing,
                response=f"我需要更多信息才能帮您查询：\n" + "\n".join(missing_descriptions) + "\n\n请提供这些信息。"
            )
        
        return ToolResult(status=ToolStatus.PENDING)
    
    def call_with_retry(self, handler: Callable, arguments: Dict, tool_name: str) -> ToolResult:
        """
        带重试的工具调用
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                # 记录调用
                self.call_history.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "retry": retry_count,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # 执行调用
                result = handler(**arguments)
                
                # 检查结果是否为空
                if result is None or (isinstance(result, dict) and not result):
                    return ToolResult(
                        status=ToolStatus.FAILED,
                        error="工具返回空结果",
                        retry_count=retry_count,
                        response="抱歉，查询结果为空。可能是您提供的信息有误，请检查后再试。"
                    )
                
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    result=result,
                    retry_count=retry_count,
                    response=""
                )
                
            except TypeError as e:
                # 参数类型错误
                last_error = str(e)
                retry_count += 1
                if retry_count <= self.max_retries:
                    time.sleep(0.5)
                    continue
                
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=f"参数错误: {last_error}",
                    retry_count=retry_count,
                    response="抱歉，参数格式不正确。请检查您输入的信息。"
                )
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                # 特定异常处理
                if "timeout" in last_error.lower() or "connection" in last_error.lower():
                    if retry_count <= self.max_retries:
                        time.sleep(1.0)  # 网络问题多等待
                        continue
                
                if retry_count <= self.max_retries:
                    time.sleep(0.5)
                    continue
                
                # 重试耗尽
                return ToolResult(
                    status=ToolStatus.FAILED,
                    error=f"调用失败: {last_error}",
                    retry_count=retry_count,
                    response=f"抱歉，查询服务暂时不可用（已重试{retry_count}次）。请稍后再试，或联系人工客服。"
                )
        
        return ToolResult(
            status=ToolStatus.FAILED,
            error="未知错误",
            retry_count=retry_count,
            response="抱歉，服务暂时不可用。"
        )
    
    def execute(self, tool_config: Dict, handler: Callable, arguments: Dict, tool_name: str) -> ToolResult:
        """
        完整执行流程：验证 -> 调用 -> 异常处理
        """
        # 1. 参数验证
        validation = self.validate_params(tool_config, arguments)
        if validation.status == ToolStatus.MISSING_PARAM:
            return validation
        
        # 2. 调用工具（带重试）
        result = self.call_with_retry(handler, arguments, tool_name)
        
        # 3. 结果处理 - 如果结果为空，提供引导
        if result.status == ToolStatus.SUCCESS:
            result.response = self._format_success_response(tool_name, result.result)
        
        return result
    
    def _format_success_response(self, tool_name: str, result: Any) -> str:
        """格式化成功响应"""
        if isinstance(result, dict):
            if "error" in result:
                # 业务逻辑错误（如订单不存在）
                if "不存在" in result["error"] or "找不到" in result["error"]:
                    hint = result.get("hint", "请检查信息是否正确")
                    return f"抱歉，{result['error']}。{hint}，或者您可以尝试：\n  - 换个关键词搜索\n  - 联系人工客服核实"
                return f"查询结果: {result}"
            
            # 正常结果
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        return str(result)


# 使用示例
def test_tool_wrapper():
    """测试工具包装器"""
    wrapper = ToolWrapper(max_retries=2)
    
    # 模拟工具配置
    tool_config = {
        "name": "query_order_status",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "订单编号"},
                "phone_number": {"type": "string", "description": "手机号码"}
            },
            "required": ["order_id"]
        }
    }
    
    # 测试1: 参数缺失
    print("=" * 50)
    print("测试1: 参数缺失")
    result = wrapper.execute(tool_config, lambda **kwargs: kwargs, {}, "query_order_status")
    print(f"状态: {result.status.value}")
    print(f"回复: {result.response}")
    print()
    
    # 测试2: 正常调用
    print("测试2: 正常调用")
    result = wrapper.execute(
        tool_config, 
        lambda **kwargs: {"status": "配送中", "eta": "15分钟"},
        {"order_id": "12345"},
        "query_order_status"
    )
    print(f"状态: {result.status.value}")
    print(f"结果: {result.result}")
    print()
    
    # 测试3: 返回空结果
    print("测试3: 返回空结果")
    result = wrapper.execute(
        tool_config,
        lambda **kwargs: {},
        {"order_id": "99999"},
        "query_order_status"
    )
    print(f"状态: {result.status.value}")
    print(f"回复: {result.response}")
    print()
    
    # 测试4: 业务错误（订单不存在）
    print("测试4: 业务错误")
    result = wrapper.execute(
        tool_config,
        lambda **kwargs: {"error": "订单不存在", "hint": "请检查订单号是否正确"},
        {"order_id": "00000"},
        "query_order_status"
    )
    print(f"状态: {result.status.value}")
    print(f"回复: {result.response}")

if __name__ == "__main__":
    test_tool_wrapper()
