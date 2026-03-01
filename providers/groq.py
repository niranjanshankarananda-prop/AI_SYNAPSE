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
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.config.timeout
            )
        return self.client

    async def _check_available(self) -> bool:
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
                raise RateLimitError("Groq rate limit exceeded")
            elif response.status_code == 401:
                raise AuthenticationError("Invalid Groq API key")
            elif response.status_code != 200:
                raise ServiceUnavailableError(f"Groq error {response.status_code}: {response.text}")

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
            raise ServiceUnavailableError("Groq request timed out")
