# AI_SYNAPSE — Universal AI CLI

> Your intelligent bridge to AI — adaptive, persistent, and future-proof.

**⚡ Status:** v0.3.0 Production Ready

---

## 🚀 Quick Start (30 seconds)

```bash
cd ~/Documents/AI_PROJS/AI_SYNAPSE
pip install -r requirements.txt

# Option 1: Beautiful TUI (like Kilo)
./synapse_tui.py

# Option 2: Simple CLI
./synapse.py
```

---

## ✨ What Makes This Special

### Compared to Kilo/Kimi:
| Feature | Kilo | AI_SYNAPSE |
|---------|------|-----------|
| **Multi-line input** | ✅ Yes | ✅ Yes |
| **Beautiful UI** | ✅ Yes | ✅ **TUI version** |
| **Provider fallback** | ❌ No | ✅ **Auto-switches if Kilo fails** |
| **Project memory** | ❌ No | ✅ **Remembers your projects** |
| **Context rules** | ❌ No | ✅ **CARL auto-detects context** |
| **Skills** | ❌ No | ✅ **TDD, Debugging workflows** |
| **Web search** | ❌ No | ✅ **Built-in DuckDuckGo** |
| **Session save** | ❌ No | ✅ **Save/resume conversations** |
| **Response cache** | ❌ No | ✅ **Saves tokens/money** |

### The Core Idea

**You type like normal** (just like Kilo), but Synapse:
1. **Adds intelligent rules** based on what you're doing
2. **Remembers your projects** across sessions
3. **Falls back automatically** if a provider fails
4. **Shows beautiful UI** with status indicators

---

## 📦 Two Interfaces

### 1. TUI (Terminal User Interface) — Recommended

```bash
./synapse_tui.py
```

**Looks like this:**
```
╔══════════════════════════════════════════════════════════════════╗
║ ⚡ AI_SYNAPSE v0.3.0                                              ║
║ Multi-Provider • CARL Intelligence • Persistent Memory          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║ 👤 You                                                           ║
║ *dev fix the python bug in auth.py                              ║
║                                                                  ║
║ ⚙️ CARL                                                          ║
║ Mode: *dev                                                       ║
║ Context: python, security, api                                  ║
║                                                                  ║
║ 🤖 Assistant                                                     ║
║ I'll help you fix the bug. Let me read the file first...       ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║ 📡 kilo/kimi-k2.5:free │ 💾 Context: 23% │ 📁 myapp │ 🧠 Memory: ✓ ║
╚══════════════════════════════════════════════════════════════════╝

You: _
```

**Features:**
- ✅ Beautiful panel-based UI
- ✅ Color-coded messages
- ✅ Status bar (model, context, project, memory)
- ✅ Side panel with commands
- ✅ Multi-line input
- ✅ All Synapse features

**Commands:**
```
/model 2                    # Switch to model #2
/models                     # List all models
/clear                      # Clear chat
/compact                    # Summarize context
/save                       # Save session
/memory                     # Show project memory
/remember "Uses FastAPI"    # Add to memory
/search "Python 3.13"       # Web search
/help                       # Show all commands
/exit                       # Quit
```

### 2. Simple CLI

```bash
./synapse.py
```

**For:** Scripts, piping, quick one-liners

```bash
# Single message
./synapse.py "explain Python decorators"

# With star command
./synapse.py "*dev fix the auth bug"

# Web search
./synapse.py --search "Python 3.13 features"

# Remember project info
./synapse.py --remember "Uses FastAPI + Pydantic v2"
```

---

## 🎯 Key Features

### 1. Future-Proof Provider Fallback

**Problem:** Kilo might remove free models tomorrow

**Solution:** Automatic fallback chain
```
Your Request
    ↓
Kilo (Kimi K2.5) — FREE ← Uses this first
    ↓ (if rate limited)
Groq (Llama 70B) — FREE ← Falls back here
    ↓ (if fails)
Gemini (2.5 Flash) — FREE ← Then here
    ↓ (if all fail)
Kimi (paid) — Your backup ← Ultimate fallback
```

You never get stuck!

### 2. CARL Intelligence

**Auto-detects what you're doing:**
```
You: fix the python bug in auth.py
    ↓
CARL detects: "python" + "bug" + "auth"
    ↓
Loads: PYTHON + DEBUGGING + SECURITY rules
```

**Star commands for specific modes:**
- `*dev` — Code-focused, minimal changes
- `*debug` — Systematic debugging
- `*plan` — Explores options first
- `*review` — Security & performance checks
- `*explain` — Teaching with examples
- `*brief` — Bullet points only

