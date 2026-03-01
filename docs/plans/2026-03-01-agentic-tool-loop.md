# Agentic Tool Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform AI_SYNAPSE from a chat forwarder into a full agentic coding assistant where the AI can autonomously read files, edit code, run commands, and reason about results — like Claude Code.

**Architecture:** Hybrid approach — native function calling for Groq/Gemini/Kimi (OpenAI-compatible and Gemini-native APIs), prompt-based tool parsing for Kilo CLI. A shared `AgentLoop` orchestrates: send message with tool schemas → receive response → if tool calls, execute and loop back → if text, display and stop. Max 50 iterations with permission system.

**Tech Stack:** Python 3.9+, httpx (async HTTP), Rich (terminal UI), Pydantic (config), asyncio

---

## Task 1: Create AgentResponse — Unified Response Type

**Files:**
- Create: `core/agent_response.py`

**Step 1: Create the unified response dataclass**

```python
"""
AI_SYNAPSE — Agent Response Types

Unified response format for all providers, regardless of whether they use
native function calling or prompt-based tool parsing.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ResponseType(Enum):
    """Type of agent response chunk."""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


@dataclass
class ToolCall:
    """A single tool call from the AI."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_call_id: str = ""
    name: str = ""
    output: str = ""
    is_error: bool = False


@dataclass
class AgentResponse:
    """
    Unified response from any provider.

    Can represent:
    - A text chunk (streaming or complete)
    - A tool call request from the AI
    - A tool result to send back
    - An error
    - A done signal
    """
    type: ResponseType
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_result: Optional[ToolResult] = None
    finish_reason: Optional[str] = None  # "stop", "tool_calls", "length"
```

**Step 2: Commit**

```bash
git add core/agent_response.py
git commit -m "feat: add unified AgentResponse types for tool loop"
```

---

## Task 2: Extend Provider Base Class for Tool Support

**Files:**
- Modify: `providers/base.py`

**Step 1: Add tool support to Provider ABC**

Add these after line 108 (after `default_model` property) in `providers/base.py`:

```python
@property
def supports_function_calling(self) -> bool:
    """Whether this provider supports native function calling."""
    return False

async def complete_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    model: Optional[str] = None,
    stream: bool = True,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> AsyncIterator:
    """
    Generate completion with tool calling support.

    Default implementation falls back to regular complete().
    Providers that support function calling should override this.

    Args:
        messages: Conversation messages
        tools: Tool schemas in OpenAI format
        model: Model to use
        stream: Whether to stream

    Yields:
        AgentResponse objects (text chunks or tool calls)
    """
    # Default: no tool support, just stream text
    from core.agent_response import AgentResponse, ResponseType
    async for chunk in self.complete(messages, model, stream, temperature, max_tokens, **kwargs):
        yield AgentResponse(type=ResponseType.TEXT, text=chunk)
    yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")
```

**Step 2: Commit**

```bash
git add providers/base.py
git commit -m "feat: add tool calling support to Provider base class"
```

---

## Task 3: Add Function Calling to Groq Provider

**Files:**
- Modify: `providers/groq.py`

**Step 1: Fix the import bug and add function calling**

Replace the entire `providers/groq.py` with:

```python
"""
AI_SYNAPSE — Groq Provider

Provider implementation for Groq API.
Groq offers fast inference with free tier: 14,400 req/day, 60 RPM.
"""

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from providers.base import (
    Provider,
    ProviderConfig,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ServiceUnavailableError
)
from core.agent_response import AgentResponse, ResponseType, ToolCall

logger = logging.getLogger(__name__)


class GroqProvider(Provider):
    """
    Provider implementation for Groq API.

    Free tier limits:
    - 14,400 requests per day
    - 60 RPM for most models
    - 500K tokens per day

    Models available:
    - llama-3.3-70b-versatile (30 RPM)
    - qwen/qwen3-32b (60 RPM)

    Get API key: https://console.groq.com/keys
    """

    API_BASE = "https://api.groq.com/openai/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.client: Optional[httpx.AsyncClient] = None

    @property
    def default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    @property
    def supports_function_calling(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.config.timeout
            )
        return self.client

    async def check_available(self) -> bool:
        """Check if Groq API is accessible."""
        if not self.api_key:
            self._set_error("GROQ_API_KEY not set")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/models")

            if response.status_code == 200:
                self._set_available()
                return True
            elif response.status_code == 401:
                self._set_error("Invalid Groq API key")
                return False
            else:
                self._set_error(f"Groq API error: {response.status_code}")
                return False

        except Exception as e:
            self._set_error(f"Groq connection failed: {e}")
            return False

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate completion using Groq API (text only, no tools)."""
        model = self.get_model(model)
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with client.stream(
                "POST",
                "/chat/completions",
                json=payload
            ) as response:
                if response.status_code == 429:
                    self._set_rate_limited()
                    raise RateLimitError("Groq rate limit exceeded")
                elif response.status_code == 401:
                    raise AuthenticationError("Invalid Groq API key")
                elif response.status_code != 200:
                    text = await response.aread()
                    raise ServiceUnavailableError(f"Groq error {response.status_code}: {text}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            raise ServiceUnavailableError("Groq request timed out")

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[AgentResponse]:
        """Generate completion with function calling support."""
        model = self.get_model(model)
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,  # Non-streaming for tool calls (simpler parsing)
            "tools": tools,
            "tool_choice": "auto"
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = await client.post("/chat/completions", json=payload)

            if response.status_code == 429:
                self._set_rate_limited()
                raise RateLimitError("Groq rate limit exceeded")
            elif response.status_code == 401:
                raise AuthenticationError("Invalid Groq API key")
            elif response.status_code != 200:
                raise ServiceUnavailableError(f"Groq error {response.status_code}: {response.text}")

            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            finish_reason = choice.get("finish_reason", "stop")

            # Check for tool calls
            if message.get("tool_calls"):
                tool_calls = []
                for tc in message["tool_calls"]:
                    func = tc["function"]
                    try:
                        args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(ToolCall(
                        id=tc["id"],
                        name=func["name"],
                        arguments=args
                    ))
                yield AgentResponse(
                    type=ResponseType.TOOL_CALL,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls"
                )
            else:
                # Plain text response
                content = message.get("content", "")
                if content:
                    yield AgentResponse(type=ResponseType.TEXT, text=content)
                yield AgentResponse(type=ResponseType.DONE, finish_reason=finish_reason)

        except httpx.TimeoutException:
            raise ServiceUnavailableError("Groq request timed out")
```

