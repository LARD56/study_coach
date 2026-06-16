"""
工具定义 - MCP 风格的协议化工具
"""
import json
import uuid
from typing import Any
from datetime import datetime


# ============================================================================
# 协议化工具契约定义
# ============================================================================

TOOL_CONTRACTS = {
    "study_plan_generator": {
        "name": "study_plan_generator",
        "description": "根据用户目标和日期生成个性化学习计划",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "学习主题"},
                "days": {"type": "integer", "description": "计划天数(1-30)", "minimum": 1, "maximum": 30},
                "daily_hours": {"type": "number", "description": "每天学习时长(0.5-8)", "minimum": 0.5, "maximum": 8},
            },
            "required": ["topic", "days"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phase": {"type": "string"},
                            "days": {"type": "integer"},
                            "goals": {"type": "array", "items": {"type": "string"}},
                            "activities": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "total_hours": {"type": "number"},
            },
        },
        "failure_modes": {
            "validation_error": "topic为空或days超出范围(1-30)",
            "knowledge_gap": "主题过于冷门，无法生成计划",
        },
        "safety_boundary": "仅读取 data/knowledge 目录，不访问其他路径",
    },
    "question_generator": {
        "name": "question_generator",
        "description": "根据学习主题生成练习题",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "学习主题"},
                "count": {"type": "integer", "description": "题目数量(1-10)", "minimum": 1, "maximum": 10},
                "difficulty": {"type": "string", "description": "难度: easy/medium/hard", "enum": ["easy", "medium", "hard"]},
            },
            "required": ["topic", "count"],
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
        },
        "failure_modes": {
            "validation_error": "topic为空或count超出范围",
            "insufficient_knowledge": "知识库中该主题资料不足",
        },
        "safety_boundary": "仅基于已有知识库内容生成，不访问外部网络",
    },
    "answer_evaluator": {
        "name": "answer_evaluator",
        "description": "评估用户答案并给出反馈",
        "input_schema": {
            "type": "object",
            "properties": {
                "question_id": {"type": "string", "description": "题目ID"},
                "user_answer": {"type": "string", "description": "用户答案"},
            },
            "required": ["question_id", "user_answer"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "correct": {"type": "boolean"},
                "score": {"type": "number", "description": "得分 0-100"},
                "feedback": {"type": "string"},
                "suggestions": {"type": "array", "items": {"type": "string"}},
            },
        },
        "failure_modes": {
            "validation_error": "参数为空或格式错误",
            "question_not_found": "题目ID不存在",
        },
        "safety_boundary": "仅评估答案正确性，不收集或存储敏感信息",
    },
    "knowledge_retriever": {
        "name": "knowledge_retriever",
        "description": "从本地知识库检索相关内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索查询"},
                "top_k": {"type": "integer", "description": "返回结果数量(1-5)", "minimum": 1, "maximum": 5},
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "snippet": {"type": "string"},
                            "source": {"type": "string"},
                        },
                    },
                },
            },
        },
        "failure_modes": {
            "validation_error": "query为空",
            "knowledge_base_missing": "知识库不存在或无法访问",
        },
        "safety_boundary": "仅读取项目 data/knowledge 目录，不访问其他本地路径",
    },
}


# ============================================================================
# 工具实现
# ============================================================================

class ToolExecutionError(Exception):
    """工具执行错误"""
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(f"[{error_type}] {message}")


class KnowledgeBase:
    """本地知识库模拟"""

    def __init__(self, base_path: str = "data/knowledge"):
        self.base_path = base_path
        self.knowledge = {
            "python基础": [
                "Python是一种高级编程语言...",
                "变量不需要声明类型...",
                "列表是可变的有序序列...",
            ],
            "机器学习": [
                "监督学习使用标记数据...",
                "神经网络由多层组成...",
                "梯度下降是优化的基本方法...",
            ],
        }

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """检索知识"""
        results = []
        query_lower = query.lower()
        for topic, contents in self.knowledge.items():
            if query_lower in topic.lower():
                for content in contents[:top_k]:
                    results.append({
                        "title": topic,
                        "snippet": content,
                        "source": f"{self.base_path}/{topic}.md",
                    })
        return results[:top_k]


