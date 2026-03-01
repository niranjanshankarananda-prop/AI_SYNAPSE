"""
AI_SYNAPSE — Provider Router

Routes requests to available providers with intelligent fallback.
"""

import logging
from typing import AsyncIterator, List, Optional
from dataclasses import dataclass

from providers.base import (
    Provider, 
    ProviderConfig, 
    ProviderError,
    AllProvidersFailed
)
from core.config import SynapseConfig, get_config

logger = logging.getLogger(__name__)


@dataclass
class RouterStats:
    """Statistics for router operations."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_count: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class ProviderRouter:
    """
    Routes requests to providers with automatic fallback.
    
    Maintains a priority-ordered list of providers. For each request:
    1. Try providers in priority order
    2. Skip unavailable providers
    3. On failure, try next provider (fallback)
    4. Track statistics
    
    Example:
        router = ProviderRouter()
        async for chunk in router.complete(messages):
            print(chunk, end="")
    """
    
    def __init__(self, config: Optional[SynapseConfig] = None):
        self.config = config or get_config()
        self.providers: List[Provider] = []
        self.current_provider: Optional[Provider] = None
        self.stats = RouterStats()
        self._initialized = False
    
    async def initialize(self):
        """Initialize and sort providers by priority."""
        if self._initialized:
            return
        
        self.providers = []
        
        # Get enabled providers sorted by priority
        provider_configs = self.config.providers
        sorted_providers = sorted(
            provider_configs.items(),
            key=lambda x: x[1].priority
        )
        
        # Import and instantiate providers
        for name, provider_config in sorted_providers:
            if not provider_config.enabled:
                logger.debug(f"Provider {name} is disabled, skipping")
                continue
            
            try:
                provider = self._load_provider(name, provider_config)
                if provider:
                    self.providers.append(provider)
                    logger.info(f"Loaded provider: {name} (priority {provider_config.priority})")
            except Exception as e:
                logger.warning(f"Failed to load provider {name}: {e}")
        
        self._initialized = True
        logger.info(f"Router initialized with {len(self.providers)} providers")
    
    def _load_provider(self, name: str, config) -> Optional[Provider]:
        """Dynamically load a provider implementation."""
        try:
            if name == "kilo":
                from providers.kilo import KiloProvider
                return KiloProvider(ProviderConfig(
                    name=name,
                    priority=config.priority,
                    models=[m.name for m in config.models],
                    default_model=config.get_default_model()
                ))
            elif name == "groq":
                from providers.groq import GroqProvider
                return GroqProvider(ProviderConfig(
                    name=name,
                    priority=config.priority,
                    api_key=config.api_key,
                    models=[m.name for m in config.models],
                    default_model=config.get_default_model()
                ))
            elif name == "gemini":
                from providers.gemini import GeminiProvider
                return GeminiProvider(ProviderConfig(
                    name=name,
                    priority=config.priority,
                    api_key=config.api_key,
                    models=[m.name for m in config.models],
                    default_model=config.get_default_model()
                ))
            elif name == "kimi":
                from providers.kimi import KimiProvider
                return KimiProvider(ProviderConfig(
                    name=name,
                    priority=config.priority,
                    api_key=config.api_key,
                    models=[m.name for m in config.models],
                    default_model=config.get_default_model()
                ))
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
            else:
                logger.warning(f"Unknown provider: {name}")
                return None
        except ImportError as e:
            logger.warning(f"Provider {name} not available: {e}")
            return None
    
    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate completion, trying providers until one succeeds.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (None = provider default)
            stream: Whether to stream response
            **kwargs: Additional arguments passed to provider
            
        Yields:
            Text chunks from the successful provider
            
        Raises:
            AllProvidersFailed: If no provider succeeds
        """
        if not self._initialized:
            await self.initialize()
        
        self.stats.total_requests += 1
        last_error = None
        
        for provider in self.providers:
            try:
                # Check if provider is available
                if not await provider.check_available():
                    logger.debug(f"Provider {provider.name} is not available, skipping")
                    continue
                
                logger.info(f"Trying provider: {provider.name}")
                self.current_provider = provider
                
                # Attempt completion
                async for chunk in provider.complete(messages, model, stream, **kwargs):
                    yield chunk
                
                # Success!
                self.stats.successful_requests += 1
                return
                
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                self.stats.fallback_count += 1
                last_error = e
                continue
        
        # All providers failed
        self.stats.failed_requests += 1
        self.current_provider = None
        
        error_msg = f"All providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise AllProvidersFailed(error_msg)

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

        # Use priority order — all providers implement complete_with_tools
        # (either native FC or prompt-based parsing)
        sorted_providers = sorted(
            self.providers,
            key=lambda p: p.priority
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

    def get_current_provider_name(self) -> Optional[str]:
        """Get the name of the current (last used) provider."""
        if self.current_provider:
            return self.current_provider.name
        return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [p.name for p in self.providers]
    
    def get_stats(self) -> RouterStats:
        """Get router statistics."""
        return self.stats