**Step 2: Commit**

```bash
git add providers/groq.py
git commit -m "feat: add function calling to Groq provider, fix import bug"
```

---

## Task 4: Add Function Calling to Gemini Provider

**Files:**
- Modify: `providers/gemini.py`

**Step 1: Add function calling support**

Add `supports_function_calling` property after `default_model` (after line 51):

```python
@property
def supports_function_calling(self) -> bool:
    return True
```

Add `complete_with_tools` method after the `complete` method (after line 188). Gemini uses a different tool schema format — we convert from OpenAI format:

```python
async def complete_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    model: Optional[str] = None,
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> AsyncIterator:
    """Generate completion with function calling (Gemini format)."""
    from core.agent_response import AgentResponse, ResponseType, ToolCall

    model = self.get_model(model)
    client = await self._get_client()

    system_instruction, contents = self._convert_messages(messages)

    # Convert OpenAI tool format to Gemini format
    gemini_tools = self._convert_tools_to_gemini(tools)

    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
        "tools": gemini_tools
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    if max_tokens:
        payload["generationConfig"]["maxOutputTokens"] = max_tokens

    endpoint = f"{self.API_BASE}/models/{model}:generateContent"

    try:
        response = await client.post(
            endpoint,
            params={"key": self.api_key},
            json=payload
        )

        if response.status_code == 429:
            self._set_rate_limited()
            raise RateLimitError("Gemini rate limit exceeded")
        elif response.status_code == 400:
            raise AuthenticationError(f"Gemini error: {response.text}")
        elif response.status_code != 200:
            raise ServiceUnavailableError(f"Gemini error {response.status_code}: {response.text}")

        data = response.json()

        if "candidates" not in data or not data["candidates"]:
            yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")
            return

        candidate = data["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])

        tool_calls = []
        text_parts = []

        for part in parts:
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(ToolCall(
                    name=fc["name"],
                    arguments=fc.get("args", {})
                ))
            elif "text" in part:
                text_parts.append(part["text"])

        if tool_calls:
            yield AgentResponse(
                type=ResponseType.TOOL_CALL,
                tool_calls=tool_calls,
                finish_reason="tool_calls"
            )
        else:
            content = "".join(text_parts)
            if content:
                yield AgentResponse(type=ResponseType.TEXT, text=content)
            yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")

    except httpx.TimeoutException:
        raise ServiceUnavailableError("Gemini request timed out")

def _convert_tools_to_gemini(self, openai_tools: list[dict]) -> list[dict]:
    """Convert OpenAI tool format to Gemini function declarations."""
    function_declarations = []

    for tool in openai_tools:
        if tool.get("type") == "function":
            func = tool["function"]
            declaration = {
                "name": func["name"],
                "description": func.get("description", ""),
            }
            if "parameters" in func:
                declaration["parameters"] = func["parameters"]
            function_declarations.append(declaration)

    return [{"functionDeclarations": function_declarations}]
```

Also add the import at top of file:

```python
from core.agent_response import AgentResponse, ResponseType, ToolCall
```

**Step 2: Commit**

```bash
git add providers/gemini.py
git commit -m "feat: add function calling to Gemini provider"
```

---

## Task 5: Add Function Calling to Kimi Provider

**Files:**
- Modify: `providers/kimi.py`

**Step 1: Add function calling**

Kimi uses OpenAI-compatible API, so this is nearly identical to Groq. Add `supports_function_calling` property and `complete_with_tools` method.

Add after `default_model` property (after line 38):

```python
@property
def supports_function_calling(self) -> bool:
    return True
```

Add `complete_with_tools` after the `complete` method (after line 139) — same logic as Groq but with Kimi's client:

```python
async def complete_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    model: Optional[str] = None,
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> AsyncIterator:
    """Generate completion with function calling support."""
    from core.agent_response import AgentResponse, ResponseType, ToolCall

    model = self.get_model(model)
    client = await self._get_client()

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
        "tools": tools,
        "tool_choice": "auto"
    }

    if max_tokens:
        payload["max_tokens"] = max_tokens

    try:
        response = await client.post("/chat/completions", json=payload)

        if response.status_code == 429:
            self._set_rate_limited()
            raise RateLimitError("Kimi rate limit exceeded")
        elif response.status_code == 401:
            raise AuthenticationError("Invalid Kimi API key")
        elif response.status_code != 200:
            raise ServiceUnavailableError(f"Kimi error {response.status_code}: {response.text}")

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        if message.get("tool_calls"):
            tool_calls = []
            for tc in message["tool_calls"]:
                func = tc["function"]
                try:
                    args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=func["name"],
                    arguments=args
                ))
            yield AgentResponse(
                type=ResponseType.TOOL_CALL,
                tool_calls=tool_calls,
                finish_reason="tool_calls"
            )
        else:
            content = message.get("content", "")
            if content:
                yield AgentResponse(type=ResponseType.TEXT, text=content)
            yield AgentResponse(type=ResponseType.DONE, finish_reason=finish_reason)

    except httpx.TimeoutException:
        raise ServiceUnavailableError("Kimi request timed out")
```

**Step 2: Commit**

```bash
git add providers/kimi.py
git commit -m "feat: add function calling to Kimi provider"
```

---

## Task 6: Add Prompt-Based Tool Parsing to Kilo Provider

**Files:**
- Modify: `providers/kilo.py`

**Step 1: Add prompt-based tool calling**

Kilo CLI doesn't support native function calling, so we inject tool schemas into the prompt and parse structured output. Add `complete_with_tools` after the `complete` method (after line 182):

