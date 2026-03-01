# AI_SYNAPSE — Product Plan

## 1. Problem Statement

### Current Pain Points

| Pain Point | Current Reality | Impact |
|------------|-----------------|--------|
| **Free AI uncertainty** | Kilo offers free Kimi K2.5 today, but may remove it tomorrow | Workflow disruption, re-learning new tools |
| **No intelligent routing** | User must manually choose which AI to use for each task | Wasted time, suboptimal model selection |
| **No context memory** | Each session starts fresh, no project knowledge persists | Repeated explanations, inconsistent quality |
| **No workflow rules** | No automatic enforcement of coding standards or processes | Inconsistent output, forgotten best practices |
| **No skill system** | Can't load specialized workflows (TDD, debugging, etc.) on demand | Manual guidance every time |
| **Multiple CLI tools** | Kilo, Kimi, Groq, Gemini — each with different interfaces | Context switching overhead |

### User Quote
> "I generally login to kilo and I enter more generic natural language, not simple statement... what if tomorrow kilo removes these free models?"

**Core Problem:** Need a **future-proof, intelligent AI CLI** that adapts to the user's workflow, persists project knowledge, and automatically handles provider changes.

---

## 2. Idea & Solution

### Product Name: **AI_SYNAPSE**

**Tagline:** *"Your intelligent bridge to AI — adaptive, persistent, and future-proof"*

### Core Concept

AI_SYNAPSE is a **universal AI CLI orchestrator** that:

1. **Bridges** multiple AI providers (Kilo, Groq, Gemini, Kimi paid)
2. **Orchestrates** intelligent routing, context management, and workflows
3. **Shell** interface that feels natural and remembers everything

### Key Differentiators

| Feature | Existing Tools | AI_SYNAPSE |
|---------|----------------|------------|
| Multi-provider | LiteLLM, LLMSwap | ✅ Yes + **Smart fallbacks** |
| CARL rules | ❌ None | ✅ **Context-aware rule injection** |
| Project memory | ❌ None | ✅ **Persistent project knowledge** |
| Skill system | ❌ None | ✅ **Progressive skill loading** |
| Provider resilience | Manual switching | ✅ **Automatic fallback chain** |
| Natural language | Basic | ✅ **Optimized for long-form input** |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AI_SYNAPSE CLI                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     USER INTERFACE LAYER                         │   │
│  │  • Natural language input processing                             │   │
│  │  • Streaming output display                                      │   │
│  │  • Conversation history management                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      CARL SYSTEM (Core)                          │   │
│  │  • Keyword-based rule injection                                  │   │
│  │  • Star-commands (*dev, *review, *debug)                         │   │
│  │  • Context bracket management (FRESH→CRITICAL)                   │   │
│  │  • Domain-specific rule loading (PYTHON, FRONTEND, etc.)         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     SKILL SYSTEM                                 │   │
│  │  • Progressive disclosure (metadata → full content)              │   │
│  │  • Auto-trigger based on intent                                  │   │
│  │  • Manual trigger via --skill flag                               │   │
│  │  • Skills: TDD, debugging, brainstorming, FastAPI, React, etc.   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     MEMORY SYSTEM                                │   │
│  │  • Project-specific MEMORY.md auto-loading                       │   │
│  │  • Key patterns, gotchas, architecture decisions                 │   │
│  │  • User preferences persistence                                  │   │
│  │  • Topic-specific memory files (railway-deploy.md, etc.)         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   PROVIDER ROUTER                                │   │
│  │                                                                  │   │
│  │   Priority Chain:                                                │   │
│  │   1. Kilo (free) → Kimi K2.5, MiniMax M2.5, Qwen 235B          │   │
│  │   2. Groq (free) → Llama 3.3 70B, Qwen3 32B                     │   │
│  │   3. Gemini (free) → Gemini 2.5 Flash (1M context)              │   │
│  │   4. Kimi (paid) → Your paid Kimi K2.5 (ultimate backup)        │   │
│  │   5. Local → Ollama qwen2.5-coder:7b (offline backup)           │   │
│  │                                                                  │   │
│  │   Auto-fallback on: rate limits, errors, provider unavailable   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   TOOL INTEGRATION                               │   │
│  │  • File read/write (Read, Edit, Write)                          │   │
│  │  • Command execution (Bash)                                      │   │
│  │  • File search (Glob, Grep)                                      │   │
│  │  • Web search (DuckDuckGo)                                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. How to Build (Development Plan)

