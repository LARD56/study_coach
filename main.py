"""
StudyCoach AI - 学习教练智能体
"""
import argparse
import json
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent import StudyCoachAgent


def check_model(args):
    """检查模型连通性"""
    agent = StudyCoachAgent()
    result = agent.model_client.check_connection()

    print("=" * 50)
    print("模型连通性测试")
    print("=" * 50)
    print(f"状态: {'成功' if result['success'] else '失败'}")
    if result["success"]:
        print(f"模型: {result['model']}")
        print(f"延迟: {result['latency_ms']}ms")
        print(f"词元数: {result['tokens']}")
    else:
        print(f"错误: {result.get('error', '未知错误')}")
    print("=" * 50)

    return 0 if result["success"] else 1


def run_goal(args):
    """运行目标"""
    agent = StudyCoachAgent()

    print(f"正在处理目标: {args.goal}")
    print("-" * 50)

    result = agent.process_goal(args.goal)

    print("执行结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.verbose:
        print("\n工作流日志:")
        for log in agent.get_workflow_log():
            print(f"  [{log['state']}] {log['action']}")

        print("\n统计信息:")
        print(json.dumps(agent.get_stats(), indent=2))

    return 0 if result.get("status") != "error" else 1


def chat_mode(args):
    """交互式对话模式"""
    agent = StudyCoachAgent()

    print("=" * 50)
    print("StudyCoach AI 学习教练 - 对话模式")
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'tools' 查看可用工具")
    print("输入 'stats' 查看统计信息")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n用户> ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("再见!")
                break

            if not user_input:
                continue

            if user_input.lower() == "tools":
                print("\n可用工具:")
                for tool in agent.get_available_tools():
                    print(f"  - {tool['name']}: {tool['description']}")
                continue

            if user_input.lower() == "stats":
                print("\n统计信息:")
                print(json.dumps(agent.get_stats(), indent=2))
                continue

            result = agent.chat(user_input)

            print(f"\n助手> {result.get('response', result.get('error', '未知错误'))}")

            if result.get("tokens"):
                print(f"    [词元: {result['tokens']}, 延迟: {result['latency_ms']}ms]")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="StudyCoach AI 学习教练智能体")
    parser.add_argument("--check-model", action="store_true", help="检查模型连通性")
    parser.add_argument("--goal", type=str, help="处理学习目标")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--chat", action="store_true", help="交互式对话模式")

    args = parser.parse_args()

    if args.check_model:
        return check_model(args)
    elif args.goal:
        return run_goal(args)
    elif args.chat:
        return chat_mode(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())