```python
TOOL_INSTRUCTION_TEMPLATE = """You have access to these tools. When you need to use a tool, output EXACTLY this format (one per line):

<tool_call>{"name": "tool_name", "arguments": {"arg1": "value1"}}</tool_call>

After ALL tool results come back, continue your response.

Available tools:
{tool_descriptions}

IMPORTANT: Output tool calls ONE AT A TIME. Wait for results before continuing. If you don't need a tool, just respond normally with text."""

async def complete_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    model: Optional[str] = None,
    stream: bool = True,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> AsyncIterator:
    """Generate completion with prompt-based tool parsing for Kilo."""
    import re
    from core.agent_response import AgentResponse, ResponseType, ToolCall

    model = self.get_model(model)

    # Build tool descriptions for the prompt
    tool_descriptions = []
    for tool in tools:
        if tool.get("type") == "function":
            func = tool["function"]
            params = func.get("parameters", {}).get("properties", {})
            required = func.get("parameters", {}).get("required", [])
            param_str = ", ".join([
                f"{k}: {v.get('type', 'string')}{'(required)' if k in required else ''}"
                for k, v in params.items()
            ])
            tool_descriptions.append(f"- {func['name']}({param_str}): {func.get('description', '')}")

    tool_instruction = self.TOOL_INSTRUCTION_TEMPLATE.format(
        tool_descriptions="\n".join(tool_descriptions)
    )

    # Inject tool instruction into system message
    enhanced_messages = []
    has_system = False
    for msg in messages:
        if msg["role"] == "system":
            enhanced_messages.append({
                "role": "system",
                "content": msg["content"] + "\n\n" + tool_instruction
            })
            has_system = True
        else:
            enhanced_messages.append(msg)

    if not has_system:
        enhanced_messages.insert(0, {"role": "system", "content": tool_instruction})

    # Get response from Kilo
    response_text = ""
    async for chunk in self.complete(enhanced_messages, model, stream=False, **kwargs):
        response_text += chunk

    # Parse tool calls from response
    tool_call_pattern = r'<tool_call>\s*(\{[^}]+\})\s*</tool_call>'
    matches = re.findall(tool_call_pattern, response_text)

    if matches:
        tool_calls = []
        for match in matches:
            try:
                parsed = json.loads(match)
                tool_calls.append(ToolCall(
                    name=parsed.get("name", ""),
                    arguments=parsed.get("arguments", {})
                ))
            except json.JSONDecodeError:
                continue

        if tool_calls:
            # Remove tool call tags from text
            clean_text = re.sub(tool_call_pattern, '', response_text).strip()
            if clean_text:
                yield AgentResponse(type=ResponseType.TEXT, text=clean_text)
            yield AgentResponse(
                type=ResponseType.TOOL_CALL,
                tool_calls=tool_calls,
                finish_reason="tool_calls"
            )
            return

    # No tool calls found — just text
    if response_text.strip():
        yield AgentResponse(type=ResponseType.TEXT, text=response_text.strip())
    yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")
```

**Step 2: Commit**

```bash
git add providers/kilo.py
git commit -m "feat: add prompt-based tool calling to Kilo provider"
```

---

## Task 7: Wire Permission System into Tools

**Files:**
- Modify: `core/tools.py`

**Step 1: Add permission checking to BashTool and ToolRegistry**

In `core/tools.py`, modify `BashTool.execute` (around line 257) to accept a `confirmed` parameter:

```python
def execute(self, command: str, timeout: int = 60, confirmed: bool = False) -> str:
    """
    Execute bash command.

    Args:
        command: Command to execute
        timeout: Timeout in seconds
        confirmed: Whether user has confirmed (for dangerous commands)

    Returns:
        Command output or error
    """
    if self.is_dangerous(command) and not confirmed:
        return f"PERMISSION_REQUIRED: Command '{command}' requires confirmation (potentially dangerous)"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = []
        if result.stdout:
            output.append(result.stdout)
        if result.stderr:
            output.append(f"stderr: {result.stderr}")

        if result.returncode != 0:
            output.append(f"Exit code: {result.returncode}")

        return "\n".join(output) if output else "Command completed (no output)"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"
```

Also add a method to `ToolRegistry` to get tools in OpenAI function calling format (add after `get_schemas` at line 504):

```python
def get_openai_tools(self) -> list[dict]:
    """Get tools formatted for OpenAI function calling API."""
    return [
        {
            "type": "function",
            "function": tool.get_schema()
        }
        for tool in self.tools.values()
    ]
```

**Step 2: Commit**

```bash
git add core/tools.py
git commit -m "feat: wire permission system into tools, add OpenAI format export"
```

---

## Task 8: Add Tool Message Support to Conversation

**Files:**
- Modify: `core/conversation.py`

**Step 1: Extend Message and Conversation for tool messages**

In `core/conversation.py`, update the `Message.to_dict` method (around line 29) to handle tool messages:

```python
def to_dict(self) -> Dict:
    """Convert to dictionary for API calls."""
    d = {
        "role": self.role,
        "content": self.content
    }
    # Tool call results need tool_call_id
    if self.role == "tool" and self.metadata:
        if "tool_call_id" in self.metadata:
            d["tool_call_id"] = self.metadata["tool_call_id"]
        if "name" in self.metadata:
            d["name"] = self.metadata["name"]
    # Assistant messages with tool calls
    if self.role == "assistant" and self.metadata and "tool_calls" in self.metadata:
        d["tool_calls"] = self.metadata["tool_calls"]
        if not self.content:
            d["content"] = None
    return d
```

**Step 2: Commit**

```bash
git add core/conversation.py
git commit -m "feat: add tool message support to conversation"
```

---

## Task 9: Fix CARL Operator Precedence Bug

**Files:**
- Modify: `core/carl.py`

**Step 1: Fix the bug at line 139**

In `core/carl.py`, the `elif` at line 139 has an operator precedence issue. The `or` conditions aren't grouped with the `current_bracket and` check. Replace lines 139-145:

```python
                elif current_bracket and (
                    line.startswith('FRESH_RULE_') or
                    line.startswith('MODERATE_RULE_') or
                    line.startswith('DEPLETED_RULE_') or
                    line.startswith('CRITICAL_RULE_')
                ):
                    if '=' in line:
                        rule = line.split('=', 1)[1].strip()
                        self.context_rules[current_bracket].append(rule)
```

**Step 2: Commit**

