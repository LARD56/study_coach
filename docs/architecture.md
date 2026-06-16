# StudyCoach AI 学习教练智能体

```python
from src.agent import StudyCoachAgent

# 初始化智能体
agent = StudyCoachAgent()

# 检查模型连通性
result = agent.model_client.check_connection()
print(result)

# 处理学习目标
result = agent.process_goal("我想用两周时间学习Python数据分析")
print(result)

# 对话模式
result = agent.chat("如何学习机器学习？")
print(result['response'])
```

## 核心模块

### Agent (agent.py)
智能体主模块，协调模型、工具和护栏。

### ModelClient (model_client.py)
统一模型客户端，支持 Ollama 和 OpenAI。

### Tools (tools.py)
协议化工具集，包含 MCP 风格契约定义。

### Guardrails (guardrails.py)
安全护栏，包括输入验证、路径限制、敏感信息检测。

### Workflow (workflow.py)
目标-计划-验证工作流引擎。

## 工具契约示例

```json
{
  "name": "study_plan_generator",
  "description": "根据用户目标和日期生成个性化学习计划",
  "input_schema": {
    "type": "object",
    "properties": {
      "topic": {"type": "string"},
      "days": {"type": "integer", "minimum": 1, "maximum": 30},
      "daily_hours": {"type": "number", "minimum": 0.5, "maximum": 8}
    },
    "required": ["topic", "days"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "plan_id": {"type": "string"},
      "phases": {"type": "array"},
      "total_hours": {"type": "number"}
    }
  },
  "failure_modes": {
    "validation_error": "topic为空或days超出范围",
    "knowledge_gap": "主题过于冷门"
  },
  "safety_boundary": "仅读取 data/knowledge 目录"
}
```