# AI_SYNAPSE Quality Improvements Design

**Goal:** Raise AI_SYNAPSE from 5/10 to 8/10 by fixing provider ordering, eliminating noise, improving tool-use quality, and adding streaming.

**Scope:** 8 targeted changes across existing files. No new files.

## Changes

### 1. Provider Reorder
- **Files:** `core/config.py`, `~/.synapse/config.yaml`
- Kilo (1), Kimi (2), Ollama (3), OpenRouter (4), Groq (5), Gemini (6)

### 2. Cache `check_available()` Results
- **File:** `providers/base.py`
- Add `_availability_cache` with 60-second TTL to `Provider` base class
- `check_available()` returns cached result within TTL window

### 3. Suppress Duplicate Warnings
- **File:** `providers/base.py`
- Track logged errors in `_logged_errors: set`. Only log once per unique error message.

### 4. Better System Prompt
- **File:** `synapse.py`
- Add explicit tool-use instructions: always read before answering, never guess
- Include `os.getcwd()` so AI knows current directory

### 5. Streaming for Ollama `complete_with_tools`
- **File:** `providers/ollama.py`
- Stream text responses instead of waiting for full response
- Still collect full response for tool call parsing

### 6. Show Active Provider
- **File:** `synapse.py`
- Display `[provider/model]` when AI starts responding

### 7. Auto-Compact
- **File:** `core/agent_loop.py`
- Check context usage after each tool execution loop
- Auto-compact if over threshold

### 8. Config-Driven Priorities
- **File:** `core/config.py`
- Verify defaults match new priority order (already wired in router)
