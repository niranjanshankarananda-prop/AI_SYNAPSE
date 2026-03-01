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
        return "qwen2.5-coder:7b"

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

    async def _check_available(self) -> bool:
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

        # Ollama expects tool_call arguments as dicts, not JSON strings
        # (OpenAI uses strings, Ollama uses dicts). Convert before sending.
        fixed_messages = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                msg = dict(msg)
                fixed_tcs = []
                for tc in msg["tool_calls"]:
                    tc = dict(tc)
                    if "function" in tc:
                        func = dict(tc["function"])
                        args = func.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                func["arguments"] = json.loads(args)
                            except json.JSONDecodeError:
                                pass
                        tc["function"] = func
                    fixed_tcs.append(tc)
                msg["tool_calls"] = fixed_tcs
            fixed_messages.append(msg)

        payload = {
            "model": model,
            "messages": fixed_messages,
            "stream": True,
            "tools": tools,
            "options": {"temperature": temperature}
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            # Collect full response first, then decide if it's text or tool call.
            # We can't stream text and also detect text-based tool calls,
            # so we buffer everything and yield at the end.
            full_content = ""
            tool_calls_data = []

            async with client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise ServiceUnavailableError(f"Ollama error: {error_text.decode()}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})

                        # Collect structured tool calls if present
                        if msg.get("tool_calls"):
                            tool_calls_data.extend(msg["tool_calls"])

                        # Buffer text content
                        content = msg.get("content", "")
                        if content:
                            full_content += content

                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

            # 1. If we got structured tool calls, yield them
            if tool_calls_data:
                tool_calls = []
                for tc in tool_calls_data:
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
                return

            # 2. Try parsing text-based tool calls (for models without native FC)
            if full_content:
                parsed_tc = self._try_parse_text_tool_call(full_content)
                if parsed_tc:
                    yield AgentResponse(
                        type=ResponseType.TOOL_CALL,
                        tool_calls=parsed_tc,
                        finish_reason="tool_calls"
                    )
                    return

            # 3. It's just text — yield it all at once
            if full_content:
                yield AgentResponse(type=ResponseType.TEXT, text=full_content)
            yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")

        except httpx.ConnectError:
            raise ServiceUnavailableError("Ollama not running")

    @staticmethod
    def _try_parse_text_tool_call(content: str) -> list:
        """Try to parse a tool call from text content (for models without native FC)."""
        import re
        content = content.strip()
        # Try direct JSON: {"name": "...", "arguments": {...}}
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "name" in parsed:
                return [ToolCall(
                    name=parsed["name"],
                    arguments=parsed.get("arguments", {})
                )]
        except json.JSONDecodeError:
            pass
        # Try <tool_call> tags (same as Kilo)
        pattern = r'<tool_call>\s*(\{.+?\})\s*</tool_call>'
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            results = []
            for m in matches:
                try:
                    parsed = json.loads(m)
                    results.append(ToolCall(
                        name=parsed.get("name", ""),
                        arguments=parsed.get("arguments", {})
                    ))
                except json.JSONDecodeError:
                    continue
            if results:
                return results
        return []
