"""
AI_SYNAPSE — Kimi Provider

Provider implementation for Moonshot AI Kimi API.
This is the paid backup provider.
"""

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from core.agent_response import AgentResponse, ResponseType, ToolCall
from providers.base import (
    Provider,
    ProviderConfig,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ServiceUnavailableError
)

logger = logging.getLogger(__name__)


class KimiProvider(Provider):
    """
    Provider implementation for Moonshot AI Kimi API.
    
    This is your PAID backup provider when all free tiers are exhausted.
    
    Models available:
    - kimi-k2.5 (128K context, excellent reasoning)
    
    Get API key: https://platform.moonshot.cn/
    """
    
    API_BASE = "https://api.moonshot.cn/v1"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.client: Optional[httpx.AsyncClient] = None
    
    @property
    def default_model(self) -> str:
        return "kimi-k2.5"

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
    
    async def _check_available(self) -> bool:
        """Check if Kimi API is accessible."""
        if not self.api_key:
            self._set_error("KIMI_API_KEY not set")
            return False
        
        try:
            client = await self._get_client()
            response = await client.get("/models")
            
            if response.status_code == 200:
                self._set_available()
                return True
            elif response.status_code == 401:
                self._set_error("Invalid Kimi API key")
                return False
            else:
                self._set_error(f"Kimi API error: {response.status_code}")
                return False
                
        except Exception as e:
            self._set_error(f"Kimi connection failed: {e}")
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
        """Generate completion using Kimi API."""
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
                    raise RateLimitError("Kimi rate limit exceeded")
                elif response.status_code == 401:
                    raise AuthenticationError("Invalid Kimi API key")
                elif response.status_code != 200:
                    text = await response.aread()
                    raise ServiceUnavailableError(f"Kimi error {response.status_code}: {text}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.TimeoutException:
            raise ServiceUnavailableError(f"Kimi request timed out")
        except Exception as e:
            raise ProviderError(f"Kimi error: {e}")

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
