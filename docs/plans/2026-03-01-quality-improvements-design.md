# AI_SYNAPSE Quality Improvements Design

## Round 1: Quality 5 → 7 (DONE)

**Goal:** Fix provider ordering, eliminate noise, improve tool-use quality, and add streaming.

**Scope:** 8 targeted changes across existing files. No new files.

### Changes

1. **Provider Reorder** — `core/config.py`, `~/.synapse/config.yaml` — Kilo (1), Kimi (2), Ollama (3), OpenRouter (4), Groq (5), Gemini (6)
2. **Cache `check_available()` Results** — `providers/base.py` — 60-second TTL cache
3. **Suppress Duplicate Warnings** — `providers/base.py` — `_logged_errors: set`, log once per unique error
4. **Better System Prompt** — `synapse.py` — explicit tool-use instructions, `os.getcwd()`
5. **Streaming for Ollama `complete_with_tools`** — `providers/ollama.py` — stream text, buffer tool calls
6. **Show Active Provider** — `synapse.py` — display `[provider/model]`
7. **Auto-Compact** — `core/agent_loop.py` — compact when context usage > 75%
8. **Config-Driven Priorities** — `core/config.py` — defaults match new priority order

---

## Round 2: Quality 7 → 8 (DONE)

**Goal:** Add retry logic, parallel tool execution, async I/O, better streaming, and unit tests.

**Scope:** 5 changes across 5 files + new test suite.

### Changes

1. **Retry Logic in Router** — `core/router.py` — tenacity-based retry on `ServiceUnavailableError` and `RateLimitError` (max 2 retries, exponential backoff 1s→2s). No retry on `AuthenticationError`. Applied to both `complete()` and `complete_with_tools()`.
2. **Parallel Tool Execution** — `core/agent_loop.py` — replaced sequential `for tc in tool_calls` with `asyncio.gather()` for concurrent execution. Results yielded in order.
3. **Async Web Search** — `core/web_search.py` — replaced blocking `urllib.request` with async `httpx`. Added result caching with dict + 5-minute TTL.
4. **Ollama Streaming for Tool Calls** — `providers/ollama.py` — `complete_with_tools()` streams text chunks immediately. Switches to buffering only when structured `tool_calls` appear.
5. **Unit Tests** — `tests/` — 46 tests covering tools (17), conversation (14), and router (11+4 async). Uncommented pytest/pytest-asyncio/pytest-cov in `requirements.txt`.
