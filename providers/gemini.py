"""
AI_SYNAPSE — Gemini Provider

Provider implementation for Google Gemini API.
Gemini offers 1M context window with free tier.
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


class GeminiProvider(Provider):
    """
    Provider implementation for Google Gemini API.
    
    Free tier limits:
    - 15 RPM (requests per minute)
    - 1M tokens per minute
    - 1,500 requests per day
    
    Models available:
    - gemini-2.5-flash (1M context, 15 RPM)
    - gemini-2.0-flash (1M context, 15 RPM)
    
    Get API key: https://aistudio.google.com/app/apikey
    """
    
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.client: Optional[httpx.AsyncClient] = None
    
    @property
    def default_model(self) -> str:
        return "gemini-2.5-flash"

    @property
    def supports_function_calling(self) -> bool:
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.config.timeout
            )
        return self.client
    
    def _convert_messages(self, messages: list[dict]) -> tuple[Optional[str], list[dict]]:
        """
        Convert OpenAI-style messages to Gemini format.
        
        Returns:
            (system_instruction, contents)
        """
        system_instruction = None
        contents = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        return system_instruction, contents
    
    async def _check_available(self) -> bool:
        """Check if Gemini API is accessible."""
        if not self.api_key:
            self._set_error("GEMINI_API_KEY not set")
            return False
        
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.API_BASE}/models",
                params={"key": self.api_key}
            )
            
            if response.status_code == 200:
                self._set_available()
                return True
            elif response.status_code == 400:
                self._set_error("Invalid Gemini API key")
                return False
            else:
                self._set_error(f"Gemini API error: {response.status_code}")
                return False
                
        except Exception as e:
            self._set_error(f"Gemini connection failed: {e}")
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
        """Generate completion using Gemini API."""
        model = self.get_model(model)
        client = await self._get_client()
        
        system_instruction, contents = self._convert_messages(messages)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        
        endpoint = f"{self.API_BASE}/models/{model}:streamGenerateContent"
        
        try:
            async with client.stream(
                "POST",
                endpoint,
                params={"key": self.api_key},
                json=payload
            ) as response:
                if response.status_code == 429:
                    self._set_rate_limited()
                    raise RateLimitError("Gemini rate limit exceeded")
                elif response.status_code == 400:
                    raise AuthenticationError("Invalid Gemini API key")
                elif response.status_code != 200:
                    text = await response.aread()
                    raise ServiceUnavailableError(f"Gemini error {response.status_code}: {text}")
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # Gemini returns JSON objects, not SSE
                    if line.startswith("[") or line.startswith("{"):
                        try:
                            # Handle streaming JSON array
                            if line.startswith(","):
                                line = line[1:]
                            if line.endswith("]"):
                                line = line[:-1]
                            
                            chunk = json.loads(line)
                            if "candidates" in chunk and len(chunk["candidates"]) > 0:
                                candidate = chunk["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            yield part["text"]
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.TimeoutException:
            raise ServiceUnavailableError(f"Gemini request timed out")
        except Exception as e:
            raise ProviderError(f"Gemini error: {e}")

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
        model = self.get_model(model)
        client = await self._get_client()

        system_instruction, contents = self._convert_messages(messages)
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