### Phase 1: Foundation (Week 1)
**Goal:** Basic CLI with provider routing

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Project setup, config system, provider abstraction | `config/`, `providers/base.py` |
| 2 | Kilo provider implementation | `providers/kilo.py` |
| 3 | Groq & Gemini providers | `providers/groq.py`, `providers/gemini.py` |
| 4 | Provider router with fallback logic | `core/router.py` |
| 5 | Basic CLI entry point | `synapse.py`, basic chat loop |
| 6-7 | Testing, debugging, documentation | Working MVP with routing |

**End of Phase 1:** `synapse "hello"` works and tries Kilo → Groq → Gemini → Kimi paid

### Phase 2: CARL System (Week 2)
**Goal:** Rule injection and context management

| Day | Task | Deliverable |
|-----|------|-------------|
| 8 | CARL manifest system | `config/carl/manifest` |
| 9 | Global rules + domain rules structure | `config/carl/global`, `config/carl/python` |
| 10 | Keyword matching engine | `core/carl.py` - `process_message()` |
| 11 | Star-commands (*dev, *review, etc.) | `config/carl/commands` |
| 12 | Context bracket calculation | FRESH/MODERATE/DEPLETED/CRITICAL |
| 13-14 | Integration + testing | CARL rules injected into prompts |

**End of Phase 2:** `synapse "*dev fix the bug"` loads DEV rules automatically

### Phase 3: Memory System (Week 3)
**Goal:** Project knowledge persistence

| Day | Task | Deliverable |
|-----|------|-------------|
| 15 | Memory directory structure | `memory/` organization |
| 16 | MEMORY.md auto-loading | `core/memory.py` |
| 17 | Project detection (git root or cwd) | `detect_project()` |
| 18 | Memory CRUD operations | `remember()`, `recall()`, `forget()` |
| 19 | CLI commands for memory | `synapse --remember`, `synapse --recall` |
| 20-21 | Integration + testing | Memory loads automatically per project |

**End of Phase 3:** Switch projects, different memory loads automatically

### Phase 4: Skill System (Week 4)
**Goal:** Progressive skill loading

| Day | Task | Deliverable |
|-----|------|-------------|
| 22 | Skill directory structure | `skills/` with metadata files |
| 23 | Progressive disclosure implementation | Level 1 (metadata) → Level 2 (full) |
| 24 | Skill auto-detection | Match user intent to skill |
| 25 | Manual skill loading | `--skill` flag |
| 26 | Built-in skills: TDD, debugging, brainstorming | `skills/tdd/`, `skills/debugging/` |
| 27-28 | Integration + documentation | Skills work seamlessly |

**End of Phase 4:** `synapse "using TDD, add auth"` loads TDD skill automatically

### Phase 5: Polish & Release (Week 5-6)
**Goal:** Production-ready tool

| Task | Description |
|------|-------------|
| Streaming output | Real-time response display |
| Conversation history | Save/resume sessions |
| Configuration wizard | `synapse --setup` interactive setup |
| Error handling | Graceful degradation, clear error messages |
| Documentation | README, usage examples, API docs |
| Testing | Unit tests, integration tests |
| Release | v1.0.0 tagged release |

---

## 5. How It Helps (Use Cases)

### Use Case 1: Natural Language Development

```bash
# Instead of:
kilo run "fix auth"

# You use:
synapse "I'm having trouble with authentication. When users try to log in 
with uppercase emails, it fails silently. The auth code is in backend/auth.py. 
Can you help me fix this and add proper error handling?"

# What happens:
# 1. CARL detects: "auth", "backend/auth.py", "fix", "error handling"
# 2. Loads: PYTHON + API + SECURITY rules
# 3. Loads project memory (FastAPI + PostgreSQL context)
# 4. Tries Kilo (Kimi K2.5) first → gets excellent response
# 5. Response follows your coding standards automatically
```

### Use Case 2: Long Conversation with Context Management

