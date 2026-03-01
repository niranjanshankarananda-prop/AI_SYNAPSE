"""Tests for core/router.py — provider ordering, stats, fallback, retry."""

import pytest

from core.router import ProviderRouter, RouterStats
from core.agent_response import AgentResponse, ResponseType
from providers.base import (
    Provider,
    ProviderConfig,
    ProviderError,
    ServiceUnavailableError,
    AuthenticationError,
    AllProvidersFailed,
)


# ── Mock Providers ────────────────────────────────────────────────────

class MockProvider(Provider):
    """A provider that yields fixed chunks."""

    def __init__(self, name="mock", priority=1, available=True, chunks=None, fail_with=None):
        config = ProviderConfig(name=name, priority=priority)
        super().__init__(config)
        self._available = available
        self._chunks = chunks or ["hello ", "world"]
        self._fail_with = fail_with
        self._call_count = 0

    @property
    def default_model(self) -> str:
        return "mock-model"

    async def _check_available(self) -> bool:
        return self._available

    async def complete(self, messages, model=None, stream=True, temperature=0.7, max_tokens=None, **kwargs):
        self._call_count += 1
        if self._fail_with:
            raise self._fail_with
        for chunk in self._chunks:
            yield chunk

    async def complete_with_tools(self, messages, tools, model=None, stream=True, temperature=0.7, max_tokens=None, **kwargs):
        self._call_count += 1
        if self._fail_with:
            raise self._fail_with
        yield AgentResponse(type=ResponseType.TEXT, text="tool response")
        yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")


# ── RouterStats ───────────────────────────────────────────────────────

class TestRouterStats:
    def test_success_rate_zero(self):
        stats = RouterStats()
        assert stats.success_rate == 0.0

    def test_success_rate_calculation(self):
        stats = RouterStats(total_requests=10, successful_requests=7)
        assert stats.success_rate == pytest.approx(0.7)


# ── ProviderRouter ────────────────────────────────────────────────────

class TestProviderRouter:
    @pytest.mark.asyncio
    async def test_complete_success(self):
        router = ProviderRouter()
        router._initialized = True
        router.providers = [MockProvider()]

        chunks = []
        async for chunk in router.complete([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["hello ", "world"]
        assert router.stats.successful_requests == 1

    @pytest.mark.asyncio
    async def test_fallback_to_second_provider(self):
        failing = MockProvider(name="failing", priority=1, fail_with=ProviderError("oops"))
        working = MockProvider(name="working", priority=2, chunks=["fallback"])

        router = ProviderRouter()
        router._initialized = True
        router.providers = [failing, working]

        chunks = []
        async for chunk in router.complete([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["fallback"]
        assert router.stats.fallback_count >= 1

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        failing = MockProvider(name="fail1", fail_with=ProviderError("err"))

        router = ProviderRouter()
        router._initialized = True
        router.providers = [failing]

        with pytest.raises(AllProvidersFailed):
            async for _ in router.complete([{"role": "user", "content": "hi"}]):
                pass

    @pytest.mark.asyncio
    async def test_skip_unavailable_provider(self):
        unavailable = MockProvider(name="down", available=False)
        available = MockProvider(name="up", chunks=["ok"])

        router = ProviderRouter()
        router._initialized = True
        router.providers = [unavailable, available]

        chunks = []
        async for chunk in router.complete([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["ok"]

    @pytest.mark.asyncio
    async def test_complete_with_tools_success(self):
        router = ProviderRouter()
        router._initialized = True
        router.providers = [MockProvider()]

        responses = []
        async for resp in router.complete_with_tools(
            [{"role": "user", "content": "hi"}], tools=[]
        ):
            responses.append(resp)
        assert any(r.type == ResponseType.TEXT for r in responses)

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Provider that fails once with ServiceUnavailableError then works."""
        call_count = 0

        class FlakeyProvider(MockProvider):
            async def complete(self, messages, model=None, stream=True, temperature=0.7, max_tokens=None, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ServiceUnavailableError("temporary")
                for chunk in self._chunks:
                    yield chunk

        router = ProviderRouter()
        router._initialized = True
        router.providers = [FlakeyProvider()]

        chunks = []
        async for chunk in router.complete([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["hello ", "world"]
        assert call_count == 2  # retried once

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """AuthenticationError should NOT be retried — fall through to next provider."""
        failing = MockProvider(
            name="auth_fail", priority=1,
            fail_with=AuthenticationError("bad key")
        )
        working = MockProvider(name="backup", priority=2, chunks=["ok"])

        router = ProviderRouter()
        router._initialized = True
        router.providers = [failing, working]

        chunks = []
        async for chunk in router.complete([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["ok"]
        # Auth-failing provider should only be called once (no retry)
        assert failing._call_count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self):
        router = ProviderRouter()
        router._initialized = True
        router.providers = [MockProvider()]

        async for _ in router.complete([{"role": "user", "content": "hi"}]):
            pass

        stats = router.get_stats()
        assert stats.total_requests == 1
        assert stats.successful_requests == 1

    def test_get_current_provider_name_none(self):
        router = ProviderRouter()
        assert router.get_current_provider_name() is None
