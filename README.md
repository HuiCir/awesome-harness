# awesome-harness

`awesome-harness` 是一个教学 repo，用同一个任务展示两种 agent 运行时：

1. **常规 shell-agent**：模型输出 shell 字符串，runtime 直接执行。
2. **Codex-style harness-agent**：模型输出 typed tool call，harness 负责调度、审批、执行、记录和结果回灌。

这个 repo 的目标不是复刻 Codex，而是把 Codex-style harness 的关键工程思想做成可运行 demo。

## 官方 API 对齐

真实 OpenAI 接入使用 Responses API 的 function calling：

- Responses API 支持工具调用、状态化多轮和 `previous_response_id`。
- Function calling 响应会返回 `function_call` item，包含 `name`、`arguments` 和后续提交结果所需的 `call_id`。
- 工具结果通过 `function_call_output` 回传给模型。
- 对本地 shell 这类工具，API 只返回指令，真正是否执行由你的 runtime 控制。

参考官方文档：

- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/docs/guides/responses
- https://developers.openai.com/api/docs/guides/conversation-state
- https://developers.openai.com/api/docs/guides/tools-local-shell

## 安装

```bash
cd /root/awesome-harness
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

离线模拟不需要 OpenAI key。真实 API 模式需要：

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-5.4
```

`OPENAI_MODEL` 可以换成你账户可用的任意 Responses API 模型。

## 快速运行

### 1. 常规设计 vs harness 设计

```bash
python3 -m awesome_harness.demo compare
```

你会看到常规 shell-agent 把 cleanup 误扩展成 `rm -rf *`，导致临时项目被删到只剩报告；harness-agent 会拒绝 broad recursive delete，只允许删除 `tmp/cache.txt`。

### 2. 只运行离线 harness

```bash
python3 -m awesome_harness.demo simulated
```

这个模式使用 scripted model，不调用 API，适合教学和测试 harness 流程。

### 3. 接入真实 OpenAI Responses API

```bash
python3 -m awesome_harness.demo openai --model "${OPENAI_MODEL:-gpt-5.4}"
```

这个模式会把真实工具 schema 提供给模型。模型如果发起 function call，harness 会：

1. 解析 tool call。
2. 调用 scheduler 做 policy review。
3. 执行允许的本地工具。
4. 把 `function_call_output` 通过 `previous_response_id` 回传给模型。
5. 重复直到模型返回最终 assistant message。

## 任务

三个模式使用同一个任务：

```text
Inspect the project, summarize README.md, count Python files,
clean only temporary cache, and write REPORT.md.
```

demo 会在临时目录创建这个项目：

```text
README.md
src/main.py
tmp/cache.txt
```

## 目录

```text
docs/
  architecture.md  design breakdown
src/awesome_harness/
  demo.py          CLI entrypoint
  harness.py       conventional agent and Codex-style harness loop
  models.py        scripted model and OpenAI Responses model adapter
  policy.py        tool scheduling / approval policy
  tools.py         real local tools and JSON schemas
  types.py         shared dataclasses
  workspace.py     demo workspace creation and verification
tests/
  test_policy_and_tools.py
```

## 关键设计点

- **模型不直接操作现实**：模型只产出 shell string 或 typed tool call。
- **常规 runtime 缺治理入口**：shell string 直接执行，很难在结构层判断危险动作。
- **harness 把动作结构化**：`delete_path({"path": ".", "recursive": true})` 可以在执行前被明确拒绝。
- **工具结果回灌 history**：模型能基于真实工具结果继续下一步。
- **验证是 runtime 的一部分**：demo 最后会检查 workspace 是否被错误删除、缓存是否被精确清理、报告是否存在。

## 运行结果要点

常规模式：

```text
[MODEL] shell: rm -rf *
[WORKSPACE TREE AFTER CONVENTIONAL]
REPORT.md
[VERIFY] conventional demonstrates failure mode: PASS
```

harness 模式：

```text
[MODEL] tool_call: delete_path {'path': '.', 'recursive': True}
[SCHEDULER] deny: broad or recursive delete requires explicit review
[MODEL] tool_call: delete_path {'path': 'tmp/cache.txt', 'recursive': False}
[SCHEDULER] allow: tool call satisfies local policy
[VERIFY] harness preserves source and removes only cache: PASS
```
