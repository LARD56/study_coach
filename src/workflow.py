"""
工作流 - 目标-计划-验证流程
"""
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field


class WorkflowState(Enum):
    """工作流状态"""
    IDLE = "idle"
    GOAL_RECEIVED = "goal_received"
    PLANNING = "planning"
    PLAN_GENERATED = "plan_generated"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    state: WorkflowState
    action: str
    input_data: dict = field(default_factory=dict)
    output_data: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Workflow:
    """工作流引擎 - 目标-计划-验证"""

    def __init__(self, agent):
        self.agent = agent
        self.current_state = WorkflowState.IDLE
        self.steps: list[WorkflowStep] = []
        self.context: dict[str, Any] = {}

    def execute(
        self,
        goal: str,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """
        执行工作流

        Args:
            goal: 用户目标
            max_iterations: 最大迭代次数

        Returns:
            工作流执行结果
        """
        self._add_step("workflow_start", WorkflowState.GOAL_RECEIVED, "接收目标", {"goal": goal})

        # 目标验证
        try:
            validated_goal = self.agent.guardrails.validate_input(goal)
            self.context["goal"] = validated_goal
            self.current_state = WorkflowState.GOAL_RECEIVED
        except Exception as e:
            return self._fail(f"目标验证失败: {e}")

        # 计划生成
        self._transition(WorkflowState.PLANNING, "生成计划")
        try:
            plan = self._generate_plan(validated_goal)
            self.context["plan"] = plan
            self._transition(WorkflowState.PLAN_GENERATED, "计划已生成", output_data=plan)
        except Exception as e:
            return self._fail(f"计划生成失败: {e}")

        # 执行计划
        self._transition(WorkflowState.EXECUTING, "执行计划")
        try:
            result = self._execute_plan(plan, max_iterations)
            self.context["result"] = result
            self._transition(WorkflowState.COMPLETED, "执行完成", output_data=result)
            return result
        except Exception as e:
            return self._fail(f"计划执行失败: {e}")

    def _generate_plan(self, goal: str) -> dict:
        """生成执行计划"""
        prompt = f"""用户目标: {goal}

请制定执行计划，返回JSON格式：
{{
  "steps": [
    {{"id": "step1", "tool": "工具名", "description": "步骤描述", "input": {{"参数": "值"}}}}
  ],
  "expected_outcome": "预期结果"
}}"""

        response = self.agent.model_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )

        try:
            plan = json.loads(response["content"])
            plan["goal"] = goal
            plan["created_at"] = datetime.now().isoformat()
            return plan
        except json.JSONDecodeError:
            # 返回默认计划
            return {
                "goal": goal,
                "steps": [
                    {"id": "step1", "tool": "knowledge_retriever", "description": "检索相关知识", "input": {"query": goal, "top_k": 3}},
                    {"id": "step2", "tool": "study_plan_generator", "description": "生成学习计划", "input": {"topic": goal, "days": 7, "daily_hours": 2}},
                ],
                "expected_outcome": "完成学习计划生成",
            }

    def _execute_plan(self, plan: dict, max_iterations: int) -> dict:
        """执行计划"""
        results = []
        steps = plan.get("steps", [])

        for i, step in enumerate(steps):
            if i >= max_iterations:
                self._add_step(
                    f"iteration_limit",
                    WorkflowState.STOPPED,
                    f"达到最大迭代次数 {max_iterations}",
                )
                break

            step_id = step.get("id", f"step{i+1}")
            tool_name = step.get("tool")
            description = step.get("description", "")
            step_input = step.get("input", {})

            self._add_step(step_id, WorkflowState.EXECUTING, description, {"tool": tool_name, "input": step_input})

            # 检查是否需要确认
            if self._is_high_risk_step(step):
                confirmed = self.agent.guardrails.request_confirmation(
                    action=description,
                    details=str(step_input),
                )
                if not confirmed:
                    self._add_step(
                        step_id,
                        WorkflowState.STOPPED,
                        "用户取消高风险操作",
                        error="高风险操作被人工确认拦截",
                    )
                    break

            # 执行工具
            try:
                # 验证输入
                validated_input = self.agent.guardrails.validate_tool_input(tool_name, step_input)

                result = self.agent.tools.execute(tool_name, validated_input)
                self._add_step(step_id, WorkflowState.VALIDATING, description, output_data=result)
                results.append({"step_id": step_id, "status": "success", "result": result})
            except Exception as e:
                self._add_step(step_id, WorkflowState.FAILED, description, error=str(e))
                results.append({"step_id": step_id, "status": "failed", "error": str(e)})

                # 检查是否应该停止
                if self._should_stop_on_failure(step):
                    break

        return {
            "workflow_status": self.current_state.value,
            "steps_executed": len(results),
            "results": results,
            "final_state": self.current_state.value,
        }

    def _is_high_risk_step(self, step: dict) -> bool:
        """判断是否为高风险步骤"""
        high_risk_tools = ["file_write", "file_delete", "network_send"]
        return step.get("tool") in high_risk_tools

    def _should_stop_on_failure(self, step: dict) -> bool:
        """判断失败时是否停止"""
        critical_tools = ["study_plan_generator", "answer_evaluator"]
        return step.get("tool") in critical_tools

    def _transition(self, new_state: WorkflowState, action: str, output_data: Any = None):
        """状态转换"""
        self.current_state = new_state
        self._add_step(
            f"transition_{new_state.value}",
            new_state,
            action,
            output_data=output_data,
        )

    def _fail(self, error: str) -> dict:
        """标记工作流失败"""
        self.current_state = WorkflowState.FAILED
        self._add_step("workflow_failure", WorkflowState.FAILED, "工作流失败", error=error)
        return {
            "workflow_status": "failed",
            "error": error,
            "steps_completed": len(self.steps),
        }

    def _add_step(
        self,
        step_id: str,
        state: WorkflowState,
        action: str,
        input_data: dict = None,
        output_data: Any = None,
        error: str = None,
    ):
        """添加工作流步骤"""
        step = WorkflowStep(
            step_id=step_id,
            state=state,
            action=action,
            input_data=input_data or {},
            output_data=output_data,
            error=error,
        )
        self.steps.append(step)

    def get_log(self) -> list[dict]:
        """获取工作流日志"""
        return [
            {
                "step_id": s.step_id,
                "state": s.state.value,
                "action": s.action,
                "input": s.input_data,
                "output": s.output_data,
                "error": s.error,
                "timestamp": s.timestamp,
            }
            for s in self.steps
        ]