class Tools:
    """工具执行器"""

    def __init__(self, model_client):
        self.model_client = model_client
        self.knowledge_base = KnowledgeBase()
        self.execution_log = []

    def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        执行工具

        Args:
            tool_name: 工具名称
            parameters: 输入参数

        Returns:
            工具执行结果
        """
        if tool_name not in TOOL_CONTRACTS:
            raise ToolExecutionError("tool_not_found", f"工具 {tool_name} 不存在")

        contract = TOOL_CONTRACTS[tool_name]
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "input": parameters,
            "status": "pending",
        }

        try:
            # 根据工具名称执行对应逻辑
            if tool_name == "study_plan_generator":
                result = self._generate_study_plan(parameters)
            elif tool_name == "question_generator":
                result = self._generate_questions(parameters)
            elif tool_name == "answer_evaluator":
                result = self._evaluate_answer(parameters)
            elif tool_name == "knowledge_retriever":
                result = self._retrieve_knowledge(parameters)
            else:
                raise ToolExecutionError("tool_not_found", f"工具 {tool_name} 未实现")

            log_entry["status"] = "success"
            log_entry["output"] = result
            self.execution_log.append(log_entry)
            return result

        except ToolExecutionError:
            log_entry["status"] = "failed"
            self.execution_log.append(log_entry)
            raise
        except Exception as e:
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            self.execution_log.append(log_entry)
            raise ToolExecutionError("internal_error", str(e))

    def _generate_study_plan(self, params: dict) -> dict:
        """生成学习计划"""
        topic = params.get("topic", "").strip()
        days = params.get("days", 7)
        daily_hours = params.get("daily_hours", 2.0)

        if not topic:
            raise ToolExecutionError("validation_error", "topic 不能为空")
        if not 1 <= days <= 30:
            raise ToolExecutionError("validation_error", "days 必须在 1-30 范围内")

        prompt = f"""为学习主题"{topic}"生成一个{days}天的学习计划，每天学习{daily_hours}小时。
返回JSON格式：
{{
  "plan_id": "唯一ID",
  "phases": [
    {{"phase": "阶段名", "days": 天数, "goals": ["目标1", "目标2"], "activities": ["活动1", "活动2"]}}
  ],
  "total_hours": 总小时数
}}"""

        response = self.model_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )

        try:
            plan = json.loads(response["content"])
            plan["plan_id"] = str(uuid.uuid4())[:8]
            plan["total_hours"] = days * daily_hours
            return plan
        except json.JSONDecodeError:
            # 返回模拟计划
            return {
                "plan_id": str(uuid.uuid4())[:8],
                "phases": [
                    {
                        "phase": "基础入门",
                        "days": days // 3 or 1,
                        "goals": [f"了解{topic}基本概念"],
                        "activities": ["阅读资料", "观看教程"],
                    },
                    {
                        "phase": "进阶学习",
                        "days": days // 3 or 1,
                        "goals": [f"掌握{topic}核心技能"],
                        "activities": ["动手实践", "完成练习"],
                    },
                    {
                        "phase": "项目实战",
                        "days": days - 2 * (days // 3 or 1),
                        "goals": [f"能够独立完成{topic}相关项目"],
                        "activities": ["项目开发", "总结复盘"],
                    },
                ],
                "total_hours": days * daily_hours,
            }

    def _generate_questions(self, params: dict) -> dict:
        """生成练习题"""
        topic = params.get("topic", "").strip()
        count = params.get("count", 5)
        difficulty = params.get("difficulty", "medium")

        if not topic:
            raise ToolExecutionError("validation_error", "topic 不能为空")
        if not 1 <= count <= 10:
            raise ToolExecutionError("validation_error", "count 必须在 1-10 范围内")

        # 检索相关知识
        knowledge = self.knowledge_base.search(topic, top_k=3)

        prompt = f"""基于"{topic}"生成{count}道{difficulty}难度练习题。
相关知识：{knowledge}

返回JSON数组格式：
[
  {{"id": "q1", "question": "题目", "options": ["A", "B", "C", "D"], "answer": "正确答案", "explanation": "解析"}}
]"""

        response = self.model_client.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )

        try:
            questions = json.loads(response["content"])
            return questions
        except json.JSONDecodeError:
            # 返回模拟题目
            return [
                {
                    "id": f"q{i+1}",
                    "question": f"关于{topic}的第{i+1}题",
                    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
                    "answer": "A",
                    "explanation": f"这是{topic}的基础知识",
                }
                for i in range(count)
            ]

    def _evaluate_answer(self, params: dict) -> dict:
        """评估答案"""
        question_id = params.get("question_id", "").strip()
        user_answer = params.get("user_answer", "").strip()

        if not question_id or not user_answer:
            raise ToolExecutionError("validation_error", "参数不能为空")

        # 模拟评估逻辑
        is_correct = len(user_answer) > 0  # 简化判断

        return {
            "correct": is_correct,
            "score": 100 if is_correct else 0,
            "feedback": "回答正确！" if is_correct else "回答错误，请查看解析",
            "suggestions": ["多做练习", "查看相关知识点"] if not is_correct else ["继续保持"],
        }

    def _retrieve_knowledge(self, params: dict) -> dict:
        """检索知识"""
        query = params.get("query", "").strip()
        top_k = params.get("top_k", 3)

        if not query:
            raise ToolExecutionError("validation_error", "query 不能为空")
        if not 1 <= top_k <= 5:
            raise ToolExecutionError("validation_error", "top_k 必须在 1-5 范围内")

        items = self.knowledge_base.search(query, top_k)
        return {"items": items}

    def get_execution_log(self) -> list[dict]:
        """获取执行日志"""
        return self.execution_log


def list_tools() -> list[dict]:
    """列出所有可用工具（带契约）"""
    return [
        {
            "name": contract["name"],
            "description": contract["description"],
            "input_schema": contract["input_schema"],
            "output_schema": contract["output_schema"],
            "failure_modes": contract["failure_modes"],
            "safety_boundary": contract["safety_boundary"],
        }
        for contract in TOOL_CONTRACTS.values()
    ]