```bash
git add core/carl.py
git commit -m "fix: CARL operator precedence bug in context rule parsing"
```

---

## Task 10: Update Router for Tool-Aware Routing

**Files:**
- Modify: `core/router.py`

**Step 1: Add `complete_with_tools` to the router**

Add this method after `complete` (after line 194) in `core/router.py`:

```python
async def complete_with_tools(
    self,
    messages: list[dict],
    tools: list[dict],
    model: Optional[str] = None,
    stream: bool = True,
    **kwargs
) -> AsyncIterator:
    """
    Generate completion with tools, trying providers until one succeeds.

    Prefers providers that support native function calling.
    Falls back to prompt-based for providers that don't.
    """
    from core.agent_response import AgentResponse, ResponseType

    if not self._initialized:
        await self.initialize()

    self.stats.total_requests += 1
    last_error = None

    # Sort providers: function-calling-capable first
    sorted_providers = sorted(
        self.providers,
        key=lambda p: (0 if p.supports_function_calling else 1, p.priority)
    )

    for provider in sorted_providers:
        try:
            if not await provider.check_available():
                logger.debug(f"Provider {provider.name} not available, skipping")
                continue

            logger.info(f"Trying provider with tools: {provider.name}")
            self.current_provider = provider

            async for response in provider.complete_with_tools(
                messages, tools, model, stream, **kwargs
            ):
                yield response

            self.stats.successful_requests += 1
            return

        except Exception as e:
            logger.warning(f"Provider {provider.name} failed: {e}")
            self.stats.fallback_count += 1
            last_error = e
            continue

    self.stats.failed_requests += 1
    self.current_provider = None
    raise AllProvidersFailed(f"All providers failed. Last error: {last_error}")
```

**Step 2: Commit**

```bash
git add core/router.py
git commit -m "feat: add tool-aware routing to ProviderRouter"
```

---

## Task 11: Create the Agent Loop — The Heart of Everything

**Files:**
- Create: `core/agent_loop.py`

**Step 1: Create the agentic tool loop**

```python
"""
AI_SYNAPSE — Agent Loop

The core agentic loop that makes AI_SYNAPSE a real coding assistant.
Sends messages to AI, executes tool calls, sends results back, repeats.
"""

import logging
from typing import AsyncIterator, Optional, Callable
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

from core.agent_response import AgentResponse, ResponseType, ToolCall, ToolResult
from core.tools import ToolRegistry
from core.router import ProviderRouter
from core.conversation import Conversation

logger = logging.getLogger(__name__)


class AgentLoop:
    """
    Orchestrates the agentic tool loop.

    Flow:
    1. Send user message + tool schemas to provider
    2. If provider returns tool calls → execute tools → add results → go to 1
    3. If provider returns text → display to user → done
    4. Safety: max iterations prevent infinite loops

    Example:
        loop = AgentLoop(router, tools, conversation)
        async for event in loop.run("fix the bug in main.py"):
            if event.type == ResponseType.TEXT:
                print(event.text, end="")
            elif event.type == ResponseType.TOOL_CALL:
                print(f"[calling {event.tool_calls[0].name}]")
    """

    def __init__(
        self,
        router: ProviderRouter,
        tools: ToolRegistry,
        conversation: Conversation,
        console: Optional[Console] = None,
        max_iterations: int = 50,
        auto_approve: bool = False
    ):
        self.router = router
        self.tools = tools
        self.conversation = conversation
        self.console = console or Console()
        self.max_iterations = max_iterations
        self.auto_approve = auto_approve
        self.iteration_count = 0

    async def run(self, user_message: str) -> AsyncIterator[AgentResponse]:
        """
        Run the agentic loop for a user message.

        Args:
            user_message: The user's input

        Yields:
            AgentResponse events (text chunks, tool activities, done signal)
        """
        # Add user message to conversation
        self.conversation.add_message("user", user_message)
        self.iteration_count = 0

        # Get tool schemas in OpenAI format
        openai_tools = self.tools.get_openai_tools()

        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            logger.info(f"Agent loop iteration {self.iteration_count}/{self.max_iterations}")

            # Get messages for API
            messages = self.conversation.get_messages_for_api()

            # Collect full response
            text_buffer = ""
            tool_calls = []
            done = False

            try:
                async for response in self.router.complete_with_tools(
                    messages, openai_tools
                ):
                    if response.type == ResponseType.TEXT:
                        text_buffer += response.text
                        yield response  # Stream text to caller

                    elif response.type == ResponseType.TOOL_CALL:
                        tool_calls = response.tool_calls
                        yield response  # Notify caller of tool calls

                    elif response.type == ResponseType.DONE:
                        done = True

                    elif response.type == ResponseType.ERROR:
                        yield response
                        return

            except Exception as e:
                logger.error(f"Provider error in agent loop: {e}")
                yield AgentResponse(type=ResponseType.ERROR, text=str(e))
                return

            # If we got tool calls, execute them
            if tool_calls:
                # Save assistant message with tool calls
                tool_calls_data = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": str(tc.arguments)
                        }
                    }
                    for tc in tool_calls
                ]
                self.conversation.add_message(
                    "assistant",
                    text_buffer or "",
                    metadata={"tool_calls": tool_calls_data}
                )

                # Execute each tool call
                for tc in tool_calls:
                    result = await self._execute_tool(tc)

                    # Yield tool result for display
                    yield AgentResponse(
                        type=ResponseType.TOOL_RESULT,
                        tool_result=result
                    )

                    # Add tool result to conversation
                    self.conversation.add_message(
                        "tool",
                        result.output,
                        metadata={
                            "tool_call_id": tc.id,
                            "name": tc.name
                        }
                    )

                # Continue loop — send tool results back to AI
                continue

            # No tool calls — we have a final text response
            if text_buffer:
                self.conversation.add_message("assistant", text_buffer)

            yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")
            return

        # Hit max iterations
        self.console.print(
            f"\n[yellow]Warning: Hit max iterations ({self.max_iterations}). "
            f"Stopping agent loop.[/yellow]"
        )
        yield AgentResponse(
            type=ResponseType.ERROR,
            text=f"Max iterations ({self.max_iterations}) reached"
        )

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call with permission checking.

        Args:
            tool_call: The tool call to execute

        Returns:
            ToolResult with output or error
        """
        tool_name = tool_call.name
        tool_args = tool_call.arguments

        logger.info(f"Executing tool: {tool_name}({tool_args})")

        # Get the tool
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                output=f"Error: Unknown tool '{tool_name}'",
                is_error=True
            )

        # Permission check for bash commands
        if tool_name == "bash":
            command = tool_args.get("command", "")
            from core.tools import BashTool
            if isinstance(tool, BashTool) and tool.is_dangerous(command):
                if not self.auto_approve:
                    self.console.print(
                        Panel(
                            f"[yellow]Command:[/yellow] {command}",
                            title="Permission Required",
                            border_style="yellow"
                        )
                    )
                    if not Confirm.ask("Allow this command?"):
                        return ToolResult(
                            tool_call_id=tool_call.id,
                            name=tool_name,
                            output="User denied permission for this command",
                            is_error=True
                        )
                # Mark as confirmed
                tool_args["confirmed"] = True

        # Execute the tool
        try:
            output = tool.execute(**tool_args)

            # Truncate very long outputs
            if len(output) > 10000:
                output = output[:10000] + f"\n... (truncated, {len(output)} chars total)"

            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                output=output,
                is_error=False
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                output=f"Error executing {tool_name}: {e}",
                is_error=True
            )
```

