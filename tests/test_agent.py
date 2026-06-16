"""
StudyCoach AI 学习教练智能体 - 自动化测试
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agent import StudyCoachAgent
from src.model_client import ModelClient
from src.tools import Tools, ToolExecutionError
from src.guardrails import Guardrails, GuardrailError


class TestModelClient:
    """模型客户端测试"""

    def test_model_client_init(self):
        """测试模型客户端初始化"""
        client = ModelClient()
        assert client is not None
        assert client.total_tokens == 0
        assert client.total_cost == 0.0

    def test_get_stats(self):
        """测试统计信息"""
        client = ModelClient()
        stats = client.get_stats()
        assert "total_tokens" in stats
        assert "total_cost_usd" in stats
        assert "request_count" in stats


class TestGuardrails:
    """安全护栏测试"""

    def setup_method(self):
        self.guardrails = Guardrails()

    def test_valid_input(self):
        """测试有效输入"""
        result = self.guardrails.validate_input("Python基础学习")
        assert result == "Python基础学习"

    def test_empty_input(self):
        """测试空输入被拒绝"""
        with pytest.raises(GuardrailError) as exc_info:
            self.guardrails.validate_input("")
        assert exc_info.value.reason == "empty_input"

    def test_sensitive_info_detection(self):
        """测试敏感信息检测"""
        with pytest.raises(GuardrailError) as exc_info:
            self.guardrails.validate_input("我的API密钥是sk-1234567890abcdef")
        assert exc_info.value.reason == "sensitive_info_detected"

    def test_high_risk_operation_detection(self):
        """测试高风险操作检测"""
        with pytest.raises(GuardrailError) as exc_info:
            self.guardrails.validate_input("请删除所有文件 rm -rf /")
        assert exc_info.value.reason == "high_risk_operation"

    def test_path_validation_allowed(self):
        """测试允许的路径"""
        result = self.guardrails.validate_path("data/knowledge/test.md")
        assert "data/knowledge" in result or "test.md" in result

    def test_path_validation_blocked(self):
        """测试路径被阻止"""
        with pytest.raises(GuardrailError) as exc_info:
            self.guardrails.validate_path("/etc/passwd")
        assert exc_info.value.reason == "path_not_allowed"

    def test_tool_input_validation(self):
        """测试工具输入验证"""
        params = {"query": "Python基础", "top_k": 3}
        result = self.guardrails.validate_tool_input("knowledge_retriever", params)
        assert result["query"] == "Python基础"
        assert result["top_k"] == 3

    def test_get_stats(self):
        """测试统计信息"""
        stats = self.guardrails.get_stats()
        assert "blocked_count" in stats
        assert "audit_log_size" in stats


class TestTools:
    """工具测试"""

    def setup_method(self):
        self.model_client = ModelClient()
        self.tools = Tools(self.model_client)

    def test_tools_init(self):
        """测试工具初始化"""
        assert self.tools is not None
        assert self.tools.knowledge_base is not None

    def test_execute_unknown_tool(self):
        """测试执行未知工具"""
        with pytest.raises(ToolExecutionError) as exc_info:
            self.tools.execute("unknown_tool", {})
        assert exc_info.value.error_type == "tool_not_found"

    def test_knowledge_retriever_empty_query(self):
        """测试空查询被拒绝"""
        with pytest.raises(ToolExecutionError) as exc_info:
            self.tools.execute("knowledge_retriever", {"query": ""})
        assert exc_info.value.error_type == "validation_error"

    def test_knowledge_retriever_success(self):
        """测试知识检索成功"""
        result = self.tools.execute("knowledge_retriever", {"query": "Python基础", "top_k": 2})
        assert "items" in result
        assert isinstance(result["items"], list)

    def test_study_plan_generator_empty_topic(self):
        """测试空主题被拒绝"""
        with pytest.raises(ToolExecutionError) as exc_info:
            self.tools.execute("study_plan_generator", {"topic": "", "days": 7})
        assert exc_info.value.error_type == "validation_error"

    def test_study_plan_generator_invalid_days(self):
        """测试超出范围的天数被拒绝"""
        with pytest.raises(ToolExecutionError) as exc_info:
            self.tools.execute("study_plan_generator", {"topic": "Python", "days": 100})
        assert exc_info.value.error_type == "validation_error"

    def test_study_plan_generator_success(self):
        """测试学习计划生成成功"""
        result = self.tools.execute("study_plan_generator", {"topic": "Python", "days": 7, "daily_hours": 2})
        assert "plan_id" in result
        assert "phases" in result
        assert "total_hours" in result
        assert result["total_hours"] == 14.0

    def test_question_generator_success(self):
        """测试题目生成成功"""
        result = self.tools.execute("question_generator", {"topic": "Python", "count": 3})
        assert isinstance(result, list)
        assert len(result) == 3

    def test_answer_evaluator_success(self):
        """测试答案评估成功"""
        result = self.tools.execute("answer_evaluator", {"question_id": "q1", "user_answer": "A"})
        assert "correct" in result
        assert "score" in result
        assert "feedback" in result

    def test_get_execution_log(self):
        """测试获取执行日志"""
        self.tools.execute("knowledge_retriever", {"query": "test", "top_k": 1})
        log = self.tools.get_execution_log()
        assert len(log) > 0


class TestAgent:
    """智能体测试"""

    def setup_method(self):
        self.agent = StudyCoachAgent()

    def test_agent_init(self):
        """测试智能体初始化"""
        assert self.agent is not None
        assert self.agent.model_client is not None
        assert self.agent.tools is not None
        assert self.agent.guardrails is not None

    def test_get_available_tools(self):
        """测试获取可用工具"""
        tools = self.agent.get_available_tools()
        assert len(tools) >= 4
        tool_names = [t["name"] for t in tools]
        assert "study_plan_generator" in tool_names
        assert "question_generator" in tool_names
        assert "answer_evaluator" in tool_names
        assert "knowledge_retriever" in tool_names

    def test_get_tool_contract(self):
        """测试获取工具契约"""
        contract = self.agent.get_tool_contract("study_plan_generator")
        assert contract is not None
        assert "input_schema" in contract
        assert "output_schema" in contract
        assert "failure_modes" in contract
        assert "safety_boundary" in contract

    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.agent.get_stats()
        assert "model_stats" in stats
        assert "guardrail_stats" in stats
        assert "conversation_turns" in stats

    def test_reset(self):
        """测试重置"""
        self.agent.conversation_history = [{"role": "user", "content": "test"}]
        self.agent.reset()
        assert len(self.agent.conversation_history) == 0

    def test_chat_with_empty_input(self):
        """测试空输入被拒绝"""
        result = self.agent.chat("")
        assert result["status"] == "error"
        assert "empty_input" in result["error"]

    def test_chat_with_sensitive_info(self):
        """测试敏感信息被拒绝"""
        result = self.agent.chat("我的密码是password123")
        assert result["status"] == "error"


class TestWorkflow:
    """工作流测试"""

    def setup_method(self):
        self.agent = StudyCoachAgent()
        self.workflow = self.agent.workflow

    def test_workflow_init(self):
        """测试工作流初始化"""
        from src.workflow import Workflow
        wf = Workflow(self.agent)
        assert wf is not None
        assert wf.current_state.value == "idle"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])