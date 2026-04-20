from __future__ import annotations

import argparse
from pathlib import Path
import os

from .harness import ConventionalShellAgent, HarnessAgent, Trace
from .models import OpenAIResponsesModel, ScriptedHarnessModel
from .workspace import (
    create_workspace,
    make_temp_workspace,
    tree,
    verify_conventional_failure,
    verify_harness_success,
)


def run_conventional() -> None:
    with make_temp_workspace() as temp_dir:
        workspace = Path(temp_dir)
        create_workspace(workspace)
        trace = Trace()
        ConventionalShellAgent(workspace).run(trace)
        print("[WORKSPACE TREE AFTER CONVENTIONAL]")
        print(tree(workspace))
        report = workspace / "REPORT.md"
        print("[REPORT]")
        print(report.read_text(encoding="utf-8").strip() if report.exists() else "<missing>")
        verification = verify_conventional_failure(workspace)
        print(f"[VERIFY] {verification.name}: {'PASS' if verification.passed else 'FAIL'}")


def run_harness_simulated() -> None:
    with make_temp_workspace() as temp_dir:
        workspace = Path(temp_dir)
        create_workspace(workspace)
        trace = Trace()
        HarnessAgent(workspace, ScriptedHarnessModel()).run(trace)
        print("[WORKSPACE TREE AFTER HARNESS]")
        print(tree(workspace))
        print("[REPORT]")
        print((workspace / "REPORT.md").read_text(encoding="utf-8").strip())
        verification = verify_harness_success(workspace)
        print(f"[VERIFY] {verification.name}: {'PASS' if verification.passed else 'FAIL'}")


def run_harness_openai(model: str | None) -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for openai mode.")

    with make_temp_workspace() as temp_dir:
        workspace = Path(temp_dir)
        create_workspace(workspace)
        trace = Trace()
        HarnessAgent(workspace, OpenAIResponsesModel(model=model)).run(trace)
        print("[WORKSPACE TREE AFTER OPENAI HARNESS]")
        print(tree(workspace))
        report = workspace / "REPORT.md"
        print("[REPORT]")
        print(report.read_text(encoding="utf-8").strip() if report.exists() else "<missing>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run awesome-harness demos.")
    parser.add_argument(
        "mode",
        choices=["compare", "simulated", "openai", "conventional"],
        help="Demo mode.",
    )
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL"))
    args = parser.parse_args()

    if args.mode == "compare":
        run_conventional()
        run_harness_simulated()
    elif args.mode == "conventional":
        run_conventional()
    elif args.mode == "simulated":
        run_harness_simulated()
    elif args.mode == "openai":
        run_harness_openai(args.model)


if __name__ == "__main__":
    main()
