# Harness Architecture

This repo separates four responsibilities that are often mixed together in simple agent demos.

## 1. Model

The model proposes the next step.

- In `ScriptedHarnessModel`, the proposal is deterministic and offline.
- In `OpenAIResponsesModel`, proposals come from the Responses API as `function_call` output items.

The model does not execute tools.

## 2. Scheduler / Policy

`HarnessPolicy.review()` decides whether a proposed tool call is allowed.

Examples:

- `delete_path({"path": ".", "recursive": true})` is denied.
- `delete_path({"path": "tmp/cache.txt", "recursive": false})` is allowed.
- `run_shell({"argv": ["git", "status", "--short"]})` is allowed.
- arbitrary shell commands are denied.

## 3. Tool Registry

`LocalToolRegistry` maps tool names to real local implementations:

- `list_tree`
- `read_file`
- `count_files`
- `delete_path`
- `write_file`
- `run_shell`

Each tool also exposes a JSON schema suitable for Responses API function calling.

## 4. Harness Loop

`HarnessAgent.run()` owns the loop:

1. Send user query and tool schemas to the model.
2. Receive typed tool calls.
3. Review each call through policy.
4. Execute allowed calls.
5. Return `function_call_output` items to the model.
6. Stop when the model returns an assistant message.

The result is not a smarter model. It is a model whose actions must pass through a runtime boundary.
