# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

Python AI agent project built on the **Claude Agent SDK** (`claude-agent-sdk`), Anthropic's Python framework for building Claude-Code-style agents programmatically. This is distinct from the raw `anthropic` Messages API SDK — the Agent SDK wraps the full agent loop (tool execution, permissions, context management) for you.

*(Fill in the specific purpose of this agent once defined.)*

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install claude-agent-sdk
```

Requires Python 3.10+.

## Running

Entry point TBD — see conventions below for the two ways to invoke the SDK.

## Claude Agent SDK conventions

### Entry points

- **`query()`** — stateless, one-shot tasks. Use for scripts and single-turn jobs.
- **`ClaudeSDKClient`** — stateful, multi-turn sessions. Use when the agent needs conversational context across turns (`async with ClaudeSDKClient(options=...) as client:`).

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(system_prompt="...")
    async for message in query(prompt="...", options=options):
        print(message)

asyncio.run(main())
```

### Custom tools

Define tools with the `@tool` decorator and register them via an in-process MCP server (`create_sdk_mcp_server`), then allow them explicitly in `allowed_tools` as `mcp__<server>__<tool>`.

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

@tool("calculate", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": f"Result: {args['a'] + args['b']}"}]}

server = create_sdk_mcp_server(name="math-tools", version="1.0.0", tools=[add])
options = ClaudeAgentOptions(mcp_servers={"math": server}, allowed_tools=["mcp__math__calculate"])
```

### Permission modes

Set `permission_mode` on `ClaudeAgentOptions`, or pass a `can_use_tool` callback for custom per-call logic (overrides `permission_mode`).

| Mode | Behavior |
|---|---|
| `default` | Prompts for permission on each tool use |
| `acceptEdits` | Auto-approves file edits |
| `plan` | Exploration only — blocks modifications |
| `dontAsk` | Denies any tool not in `allowed_tools` |
| `bypassPermissions` | Skips permission checks (explicit deny rules still apply) |

Also configure `allowed_tools` / `disallowed_tools` (supports patterns like `"Bash(rm *)"`) on the same options object.

### Configuration

There is **no `settings.json` equivalent** for SDK-driven agents — unlike interactive Claude Code, everything (model, system prompt, permissions, hooks, MCP servers) is passed programmatically via `ClaudeAgentOptions`:

```python
options = ClaudeAgentOptions(
    model="claude-opus-4-8",
    system_prompt="...",
    max_turns=10,
    cwd="/path/to/project",
    permission_mode="default",
    allowed_tools=["Read", "Write", "Bash"],
    hooks={"PreToolUse": [my_hook_handler]},
)
```

Session continuity uses `continue_conversation=True` or `resume="<session-id>"` rather than a config file.

### Models

Use the current model ID strings — do not append date suffixes:

| Model | ID |
|---|---|
| Claude Opus 4.8 (default choice) | `claude-opus-4-8` |
| Claude Sonnet 5 | `claude-sonnet-5` |
| Claude Haiku 4.5 | `claude-haiku-4-5` |

Default to `claude-opus-4-8` unless the task is high-volume/latency-sensitive (favor `claude-sonnet-5`) or trivially simple (favor `claude-haiku-4-5`).
