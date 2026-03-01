# AI_SYNAPSE — Complete Usage Guide

> 🎯 **Quick Start:** Run `./synapse.py` and start chatting!

---

## Table of Contents

1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Interactive Mode](#interactive-mode)
4. [Star Commands](#star-commands)
5. [Memory System](#memory-system)
6. [Skills](#skills)
7. [Session Management](#session-management)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Step 1: Install Dependencies

```bash
cd ~/Documents/AI_PROJS/AI_SYNAPSE
pip install -r requirements.txt
```

### Step 2: First Run (Auto-Setup)

```bash
./synapse.py
```

This will:
- ✅ Create `~/.synapse/config.yaml`
- ✅ Create CARL rules in `~/.synapse/carl/`
- ✅ Create skill templates in `~/.synapse/skills/`

### Step 3: Set API Keys (Optional but Recommended)

```bash
# Add to your ~/.zshrc or ~/.bashrc
export GROQ_API_KEY="gsk_your_key_here"
export GEMINI_API_KEY="your_gemini_key"
export KIMI_API_KEY="your_kimi_key"  # Paid backup
```

Get your free API keys:
- **Groq**: https://console.groq.com/keys (14,400 req/day FREE)
- **Gemini**: https://aistudio.google.com/app/apikey (1,500 req/day FREE)

---

## Basic Usage

### Single Message (One-Shot)

```bash
# Quick question
./synapse.py "What is Python asyncio?"

# Code help
./synapse.py "How do I read a file in Python?"

# With specific skill
./synapse.py --skill tdd "add a payment module"
```

### Interactive Mode (Recommended)

```bash
# Start chat session
./synapse.py

# You'll see:
╔═══════════════════════════════════════════════════════════╗
║  ⚡ AI_SYNAPSE — Universal AI CLI                         ║
╚═══════════════════════════════════════════════════════════╝

💡 Tips:
   • Use *dev, *debug, *plan, etc. for different modes
   • Use /compact when context fills up
   • Use /stats to see session info
   • Type 'exit' or press Ctrl+C to quit

You: 
```

Now type naturally:
```
You: I need to build a REST API with user authentication. 
     The app should support JWT tokens and refresh tokens.
     Can you help me design and implement this using FastAPI?
```

---

## Interactive Mode Commands

### Special Commands (Type at prompt)

| Command | What It Does |
|---------|--------------|
| `/exit` or `exit` | Quit Synapse |
| `/compact` | Summarize old messages to save context |
| `/clear` | Clear conversation history |
| `/stats` | Show token usage and session info |
| `/save` | Save current session |
| `/sessions` | List saved sessions |
| `/load <id>` | Load a saved session |

### Example Session

```
You: *dev create a Python function to validate email addresses
✨ Mode: *dev
🎯 Skills: debugging
Assistant: Here's the implementation...

You: /stats
📊 Session: 20260301_143022
   Messages: 4 total
   Context: 12.3% used (112,345 tokens remaining)

You: /compact
📝 Compacted conversation: summarized 10 messages

You: exit
👋 Goodbye!
```

---

## Star Commands

Type `*command` at the **start** of your message to activate special modes.

### Available Star Commands

| Command | Use When... | Effect |
|---------|-------------|--------|
| `*dev` | Writing code | Code-focused, runs tests, minimal changes |
| `*debug` | Fixing bugs | Systematic debugging workflow |
| `*plan` | Starting feature | Explores options, waits for approval |
| `*review` | Reviewing code | Checks for security, performance issues |
| `*brief` | Want quick answer | Bullet points only, max 5 items |
| `*explain` | Learning concept | Teaching mode with examples |
| `*test` | Writing tests | TDD workflow, test-first approach |

### Examples

```bash
# Development mode
./synapse.py "*dev add user authentication to FastAPI app"

# Debugging mode
./synapse.py "*debug why is the login returning 500 error"

# Planning mode
./synapse.py "*plan should I use PostgreSQL or MongoDB for this?"

# Code review
./synapse.py "*review this auth.py file for security issues"

# Quick answer
./synapse.py "*brief list the HTTP status codes for REST APIs"

# Learning
./synapse.py "*explain how Python decorators work"
```

### How CARL Detects Context

You don't need star commands! CARL **automatically** detects context:

```
You: fix the python bug in auth.py
↓
CARL detects: "python", "bug", "auth"
↓
Loads: PYTHON + DEBUGGING + SECURITY rules
```

```
You: deploy this docker container to railway
↓
CARL detects: "deploy", "docker", "railway"
↓
Loads: DEPLOY + DOCKER rules
```

---

## Memory System

Synapse **remembers** your projects across sessions!

### Remember Information

```bash
# Save project context
./synapse.py --remember "This project uses FastAPI + Pydantic v2"

# Save with category
./synapse.py --remember "Always use async/await for DB operations"
```

### View Memory

```bash
# Show current project memory
./synapse.py --memory

# Output:
📝 Project Memory for /Users/niranjan/Projects/myapp:

- (2026-03-01 14:30) This project uses FastAPI + Pydantic v2
- (2026-03-01 14:35) Always use async/await for DB operations
```

### How Memory Works

1. **Auto-detection**: Synapse detects your project by looking for `.git` or using current directory
2. **Auto-loading**: Every prompt automatically includes project memory
3. **Context-aware**: Different projects = different memories

### Example Workflow

```bash
cd ~/Projects/my-fastapi-app

# First time - tell Synapse about your project
./synapse.py --remember "This is a FastAPI app with PostgreSQL"
./synapse.py --remember "Uses SQLAlchemy 2.0 with async support"
./synapse.py --remember "Deployed on Railway"

# Now every command knows this:
./synapse.py "add user authentication"
# → Knows to use FastAPI + async + SQLAlchemy 2.0

./synapse.py "create database migration"
# → Knows about PostgreSQL and Railway
```

### Forget Information

```bash
# Forget specific pattern
./synapse.py --forget "SQLAlchemy"

# Clear all memory for this project
./synapse.py --forget ""
```

---

## Skills

Skills provide **structured workflows** for complex tasks.

### Built-In Skills

| Skill | Trigger Words | What It Does |
|-------|---------------|--------------|
| **TDD** | "tdd", "test-driven", "write tests" | Enforces RED-GREEN-REFACTOR cycle |
| **Debugging** | "debug", "bug", "error", "fix" | Systematic 4-phase debugging |

### Using Skills

**Auto-detection** (just talk naturally):
```bash
./synapse.py "using TDD, add a payment processing module"
# → Automatically loads TDD skill
```

**Manual loading**:
```bash
./synapse.py --skill tdd --skill debugging "fix the auth bug"
```

### TDD Skill Example

```
You: using TDD, add a function to calculate compound interest
🎯 Skills: tdd
Assistant: 
Let's follow TDD:

**Step 1: RED - Write failing test**

Here's the test:
```python
def test_compound_interest():
    assert compound_interest(1000, 0.05, 10) == 1628.89
```

Run it: pytest test_interest.py
It should FAIL (function doesn't exist yet)

Proceed? (yes/no): yes

**Step 2: GREEN - Write minimal code**

def compound_interest(principal, rate, years):
    return principal * (1 + rate) ** years

Run test again - should PASS

Proceed? (yes/no): yes

**Step 3: REFACTOR**

The code is clean. Add docstring:

def compound_interest(principal: float, rate: float, years: int) -> float:
    """Calculate compound interest."""
    return principal * (1 + rate) ** years

✅ TDD cycle complete!
```

---

## Session Management

Save and resume conversations!

### In Interactive Mode

```
You: /save
✅ Session saved: 20260301_143022

You: /sessions
💾 Saved Sessions:
  1. 20260301_143022 - "build REST API with auth" (12 messages)
  2. 20260301_102345 - "debug login issue" (8 messages)

You: /load 20260301_143022
📂 Loaded session: 20260301_143022
   12 messages restored
```

### Auto-Save

Sessions are automatically saved when you exit cleanly.

### Export Conversations

```bash
# Export as Markdown
./synapse.py --export 20260301_143022 --format markdown > conversation.md

# Export as JSON
./synapse.py --export 20260301_143022 --format json > conversation.json
```

---

## Advanced Features

### 1. Multi-Line Input

For complex prompts, use heredoc:

```bash
./synapse.py << 'EOF'
I'm building a trading bot with these requirements:
1. Connect to Binance API
2. Fetch real-time price data
3. Calculate moving averages
4. Execute trades based on signals
5. Log all transactions

The bot should use Python with asyncio for concurrency.
Can you help me design the architecture?
EOF
```

### 2. Pipe Input

```bash
# Send file content to Synapse
cat error.log | ./synapse.py "analyze this error"

# Process code file
./synapse.py "review this code" < main.py
```

### 3. Web Search (Built-in)

Synapse can search the web for current information:

```
You: search for latest Python 3.13 features
Assistant: 🔍 Searching...

Found 5 results:
1. Python 3.13: What's New - python.org
   URL: https://docs.python.org/3.13/whatsnew/
   New features include: improved error messages, ...

Let me summarize the key features for you...
```

### 4. Response Caching

Repeated queries are cached to save tokens:

```bash
# First time: calls API
./synapse.py "explain Python decorators"
# → Takes 2-3 seconds

# Second time: instant from cache
./synapse.py "explain Python decorators"
# → Instant (cached)
```

Clear cache:
```bash
rm -rf ~/.synapse/cache/
```

### 5. Provider Override

Force a specific provider:

```bash
# Edit ~/.synapse/config.yaml temporarily
# Or set priority in config

# Kilo first (default)
./synapse.py "hello"

# If Kilo fails, automatically tries:
# 1. Groq (Llama 70B)
# 2. Gemini (2.5 Flash)
# 3. Kimi (paid backup)
```

### 6. Tool Usage

Synapse can use tools (read files, run commands):

```
You: read the auth.py file and fix the bug
Assistant: 🔧 Using tool: read
           Reading auth.py...
           
           I see the issue on line 45...
           
           🔧 Using tool: edit
           Fixed the bug. Here's what changed:
           - Old: if user.email == email
           + New: if user.email.lower() == email.lower()
```

### 7. Context Management

Long conversations automatically managed:

```
You: [20 turns later...]
⚠️  Context filling up (75% used)
   Use /compact to summarize or /clear to start fresh

You: /compact
📝 Compacted conversation:
   - Summarized 15 older messages
   - Keeping 5 recent messages
   - Context now at 25%

You: continue where we left off
Assistant: [Knows the context from summary]
```

---

## Troubleshooting

### Problem: "No providers available"

**Solution:**
```bash
# Check config
./synapse.py --config

# Set at least one API key
export GROQ_API_KEY="gsk_your_key"

# Or rely on Kilo (free, no API key needed)
# Make sure Kilo CLI is installed:
which kilo
```

### Problem: "Kilo not found"

**Solution:**
```bash
# Install Kilo CLI
curl -fsSL https://kilo.ai/install.sh | bash

# Or if installed but not in PATH
export PATH="$PATH:$HOME/.kilo/bin"
```

### Problem: "Rate limit exceeded"

**Solution:**
- Wait a minute (rate limits reset)
- Synapse automatically falls back to next provider
- Add more API keys for more quota

### Problem: "Context too long"

**Solution:**
```
You: /compact
# Summarizes old messages

# Or
You: /clear
# Starts fresh (but loses history)
```

### Problem: "CARL rules not loading"

**Solution:**
```bash
# Check CARL config exists
ls ~/.synapse/carl/

# Should see: manifest, global, context, commands, domains/

# If missing, reinstall:
rm -rf ~/.synapse/
./synapse.py  # Will recreate
```

### Debug Mode

```bash
# See detailed logs
./synapse.py --verbose "hello"

# Or set env var
export SYNAPSE_LOG_LEVEL=DEBUG
./synapse.py
```

---

## Configuration Reference

### Config File Location

```
~/.synapse/config.yaml
```

### Key Settings

```yaml
# Provider priority (lower = tried first)
providers:
  kilo:
    enabled: true
    priority: 1
  groq:
    enabled: true
    priority: 2
  gemini:
    enabled: true
    priority: 3
  kimi:
    enabled: true
    priority: 100  # Last (paid)

# CARL settings
carl:
  enabled: true
  config_path: ~/.synapse/carl

# Memory settings
memory:
  enabled: true
  location: ~/.synapse/memory
  max_lines: 200

# Conversation
conversation:
  max_tokens: 128000
  compact_threshold: 0.75  # Warn at 75% usage

# UI
ui:
  stream: true
  show_provider: true
  syntax_highlight: true
```

---

## Tips & Best Practices

### 1. Use Star Commands for Consistency

```bash
# Good: Gets consistent, focused responses
./synapse.py "*dev fix the bug"

# Okay: But might be too broad
./synapse.py "fix the bug"
```

### 2. Remember Project Context

```bash
# Once per project
./synapse.py --remember "Uses FastAPI + SQLAlchemy 2.0"

# Now all commands know this automatically
```

### 3. Save Important Sessions

```bash
# After important work
./synapse.py

You: [complex architecture discussion]
You: /save

# Resume later
./synapse.py
You: /sessions
You: /load <session_id>
```

### 4. Compact Regularly

```bash
# Every ~20 turns
You: /compact

# Keeps context window healthy
```

### 5. Use Skills for Complex Workflows

```bash
# TDD for robust code
./synapse.py "using TDD, add payment processing"

# Debugging for tricky bugs
./synapse.py "*debug why is the cron job failing"
```

---

## Summary

| Feature | Command | When to Use |
|---------|---------|-------------|
| **Quick question** | `./synapse.py "question"` | One-off queries |
| **Deep work** | `./synapse.py` (interactive) | Complex tasks |
| **Code mode** | `*dev your prompt` | Writing code |
| **Debug mode** | `*debug your prompt` | Fixing bugs |
| **Plan mode** | `*plan your prompt` | Architecture decisions |
| **Remember** | `--remember "info"` | Save project context |
| **View memory** | `--memory` | Check saved info |
| **Save session** | `/save` (interactive) | Preserve conversation |
| **Compact** | `/compact` | Free up context |
| **Stats** | `/stats` | Check usage |

---

**🎉 You're ready to use AI_SYNAPSE!**

Start with: `./synapse.py`