**Step 2: Commit**

```bash
git add core/agent_loop.py
git commit -m "feat: create AgentLoop — the agentic tool execution loop"
```

---

## Task 12: Integrate Agent Loop into CLI (`synapse.py`)

**Files:**
- Modify: `synapse.py`

**Step 1: Replace `process_ai_message` with agent loop**

Replace the `process_ai_message` function (lines 232-332) with:

```python
async def process_ai_message(
    message: str,
    router: ProviderRouter,
    carl: CARLSystem,
    memory: MemorySystem,
    skills: SkillSystem,
    conversation: Conversation,
    tools: ToolRegistry,
    cache: ResponseCache,
    config: SynapseConfig,
    console=None,
    auto_approve: bool = False
):
    """Process a message through the agentic AI pipeline."""
    from core.agent_loop import AgentLoop
    from core.agent_response import ResponseType

    # 1. CARL Processing
    context_usage = conversation.get_context_usage()
    carl_result = carl.process_message(message, context_usage)

    # Show what CARL detected
    if carl_result.star_command:
        print(f"  Mode: *{carl_result.star_command}")
    if carl_result.loaded_domains:
        print(f"  Context: {', '.join(carl_result.loaded_domains)}")

    # 2. Load Memory
    memory_content = ""
    if config.memory.enabled:
        memory_content = memory.load_for_project(Path.cwd())

    # 3. Detect Skills
    loaded_skills = skills.detect_skills(carl_result.modified_message)
    if loaded_skills:
        skill_names = [s.metadata.name for s in loaded_skills]
        print(f"  Skills: {', '.join(skill_names)}")

    # 4. Build System Prompt
    system_parts = [
        "You are AI_SYNAPSE, an intelligent coding assistant. "
        "You can read files, edit code, run commands, and search for files. "
        "Use the provided tools to help the user with their coding tasks. "
        "Always read files before editing them. Think step by step."
    ]
    if carl_result.rules:
        system_parts.append(carl.format_rules_for_prompt(carl_result.rules))
    if memory_content:
        system_parts.append(f"<project-memory>\n{memory_content}\n</project-memory>")
    if loaded_skills:
        system_parts.append(skills.format_for_prompt(loaded_skills))

    system_prompt = "\n\n".join(system_parts)
    conversation.system_prompt = system_prompt

    # Ensure system message is first in conversation
    if not conversation.messages or conversation.messages[0].role != "system":
        from core.conversation import Message
        conversation.messages.insert(0, Message(role="system", content=system_prompt))
    else:
        conversation.messages[0].content = system_prompt

    # 5. Run Agent Loop
    agent = AgentLoop(
        router=router,
        tools=tools,
        conversation=conversation,
        max_iterations=50,
        auto_approve=auto_approve
    )

    print()
    if console:
        from rich.console import Console as RichConsole
        rich_console = console if isinstance(console, RichConsole) else RichConsole()

    async for event in agent.run(carl_result.modified_message):
        if event.type == ResponseType.TEXT:
            print(event.text, end="", flush=True)

        elif event.type == ResponseType.TOOL_CALL:
            for tc in event.tool_calls:
                args_preview = str(tc.arguments)
                if len(args_preview) > 80:
                    args_preview = args_preview[:80] + "..."
                print(f"\n  [tool] {tc.name}({args_preview})")

        elif event.type == ResponseType.TOOL_RESULT:
            tr = event.tool_result
            status = "ok" if not tr.is_error else "error"
            output_preview = tr.output[:200] if tr.output else ""
            if len(tr.output) > 200:
                output_preview += "..."
            print(f"  [{status}] {output_preview}")

        elif event.type == ResponseType.ERROR:
            print(f"\n  Error: {event.text}")

        elif event.type == ResponseType.DONE:
            print()  # Final newline

    # Context warning
    if conversation.get_context_usage() > config.conversation.compact_threshold:
        print(f"\n  Context at {conversation.get_context_usage():.0%}. Use /compact or /clear\n")

    return 'continue'
```

**Step 2: Fix single-shot mode**

Replace lines 486-493 (the TODO section) with:

```python
    # Single message mode
    if args.message:
        config_obj = config
        asyncio.run(single_message(args.message, config_obj, auto_approve=args.yes if hasattr(args, 'yes') else False))
        return 0

    # Interactive mode
    asyncio.run(chat_loop(config, auto_approve=getattr(args, 'yes', False)))
    return 0
```

Add `single_message` function before `main()`:

```python
async def single_message(message: str, config: SynapseConfig, auto_approve: bool = False):
    """Process a single message and exit."""
    router = ProviderRouter(config)
    carl = CARLSystem(Path(config.carl.config_path))
    memory = MemorySystem(config.memory.location)
    skills = SkillSystem(config.skills.location)
    conversation = Conversation(max_tokens=config.conversation.max_tokens)
    tools = ToolRegistry()
    cache = ResponseCache("~/.synapse/cache")

    await process_ai_message(
        message, router, carl, memory, skills,
        conversation, tools, cache, config, None, auto_approve
    )
```