```bash
# Session continues for 20+ turns
synapse "Add user authentication"
synapse "Now add password reset"
synapse "Add email verification"
# ... 15 more turns ...

# When context approaches limit:
# CARL enters DEPLETED bracket
# Suggests: "Context filling up. Start new session or /compact?"

synapse /compact
# Summarizes entire conversation
# Frees up 60% of context
# Continues seamlessly
```

### Use Case 3: Provider Resilience

```bash
# Day 1: Kilo works great
synapse "Build a REST API"  # Uses Kilo (free Kimi K2.5)

# Day 30: Kilo removes free tier
synapse "Build a REST API"  
# Detects Kilo failure
# Automatically falls back to Groq
# Shows: "⚠️ Kilo unavailable. Using Groq (Llama 3.3 70B)..."
# Your workflow continues unchanged

# Day 60: All free tiers exhausted
synapse "Build a REST API"
# Falls back to your paid Kimi
# Shows: "💎 Using Kimi K2.5 (paid)"
# Still works, just costs money now
```

### Use Case 4: Project Memory

```bash
cd ~/Projects/my-fastapi-app

# First time:
synapse --remember "This project uses FastAPI with Pydantic v2, 
PostgreSQL with SQLAlchemy 2.0, deployed on Railway. 
Always use async/await for DB operations."

# Every subsequent command automatically knows:
synapse "add user authentication"  # Knows to use FastAPI + async
synapse "create database migration"  # Knows SQLAlchemy 2.0 patterns
synapse "deploy"  # Knows Railway deployment process
```

### Use Case 5: Skill-Assisted Workflows

```bash
# TDD workflow automatically enforced:
synapse "using TDD, add payment processing"
# Loads TDD skill
# 1. Asks: "What should the payment function do?"
# 2. You describe it
# 3. It writes failing test first
# 4. You confirm
# 5. It writes minimal code
# 6. You confirm
# 7. It refactors
# 8. Done

# Debugging workflow:
synapse "*debug why is the cron job failing"
# Loads DEBUG skill
# 1. Gathers context (reads cron config, logs)
# 2. Forms hypothesis
# 3. Suggests tests to verify
# 4. Root cause analysis
# 5. Fix proposal
```

---

## 6. Accuracy Assessment

### Expected Performance vs Claude Code

| Capability | Claude Code | AI_SYNAPSE | Expected Accuracy |
|------------|-------------|------------|-------------------|
| **Code generation** | 95% | 80-85% | Good, occasional misses |
| **Debugging** | 90% | 75-80% | Decent, may need guidance |
| **Architecture** | 85% | 70-75% | Okay for simple cases |
| **Long context** | 95% | 85-90% | Good with 128K+ models |
| **Tool use** | 95% | 70-75% | Inconsistent on free models |
| **Reasoning** | 90% | 75-80% | Simpler reasoning chains |

### Why the Gap?

1. **Model size:** Claude Opus 175B+ vs free models 32B-70B
2. **Training:** Claude is fine-tuned for tool use and coding
3. **Context:** Claude has 200K, best free is 128K

### Mitigation Strategies

| Strategy | Implementation |
|----------|----------------|
| **CARL rules** | Enforce best practices automatically |
| **Skills** | Provide structured workflows |
| **Memory** | Persist project-specific knowledge |
| **Fallback chain** | Use best available model |
| **Self-correction** | Build in verification steps |

### Realistic Expectation

> **AI_SYNAPSE will deliver 75-85% of Claude Code's capability at $0 cost (while free tiers last), with graceful degradation to paid options.**

---

## 7. Progress Tracking

### Milestone Tracking

| Milestone | Target Date | Status | Notes |
|-----------|-------------|--------|-------|
| Phase 1: Provider routing | Week 1 | ⬜ Not Started | Foundation |
| Phase 2: CARL system | Week 2 | ⬜ Not Started | Core intelligence |
| Phase 3: Memory system | Week 3 | ⬜ Not Started | Persistence |
| Phase 4: Skill system | Week 4 | ⬜ Not Started | Workflows |
| Phase 5: Polish & release | Week 6 | ⬜ Not Started | Production |
| v1.0.0 Release | Week 6 | ⬜ Not Started | Ready to use |

### Daily Standup Format (for AI collaboration)

Each day, update this file with:

```markdown
## Day X - [Date]

### Yesterday
- Completed: [What was done]
- Blockers: [Any issues]

### Today
- Goal: [What we're building]
- Approach: [How we're building it]
- Files: [What files to modify/create]

### Notes
- [Any decisions made]
- [Technical discoveries]
- [Next day considerations]
```

