# Quick Start

## 1. Install

```bash
git clone https://github.com/niranjanshankarananda-prop/AI_SYNAPSE.git
cd AI_SYNAPSE
pip install -r requirements.txt
```

## 2. Set Up a Provider

Pick at least one:

```bash
# Option A: Kilo CLI (free, recommended)
brew install kiloai/tap/kilo
kilo auth

# Option B: Ollama (free, local)
brew install ollama
ollama serve &
ollama pull qwen2.5-coder:7b

# Option C: API key (any of these)
export GROQ_API_KEY='gsk_...'
export GEMINI_API_KEY='...'
export KIMI_API_KEY='...'
```

## 3. Run

```bash
# Single question
python3 synapse.py "read requirements.txt and count the lines" --yes

# Interactive mode
python3 synapse.py
```

## 4. What You'll See

```
  [tool] read({'file_path': 'requirements.txt'})
  [ok]    1| # AI_SYNAPSE — Dependencies ...
  [kilo/moonshotai/kimi-k2.5:free]
The file requirements.txt has 29 lines.
```

The AI reads files, runs commands, and answers based on actual results.

## 5. Key Commands

In interactive mode:

- `/help` — show all commands
- `/save` — save session
- `/search <query>` — web search
- `/compact` — free up context
- `exit` — quit

Star commands (prefix your message):

- `*dev` — code-focused mode
- `*debug` — systematic debugging
- `*plan` — explore options first

## 6. Configuration

Edit `~/.synapse/config.yaml` to change provider priorities, models, or subsystem settings.

Full documentation: [README.md](README.md)