**Step 3: Add `--yes` flag to argparse**

Add after the `--verbose` argument (around line 420):

```python
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-approve all tool calls")
```

**Step 4: Update `chat_loop` signature**

Change `chat_loop` to accept `auto_approve`:

```python
async def chat_loop(config: SynapseConfig, auto_approve: bool = False):
```

And pass it through to `process_ai_message` in `handle_command`:

```python
    result = await handle_command(
        user_input, router, carl, memory, skills,
        conversation, tools, web_search, cache, sessions, config, console, auto_approve
    )
```

Update `handle_command` signature to accept `auto_approve: bool = False` and pass it to `process_ai_message`.

**Step 5: Fix banner alignment**

Replace the `print_banner` function (lines 55-64):

```python
def print_banner():
    """Print the Synapse banner."""
    print("""
+------------------------------------------------------------------+
|  AI_SYNAPSE v0.4.0 — Universal AI Coding Assistant               |
|                                                                  |
|  Multi-Provider | CARL Intelligence | Persistent Memory          |
|  Skills | Agentic Tool Loop | Session Save | Web Search          |
+------------------------------------------------------------------+
    """)
```

**Step 6: Commit**

```bash
git add synapse.py
git commit -m "feat: integrate agent loop into CLI, fix single-shot mode, add --yes flag"
```

---

## Task 13: Integrate Agent Loop into TUI (`synapse_tui.py`)

**Files:**
- Modify: `synapse_tui.py`

**Step 1: Replace `call_provider` with agent loop**

Replace the `call_provider` method (lines 223-293) and `fallback_to_next_provider` (lines 295-323) with a proper agent loop integration:

```python
async def call_provider(self, message: str) -> str:
    """Call the AI provider through the agent loop."""
    from core.agent_loop import AgentLoop
    from core.agent_response import ResponseType
    from core.conversation import Conversation
    from core.tools import ToolRegistry

    # 1. CARL Processing
    carl_result = self.carl.process_message(message, self.context_usage)

    if carl_result.star_command:
        self.messages.append(TUIMessage(
            role="system",
            content=f"Mode: *{carl_result.star_command}",
            timestamp=datetime.now().isoformat(),
            metadata={"type": "carl"}
        ))

    if carl_result.loaded_domains:
        self.messages.append(TUIMessage(
            role="system",
            content=f"Context: {', '.join(carl_result.loaded_domains)}",
            timestamp=datetime.now().isoformat(),
            metadata={"type": "carl"}
        ))

    # 2. Load Memory
    memory_content = self.memory.load_for_project(self.project_path)

    # 3. Detect Skills
    loaded_skills = self.skills.detect_skills(carl_result.modified_message)
    if loaded_skills:
        skill_names = [s.metadata.name for s in loaded_skills]
        self.messages.append(TUIMessage(
            role="system",
            content=f"Skills: {', '.join(skill_names)}",
            timestamp=datetime.now().isoformat(),
            metadata={"type": "carl"}
        ))

    # 4. Build system prompt
    system_parts = [
        "You are AI_SYNAPSE, an intelligent coding assistant. "
        "Use the provided tools to help the user."
    ]
    if carl_result.rules:
        system_parts.append("\n".join([f"- {r}" for r in carl_result.rules]))
    if memory_content:
        system_parts.append(f"Project Context:\n{memory_content}")
    if loaded_skills:
        for skill in loaded_skills:
            system_parts.append(f"Skill ({skill.metadata.name}):\n{skill.content}")

    system_prompt = "\n\n".join(system_parts)

    # 5. Create conversation and run agent loop
    conversation = Conversation(max_tokens=128000, system_prompt=system_prompt)
    from core.conversation import Message
    conversation.messages.append(Message(role="system", content=system_prompt))

    # Add history from TUI messages
    for msg in self.messages[-20:]:  # Last 20 for context
        if msg.role in ("user", "assistant"):
            conversation.add_message(msg.role, msg.content)

    tools = ToolRegistry()
    agent = AgentLoop(
        router=self.router,
        tools=tools,
        conversation=conversation,
        console=self.console,
        max_iterations=50,
        auto_approve=False
    )

    response_parts = []

    from rich.status import Status

    async for event in agent.run(carl_result.modified_message):
        if event.type == ResponseType.TEXT:
            response_parts.append(event.text)
        elif event.type == ResponseType.TOOL_CALL:
            for tc in event.tool_calls:
                tool_msg = f"[Tool: {tc.name}]"
                self.messages.append(TUIMessage(
                    role="system", content=tool_msg,
                    timestamp=datetime.now().isoformat(),
                    metadata={"type": "tool"}
                ))
        elif event.type == ResponseType.TOOL_RESULT:
            tr = event.tool_result
            preview = tr.output[:100] + "..." if len(tr.output) > 100 else tr.output
            self.messages.append(TUIMessage(
                role="system", content=preview,
                timestamp=datetime.now().isoformat(),
                metadata={"type": "tool"}
            ))
        elif event.type == ResponseType.ERROR:
            response_parts.append(f"Error: {event.text}")

    return "".join(response_parts)
```

Remove the `fallback_to_next_provider` method entirely — the router handles fallback now.

**Step 2: Commit**

```bash
git add synapse_tui.py
git commit -m "feat: integrate agent loop into TUI, remove manual fallback"
```

---

## Task 14: Create OpenRouter Provider

**Files:**
- Create: `providers/openrouter.py`

**Step 1: Create OpenRouter provider**

OpenRouter uses OpenAI-compatible API so this is straightforward:

