# AI_SYNAPSE — 5-Minute Quick Start

> ⚡ Get started in 5 minutes or less

---

## 🚀 Step 1: Install (30 seconds)

```bash
cd ~/Documents/AI_PROJS/AI_SYNAPSE
pip install -r requirements.txt
```

---

## 🎯 Step 2: First Run (30 seconds)

```bash
./synapse.py
```

You'll see:
```
👋 Welcome to AI_SYNAPSE!

🔧 Setting up your AI assistant...

✅ Configuration: ~/.synapse/config.yaml
✅ CARL rules: ~/.synapse/carl/
✅ Skills: ~/.synapse/skills/
✅ Memory: ~/.synapse/memory/
✅ Cache: ~/.synapse/cache/
✅ Sessions: ~/.synapse/sessions/
```

---

## 💬 Step 3: Start Chatting (Instant!)

```bash
./synapse.py
```

Type naturally:
```
You: explain Python decorators with examples
Assistant: [streams detailed response]

You: *dev create a function to validate emails
✨ Mode: *dev
🎯 Context: python
Assistant: [code-focused response]

You: /exit
👋 Session saved. Goodbye!
```

---

## 📖 Common Commands

### Star Commands (Start your message with)
- `*dev` — Development mode (code-focused)
- `*debug` — Debugging mode (systematic problem solving)
- `*plan` — Planning mode (explores options first)
- `*review` — Code review mode
- `*explain` — Teaching mode
- `*brief` — Concise bullet points only

### Slash Commands (Type at prompt)
- `/save` — Save conversation
- `/sessions` — List saved sessions
- `/load <id>` — Load a session
- `/compact` — Summarize old messages
- `/clear` — Start fresh
- `/stats` — Show token usage
- `/search <query>` — Web search
- `/help` — Show all commands
- `exit` — Quit

---

## 💾 Remember Your Projects

```bash
# Tell Synapse about your project once
./synapse.py --remember "This is a FastAPI + PostgreSQL app"
./synapse.py --remember "Uses SQLAlchemy 2.0 with async"

# Now all commands know this context automatically
./synapse.py "add user authentication"
# → Knows to use FastAPI + async + SQLAlchemy 2.0
```

---

## 🔍 Search the Web

```bash
# Inside interactive mode
You: /search latest Python 3.13 features
🔍 Searching...
[shows search results]
```

Or one-shot:
```bash
./synapse.py --search "Python 3.13 features"
```

---

## 🛠️ Use Skills

```bash
# TDD skill auto-loads when you mention it
./synapse.py "using TDD, add a payment module"
🛠️ Skills: tdd
Assistant: 
Let's follow TDD:
1. RED: Write failing test
2. GREEN: Make it pass
3. REFACTOR: Clean up
...
```

---

## 📊 Check Status

```bash
# In interactive mode
You: /stats
📊 Session Stats:
   Session ID: 20260301_143022
   Messages: 12 total
   Context: 23% used
   Remaining: 98,432 tokens

💾 Cache Stats:
   Entries: 15
   Size: 0.5 MB
```

---

## 🎓 Learn More

```bash
# Complete guide
cat USAGE_GUIDE.md

# Product specification
cat PRODUCT_PLAN.md

# Technical architecture
cat ARCHITECTURE.md
```

---

## ⚡ Pro Tips

1. **Use Star Commands** for consistent responses
   - `*dev` when writing code
   - `*debug` when fixing bugs
   - `*plan` when designing architecture

2. **Remember Once, Use Forever**
   - `--remember "Uses FastAPI"` saves for entire project

3. **Save Important Sessions**
   - `/save` after complex work
   - `/load <id>` to resume later

4. **Compact Regularly**
   - `/compact` every ~20 messages
   - Keeps context window healthy

5. **Search First**
   - `/search` for current information
   - No API key needed!

---

## ❓ Need Help?

```bash
# Show all options
./synapse.py --help

# Show commands in app
You: /help

# Check configuration
./synapse.py --config
```

---

## 🎉 You're Ready!

Start chatting:
```bash
./synapse.py
```

**Welcome to AI_SYNAPSE!** 🚀
