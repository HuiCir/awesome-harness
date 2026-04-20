from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import subprocess
from typing import Any, Callable

from .types import ToolCall, ToolResult
from .workspace import tree


ToolHandler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def response_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "strict": True,
            "parameters": self.parameters,
        }


class LocalToolRegistry:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self._tools = {
            "list_tree": ToolSpec(
                name="list_tree",
                description="List files under the workspace as relative paths.",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                handler=self._list_tree,
            ),
            "read_file": ToolSpec(
                name="read_file",
                description="Read a UTF-8 text file from the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path inside the workspace.",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                handler=self._read_file,
            ),
            "count_files": ToolSpec(
                name="count_files",
                description="Count files with a suffix under the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "suffix": {
                            "type": "string",
                            "description": "File suffix such as .py or .md.",
                        }
                    },
                    "required": ["suffix"],
                    "additionalProperties": False,
                },
                handler=self._count_files,
            ),
            "delete_path": ToolSpec(
                name="delete_path",
                description="Delete an allowlisted path inside the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to delete.",
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Whether deletion is recursive.",
                        },
                    },
                    "required": ["path", "recursive"],
                    "additionalProperties": False,
                },
                handler=self._delete_path,
            ),
            "write_file": ToolSpec(
                name="write_file",
                description="Write a UTF-8 text file inside the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path to write.",
                        },
                        "content": {
                            "type": "string",
                            "description": "File content.",
                        },
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
                handler=self._write_file,
            ),
            "run_shell": ToolSpec(
                name="run_shell",
                description="Run a small allowlisted argv command in the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "argv": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command argv list, not a shell string.",
                        }
                    },
                    "required": ["argv"],
                    "additionalProperties": False,
                },
                handler=self._run_shell,
            ),
        }

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.response_schema() for tool in self._tools.values()]

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(call.call_id, "error", f"unknown tool: {call.name}")
        try:
            return ToolResult(call.call_id, "ok", tool.handler(call.arguments))
        except Exception as exc:  # noqa: BLE001 - tool failures are returned to the model.
            return ToolResult(call.call_id, "error", str(exc))

    def safe_path(self, relative_path: str) -> Path:
        target = (self.workspace / relative_path).resolve()
        if self.workspace != target and self.workspace not in target.parents:
            raise ValueError(f"path escapes workspace: {relative_path}")
        return target

    def _list_tree(self, arguments: dict[str, Any]) -> str:
        return tree(self.workspace)

    def _read_file(self, arguments: dict[str, Any]) -> str:
        target = self.safe_path(str(arguments["path"]))
        if not target.is_file():
            raise FileNotFoundError(str(target.relative_to(self.workspace)))
        return target.read_text(encoding="utf-8").strip()

    def _count_files(self, arguments: dict[str, Any]) -> str:
        suffix = str(arguments["suffix"])
        count = sum(1 for path in self.workspace.rglob(f"*{suffix}") if path.is_file())
        return str(count)

    def _delete_path(self, arguments: dict[str, Any]) -> str:
        target = self.safe_path(str(arguments["path"]))
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return f"deleted {target.relative_to(self.workspace)}"

    def _write_file(self, arguments: dict[str, Any]) -> str:
        target = self.safe_path(str(arguments["path"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(arguments["content"]), encoding="utf-8")
        return f"wrote {target.relative_to(self.workspace)}"

    def _run_shell(self, arguments: dict[str, Any]) -> str:
        argv = arguments["argv"]
        if not isinstance(argv, list) or not all(isinstance(part, str) for part in argv):
            raise ValueError("argv must be a list of strings")
        completed = subprocess.run(
            argv,
            cwd=self.workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        payload = {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        return json.dumps(payload, ensure_ascii=False)
