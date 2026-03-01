"""
AI_SYNAPSE — Provider Base Class

Abstract base class for all AI providers.
Each provider (Kilo, Groq, Gemini, Kimi, Ollama) implements this interface.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Status of a provider."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    name: str
    enabled: bool = True
    priority: int = 10  # Lower = higher priority
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    models: List[str] = field(default_factory=list)
    timeout: float = 60.0


class Provider(ABC):
    """
    Abstract base class for all AI providers.
    
    Each provider must implement:
    - complete(): Generate text completion
    - check_available(): Check if provider is usable
    - get_default_model(): Return default model name
    
    Example:
        provider = KiloProvider(config)
        if await provider.check_available():
            async for chunk in provider.complete(messages):
                print(chunk, end="")
    """
    
    # Cache availability checks for this many seconds
    AVAILABILITY_CACHE_TTL = 60

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.priority = config.priority
        self._status = ProviderStatus.UNAVAILABLE
        self._last_error: Optional[str] = None
        self._availability_cache: Optional[bool] = None
        self._availability_cache_time: float = 0
        self._logged_errors: set = set()
    
    @abstractmethod
    async def complete(
        self,
        messages: list[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate text completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (None = use default)
            stream: Whether to stream response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific params
            
        Yields:
            Text chunks (if stream=True) or full text (if stream=False)
            
        Raises:
            ProviderError: If the provider fails
        """
        # Abstract: subclasses must implement as async generator with yield
        raise NotImplementedError
        yield  # noqa: makes this an async generator for type checking

    async def check_available(self) -> bool:
        """
        Check if provider is available (with caching).

        Returns cached result within TTL window to avoid
        redundant network calls on every agent loop iteration.
        """
        now = time.monotonic()
        if (self._availability_cache is not None
                and now - self._availability_cache_time < self.AVAILABILITY_CACHE_TTL):
            return self._availability_cache

        result = await self._check_available()
        self._availability_cache = result
        self._availability_cache_time = now
        return result

    @abstractmethod
    async def _check_available(self) -> bool:
        """
        Actually check if provider is available and ready to use.

        Subclasses implement this. Called by check_available() when cache expires.
        """
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass

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
        """
        from core.agent_response import AgentResponse, ResponseType
        result = self.complete(messages, model, stream, temperature, max_tokens, **kwargs)
        async for chunk in result:  # type: ignore[union-attr]
            yield AgentResponse(type=ResponseType.TEXT, text=chunk)
        yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")

    @property
    def status(self) -> ProviderStatus:
        """Current status of the provider."""
        return self._status
    
    @property
    def last_error(self) -> Optional[str]:
        """Last error message, if any."""
        return self._last_error
    
    def _set_error(self, error: str):
        """Set error state. Only logs each unique error once."""
        self._status = ProviderStatus.ERROR
        self._last_error = error
        if error not in self._logged_errors:
            self._logged_errors.add(error)
            logger.warning(f"{self.name} error: {error}")
    
    def _set_available(self):
        """Set available state."""
        self._status = ProviderStatus.AVAILABLE
        self._last_error = None
    
    def _set_rate_limited(self):
        """Set rate limited state."""
        self._status = ProviderStatus.RATE_LIMITED
        logger.warning(f"{self.name} rate limited")
    
    def get_model(self, model: Optional[str] = None) -> str:
        """Get model to use, falling back to default if needed."""
        if model:
            return model
        if self.config.default_model:
            return self.config.default_model
        return self.default_model


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class RateLimitError(ProviderError):
    """Provider is rate limited."""
    pass


class AuthenticationError(ProviderError):
    """Authentication failed (invalid API key)."""
    pass


class ServiceUnavailableError(ProviderError):
    """Provider service is down."""
    pass


class AllProvidersFailed(ProviderError):
    """All providers in the chain failed."""
    pass