### Resume Capability

**Any AI tool (Kimi, Kilo, Claude, etc.) can pick up this project by reading:**

1. **PRODUCT_PLAN.md** ← This file
2. **PROGRESS.md** ← Daily updates
3. **ARCHITECTURE.md** ← Technical design
4. **TODO.md** ← Current tasks

**Resume workflow:**
```bash
# AI reads these files:
cat PRODUCT_PLAN.md
head -100 PROGRESS.md
cat TODO.md

# AI understands current state and continues
```

---

## 8. How to Use It

### Installation

```bash
# Clone the repo
git clone https://github.com/niranjan/ai-synapse.git ~/.ai-synapse

# Install dependencies
pip install -r ~/.ai-synapse/requirements.txt

# Add to PATH
echo 'export PATH="$HOME/.ai-synapse:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Run setup wizard
synapse --setup
```

### Configuration

```bash
# Interactive setup:
synapse --setup

# Or manual config at ~/.synapse/config.yaml:
providers:
  kilo:
    enabled: true
    models:
      - kilo/moonshotai/kimi-k2.5:free
      - kilo/minimax/minimax-m2.5:free
  
  groq:
    enabled: true
    api_key: ${GROQ_API_KEY}
    models:
      - llama-3.3-70b-versatile
  
  gemini:
    enabled: true
    api_key: ${GEMINI_API_KEY}
    models:
      - gemini-2.5-flash
  
  kimi:
    enabled: true
    api_key: ${KIMI_API_KEY}  # Your paid backup
    models:
      - kimi-k2.5

carl:
  enabled: true
  domains: [python, frontend, database, api, security]

memory:
  enabled: true
  location: ~/.synapse/memory/

skills:
  enabled: true
  location: ~/.synapse/skills/
```

### Daily Usage

```bash
# Basic usage (natural language):
synapse "explain how Python decorators work"

# With star-command:
synapse "*dev add user authentication to the API"

# With explicit skill:
synapse --skill tdd "add payment processing module"

# Multi-line input:
synapse << 'EOF'
I'm building a FastAPI application and need to implement JWT authentication.
The app should support access tokens and refresh tokens.
Users should be able to login, logout, and refresh their tokens.
Can you help me design and implement this?
EOF

# Check which provider is being used:
synapse --verbose "hello"
# Output: "Using Kilo (kimi-k2.5:free)..."

# View current config:
synapse --config

# Remember something:
synapse --remember "Always use Pydantic v2 models in this project"

# View project memory:
synapse --memory

# Compact conversation (clear context):
synapse /compact

# New session:
synapse /new

# Get help:
synapse --help
```

### Project Workflow

```bash
# 1. Navigate to project
cd ~/Projects/my-fastapi-app

# 2. Initialize memory (one time):
synapse --remember "This is a FastAPI + PostgreSQL app using SQLAlchemy 2.0"

# 3. Work naturally:
synapse "add a new endpoint for user profile updates"
synapse "write tests for the auth module"
synapse "*review the changes we made today"

# 4. Memory persists automatically
```

---

## 9. How to Test It

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific module
pytest tests/test_carl.py
pytest tests/test_router.py
pytest tests/test_memory.py
```

### Integration Tests

```bash
# Test provider routing
cd tests/integration
python test_routing.py

# Test with real APIs (uses small requests)
python test_live_providers.py

# Test CARL rule injection
python test_carl_integration.py
```

### Manual Testing Checklist

| Test | Command | Expected Result |
|------|---------|-----------------|
| Basic chat | `synapse "hello"` | Response from Kilo or fallback |
| Provider fallback | Temporarily disable Kilo | Falls back to Groq/Gemini |
| CARL rules | `synapse "*dev list files"` | Loads DEV rules |
| Memory | `synapse --remember "test"` && `synapse --memory` | Shows "test" |
| Skills | `synapse --skill tdd "add function"` | Loads TDD workflow |
| Long conversation | 20+ turns | Context bracket changes, suggests /compact |
| Multi-line | `synapse << 'EOF'...` | Handles multi-line input |
| Config | `synapse --config` | Shows current configuration |

### Load Testing

```bash
# Test rate limiting and fallback
cd tests/load
python spam_requests.py --count 100
# Should automatically rotate providers, handle rate limits
```

### Error Testing

```bash
# Test with invalid API keys
export GROQ_API_KEY="invalid"
synapse "test"  # Should fallback to next provider

