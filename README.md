# AI_SYNAPSE — Universal AI Coding Assistant

> An agentic coding assistant that reads files, edits code, and runs commands — powered by free AI models with automatic provider fallback.

**Version:** 0.4.0 | **Status:** Working

---

## What It Does

AI_SYNAPSE is a CLI coding assistant (like Claude Code or Cursor) that:

- **Reads, edits, and creates files** using built-in tools
- **Runs bash commands** with permission checks
- **Searches your codebase** with glob and grep
- **Routes to multiple AI providers** with automatic fallback
- **Remembers your projects** across sessions
- **Auto-detects context** (Python, frontend, database, etc.)

It works with **free models** — no API keys required if you have [Kilo CLI](https://kilo.ai) or [Ollama](https://ollama.ai) installed.

---

## Installation

### Prerequisites

- Python 3.10+
- At least one of:
  - [Kilo CLI](https://kilo.ai) (free, recommended) — `brew install kiloai/tap/kilo && kilo auth`
  - [Ollama](https://ollama.ai) (free, local) — `brew install ollama && ollama pull qwen2.5-coder:7b`
  - API key for Groq, Gemini, OpenRouter, or Kimi (optional)

### Setup

```bash
# Clone
git clone https://github.com/niranjanshankarananda-prop/AI_SYNAPSE.git
cd AI_SYNAPSE

# Install dependencies
pip install -r requirements.txt

# First run (creates ~/.synapse/ config)
python3 synapse.py
```

On first run, it creates:
```
~/.synapse/
  config.yaml    # Provider settings, priorities
  carl/          # Context-aware rules
  memory/        # Project knowledge
  skills/        # TDD, debugging workflows
  cache/         # Response cache
  sessions/      # Saved conversations
```

### Optional: Set API Keys

```bash
# Any of these (all optional if Kilo/Ollama available)
export KIMI_API_KEY='your-key'          # https://platform.moonshot.cn
export GROQ_API_KEY='gsk_...'           # https://console.groq.com
export GEMINI_API_KEY='...'             # https://aistudio.google.com
export OPENROUTER_API_KEY='sk-or-...'   # https://openrouter.ai
```

---

## Usage

### Single Command

```bash
# Ask a question
python3 synapse.py "read main.py and explain what it does"

# Auto-approve tool calls (no confirmation prompts)
python3 synapse.py "find all TODO comments in the codebase" --yes

# Use a star command for specific mode
python3 synapse.py "*debug why is the login returning 500?"
```

### Interactive Mode

```bash
python3 synapse.py
```

```
You: read core/tools.py and tell me what tools are available
  [kilo/moonshotai/kimi-k2.5:free]
  [tool] read({'file_path': 'core/tools.py'})
  [ok] ...

The following tools are available:
- read: Read file contents with line numbers
- edit: Find-and-replace text in files
- write: Create or overwrite files
- bash: Execute shell commands
- glob: Find files by pattern
- grep: Search file contents with regex

You: /exit
```

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/save` | Save current session |
| `/load <id>` | Resume a saved session |
| `/sessions` | List saved sessions |
| `/compact` | Summarize old messages (free up context) |
| `/clear` | Clear conversation |
| `/stats` | Show context usage and cache stats |
| `/search <query>` | Search the web |
| `/cache` | Show cache stats |
| `/cache clear` | Clear response cache |
| `exit` | Quit and save |

### Star Commands

Start your message with a star command to set the mode:

| Command | Mode | Best For |
|---------|------|----------|
| `*dev` | Development | Writing code, minimal changes |
| `*debug` | Debugging | Systematic problem solving |
| `*plan` | Planning | Exploring options first |
| `*review` | Review | Security and performance checks |
| `*explain` | Teaching | Detailed explanations with examples |
| `*brief` | Concise | Bullet points only |
| `*test` | Testing | Writing tests |

### CLI Flags

```bash
python3 synapse.py --help

# Key flags:
python3 synapse.py "message"            # Single message
python3 synapse.py --yes "message"      # Auto-approve tools
python3 synapse.py --verbose "message"  # Debug logging
python3 synapse.py --remember "info"    # Save to project memory
python3 synapse.py --memory             # Show project memory
python3 synapse.py --search "query"     # Web search
python3 synapse.py --config             # Show config
python3 synapse.py --version            # Show version
```

---

## How It Works

### Agentic Tool Loop

When you ask a question, AI_SYNAPSE runs an agentic loop:

```
User message
    |
    v
Send to AI (with tool schemas)
    |
    v
AI responds with text or tool calls
    |
    +-- Text? --> Display to user. Done.
    |
    +-- Tool calls? --> Execute tools --> Send results back to AI --> Repeat
```

The AI can chain multiple tool calls to complete complex tasks:

```
You: "find all Python files with TODO comments and list them"

  [tool] glob({'pattern': '*.py'})         # Find Python files
  [tool] grep({'pattern': 'TODO'})          # Search for TODOs
  [kilo/moonshotai/kimi-k2.5:free]
  Found 3 files with TODO comments:
  - core/router.py:45: TODO: add retry logic
  - providers/kilo.py:195: TODO: implement streaming
  ...
```

### Built-in Tools

| Tool | Description |
|------|-------------|
| `read` | Read file contents with line numbers |
| `edit` | Find-and-replace text in files |
| `write` | Create new files or overwrite existing |
| `bash` | Execute shell commands (with permission checks) |
| `glob` | Find files by pattern (e.g., `**/*.py`) |
| `grep` | Search file contents with regex |

Dangerous bash commands (rm, git push, docker, sudo) require user confirmation unless `--yes` is passed.

### Provider Fallback

AI_SYNAPSE tries providers in priority order. If one fails, it automatically falls back to the next:

```
Priority 1: Kilo CLI     (free, uses kimi-k2.5)
Priority 2: Kimi API     (paid, needs KIMI_API_KEY)
Priority 3: Ollama       (free, local, needs ollama running)
Priority 4: OpenRouter   (free tier, needs OPENROUTER_API_KEY)
Priority 5: Groq         (free tier, needs GROQ_API_KEY)
Priority 6: Gemini       (free tier, needs GEMINI_API_KEY)
```

Change priorities in `~/.synapse/config.yaml`.

### CARL (Context-Aware Rule Loading)

CARL automatically detects what you're working on and loads relevant rules:

```
You: "fix the SQLAlchemy migration bug"
  Context: python, database     # Auto-detected
  Skills: debugging             # Auto-loaded
```

Domains: python, frontend, database, api, deploy, security.

### Project Memory

```bash
# Remember project context
python3 synapse.py --remember "This project uses FastAPI + PostgreSQL"

# Memory persists across sessions
python3 synapse.py "add user auth"
# AI already knows to use FastAPI + PostgreSQL

# View memory
python3 synapse.py --memory

# Forget
python3 synapse.py --forget "FastAPI"
```

---

## Configuration

Config file: `~/.synapse/config.yaml`

```yaml
providers:
  kilo:
    enabled: true
    priority: 1
    models:
    - name: kilo/moonshotai/kimi-k2.5:free
      default: true
  kimi:
    enabled: true
    priority: 2
    api_key: null  # Set via KIMI_API_KEY env var
    models:
    - name: kimi-k2.5
      default: true
  ollama:
    enabled: true
    priority: 3
    base_url: http://localhost:11434
    models:
    - name: qwen2.5-coder:7b
      default: true

# Subsystems
carl:
  enabled: true
memory:
  enabled: true
conversation:
  max_tokens: 128000
  compact_threshold: 0.75
```

### Provider Setup

**Kilo CLI (recommended, free):**
```bash
brew install kiloai/tap/kilo
kilo auth
kilo models  # verify
```

**Ollama (free, local):**
```bash
brew install ollama
ollama serve &
ollama pull qwen2.5-coder:7b
```

**Kimi API (paid backup):**
```bash
export KIMI_API_KEY='your-key'  # https://platform.moonshot.cn
```

---

## Project Structure

```
AI_SYNAPSE/
  synapse.py              # CLI entry point
  synapse_tui.py          # TUI (terminal UI) entry point
  requirements.txt        # Python dependencies
  core/
    agent_loop.py         # Agentic tool loop
    agent_response.py     # Response types (text, tool_call, done)
    config.py             # Configuration management
    conversation.py       # Conversation history + context window
    router.py             # Provider routing with fallback
    tools.py              # Built-in tools (read, edit, write, bash, glob, grep)
    carl.py               # Context-aware rule loading
    memory.py             # Project memory persistence
    skills.py             # Skill system (TDD, debugging)
    cache.py              # Response caching
    session_manager.py    # Session save/load
    web_search.py         # DuckDuckGo web search
  providers/
    base.py               # Provider base class + error types
    kilo.py               # Kilo CLI provider (prompt-based tool calling)
    kimi.py               # Kimi/Moonshot API (native function calling)
    ollama.py             # Ollama local models (native function calling)
    groq.py               # Groq API (native function calling)
    gemini.py             # Google Gemini API (native function calling)
    openrouter.py         # OpenRouter API (native function calling)
```

---

## Troubleshooting

**"No providers available"**
- Install Kilo CLI: `brew install kiloai/tap/kilo && kilo auth`
- Or start Ollama: `ollama serve` then `ollama pull qwen2.5-coder:7b`
- Or set an API key: `export GROQ_API_KEY='...'`

**"Kilo authentication required"**
- Run `kilo auth` to authenticate.

**"Ollama not running"**
- Start it: `ollama serve`

**Model gives wrong answers / doesn't use tools**
- Smaller models (qwen2.5-coder:7b) may skip tool calls. Use Kilo (kimi-k2.5) for better results.
- Pass `--yes` to auto-approve tool calls.

**Context window full**
- Use `/compact` to summarize old messages.
- Use `/clear` to start fresh.
- Auto-compact triggers at 75% usage.

**Verbose logging**
- `python3 synapse.py --verbose "your message"` to see debug output.
