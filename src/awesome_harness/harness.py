from __future__ import annotations

from pathlib import Path
import json
import subprocess
from typing import Any

from .models import ConventionalShellModel, ModelClient
from .policy import HarnessPolicy
from .tools import LocalToolRegistry
from .types import AssistantMessage, ToolCall, ToolResult
from .workspace import TASK_QUERY


INSTRUCTIONS = """
You are a careful coding agent operating through local tools.

Task requirements:
- Inspect the workspace.
- Read README.md.
- Count Python files.
- Clean only temporary cache.
- Write REPORT.md.

Important:
- Prefer typed tools over shell.
- If a delete operation is denied, recover by inspecting the allowed cache path
  and deleting only tmp/cache.txt.
- Do not claim success until REPORT.md is written.
""".strip()


class Trace:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def emit(self, line: str) -> None:
        print(line)
        self.lines.append(line)


class ConventionalShellAgent:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.model = ConventionalShellModel()
        self.history: list[dict[str, str]] = []

    def run(self, trace: Trace) -> AssistantMessage:
        trace.emit("\n=== Conventional shell-agent ===")
        self.history.append({"role": "user", "content": TASK_QUERY})
        trace.emit(f"[QUERY] {TASK_QUERY}")

        while True:
            output = self.model.sample()
            if isinstance(output, AssistantMessage):
                self.history.append({"role": "assistant", "content": output.text})
                trace.emit(f"[ASSISTANT] {output.text}")
                return output

            trace.emit(f"[MODEL] shell: {output}")
            completed = subprocess.run(
                output,
                cwd=self.workspace,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            observed = (completed.stdout or completed.stderr).strip()
            if not observed:
                observed = f"<exit {completed.returncode}; no output>"
            self.history.append({"role": "tool", "content": observed})
            trace.emit(f"[EXECUTOR] exit={completed.returncode} output={observed!r}")


class HarnessAgent:
    def __init__(
        self,
        workspace: Path,
        model: ModelClient,
        policy: HarnessPolicy | None = None,
    ) -> None:
        self.workspace = workspace
        self.model = model
        self.policy = policy or HarnessPolicy()
        self.tools = LocalToolRegistry(workspace)
        self.previous_response_id: str | None = None
        self.history: list[dict[str, Any]] = []

    def run(self, trace: Trace) -> AssistantMessage:
        trace.emit("\n=== Codex-style harness-agent ===")
        input_items: list[dict[str, Any]] = [
            {"role": "user", "content": TASK_QUERY},
        ]
        self.history.append({"type": "message", "role": "user", "content": TASK_QUERY})
        trace.emit(f"[QUERY] {TASK_QUERY}")

        while True:
            step = self.model.respond(
                input_items=input_items,
                tools=self.tools.schemas(),
                previous_response_id=self.previous_response_id,
                instructions=INSTRUCTIONS,
            )
            self.previous_response_id = step.response_id

            if step.assistant_message is not None:
                self.history.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": step.assistant_message.text,
                    }
                )
                trace.emit(f"[ASSISTANT] {step.assistant_message.text}")
                return step.assistant_message

            input_items = []
            for call in step.tool_calls:
                trace.emit(f"[MODEL] tool_call: {call.name} {call.arguments}")
                self.history.append(
                    {
                        "type": "function_call",
                        "name": call.name,
                        "arguments": call.arguments,
                        "call_id": call.call_id,
                    }
                )
                result = self.schedule_and_execute(call, trace)
                self.history.append(
                    {
                        "type": "function_call_output",
                        "call_id": result.call_id,
                        "status": result.status,
                        "output": result.output,
                    }
                )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": result.call_id,
                        "output": json.dumps(
                            {"status": result.status, "output": result.output},
                            ensure_ascii=False,
                        ),
                    }
                )

    def schedule_and_execute(self, call: ToolCall, trace: Trace) -> ToolResult:
        decision = self.policy.review(call)
        trace.emit(f"[SCHEDULER] {decision.decision}: {decision.reason}")
        if decision.decision == "deny":
            result = ToolResult(call.call_id, "denied", decision.reason)
        else:
            result = self.tools.execute(call)
        trace.emit(f"[EXECUTOR] {result.status}: {result.output!r}")
        return result
