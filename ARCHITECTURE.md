# AI_SYNAPSE — Technical Architecture

## 1. System Overview

### Design Principles

1. **Modularity:** Each component (provider, CARL, memory, skills) is independent
2. **Extensibility:** Easy to add new providers or skills
3. **Resilience:** Graceful degradation when providers fail
4. **Transparency:** User always knows which provider is being used
5. **Simplicity:** Complex orchestration, simple interface

### Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Language** | Python 3.9+ | Rich ecosystem, async support |
| **CLI Framework** | Click | Industry standard, clean API |
| **HTTP Client** | HTTPX | Async support, fast |
| **Config** | YAML + Pydantic | Human-readable, type-safe |
| **Terminal UI** | Rich | Beautiful output, streaming |
| **Logging** | structlog | Structured logging |

---

## 2. Component Architecture

### 2.1 Provider System

```python
# providers/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any

class Provider(ABC):
    """Abstract base class for all AI providers."""
    
    name: str
    priority: int  # Lower = higher priority
    
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate completion. Yields text chunks if stream=True."""
        pass
    
    @abstractmethod
    async def check_available(self) -> bool:
        """Check if provider is available (API key valid, service up)."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass
```

#### Provider Implementations

| Provider | Integration Method | Notes |
|----------|-------------------|-------|
| **Kilo** | Subprocess call to `kilo run` | Wraps CLI output |
| **Groq** | HTTP API | Direct API calls |
| **Gemini** | HTTP API | Google's Generative Language API |
| **Kimi** | HTTP API | Moonshot AI API |
| **Ollama** | HTTP API (localhost:11434) | Local models |

### 2.2 Router System

```python
# core/router.py
class ProviderRouter:
    """Routes requests to available providers with fallback."""
    
    def __init__(self, config: Config):
        self.providers = self._load_providers(config)
        self.current_provider: Provider | None = None
    
    async def complete(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        """Try providers in priority order until one succeeds."""
        for provider in self.providers:
            try:
                if await provider.check_available():
                    self.current_provider = provider
                    async for chunk in provider.complete(messages, **kwargs):
                        yield chunk
                    return
            except Exception as e:
                logger.warning(f"{provider.name} failed: {e}")
                continue
        
        raise AllProvidersFailed("No providers available")
```

### 2.3 CARL System

```python
# core/carl.py
class CARLSystem:
    """Context Augmentation & Reinforcement Layer."""
    
    def __init__(self, config_path: Path):
        self.manifest = self._load_manifest(config_path / "manifest")
        self.domains = self._load_domains(config_path / "domains")
        self.global_rules = self._load_rules(config_path / "global")
        self.commands = self._load_commands(config_path / "commands")
    
    def process_message(
        self,
        message: str,
        context_usage: float  # 0.0 to 1.0
    ) -> CARLResult:
        """Process user message and return rules to inject."""
        
        # 1. Check star-commands
        command_rules = self._parse_star_commands(message)
        
        # 2. Keyword matching
        matched_domains = self._match_domains(message)
        
        # 3. Calculate context bracket
        bracket = self._calculate_bracket(context_usage)
        
        # 4. Build injection
        return CARLResult(
            rules=self.global_rules + command_rules + matched_domains,
            bracket=bracket,
            modified_message=self._remove_star_commands(message)
        )
    
    def _calculate_bracket(self, usage: float) -> ContextBracket:
        if usage > 0.75: return ContextBracket.CRITICAL
        elif usage > 0.60: return ContextBracket.DEPLETED
        elif usage > 0.40: return ContextBracket.MODERATE
        else: return ContextBracket.FRESH
```

#### CARL Configuration Structure

```yaml
# config/carl/manifest
devmode: false

domains:
  global:
    state: active
    always_on: true
  
  context:
    state: active
    always_on: true
  
  python:
    state: active
    always_on: false
    recall_keywords: [python, fastapi, flask, django, pytest, .py]
    exclude_keywords: [snake, monty]
  
  frontend:
    state: active
    always_on: false
    recall_keywords: [react, vue, angular, frontend, css, html]
```

### 2.4 Memory System

