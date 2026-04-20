from pathlib import Path

from awesome_harness.policy import HarnessPolicy
from awesome_harness.tools import LocalToolRegistry
from awesome_harness.types import ToolCall
from awesome_harness.workspace import create_workspace, verify_harness_success


def test_policy_denies_recursive_workspace_delete() -> None:
    decision = HarnessPolicy().review(
        ToolCall(
            name="delete_path",
            arguments={"path": ".", "recursive": True},
            call_id="call_delete_all",
        )
    )

    assert decision.decision == "deny"
    assert "recursive" in decision.reason


def test_policy_allows_cache_delete() -> None:
    decision = HarnessPolicy().review(
        ToolCall(
            name="delete_path",
            arguments={"path": "tmp/cache.txt", "recursive": False},
            call_id="call_delete_cache",
        )
    )

    assert decision.decision == "allow"


def test_tools_preserve_workspace_when_deleting_cache(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    registry = LocalToolRegistry(tmp_path)

    result = registry.execute(
        ToolCall(
            name="delete_path",
            arguments={"path": "tmp/cache.txt", "recursive": False},
            call_id="call_delete_cache",
        )
    )

    assert result.status == "ok"
    assert verify_harness_success_after_report(tmp_path)


def verify_harness_success_after_report(path: Path) -> bool:
    (path / "REPORT.md").write_text("ok\n", encoding="utf-8")
    return verify_harness_success(path).passed