```python
"""
AI_SYNAPSE — OpenRouter Provider

Provider for OpenRouter — access to 100+ models through one API.
Many free models available. OpenAI-compatible API.
"""

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from providers.base import (
    Provider,
    ProviderConfig,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ServiceUnavailableError
)
from core.agent_response import AgentResponse, ResponseType, ToolCall

logger = logging.getLogger(__name__)


class OpenRouterProvider(Provider):
    """
    Provider for OpenRouter API.

    OpenRouter provides access to many free and paid models
    through a single OpenAI-compatible API.

    Free models include:
    - google/gemma-3-27b-it:free
    - mistralai/mistral-small-3.1-24b-instruct:free
    - qwen/qwen3-32b:free

    Get API key: https://openrouter.ai/keys
    """

    API_BASE = "https://openrouter.ai/api/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.client: Optional[httpx.AsyncClient] = None

    @property
    def default_model(self) -> str:
        return "qwen/qwen3-32b:free"

    @property
    def supports_function_calling(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/ai-synapse",
                    "X-Title": "AI_SYNAPSE"
                },
                timeout=self.config.timeout
            )
        return self.client

    async def check_available(self) -> bool:
        """Check if OpenRouter API is accessible."""
        if not self.api_key:
            self._set_error("OPENROUTER_API_KEY not set")
            return False

        try:
            client = await self._get_client()
            response = await client.get("/models")

            if response.status_code == 200:
                self._set_available()
                return True
            elif response.status_code == 401:
                self._set_error("Invalid OpenRouter API key")
                return False
            else:
                self._set_error(f"OpenRouter error: {response.status_code}")
                return False

        except Exception as e:
            self._set_error(f"OpenRouter connection failed: {e}")
            return False

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate completion (text only)."""
        model = self.get_model(model)
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code == 429:
                    self._set_rate_limited()
                    raise RateLimitError("OpenRouter rate limit exceeded")
                elif response.status_code == 401:
                    raise AuthenticationError("Invalid OpenRouter API key")
                elif response.status_code != 200:
                    text = await response.aread()
                    raise ServiceUnavailableError(f"OpenRouter error {response.status_code}: {text}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
        except httpx.TimeoutException:
            raise ServiceUnavailableError("OpenRouter request timed out")

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[AgentResponse]:
        """Generate completion with function calling."""
        model = self.get_model(model)
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "tools": tools,
            "tool_choice": "auto"
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = await client.post("/chat/completions", json=payload)

            if response.status_code == 429:
                self._set_rate_limited()
                raise RateLimitError("OpenRouter rate limit exceeded")
            elif response.status_code == 401:
                raise AuthenticationError("Invalid OpenRouter API key")
            elif response.status_code != 200:
                raise ServiceUnavailableError(f"OpenRouter error {response.status_code}: {response.text}")

            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            finish_reason = choice.get("finish_reason", "stop")

            if message.get("tool_calls"):
                tool_calls = []
                for tc in message["tool_calls"]:
                    func = tc["function"]
                    try:
                        args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(ToolCall(
                        id=tc["id"],
                        name=func["name"],
                        arguments=args
                    ))
                yield AgentResponse(
                    type=ResponseType.TOOL_CALL,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls"
                )
            else:
                content = message.get("content", "")
                if content:
                    yield AgentResponse(type=ResponseType.TEXT, text=content)
                yield AgentResponse(type=ResponseType.DONE, finish_reason=finish_reason)

        except httpx.TimeoutException:
            raise ServiceUnavailableError("OpenRouter request timed out")
```

**Step 2: Commit**

```bash
git add providers/openrouter.py
git commit -m "feat: add OpenRouter provider with 100+ free models"
```

---

## Task 15: Create Ollama Provider

**Files:**
- Create: `providers/ollama.py`

**Step 1: Create Ollama local provider**

```python
"""
AI_SYNAPSE — Ollama Provider

Provider for Ollama — run models locally, zero cost, works offline.
"""

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from providers.base import (
    Provider,
    ProviderConfig,
    ProviderError,
    ServiceUnavailableError
)
from core.agent_response import AgentResponse, ResponseType, ToolCall

logger = logging.getLogger(__name__)


class OllamaProvider(Provider):
    """
    Provider for Ollama local models.

    Ollama runs models locally with zero API costs.
    Supports function calling with compatible models.

    Install: https://ollama.ai

    Models:
    - qwen2.5-coder:32b (coding optimized)
    - llama3.3:70b (general purpose)
    - deepseek-coder-v2 (coding)
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.client: Optional[httpx.AsyncClient] = None

    @property
    def default_model(self) -> str:
        return "qwen2.5-coder:32b"

    @property
    def supports_function_calling(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.config.timeout
            )
        return self.client

    async def check_available(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")

            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                if models:
                    self._set_available()
                    logger.info(f"Ollama available with models: {models}")
                    return True
                else:
                    self._set_error("Ollama running but no models installed")
                    return False
            else:
                self._set_error(f"Ollama error: {response.status_code}")
                return False

        except httpx.ConnectError:
            self._set_error("Ollama not running (connection refused)")
            return False
        except Exception as e:
            self._set_error(f"Ollama check failed: {e}")
            return False

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate completion using Ollama API."""
        model = self.get_model(model)
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": temperature}
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code != 200:
                    text = await response.aread()
                    raise ServiceUnavailableError(f"Ollama error: {text}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError:
            raise ServiceUnavailableError("Ollama not running")

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[AgentResponse]:
        """Generate completion with tool calling (Ollama format)."""
        model = self.get_model(model)
        client = await self._get_client()

        # Ollama uses same format as OpenAI for tools
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "tools": tools,
            "options": {"temperature": temperature}
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = await client.post("/api/chat", json=payload)

            if response.status_code != 200:
                raise ServiceUnavailableError(f"Ollama error: {response.text}")

            data = response.json()
            message = data.get("message", {})

            if message.get("tool_calls"):
                tool_calls = []
                for tc in message["tool_calls"]:
                    func = tc.get("function", {})
                    tool_calls.append(ToolCall(
                        name=func.get("name", ""),
                        arguments=func.get("arguments", {})
                    ))
                yield AgentResponse(
                    type=ResponseType.TOOL_CALL,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls"
                )
            else:
                content = message.get("content", "")
                if content:
                    yield AgentResponse(type=ResponseType.TEXT, text=content)
                yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")

        except httpx.ConnectError:
            raise ServiceUnavailableError("Ollama not running")
```

**Step 2: Commit**

```bash
git add providers/ollama.py
git commit -m "feat: add Ollama provider for local models"
```

---

## Task 16: Update Config for New Providers and Router

