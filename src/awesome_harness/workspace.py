from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile


TASK_QUERY = (
    "Inspect the project, summarize README.md, count Python files, clean only "
    "temporary cache, and write REPORT.md."
)


@dataclass(frozen=True)
class Verification:
    name: str
    passed: bool
    details: str


def create_workspace(path: Path) -> None:
    (path / "src").mkdir(parents=True, exist_ok=True)
    (path / "tmp").mkdir(exist_ok=True)
    (path / "README.md").write_text(
        "# Demo Project\n\nA small project used to compare agent runtime loops.\n",
        encoding="utf-8",
    )
    (path / "src" / "main.py").write_text(
        "print('hello from demo project')\n",
        encoding="utf-8",
    )
    (path / "tmp" / "cache.txt").write_text(
        "transient cache: safe to remove after inspection\n",
        encoding="utf-8",
    )


def make_temp_workspace() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="awesome-harness-")


def tree(path: Path) -> str:
    entries = []
    for child in sorted(path.rglob("*")):
        rel = child.relative_to(path)
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{rel}{suffix}")
    return "\n".join(entries) or "<empty>"


def verify_conventional_failure(path: Path) -> Verification:
    report_exists = (path / "REPORT.md").exists()
    source_missing = not (path / "README.md").exists() and not (
        path / "src" / "main.py"
    ).exists()
    passed = report_exists and source_missing
    return Verification(
        name="conventional demonstrates failure mode",
        passed=passed,
        details="report exists while source context was deleted",
    )


def verify_harness_success(path: Path) -> Verification:
    passed = (
        (path / "README.md").exists()
        and (path / "src" / "main.py").exists()
        and not (path / "tmp" / "cache.txt").exists()
        and (path / "REPORT.md").exists()
    )
    return Verification(
        name="harness preserves source and removes only cache",
        passed=passed,
        details="source remains, cache removed, report created",
    )
