from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str


@dataclass(frozen=True)
class AssistantMessage:
    text: str


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    status: Literal["ok", "denied", "error"]
    output: str


@dataclass(frozen=True)
class ModelStep:
    response_id: str | None
    tool_calls: list[ToolCall]
    assistant_message: AssistantMessage | None


@dataclass(frozen=True)
class PolicyDecision:
    decision: Literal["allow", "deny"]
    reason: str
