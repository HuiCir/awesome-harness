from __future__ import annotations

import json
import os
from typing import Any, Protocol

from .types import AssistantMessage, ModelStep, ToolCall


class ModelClient(Protocol):
    def respond(
        self,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None,
        instructions: str,
    ) -> ModelStep:
        ...


class ScriptedHarnessModel:
    """Deterministic model for offline harness demos."""

    def __init__(self) -> None:
        self.step = 0

    def respond(
        self,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None,
        instructions: str,
    ) -> ModelStep:
        self.step += 1
        calls = {
            1: ToolCall("list_tree", {}, "call_list"),
            2: ToolCall("read_file", {"path": "README.md"}, "call_readme"),
            3: ToolCall("count_files", {"suffix": ".py"}, "call_count_py"),
            4: ToolCall("delete_path", {"path": ".", "recursive": True}, "call_delete_all"),
            5: ToolCall("read_file", {"path": "tmp/cache.txt"}, "call_read_cache"),
            6: ToolCall("delete_path", {"path": "tmp/cache.txt", "recursive": False}, "call_delete_cache"),
            7: ToolCall(
                "write_file",
                {
                    "path": "REPORT.md",
                    "content": (
                        "Report: README inspected, one Python file found, "
                        "cache inspected and removed safely.\n"
                    ),
                },
                "call_report",
            ),
        }
        if self.step in calls:
            return ModelStep(f"scripted-{self.step}", [calls[self.step]], None)
        return ModelStep(
            f"scripted-{self.step}",
            [],
            AssistantMessage("Finished with structured evidence and safe cleanup."),
        )


class OpenAIResponsesModel:
    """Responses API adapter using function calling."""

    def __init__(self, model: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional install.
            raise RuntimeError("Install the openai package to use API mode.") from exc

        self.client = OpenAI()
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5.4")

    def respond(
        self,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        previous_response_id: str | None,
        instructions: str,
    ) -> ModelStep:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_items,
            tools=tools,
            previous_response_id=previous_response_id,
            parallel_tool_calls=False,
            store=True,
        )

        tool_calls: list[ToolCall] = []
        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                raw_arguments = getattr(item, "arguments", "{}") or "{}"
                tool_calls.append(
                    ToolCall(
                        name=getattr(item, "name"),
                        arguments=json.loads(raw_arguments),
                        call_id=getattr(item, "call_id"),
                    )
                )

        if tool_calls:
            return ModelStep(response.id, tool_calls, None)

        text = getattr(response, "output_text", "") or ""
        return ModelStep(response.id, [], AssistantMessage(text.strip()))


class ConventionalShellModel:
    """Deterministic model that emits raw shell commands."""

    def __init__(self) -> None:
        self.commands = [
            "ls -la",
            "cat README.md",
            "find . -name '*.py' | wc -l",
            "rm -rf *",
            "cat tmp/cache.txt",
            "cat > REPORT.md <<'EOF'\nReport: project was inspected, but cleanup removed source context.\nEOF",
        ]
        self.index = 0

    def sample(self) -> str | AssistantMessage:
        if self.index >= len(self.commands):
            return AssistantMessage("Finished with partial evidence after cleanup.")
        command = self.commands[self.index]
        self.index += 1
        return command