# Test with no internet
# Should show clear error, suggest offline mode

# Test with malformed input
synapse ""  # Should handle gracefully
```

---

## 10. Success Metrics

### v1.0.0 Release Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Reliability** | 99%+ uptime | Successful requests / total requests |
| **Provider fallback** | <2s failover | Time to switch when provider fails |
| **Response quality** | 75%+ "helpful" rating | User feedback on responses |
| **Context retention** | 20+ turns | Conversation length before /compact needed |
| **Memory accuracy** | 95%+ | Project context correctly loaded |
| **Skill loading** | <1s | Time to detect and load skill |
| **Setup time** | <5 minutes | Time from clone to first working command |

### User Satisfaction Targets

- **Daily active users:** 1 (you!)
- **Retention:** Use it for 90%+ of AI-assisted tasks
- **Net Promoter Score:** Would you recommend to a friend?

---

## 11. Future Roadmap (Post v1.0)

### v1.1: Enhanced Skills
- More built-in skills (React, Docker, AWS, etc.)
- Skill marketplace
- Self-learning skills

### v1.2: Agent Teams
- Multi-agent orchestration
- Parallel task execution
- Agent spawning with isolated contexts

### v1.3: IDE Integration
- VS Code extension
- JetBrains plugin
- Vim/Neovim integration

### v1.4: Collaborative Features
- Team memory sharing
- Shared skill libraries
- Usage analytics

---

## 12. Appendices

### Appendix A: File Structure

```
AI_SYNAPSE/
├── PRODUCT_PLAN.md          ← This file
├── PROGRESS.md              ← Daily updates
├── ARCHITECTURE.md          ← Technical design
├── TODO.md                  ← Current tasks
├── README.md                ← User documentation
├── LICENSE                  ← MIT License
├── requirements.txt         ← Python dependencies
├── setup.py                 ← Package setup
├── synapse.py               ← CLI entry point
│
├── core/                    ← Core modules
│   ├── __init__.py
│   ├── router.py            ← Provider routing
│   ├── carl.py              ← CARL system
│   ├── memory.py            ← Memory system
│   ├── skills.py            ← Skill system
│   ├── conversation.py      ← Conversation management
│   └── config.py            ← Configuration
│
├── providers/               ← Provider implementations
│   ├── __init__.py
│   ├── base.py              ← Abstract base class
│   ├── kilo.py              ← Kilo CLI integration
│   ├── groq.py              ← Groq API
│   ├── gemini.py            ← Gemini API
│   ├── kimi.py              ← Kimi API (paid)
│   └── ollama.py            ← Local models
│
├── config/                  ← Configuration files
│   ├── default.yaml         ← Default config
│   └── carl/                ← CARL rules
│       ├── manifest
│       ├── global
│       ├── context
│       ├── commands
│       └── domains/
│           ├── python
│           ├── frontend
│           └── ...
│
├── skills/                  ← Skill definitions
│   ├── tdd/
│   │   ├── metadata.json
│   │   └── SKILL.md
│   ├── debugging/
│   ├── brainstorming/
│   └── ...
│
├── memory/                  ← Project memories (gitignored)
│   └── .gitkeep
│
├── utils/                   ← Utilities
│   ├── __init__.py
│   ├── file_utils.py
│   ├── token_utils.py
│   └── display.py
│
└── tests/                   ← Test suite
    ├── unit/
    ├── integration/
    └── load/
```

### Appendix B: Dependencies

```
# Core
pyyaml>=6.0
httpx>=0.24.0
rich>=13.0.0          # Terminal UI
click>=8.0.0          # CLI framework
pydantic>=2.0.0       # Data validation

# Provider SDKs
# (Most use HTTP API directly, no SDK needed)
google-generativeai   # Gemini (optional)

# Dev
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
mypy>=1.0.0
```

---

**Document Version:** 1.0  
**Last Updated:** February 28, 2026  
**Next Review:** Daily during development

---

*Ready to start building! Next: Create ARCHITECTURE.md and begin Phase 1.*