**Files:**
- Modify: `core/config.py`
- Modify: `core/router.py`

**Step 1: Add new providers to default config**

In `core/config.py`, update `_get_default_config` to add OpenRouter and Ollama. Add these entries inside the `"providers"` dict (after the `"kimi"` entry around line 220):

```python
                "openrouter": {
                    "enabled": True,
                    "priority": 4,
                    "api_key": None,  # From env: OPENROUTER_API_KEY
                    "models": [
                        {"name": "qwen/qwen3-32b:free", "default": True},
                        {"name": "google/gemma-3-27b-it:free"},
                        {"name": "mistralai/mistral-small-3.1-24b-instruct:free"}
                    ]
                },
                "ollama": {
                    "enabled": True,
                    "priority": 5,
                    "base_url": "http://localhost:11434",
                    "models": [
                        {"name": "qwen2.5-coder:32b", "default": True}
                    ]
                },
```

Add OpenRouter env var override in `_apply_env_overrides` (around line 261):

```python
            "OPENROUTER_API_KEY": ("providers", "openrouter", "api_key"),
```

**Step 2: Add new providers to router**

In `core/router.py`, add loading for new providers in `_load_provider` (after the `elif name == "kimi"` block around line 128):

```python
            elif name == "openrouter":
                from providers.openrouter import OpenRouterProvider
                return OpenRouterProvider(ProviderConfig(
                    name=name,
                    priority=config.priority,
                    api_key=config.api_key,
                    models=[m.name for m in config.models],
                    default_model=config.get_default_model()
                ))
            elif name == "ollama":
                from providers.ollama import OllamaProvider
                return OllamaProvider(ProviderConfig(
                    name=name,
                    priority=config.priority,
                    base_url=config.base_url,
                    models=[m.name for m in config.models],
                    default_model=config.get_default_model()
                ))
```

**Step 3: Commit**

```bash
git add core/config.py core/router.py
git commit -m "feat: add OpenRouter and Ollama to config and router"
```

---

## Task 17: Update Package Files

**Files:**
- Modify: `requirements.txt`
- Modify: `core/__init__.py`
- Modify: `providers/__init__.py`

**Step 1: No new dependencies needed** (httpx already covers HTTP for all providers)

The `requirements.txt` is already fine. No changes needed.

**Step 2: Update `core/__init__.py`**

Add agent loop exports:

```python
"""
AI_SYNAPSE — Core Package

Contains core functionality: router, CARL, memory, skills, agent loop.
"""

from .config import (
    ConfigManager,
    SynapseConfig,
    get_config_manager,
    get_config,
)

from .agent_response import (
    AgentResponse,
    ResponseType,
    ToolCall,
    ToolResult,
)

from .agent_loop import AgentLoop

__all__ = [
    "ConfigManager",
    "SynapseConfig",
    "get_config_manager",
    "get_config",
    "AgentResponse",
    "ResponseType",
    "ToolCall",
    "ToolResult",
    "AgentLoop",
]
```

**Step 3: Commit**

```bash
git add core/__init__.py
git commit -m "feat: export agent loop types from core package"
```

---

## Task 18: Smoke Test — Verify Everything Works

**Step 1: Run import check**

```bash
cd /Users/niranjan/Documents/AI_PROJS/AI_SYNAPSE
python -c "
from core.agent_response import AgentResponse, ResponseType, ToolCall, ToolResult
from core.agent_loop import AgentLoop
from core.tools import ToolRegistry
from core.router import ProviderRouter
from core.config import get_config
from providers.base import Provider
print('All imports OK')

# Check tool schemas
tools = ToolRegistry()
schemas = tools.get_openai_tools()
print(f'Tools: {[s[\"function\"][\"name\"] for s in schemas]}')

# Check config
try:
    config = get_config()
    print(f'Providers: {list(config.providers.keys())}')
except:
    print('Config not created yet (OK for test)')

print('Smoke test PASSED')
"
```

Expected: `All imports OK`, `Tools: ['read', 'edit', 'write', 'bash', 'glob', 'grep']`, `Smoke test PASSED`

**Step 2: Test CLI help**

```bash
python synapse.py --help
```

Expected: Should show `--yes` flag in output.

**Step 3: Test single-message mode (if API key available)**

```bash
python synapse.py "what is 2+2" --yes
```

Expected: Should get a response through the agent loop without errors.

**Step 4: Commit final version bump**

Update version in banner and docstring to `v0.4.0`.

```bash
git add -A
git commit -m "feat: AI_SYNAPSE v0.4.0 — full agentic tool loop

- Agentic tool loop: AI can read, edit, write files and run commands
- Function calling for Groq, Gemini, Kimi (native) and Kilo (prompt-based)
- New providers: OpenRouter (100+ free models), Ollama (local/offline)
- Permission system: auto-approve safe, prompt for dangerous commands
- --yes flag for auto-approve mode
- Fixed: Groq import bug, CARL operator precedence, banner alignment
- Fixed: single-shot mode, TUI router integration
- Max 50 iterations safety limit"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | AgentResponse types | `core/agent_response.py` (NEW) |
| 2 | Provider base + tool support | `providers/base.py` |
| 3 | Groq function calling + import fix | `providers/groq.py` |
| 4 | Gemini function calling | `providers/gemini.py` |
| 5 | Kimi function calling | `providers/kimi.py` |
| 6 | Kilo prompt-based tools | `providers/kilo.py` |
| 7 | Permission system in tools | `core/tools.py` |
| 8 | Tool messages in conversation | `core/conversation.py` |
| 9 | CARL bug fix | `core/carl.py` |
| 10 | Router tool-aware routing | `core/router.py` |
| 11 | **Agent Loop** (core) | `core/agent_loop.py` (NEW) |
| 12 | CLI integration | `synapse.py` |
| 13 | TUI integration | `synapse_tui.py` |
| 14 | OpenRouter provider | `providers/openrouter.py` (NEW) |
| 15 | Ollama provider | `providers/ollama.py` (NEW) |
| 16 | Config + router updates | `core/config.py`, `core/router.py` |
| 17 | Package init updates | `core/__init__.py` |
| 18 | Smoke test | All files verified |
