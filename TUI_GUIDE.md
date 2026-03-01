# AI_SYNAPSE TUI — Beautiful Terminal Interface

> A Kilo-like TUI with all Synapse superpowers built-in

---

## What's the TUI?

The **TUI** (Terminal User Interface) gives you a **beautiful, interactive experience** similar to Kilo CLI, but with AI_SYNAPSE features:

```
╔══════════════════════════════════════════════════════════════════╗
║ ⚡ AI_SYNAPSE v0.3.0                                              ║
║ Multi-Provider • CARL Intelligence • Persistent Memory          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║ 👤 You                                                           ║
║ fix the python bug in auth.py                                   ║
║                                                                  ║
║ ⚙️ CARL                                                          ║
║ Mode: *dev                                                       ║
║ Context: python, security, api                                  ║
║                                                                  ║
║ 🤖 Assistant                                                     ║
║ I'll help you fix the bug. First, let me read the file...       ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║ 📡 kilo/moonshotai/kimi-k2.5:free │ 💾 Context: 23% │ 📁 myapp   ║
╚══════════════════════════════════════════════════════════════════╝

You: _
```

---

## Quick Start

```bash
cd ~/Documents/AI_PROJS/AI_SYNAPSE
./synapse_tui.py
```

---

## Interface Elements

### 1. Header
Shows the app name and tagline.

### 2. Chat Area
Shows conversation with color-coded messages:
- **👤 You** (green) — Your inputs
- **🤖 Assistant** (blue) — AI responses
- **⚙️ CARL** (yellow) — Context rules loaded
- **🔧 Tool** (magenta) — File operations

### 3. Status Bar (Bottom)
```
📡 kilo/moonshotai/kimi-k2.5:free  │  💾 Context: 23%  │  📁 myapp  │  🧠 Memory: ✓
```

Shows:
- **📡 Model** — Currently selected provider/model
- **💾 Context** — How full the context window is (green → yellow → red)
- **📁 Project** — Current directory
- **🧠 Memory** — Whether project memory is loaded

### 4. Side Panel (Right)
Shows available commands for quick reference.

---

## Commands

### Model Commands
```
/models          # List all available models
/model 2         # Switch to model #2
/model groq/llama-3.3-70b  # Switch by name
```

### Chat Commands
```
/clear           # Clear chat history
/compact         # Summarize old messages
/save            # Save conversation
/sessions        # List saved sessions
/load <id>       # Load a saved session
```

### Memory Commands
```
/memory          # Show project memory
/remember <text> # Add to memory
/forget <text>   # Remove from memory
```

### Search Commands
```
/search <query>  # Search the web
```

### System Commands
```
/help            # Show help
/exit            # Quit and save
```

### Star Commands (In Messages)
Start your message with:
```
*dev             # Development mode
*debug           # Debugging mode  
*plan            # Planning mode
*review          # Code review mode
*explain         # Teaching mode
*brief           # Concise mode
```

---

## Workflow Examples

### Example 1: Quick Question
```
You: explain Python decorators
Assistant: [streams response]
```

### Example 2: Development Work
```
You: *dev create authentication system
⚙️ CARL
Mode: *dev
Context: python, security, api

🤖 Assistant
Here's the implementation...
```

### Example 3: Debugging
```
You: *debug why is this function returning None?
⚙️ CARL
Mode: *debug
Context: python, debugging

🤖 Assistant
Let's debug systematically...
```

### Example 4: With Memory
```bash
# First, add project context
You: /remember This project uses FastAPI + Pydantic v2

# Later, any command knows this
You: add user model
🧠 Memory: ✓  (automatically loaded)
🤖 Assistant: [uses FastAPI patterns]
```

### Example 5: Model Switching
```
You: /models
  → 1. kilo/moonshotai/kimi-k2.5:free
    2. kilo/minimax/minimax-m2.5:free
    3. groq/llama-3.3-70b-versatile

You: /model 3
✓ Model changed to: groq/llama-3.3-70b-versatile

You: hello
[using groq/llama-3.3-70b]
Assistant: [response from Groq]
```

### Example 6: Fallback (Automatic)
```
You: write a Python script
⚠️ Primary provider failed, trying fallback...
✓ Using fallback: groq/llama-3.3-70b-versatile
🤖 Assistant: [response from Groq because Kilo was unavailable]
```

---

## Multi-Line Input

The TUI supports multi-line naturally:

```
You: I need to refactor this code:
... 
... import requests
... def fetch():
...     return requests.get("https://api.example.com")
...
... Please add:
... 1. Timeout
... 2. Error handling
... 3. Retry logic
[Enter on empty line to send]

🤖 Assistant: [sees all lines and responds]
```

---

## Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| `💾 Context: 23%` [green] | Healthy context |
| `💾 Context: 65%` [yellow] | Getting full |
| `💾 Context: 85%` [red] | Use /compact soon |
| `🧠 Memory: ✓` | Project memory loaded |
| `🧠 Memory: ✗` | No memory for project |
| `✨ Mode: *dev` | Star command active |
| `🎯 Context: python` | CARL detected Python |

---

## Differences from Kilo

| Feature | Kilo | Synapse TUI |
|---------|------|-------------|
| UI | Beautiful TUI | ✅ Beautiful TUI (similar) |
| Multi-line | ✅ Yes | ✅ Yes |
| Model selector | ✅ `/model` | ✅ `/model` |
| File diffs | ✅ Yes | ⚠️ Shows in text (no visual diff yet) |
| Provider fallback | ❌ No | ✅ Automatic |
| CARL rules | ❌ No | ✅ Auto-injected |
| Project memory | ❌ No | ✅ Persistent |
| Skills | ❌ No | ✅ Built-in |
| Web search | ❌ No | ✅ `/search` |
| Session save | ❌ No | ✅ `/save` |

---

## Tips

1. **Watch the status bar** — Context color tells you when to /compact
2. **Use star commands** — Get focused responses
3. **Set memory once** — Use /remember for project context
4. **Let it fallback** — Don't worry if Kilo fails, it auto-switches
5. **Save sessions** — Use /save for important conversations

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Exit |
| `Enter` | Send message |
| `Enter` (on empty) | End multi-line input |
| `Up/Down` | Navigate history (not yet implemented) |

---

## Troubleshooting

### TUI looks garbled?
```bash
# Make sure your terminal supports Unicode
export TERM=xterm-256color
./synapse_tui.py
```

### Colors not showing?
```bash
# Rich auto-detects, but force if needed
export FORCE_COLOR=1
./synapse_tui.py
```

### Slow rendering?
```bash
# The TUI re-renders on each message
# This is normal for Rich-based TUIs
```

---

## Two Versions Available

| Version | Command | Use Case |
|---------|---------|----------|
| **TUI** | `./synapse_tui.py` | Interactive work, beautiful UI |
| **CLI** | `./synapse.py` | Scripts, piping, simple queries |

---

## Start Using It

```bash
./synapse_tui.py
```

**Enjoy your new AI assistant with a beautiful interface!** 🚀