```python
# core/memory.py
class MemorySystem:
    """Project-specific knowledge persistence."""
    
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
    
    def load_for_project(self, project_path: Path) -> str:
        """Load MEMORY.md for current project."""
        project_key = self._sanitize_path(project_path)
        memory_file = self.memory_dir / project_key / "MEMORY.md"
        
        if memory_file.exists():
            content = memory_file.read_text()
            return "\n".join(content.split("\n")[:200])  # First 200 lines
        return ""
    
    def remember(self, project_path: Path, key_info: str):
        """Add information to project memory."""
        project_key = self._sanitize_path(project_path)
        memory_file = self.memory_dir / project_key / "MEMORY.md"
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(memory_file, "a") as f:
            f.write(f"\n- {key_info}")
    
    def _sanitize_path(self, path: Path) -> str:
        """Convert path to safe directory name."""
        return str(path).replace("/", "-").replace("\\", "-")
```

### 2.5 Skill System

```python
# core/skills.py
class SkillSystem:
    """Progressive skill loading based on intent."""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.metadata = self._load_all_metadata()
    
    def detect_skills(self, message: str) -> list[Skill]:
        """Auto-detect applicable skills from user message."""
        detected = []
        for skill_meta in self.metadata:
            if self._intent_matches(message, skill_meta.triggers):
                detected.append(self._load_full_skill(skill_meta))
        return detected
    
    def get_by_name(self, name: str) -> Skill | None:
        """Load skill by explicit name."""
        for skill_meta in self.metadata:
            if skill_meta.name == name:
                return self._load_full_skill(skill_meta)
        return None
    
    def _load_full_skill(self, meta: SkillMetadata) -> Skill:
        """Load full SKILL.md content (Level 2 disclosure)."""
        skill_path = self.skills_dir / meta.name / "SKILL.md"
        content = skill_path.read_text()
        return Skill(metadata=meta, content=content)
```

#### Skill Structure

```
skills/
├── tdd/
│   ├── metadata.json       # Level 1: Always loaded (~100 bytes)
│   └── SKILL.md            # Level 2: Loaded when triggered (~1-2KB)
│
└── debugging/
    ├── metadata.json
    └── SKILL.md
```

```json
// metadata.json
{
  "name": "tdd",
  "description": "Test-driven development workflow",
  "triggers": ["tdd", "test-driven", "write tests", "testing"],
  "priority": "high"
}
```

### 2.6 Conversation Management

```python
# core/conversation.py
class Conversation:
    """Manages conversation state and context window."""
    
    def __init__(self, max_tokens: int = 128000):
        self.messages: list[dict] = []
        self.max_tokens = max_tokens
        self.total_tokens = 0
    
    def add_message(self, role: str, content: str):
        """Add message to conversation."""
        self.messages.append({"role": role, "content": content})
        self._update_token_count()
    
    def get_context_usage(self) -> float:
        """Return 0.0 to 1.0 usage ratio."""
        return self.total_tokens / self.max_tokens
    
    def compact(self) -> str:
        """Summarize and compress conversation."""
        # Implementation: Summarize older messages
        summary = self._summarize(self.messages[:-10])  # Keep last 10
        self.messages = [{"role": "system", "content": summary}] + self.messages[-10:]
        self._update_token_count()
        return summary
```

---

## 3. Data Flow

### 3.1 Request Flow

```
User Input
    ↓
[CLI] Parse arguments, read stdin
    ↓
[CARL] Process message
    ├── Detect star-commands
    ├── Match domains (keywords)
    ├── Calculate context bracket
    └── Return rules + modified message
    ↓
[Memory] Load project context
    ├── Detect project (git root or cwd)
    ├── Load MEMORY.md
    └── Return project context
    ↓
[Skills] Detect applicable skills
    ├── Match message to skill triggers
    ├── Load full skill content
    └── Return skill instructions
    ↓
[Conversation] Build message list
    ├── System prompt (base)
    ├── CARL rules
    ├── Project memory
    ├── Skill instructions
    ├── History (previous messages)
    └── User message
    ↓
[Router] Send to provider
    ├── Try Kilo first
    │   └── Success → Stream response
    ├── Kilo fails → Try Groq
    │   └── Success → Stream response
    ├── Groq fails → Try Gemini
    │   └── Success → Stream response
    └── All fail → Error
    ↓
[CLI] Display streaming response
    ↓
[Conversation] Save to history
```

### 3.2 Context Assembly

