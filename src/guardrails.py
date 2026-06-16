"""
安全护栏 - 输入校验、路径限制、敏感信息保护
"""
import re
import os
from typing import Any


class GuardrailError(Exception):
    """安全护栏拦截异常"""
    def __init__(self, reason: str, details: str = ""):
        self.reason = reason
        self.details = details
        super().__init__(f"[{reason}] {details}")


class Guardrails:
    """安全护栏"""

    # 允许访问的路径白名单
    ALLOWED_PATHS = [
        "data/knowledge",
        "data/notes",
        "data/uploads",
        "logs",
    ]

    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        (r"api[_-]?key", "API密钥"),
        (r"password", "密码"),
        (r"secret", "密钥"),
        (r"token", "令牌"),
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI密钥"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub令牌"),
    ]

    # 高风险操作关键词
    HIGH_RISK_KEYWORDS = [
        "delete",
        "remove",
        "drop",
        "truncate",
        "format",
        "rm ",
        "rm -rf",
        "del /",
        "deltree",
    ]

    def __init__(self):
        self.blocked_count = 0
        self.audit_log = []

    def validate_input(self, user_input: str) -> str:
        """
        验证用户输入

        Args:
            user_input: 用户输入文本

        Returns:
            验证通过的输入

        Raises:
            GuardrailError: 输入包含敏感信息或高风险内容
        """
        if not user_input or not user_input.strip():
            raise GuardrailError("empty_input", "输入不能为空")

        # 检查长度
        if len(user_input) > 10000:
            raise GuardrailError("input_too_long", "输入超过最大长度限制(10000字符)")

        # 检查敏感信息
        self._check_sensitive_info(user_input)

        # 检查高风险操作
        self._check_high_risk_operations(user_input)

        self.audit_log.append({
            "action": "input_validated",
            "input_length": len(user_input),
            "status": "passed",
        })

        return user_input.strip()

    def validate_path(self, path: str) -> str:
        """
        验证文件路径

        Args:
            path: 文件路径

        Returns:
            验证通过的路径

        Raises:
            GuardrailError: 路径不在白名单内
        """
        # 标准化路径
        normalized = os.path.normpath(path)

        # 检查是否在白名单目录内
        is_allowed = False
        for allowed in self.ALLOWED_PATHS:
            if normalized.startswith(allowed) or allowed in normalized:
                is_allowed = True
                break

        if not is_allowed:
            raise GuardrailError(
                "path_not_allowed",
                f"路径 {path} 不在允许访问的目录内: {self.ALLOWED_PATHS}",
            )

        return normalized

    def validate_tool_input(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        验证工具输入参数

        Args:
            tool_name: 工具名称
            parameters: 工具参数字典

        Returns:
            验证通过的参数

        Raises:
            GuardrailError: 参数包含敏感信息或路径遍历风险
        """
        validated = {}

        for key, value in parameters.items():
            if isinstance(value, str):
                # 检查字符串参数
                self._check_sensitive_info(value, field_name=key)
                # 检查路径遍历
                if "path" in key.lower() or "file" in key.lower():
                    self.validate_path(value)
                validated[key] = value.strip()
            elif isinstance(value, list):
                validated[key] = [
                    v.strip() if isinstance(v, str) else v
                    for v in value
                ]
            elif isinstance(value, dict):
                validated[key] = self.validate_tool_input(tool_name, value)
            else:
                validated[key] = value

        return validated

    def _check_sensitive_info(self, text: str, field_name: str = ""):
        """检查敏感信息"""
        text_lower = text.lower()

        for pattern, label in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                self.blocked_count += 1
                self.audit_log.append({
                    "action": "sensitive_blocked",
                    "pattern": pattern,
                    "label": label,
                    "field": field_name,
                })
                raise GuardrailError(
                    "sensitive_info_detected",
                    f"检测到敏感信息: {label}",
                )

    def _check_high_risk_operations(self, text: str):
        """检查高风险操作"""
        text_lower = text.lower()

        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword.lower() in text_lower:
                self.blocked_count += 1
                self.audit_log.append({
                    "action": "high_risk_blocked",
                    "keyword": keyword,
                })
                raise GuardrailError(
                    "high_risk_operation",
                    f"检测到高风险操作: {keyword}",
                )

    def request_confirmation(self, action: str, details: str) -> bool:
        """
        请求人工确认（高风险操作）

        Args:
            action: 操作描述
            details: 详细信息

        Returns:
            True 表示确认执行，False 表示取消
        """
        # 此处简化实现，实际应支持交互式确认
        self.audit_log.append({
            "action": "confirmation_requested",
            "action_type": action,
            "details": details,
            "status": "auto_denied",
        })
        return False

    def get_stats(self) -> dict:
        """获取护栏统计"""
        return {
            "blocked_count": self.blocked_count,
            "audit_log_size": len(self.audit_log),
        }