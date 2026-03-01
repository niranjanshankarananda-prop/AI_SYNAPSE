# AI_SYNAPSE v0.4.0 — Agentic Tool Loop Design

**Date:** 2026-03-01
**Status:** Approved
**Goal:** Transform AI_SYNAPSE from a multi-provider chat forwarder into a full agentic coding assistant with autonomous tool execution.

## Problem

AI_SYNAPSE has well-structured tool definitions (Read, Edit, Write, Bash, Glob, Grep) but no mechanism for the AI to actually call them. The tools are dead code. Without an agentic tool loop, the system is just a chat wrapper with fancy prompt injection.

## Solution: Hybrid Agentic Tool Loop

### Core Loop (`core/agent_loop.py`)

```
User Message → CARL + Memory + Skills → Build messages with tool schemas
    ↓
┌─── AGENTIC LOOP (max 50 iterations) ──────┐
│  Send to Provider (with tools)             │
│  Response = text + tool_calls?             │
│  If tool_calls:                            │
│    ├─ Permission check (safe? dangerous?)  │
│    ├─ Execute tool                         │
│    ├─ Add tool result to messages          │
│    └─ LOOP BACK                           │
│  If text only: DONE — display to user      │
└────────────────────────────────────────────┘
```

- Max 50 iterations (safety limit)
- Auto-approve mode via `--yes` flag
- Permission system: safe commands auto-allowed, dangerous ones prompt user

### Provider Strategy (Hybrid)

| Provider | Tool Support Method |
|----------|-------------------|
| Groq | Native function calling (OpenAI-compatible) |
| Gemini | Native function calling (Gemini format) |
| Kimi | Native function calling (OpenAI-compatible) |
| Kilo | Prompt-based: inject tool instructions, parse `<tool_call>` from text |
| OpenRouter (new) | Native function calling (OpenAI-compatible) |
| Ollama (new) | Native function calling (OpenAI-compatible) |

### Unified Response Type (`core/agent_response.py`)

```python
@dataclass
class AgentResponse:
    type: str  # "text", "tool_call", "error"
    content: str  # text content or error message
    tool_name: str  # tool to call (if type="tool_call")
    tool_args: dict  # arguments (if type="tool_call")
    tool_call_id: str  # for matching results back
```

## File Changes

### New Files
- `core/agent_loop.py` — Agentic tool loop with permission system
- `core/agent_response.py` — Unified response types
- `providers/openrouter.py` — OpenRouter provider (free models)
- `providers/ollama.py` — Ollama local provider

### Modified Files
- `providers/base.py` — Add `supports_function_calling`, `complete_with_tools`
- `providers/groq.py` — Add function calling, fix import bug
- `providers/gemini.py` — Add function calling
- `providers/kimi.py` — Add function calling
- `providers/kilo.py` — Add prompt-based tool parsing
- `core/tools.py` — Wire permission checks
- `core/conversation.py` — Support tool messages
- `core/carl.py` — Fix operator precedence bug at line 139
- `core/router.py` — Route tool-capable requests
- `synapse.py` — Integrate agent loop, fix single-shot mode, fix banner
- `synapse_tui.py` — Use router, integrate agent loop
- `core/config.py` — Add OpenRouter + Ollama configs

## Bug Fixes (While Building)
1. Groq `import json` at bottom → move to top
2. Banner box-drawing alignment
3. Single-shot mode TODO → implement
4. TUI uses raw subprocess instead of router
5. TUI session save creates anonymous object
6. CARL `carl.py:139` operator precedence bug
7. BashTool `is_dangerous()` never called

## New Providers
- **OpenRouter** — 100+ free models, OpenAI-compatible API, priority 4
- **Ollama** — Local models, zero cost, offline capable, priority 5
