# StudyCoach AI - 学习教练智能体

基于 AI 智能体的个人学习教练产品，支持学习计划生成、题目练习、错题分析和自适应学习。

## 功能特性

- **学习计划生成**: 根据目标和时间生成个性化学习计划
- **题目生成与练习**: 自动生成多种题型练习题
- **智能判分**: 评估答案并提供详细反馈
- **知识检索**: 基于本地知识库进行问答
- **自适应调整**: 根据学习情况动态调整计划

## 技术架构

- **模型接入**: Ollama 本地模型 / OpenAI 兼容接口
- **智能体框架**: 目标-计划-验证工作流
- **协议化工具**: MCP 风格工具契约
- **安全护栏**: 输入校验、路径限制、敏感信息保护
- **词元控制**: 用量统计、成本日志

## 环境配置

### 方式一: Conda 环境

```bash
# 创建环境
conda env create -f environment.yml
conda activate study-coach

# 安装依赖 (如使用 pip)
pip install -r requirements.txt

# 复制环境变量配置
copy .env.example .env
# 编辑 .env 填入您的配置
```

### 方式二: Docker

```bash
# 构建镜像
docker build -t study-coach .

# 运行容器
docker run --rm -it study-coach python main.py --chat
```

## 使用方法

### 检查模型连通性

```bash
python main.py --check-model
```

### 处理学习目标

```bash
python main.py --goal "我想用三周时间学习机器学习基础"
```

### 交互式对话

```bash
python main.py --chat
```

### 详细输出模式

```bash
python main.py --goal "学习Python基础" --verbose
```

## 目录结构

```
study_coach/
├── src/
│   ├── agent.py          # 智能体主逻辑
│   ├── model_client.py   # 模型客户端
│   ├── tools.py         # 工具定义
│   ├── guardrails.py    # 安全护栏
│   └── workflow.py      # 工作流
├── prompts/
│   └── agent_instructions.md  # 智能体指令
├── tests/
│   └── test_agent.py    # 自动化测试
├── docs/
│   └── architecture.md  # 架构文档
├── .env.example         # 环境变量示例
├── environment.yml      # Conda配置
├── requirements.txt     # Python依赖
├── Dockerfile           # Docker配置
└── main.py              # 入口文件
```

## MCP 风格工具契约

项目包含 4 个协议化工具:

| 工具 | 用途 | 输入 | 输出 |
|-----|------|-----|------|
| study_plan_generator | 生成学习计划 | topic, days, daily_hours | plan_id, phases, total_hours |
| question_generator | 生成练习题 | topic, count, difficulty | 题目数组 |
| answer_evaluator | 评估答案 | question_id, user_answer | correct, score, feedback |
| knowledge_retriever | 检索知识 | query, top_k | items 数组 |

详细契约请参考 `docs/architecture.md`

## 测试

```bash
# 运行所有测试
python -m pytest tests/test_agent.py -v

# 快速测试
python -m pytest -q
```

## 环境变量配置

```env
# 模型提供商: ollama 或 openai
PROVIDER=ollama

# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:35b-a3b

# OpenAI 配置 (二选一)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=qwen3.5:35b-a3b

# 词元预算控制
MAX_TOKENS_PER_REQUEST=2048
MAX_TOTAL_TOKENS=100000
DAILY_BUDGET_USD=1.0
```

## 课程能力对应

| 能力 | 实现 |
|-----|------|
| 版本管理 | Git 仓库和提交历史 |
| 测试 | 10+ 自动化测试用例 |
| 真实模型 | ModelClient 连通性测试 |
| 智能体 | Goal-Plan-Verify 工作流 |
| 协议化工具 | 4 个 MCP 风格工具契约 |
| 检索增强 | KnowledgeBase 本地检索 |
| 指令管理 | prompts/agent_instructions.md |
| 安全护栏 | 输入校验、路径限制、敏感检测 |
| 词元成本 | 用量统计、成本日志 |
| 工作流 | Workflow 状态机实现 |
| 交互入口 | CLI、模型检测、目标执行 |

## 许可证

MIT License