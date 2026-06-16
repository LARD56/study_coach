"""
模型客户端 - 支持 Ollama 本地模型和 OpenAI 兼容接口
"""
import os
import time
import json
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ModelClient:
    """统一模型客户端，支持 Ollama 和 OpenAI 兼容接口"""

    def __init__(self):
        self.provider = os.getenv("PROVIDER", "ollama")
        self.total_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0

    def _create_ollama_client(self) -> OpenAI:
        """创建 Ollama 客户端"""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OpenAI(base_url=base_url, api_key="ollama")

    def _create_openai_client(self) -> OpenAI:
        """创建 OpenAI 客户端"""
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return OpenAI(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> dict:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称 (可选)
            max_tokens: 最大输出词元数

        Returns:
            {"content": str, "model": str, "tokens": int, "cost": float, "latency_ms": int}
        """
        start_time = time.time()

        if self.provider == "ollama":
            client = self._create_ollama_client()
            model = model or os.getenv("OLLAMA_MODEL", "qwen2.5")
        else:
            client = self._create_openai_client()
            model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )

        latency_ms = int((time.time() - start_time) * 1000)
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0

        # 估算成本 (OpenAI GPT-4o-mini: $0.15/1M input, $0.6/1M output)
        cost = tokens * 0.0000015 if tokens > 0 else 0

        self.total_tokens += tokens
        self.total_cost += cost
        self.request_count += 1

        return {
            "content": content,
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "latency_ms": latency_ms,
        }

    def check_connection(self) -> dict:
        """检查模型连通性"""
        try:
            result = self.chat(
                messages=[{"role": "user", "content": "Hello, respond with OK"}],
                max_tokens=10,
            )
            return {
                "success": True,
                "model": result["model"],
                "latency_ms": result["latency_ms"],
                "tokens": result["tokens"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self) -> dict:
        """获取使用统计"""
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "request_count": self.request_count,
        }


if __name__ == "__main__":
    client = ModelClient()
    result = client.check_connection()
    print(json.dumps(result, indent=2, ensure_ascii=False))