```python
def build_system_prompt(
    base_prompt: str,
    carl_result: CARLResult,
    memory: str,
    skills: list[Skill]
) -> str:
    """Build full system prompt from components."""
    
    parts = [base_prompt]
    
    # Add CARL rules
    if carl_result.rules:
        parts.append("<carl-rules>")
        parts.append(f"<bracket>{carl_result.bracket}</bracket>")
        parts.append("<rules>")
        for rule in carl_result.rules:
            parts.append(f"- {rule}")
        parts.append("</rules>")
        parts.append("</carl-rules>")
    
    # Add project memory
    if memory:
        parts.append("<project-memory>")
        parts.append(memory)
        parts.append("</project-memory>")
    
    # Add skill instructions
    for skill in skills:
        parts.append(f"<skill-{skill.name}>")
        parts.append(skill.content)
        parts.append(f"</skill-{skill.name}>")
    
    return "\n\n".join(parts)
```

---

## 4. Configuration Schema

### 4.1 Main Config File

```yaml
# ~/.synapse/config.yaml
version: "1.0"

# Provider configuration
providers:
  kilo:
    enabled: true
    priority: 1  # Try first
    models:
      - name: kilo/moonshotai/kimi-k2.5:free
        default: true
      - name: kilo/minimax/minimax-m2.5:free
      - name: kilo/qwen/qwen3-235b-a22b-thinking-2507
  
  groq:
    enabled: true
    priority: 2
    api_key: ${GROQ_API_KEY}  # From env var
    models:
      - name: llama-3.3-70b-versatile
        default: true
      - name: qwen/qwen3-32b
  
  gemini:
    enabled: true
    priority: 3
    api_key: ${GEMINI_API_KEY}
    models:
      - name: gemini-2.5-flash
        default: true
  
  kimi:
    enabled: true
    priority: 100  # Last resort (paid)
    api_key: ${KIMI_API_KEY}
    models:
      - name: kimi-k2.5
        default: true
  
  ollama:
    enabled: false
    priority: 99
    base_url: http://localhost:11434
    models:
      - name: qwen2.5-coder:7b
        default: true

# CARL configuration
carl:
  enabled: true
  config_path: ~/.synapse/carl
  
  # Domain settings
  domains:
    - name: python
      recall: [python, fastapi, flask, django, pytest, .py, pip]
      exclude: [snake, monty]
    
    - name: frontend
      recall: [react, vue, angular, svelte, css, html, frontend, ui]
    
    - name: database
      recall: [database, postgres, mysql, sqlite, sql, migration, orm]
    
    - name: api
      recall: [api, endpoint, rest, graphql, cors, jwt, auth]
    
    - name: deploy
      recall: [deploy, docker, railway, aws, production, ci/cd]
    
    - name: security
      recall: [security, auth, password, encrypt, hash, xss, injection]

# Memory configuration
memory:
  enabled: true
  location: ~/.synapse/memory
  max_lines: 200  # Truncate MEMORY.md after this

# Skill configuration
skills:
  enabled: true
  location: ~/.synapse/skills
  auto_detect: true

# Conversation settings
conversation:
  max_tokens: 128000
  compact_threshold: 0.75  # Suggest /compact at 75%
  history_limit: 100  # Max messages to keep

# UI settings
ui:
  stream: true
  show_provider: true  # Show which provider is being used
  syntax_highlight: true
  theme: dark
```

### 4.2 Environment Variables

```bash
# Provider API Keys (optional, can use config file)
export GROQ_API_KEY="gsk_..."
export GEMINI_API_KEY="..."
export KIMI_API_KEY="..."

# Synapse settings
export SYNAPSE_CONFIG="~/.synapse/config.yaml"
export SYNAPSE_LOG_LEVEL="INFO"
export SYNAPSE_DEBUG="false"
```

---

## 5. Error Handling Strategy

### 5.1 Provider Errors

| Error | Handling |
|-------|----------|
| Rate limit | Log warning, try next provider |
| Invalid API key | Log error, disable provider, continue |
| Timeout | Cancel, try next provider |
| Service unavailable | Log error, try next provider |
| Invalid response | Log error, try next provider |

### 5.2 System Errors

| Error | Handling |
|-------|----------|
| Config not found | Create default config, warn user |
| Invalid config | Show validation errors, exit |
| No providers available | Clear error message, suggest setup |
| Disk full (memory) | Log warning, continue without memory |

### 5.3 User Errors

| Error | Handling |
|-------|----------|
| Invalid command | Show help, suggest corrections |
| Invalid skill name | List available skills |
| No project detected | Continue without memory |

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/test_carl.py
def test_keyword_matching():
    carl = CARLSystem(test_config)
    result = carl.process_message("fix the python bug", 0.1)
    assert "python" in result.matched_domains

def test_star_command_parsing():
    carl = CARLSystem(test_config)
    result = carl.process_message("*dev fix the bug", 0.1)
    assert "*dev" not in result.modified_message
    assert any("code" in rule for rule in result.rules)