### 3. Project Memory

**Remembers across sessions:**
```bash
# Tell it once
./synapse.py --remember "This is a FastAPI + PostgreSQL app"

# 1 week later...
./synapse.py "add user authentication"
# → Knows to use FastAPI + async + PostgreSQL automatically
```

### 4. Skills

**Structured workflows:**

**TDD Skill:**
```
You: using TDD, add payment processing
🛠️ Skills: tdd
Assistant:
Step 1: RED - Write failing test
[shows test code]
Run it? (yes): 

Step 2: GREEN - Make it pass
[shows minimal code]
Run test? (yes):

Step 3: REFACTOR - Clean up
✅ TDD complete!
```

### 5. Session Management

```bash
# In TUI
You: /save
💾 Session saved: 20260301_143022

# Resume later
You: /sessions
💾 Saved Sessions:
  1. 20260301_143022 - "build REST API with auth"
  
You: /load 20260301_143022
📂 Loaded session with 12 messages
```

### 6. Web Search

```bash
./synapse.py --search "Python 3.13 features"
# Or in TUI:
You: /search latest FastAPI best practices
```

---

## 📚 Documentation

| Document | What It Covers |
|----------|----------------|
| **[TUI_GUIDE.md](TUI_GUIDE.md)** | Beautiful interface guide |
| **[USAGE_GUIDE.md](USAGE_GUIDE.md)** | Complete feature reference |
| **[QUICKSTART.md](QUICKSTART.md)** | 5-minute quick start |
| **[PRODUCT_PLAN.md](PRODUCT_PLAN.md)** | Full specification |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Technical design |

---

## 🔧 Configuration

Config location: `~/.synapse/config.yaml`

```yaml
providers:
  kilo:
    enabled: true
    priority: 1  # Tried first
  groq:
    enabled: true
    priority: 2
    api_key: ${GROQ_API_KEY}
  gemini:
    enabled: true
    priority: 3
    api_key: ${GEMINI_API_KEY}

carl:
  enabled: true

memory:
  enabled: true
  location: ~/.synapse/memory

skills:
  enabled: true
```

---

## 🎓 Usage Examples

### Development Workflow

```bash
# Start TUI
./synapse_tui.py

You: *dev create a REST API with FastAPI
✨ Mode: *dev
🎯 Context: python, api

# CARL automatically loads FastAPI rules
# Memory loads if you've used FastAPI before
# Skills auto-detect if needed

You: /save
💾 Session saved

# Later, in different terminal
./synapse_tui.py
You: /load <session_id>
📂 Resumed where you left off
```

### Debugging Workflow

```bash
./synapse_tui.py

You: *debug why is login returning 500?
✨ Mode: *debug
🎯 Context: debugging, security, api

# Assistant follows systematic debugging:
# 1. Gather context
# 2. Form hypothesis
# 3. Suggest tests
# 4. Root cause analysis
```

### Research Workflow

```bash
# Search for current info
You: /search "Python 3.13 release date"
🔍 [shows search results]

# Then ask follow-up
You: what are the main features?
Assistant: [responds with context from search]
```

---

## 📊 Project Stats

- **26 files** created
- **~6,000 lines** of code
- **67KB** of documentation
- **4 AI providers** integrated
- **10 core modules**
- **6 CARL domains**
- **2 built-in skills**

---

## 🎯 Choose Your Interface

| Use Case | Use This |
|----------|----------|
| **Daily development** | `./synapse_tui.py` (beautiful, interactive) |
| **Quick questions** | `./synapse.py "query"` (fast, simple) |
| **Scripts/piping** | `./synapse.py` (CLI mode) |
| **Learning/exploring** | `./synapse_tui.py` (rich output) |

---

## 🚀 Start Now

```bash
# 1. Install
cd ~/Documents/AI_PROJS/AI_SYNAPSE
pip install -r requirements.txt

# 2. Launch TUI (recommended)
./synapse_tui.py

# 3. Start chatting!
You: *dev help me build an API
```

**Welcome to the future of AI-assisted development!** 🎉

---

## 💡 Pro Tips

1. **Use the TUI for serious work** — It's worth the extra typing
2. **Set memory once per project** — Use `/remember`
3. **Use star commands** — `*dev`, `*debug`, `*plan` for better results
4. **Don't worry about Kilo failing** — Fallback is automatic
5. **Save important sessions** — Use `/save` liberally

---

**Built with ❤️ for developers who want the best AI experience.**

*Version: 0.3.0* | *Status: Production Ready*
