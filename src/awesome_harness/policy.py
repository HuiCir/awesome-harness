from __future__ import annotations

from .types import PolicyDecision, ToolCall


class HarnessPolicy:
    def __init__(self) -> None:
        self.shell_prefix_allowlist = [
            ("pwd",),
            ("ls", "-la"),
            ("git", "status", "--short"),
        ]

    def review(self, call: ToolCall) -> PolicyDecision:
        if call.name == "delete_path":
            target = str(call.arguments.get("path", ""))
            recursive = bool(call.arguments.get("recursive", False))
            if target in {"", ".", "*", "/"} or recursive:
                return PolicyDecision(
                    "deny",
                    "broad or recursive delete requires explicit review",
                )
            if target != "tmp/cache.txt":
                return PolicyDecision(
                    "deny",
                    f"delete target not in cleanup allowlist: {target}",
                )

        if call.name == "run_shell":
            argv = call.arguments.get("argv")
            if not isinstance(argv, list) or not all(isinstance(part, str) for part in argv):
                return PolicyDecision("deny", "shell argv must be a list of strings")
            tuple_argv = tuple(argv)
            for prefix in self.shell_prefix_allowlist:
                if tuple_argv[: len(prefix)] == prefix:
                    return PolicyDecision("allow", "shell command matches allowlist")
            return PolicyDecision("deny", f"shell command not allowlisted: {argv!r}")

        return PolicyDecision("allow", "tool call satisfies local policy")
