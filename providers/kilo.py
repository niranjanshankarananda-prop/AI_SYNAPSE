"""
AI_SYNAPSE — Kilo Provider

Provider implementation for Kilo CLI.
Kilo provides free access to Kimi K2.5, MiniMax M2.5, Qwen 235B, etc.
"""

import asyncio
import json
import logging
import re
import subprocess
from typing import AsyncIterator, Optional

from core.agent_response import AgentResponse, ResponseType, ToolCall
from providers.base import (
    Provider,
    ProviderConfig,
    ProviderError,
    ServiceUnavailableError
)

logger = logging.getLogger(__name__)


class KiloProvider(Provider):
    """
    Provider implementation for Kilo CLI.
    
    Kilo (https://kilo.ai) provides free access to:
    - Kimi K2.5 (Moonshot AI) — Opus-level intelligence
    - MiniMax M2.5 — Strong reasoning
    - Qwen 235B — Massive parameter model
    - And more
    
    Usage:
        config = ProviderConfig(
            name="kilo",
            priority=1,
            models=["kilo/moonshotai/kimi-k2.5:free"],
            default_model="kilo/moonshotai/kimi-k2.5:free"
        )
        provider = KiloProvider(config)
        async for chunk in provider.complete([{"role": "user", "content": "hello"}]):
            print(chunk, end="")
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.kilo_path = "kilo"
    
    @property
    def default_model(self) -> str:
        """Default model for Kilo."""
        return "kilo/moonshotai/kimi-k2.5:free"
    
    async def _check_available(self) -> bool:
        """
        Check if Kilo CLI is installed and working.
        
        Returns:
            True if Kilo is available
        """
        try:
            # Check if kilo command exists
            result = await asyncio.create_subprocess_exec(
                "which", self.kilo_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            
            if result.returncode != 0:
                self._set_error("Kilo CLI not found in PATH")
                return False
            
            # Try to list models (requires auth)
            result = await asyncio.create_subprocess_exec(
                self.kilo_path, "models",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                error_msg = stderr.decode().strip()
                if "auth" in error_msg.lower() or "login" in error_msg.lower():
                    self._set_error("Kilo authentication required. Run 'kilo auth'")
                else:
                    self._set_error(f"Kilo error: {error_msg}")
                return False
            
            self._set_available()
            return True
            
        except Exception as e:
            self._set_error(f"Failed to check Kilo: {e}")
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
        """
        Generate completion using Kilo CLI.
        
        Note: Kilo CLI doesn't support true streaming, so we simulate it
        by yielding words as they're received.
        """
        model = self.get_model(model)
        
        # Extract the last user message for Kilo
        # Kilo's simple CLI interface takes a single message
        last_message = messages[-1]["content"] if messages else ""
        
        # Build system context from previous messages
        system_context = ""
        for msg in messages[:-1]:
            if msg["role"] == "system":
                system_context += f"{msg['content']}\n\n"
            elif msg["role"] == "assistant":
                system_context += f"Assistant: {msg['content']}\n\n"
            elif msg["role"] == "user":
                system_context += f"User: {msg['content']}\n\n"
        
        # Combine system context with last message
        if system_context:
            full_prompt = f"{system_context}\nUser: {last_message}\n\nAssistant:"
        else:
            full_prompt = last_message
        
        logger.debug(f"Kilo prompt: {full_prompt[:100]}...")
        
        try:
            # Run Kilo CLI
            cmd = [
                self.kilo_path,
                "run",
                full_prompt,
                "--model", model,
            ]
            
            # Note: Kilo doesn't support streaming well, so we capture output
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024  # 1MB buffer
            )
            
            # Read output
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                raise ServiceUnavailableError(f"Kilo failed: {error_msg}")
            
            response = stdout.decode().strip()
            
            # Simulate streaming by yielding words
            # This gives better UX even though Kilo doesn't stream
            words = response.split(" ")
            for i, word in enumerate(words):
                if i > 0:
                    yield " "
                yield word
                # Small delay to simulate streaming
                if i < len(words) - 1:
                    await asyncio.sleep(0.01)
            
            yield "\n"
            
        except asyncio.TimeoutError:
            raise ServiceUnavailableError(f"Kilo request timed out after {self.config.timeout}s")
        except Exception as e:
            raise ProviderError(f"Kilo error: {e}")

    TOOL_INSTRUCTION_TEMPLATE = """You are a coding assistant with access to tools. You MUST use tools to answer questions about files and code. NEVER guess or assume — always verify with tools first.

When you need to use a tool, output EXACTLY this format:

<tool_call>{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}</tool_call>

After the tool result comes back, continue your response based on the actual result.

Available tools:
{tool_descriptions}

RULES:
- When asked about file contents, ALWAYS use the read tool first.
- When asked to find files, ALWAYS use the glob tool first.
- Output ONE tool call at a time. Wait for results before continuing.
- Base your answer ONLY on tool results, never on assumptions."""

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
        tool_call_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
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


class KiloStreamProvider(Provider):
    """
    Alternative Kilo provider using the Kilo server API.
    
    This is for future use when Kilo exposes a proper API.
    Currently just a placeholder.
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:8080"
    
    @property
    def default_model(self) -> str:
        return "kilo/moonshotai/kimi-k2.5:free"
    
    async def _check_available(self) -> bool:
        """Check if Kilo server is running."""
        # TODO: Implement when Kilo exposes server API
        return False
    
    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate completion via Kilo server API."""
        # TODO: Implement when Kilo exposes server API
        raise NotImplementedError("Kilo server API not yet available")