def test_context_brackets():
    carl = CARLSystem(test_config)
    assert carl._calculate_bracket(0.1) == ContextBracket.FRESH
    assert carl._calculate_bracket(0.5) == ContextBracket.MODERATE
    assert carl._calculate_bracket(0.8) == ContextBracket.CRITICAL
```

### 6.2 Integration Tests

```python
# tests/test_router.py
@pytest.mark.asyncio
async def test_provider_fallback():
    router = ProviderRouter(config_with_bad_kilo)
    
    # Kilo should fail, fallback to Groq
    chunks = []
    async for chunk in router.complete([{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    
    assert router.current_provider.name == "groq"
```

### 6.3 End-to-End Tests

```bash
# tests/e2e/test_cli.sh
#!/bin/bash
set -e

# Test basic chat
echo "Testing basic chat..."
OUTPUT=$(echo "hello" | synapse --provider groq)
[[ "$OUTPUT" == *"hello"* ]] || exit 1

# Test CARL rules
echo "Testing CARL..."
OUTPUT=$(synapse "*dev list files")
[[ "$OUTPUT" == *"code"* ]] || exit 1

# Test memory
echo "Testing memory..."
synapse --remember "test memory"
OUTPUT=$(synapse --memory)
[[ "$OUTPUT" == *"test memory"* ]] || exit 1

echo "All E2E tests passed!"
```

---

## 7. Performance Considerations

### 7.1 Startup Time

| Component | Target | Optimization |
|-----------|--------|--------------|
| Config loading | <100ms | Lazy loading, caching |
| Provider initialization | <200ms | Parallel initialization |
| CARL loading | <100ms | Load only active domains |
| Memory loading | <50ms | Async file read |
| **Total startup** | **<500ms** | **Acceptable** |

### 7.2 Runtime Performance

| Operation | Target |
|-----------|--------|
| Provider selection | <10ms |
| CARL processing | <50ms |
| Memory loading | <50ms |
| First token latency | Provider-dependent |
| Streaming throughput | Real-time |

### 7.3 Memory Usage

| Component | Max Memory |
|-----------|------------|
| Base system | ~50MB |
| Per conversation | ~10MB + context size |
| Config cache | ~5MB |
| **Total typical** | **~100-200MB** |

---

## 8. Security Considerations

### 8.1 API Key Handling

```python
# Never log API keys
logger.info(f"Using provider: {provider.name}")  # OK
logger.info(f"API key: {api_key}")  # NEVER!

# Load from environment or secure keyring
api_key = os.environ.get("GROQ_API_KEY") or keyring.get_password("synapse", "groq")
```

### 8.2 File Access

```python
# Restrict file access to project directory
def safe_read(path: Path) -> str:
    resolved = path.resolve()
    if not str(resolved).startswith(str(Path.cwd())):
        raise PermissionError("Access denied: outside project directory")
    return resolved.read_text()
```

### 8.3 Command Execution

- No automatic command execution
- All bash commands require user approval
- Maintain allowlist in config

---

## 9. Deployment

### 9.1 Installation Methods

```bash
# Method 1: pip install
pip install ai-synapse

# Method 2: Homebrew
brew install ai-synapse

# Method 3: Direct install
curl -sSL https://install.ai-synapse.dev | bash

# Method 4: Clone and install
git clone https://github.com/niranjan/ai-synapse.git
pip install -e ./ai-synapse
```

### 9.2 Update Mechanism

```bash
# Check for updates
synapse --update-check

# Auto-update
synapse --update
```

---

## 10. Future Extensions

### 10.1 Planned Features

| Feature | Description | Priority |
|---------|-------------|----------|
| Agent teams | Multi-agent orchestration | Medium |
| IDE plugins | VS Code, JetBrains | Medium |
| Cloud sync | Sync memory across devices | Low |
| Team sharing | Shared skills and memory | Low |
| Analytics | Usage tracking, insights | Low |

### 10.2 Plugin Architecture

```python
# plugins/base.py
class SynapsePlugin:
    """Plugin interface for extending Synapse."""
    
    def on_message(self, message: str) -> str | None:
        """Process message before CARL. Return modified or None."""
        pass
    
    def on_response(self, response: str) -> str:
        """Process response before display."""
        pass
```

---

**Document Version:** 1.0  
**Last Updated:** February 28, 2026  
**Next Review:** After Phase 1 completion

---

*Ready to implement! Start with providers/base.py and core/config.py*
