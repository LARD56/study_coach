"""
智能体 - 学习教练智能体主模块
"""
import json
from typing import Optional
from .model_client import ModelClient
from .tools import Tools, list_tools, TOOL_CONTRACTS
from .guardrails import Guardrails
from .workflow import Workflow


class StudyCoachAgent:
    """学习教练智能体"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.model_client = ModelClient()
        self.tools = Tools(self.model_client)
        self.guardrails = Guardrails()
        self.workflow: Optional[Workflow] = None
        self.conversation_history = []

    def process_goal(self, goal: str) -> dict:
        """
        处理用户目标

        Args:
            goal: 用户输入的目标

        Returns:
            处理结果
        """
        # 记录对话历史
        self.conversation_history.append({
            "role": "user",
            "content": goal,
        })

        try:
            # 使用工作流执行
            self.workflow = Workflow(self)
            result = self.workflow.execute(goal)

            self.conversation_history.append({
                "role": "assistant",
                "content": json.dumps(result, ensure_ascii=False),
            })

            return result

        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "type": type(e).__name__,
            }
            self.conversation_history.append({
                "role": "assistant",
                "content": json.dumps(error_result, ensure_ascii=False),
            })
            return error_result

    def chat(self, message: str) -> dict:
        """
        通用对话接口

        Args:
            message: 用户消息

        Returns:
            响应结果
        """
        try:
            # 验证输入
            validated = self.guardrails.validate_input(message)

            # 构建提示词
            system_prompt = self._build_system_prompt()
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history[-6:],
                {"role": "user", "content": validated},
            ]

            # 调用模型
            response = self.model_client.chat(messages)

            self.conversation_history.append({
                "role": "assistant",
                "content": response["content"],
            })

            return {
                "status": "success",
                "response": response["content"],
                "model": response["model"],
                "tokens": response["tokens"],
                "latency_ms": response["latency_ms"],
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_info = list_tools()

        tools_description = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in tools_info
        ])

        return f"""你是 StudyCoach AI，一个专业的学习教练智能体。

你的职责是帮助用户：
1. 制定学习计划和目标
2. 生成练习题和评估答案
3. 检索相关知识和资料
4. 提供学习反馈和建议

你可以使用以下工具：
{tools_description}

工作流程：
1. 理解用户的学习目标
2. 调用适当工具执行任务
3. 记录执行结果
4. 给出最终建议

注意：
- 高风险操作需要用户确认
- 不要泄露敏感信息
- 遇到问题及时停止并说明原因
"""

    def get_available_tools(self) -> list[dict]:
        """获取可用工具列表"""
        return list_tools()

    def get_tool_contract(self, tool_name: str) -> Optional[dict]:
        """获取工具契约"""
        return TOOL_CONTRACTS.get(tool_name)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "model_stats": self.model_client.get_stats(),
            "guardrail_stats": self.guardrails.get_stats(),
            "conversation_turns": len(self.conversation_history),
            "tools_executed": len(self.tools.execution_log),
        }

    def get_workflow_log(self) -> list[dict]:
        """获取工作流日志"""
        if self.workflow:
            return self.workflow.get_log()
        return []

    def reset(self):
        """重置智能体状态"""
        self.conversation_history = []
        self.workflow = None