"""Unit tests for the provider-neutral AICOS Model Router."""

from __future__ import annotations

import unittest

from pydantic import SecretStr

from backend.aicos.core.di import Container
from backend.aicos.llm import (
    ChatMessage,
    HealthMonitor,
    ModelCapability,
    ModelDefinition,
    ModelNotFoundError,
    ModelRegistry,
    ModelRequest,
    ModelResponse,
    ModelRouter,
    ProviderHealth,
    ProviderRegistry,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RoutingError,
    RoutingStrategy,
    UnsupportedCapabilityError,
    register_model_router,
)
from backend.aicos.llm.providers import MockProvider
from backend.aicos.settings import Settings
from backend.aicos.logging import shutdown_logging


def model(
    provider: str,
    name: str,
    *,
    capabilities: frozenset[ModelCapability] | None = None,
    priority: int = 100,
    local: bool = False,
) -> ModelDefinition:
    return ModelDefinition(
        provider=provider,
        model_name=name,
        capabilities=capabilities or frozenset({ModelCapability.CHAT}),
        context_window=8192,
        priority=priority,
        local=local,
    )


def request(**overrides: object) -> ModelRequest:
    return ModelRequest(messages=(ChatMessage(role="user", content="hello"),), **overrides)


class ModelRouterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        shutdown_logging()

    async def test_provider_and_model_registration_routes_to_mock(self) -> None:
        router = ModelRouter()
        provider = MockProvider(response_content="configured")
        router.register_provider(provider)
        router.register_model(model("mock", "test-model"))

        response = await router.generate(request())

        self.assertEqual(response.content, "configured")
        self.assertEqual(response.provider, "mock")
        self.assertEqual(len(provider.requests), 1)

    async def test_capability_matching_selects_eligible_model(self) -> None:
        router = ModelRouter()
        provider = MockProvider()
        router.register_provider(provider)
        router.register_model(model("mock", "chat", priority=1))
        router.register_model(
            model("mock", "reasoning", capabilities=frozenset({ModelCapability.CHAT, ModelCapability.REASONING}))
        )

        response = await router.generate(request(required_capabilities=frozenset({ModelCapability.REASONING})))

        self.assertEqual(response.model_name, "reasoning")

    async def test_local_first_and_provider_preference_are_registry_driven(self) -> None:
        router = ModelRouter()
        local_provider = MockProvider(response_content="local")
        local_provider.name = "local"
        remote_provider = MockProvider(response_content="remote")
        remote_provider.name = "remote"
        router.register_provider(local_provider)
        router.register_provider(remote_provider)
        router.register_model(model("remote", "remote-model", priority=1))
        router.register_model(model("local", "local-model", priority=10, local=True))

        local_response = await router.generate(request(strategy=RoutingStrategy.LOCAL_FIRST))
        remote_response = await router.generate(
            request(strategy=RoutingStrategy.PROVIDER_PREFERENCE, provider_preferences=("remote",))
        )

        self.assertEqual(local_response.provider, "local")
        self.assertEqual(remote_response.provider, "remote")

    async def test_unavailable_provider_falls_back_and_health_influences_next_route(self) -> None:
        router = ModelRouter()
        unavailable = MockProvider(available=False)
        unavailable.name = "first"
        fallback = MockProvider(response_content="fallback")
        fallback.name = "second"
        router.register_provider(unavailable)
        router.register_provider(fallback)
        router.register_model(model("first", "first-model", priority=1))
        router.register_model(model("second", "second-model", priority=2))

        first_response = await router.generate(request())
        second_response = await router.generate(request())

        self.assertEqual(first_response.provider, "second")
        self.assertEqual(second_response.provider, "second")
        self.assertFalse(router.health.get("first").available)
        self.assertEqual(router.health.get("first").failures, 1)

    async def test_preferred_model_can_fall_back(self) -> None:
        router = ModelRouter()
        unavailable = MockProvider(available=False)
        unavailable.name = "first"
        fallback = MockProvider()
        fallback.name = "second"
        router.register_provider(unavailable)
        router.register_provider(fallback)
        router.register_model(model("first", "preferred", priority=1))
        router.register_model(model("second", "fallback", priority=2))

        response = await router.generate(request(preferred_model="preferred"))

        self.assertEqual(response.provider, "second")

    async def test_health_checks_and_error_cases(self) -> None:
        router = ModelRouter()
        unavailable = MockProvider(available=False)
        router.register_provider(unavailable)
        router.register_model(model("mock", "chat"))

        health = (await router.check_health())[0]
        self.assertFalse(health.available)
        with self.assertRaises(UnsupportedCapabilityError):
            await router.generate(request(required_capabilities=frozenset({ModelCapability.VISION})))
        with self.assertRaises(ModelNotFoundError):
            await router.generate(request(preferred_model="missing"))

        empty_router = ModelRouter()
        with self.assertRaises(RoutingError):
            await empty_router.generate(request())

    async def test_di_registration_creates_singleton_router(self) -> None:
        container = Container()
        settings = Settings(config_dir="missing-config")
        register_model_router(container, settings)

        self.assertIs(container.resolve(ModelRouter), container.resolve(ModelRouter))

# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class ProviderRegistryTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_duplicate_registration_raises_error(self) -> None:
        registry = ProviderRegistry()
        provider = MockProvider()
        registry.register(provider)
        with self.assertRaises(ValueError) as context:
            registry.register(provider)
        self.assertIn("mock", str(context.exception))

    def test_get_missing_provider_raises_error(self) -> None:
        registry = ProviderRegistry()
        with self.assertRaises(ProviderUnavailableError):
            registry.get("nonexistent")

    def test_all_returns_registered_providers(self) -> None:
        registry = ProviderRegistry()
        self.assertEqual(registry.all(), ())
        p1 = MockProvider()
        p1.name = "p1"
        p2 = MockProvider()
        p2.name = "p2"
        registry.register(p1)
        registry.register(p2)
        result = registry.all()
        self.assertEqual(len(result), 2)
        self.assertIn(p1, result)
        self.assertIn(p2, result)


# ---------------------------------------------------------------------------
# ModelRegistry
# ---------------------------------------------------------------------------


class ModelRegistryTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_duplicate_registration_raises_error(self) -> None:
        registry = ModelRegistry()
        m = model("test-provider", "duplicate-model")
        registry.register(m)
        with self.assertRaises(ValueError) as context:
            registry.register(m)
        self.assertIn("test-provider/duplicate-model", str(context.exception))

    def test_get_returns_registered_model(self) -> None:
        registry = ModelRegistry()
        m = model("test-provider", "get-test")
        registry.register(m)
        self.assertIs(registry.get("test-provider", "get-test"), m)

    def test_get_missing_model_raises_error(self) -> None:
        registry = ModelRegistry()
        with self.assertRaises(ModelNotFoundError):
            registry.get("nonexistent", "missing")

    def test_find_by_name_returns_matching_models(self) -> None:
        registry = ModelRegistry()
        m1 = model("p1", "gpt-4")
        m2 = model("p2", "gpt-4")
        m3 = model("p1", "other")
        registry.register(m1)
        registry.register(m2)
        registry.register(m3)
        results = registry.find_by_name("gpt-4")
        self.assertEqual(len(results), 2)
        self.assertIn(m1, results)
        self.assertIn(m2, results)

    def test_find_by_name_with_provider_filter(self) -> None:
        registry = ModelRegistry()
        m1 = model("p1", "gpt-4")
        m2 = model("p2", "gpt-4")
        registry.register(m1)
        registry.register(m2)
        results = registry.find_by_name("gpt-4", provider="p1")
        self.assertEqual(len(results), 1)
        self.assertIs(results[0], m1)

    def test_candidates_returns_enabled_models_with_capability(self) -> None:
        registry = ModelRegistry()
        chat = model("p1", "chat-model")
        reasoning = model(
            "p1", "reasoning-model", capabilities=frozenset({ModelCapability.CHAT, ModelCapability.REASONING})
        )
        registry.register(chat)
        registry.register(reasoning)
        results = registry.candidates(frozenset({ModelCapability.REASONING}))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].model_name, "reasoning-model")

    def test_candidates_excludes_disabled_models(self) -> None:
        registry = ModelRegistry()
        enabled = model("p1", "enabled-model")
        disabled = ModelDefinition(
            provider="p1",
            model_name="disabled-model",
            capabilities=frozenset({ModelCapability.CHAT}),
            context_window=8192,
            enabled=False,
        )
        registry.register(enabled)
        registry.register(disabled)
        results = registry.candidates(frozenset({ModelCapability.CHAT}))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].model_name, "enabled-model")

    def test_all_returns_sorted_models(self) -> None:
        registry = ModelRegistry()
        m1 = model("b-provider", "z-model", priority=10)
        m2 = model("a-provider", "a-model", priority=10)
        m3 = model("a-provider", "b-model", priority=5)
        registry.register(m1)
        registry.register(m2)
        registry.register(m3)
        results = registry.all()
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].model_name, "b-model")
        self.assertEqual(results[1].model_name, "a-model")
        self.assertEqual(results[2].model_name, "z-model")

    def test_all_empty_registry(self) -> None:
        registry = ModelRegistry()
        self.assertEqual(registry.all(), ())


# ---------------------------------------------------------------------------
# HealthMonitor
# ---------------------------------------------------------------------------


class HealthMonitorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        shutdown_logging()

    def test_get_unregistered_provider_returns_default_health(self) -> None:
        monitor = HealthMonitor()
        health = monitor.get("unknown")
        self.assertEqual(health.provider, "unknown")
        self.assertTrue(health.available)
        self.assertEqual(health.failures, 0)
        self.assertIsNone(health.latency_ms)

    def test_record_success_returns_healthy_state(self) -> None:
        monitor = HealthMonitor()
        health = monitor.record_success("ollama", 42.5)
        self.assertEqual(health.provider, "ollama")
        self.assertTrue(health.available)
        self.assertEqual(health.latency_ms, 42.5)
        self.assertEqual(health.failures, 0)
        self.assertIsNotNone(health.last_successful_request)

    def test_record_failure_increments_failures_and_marks_unavailable(self) -> None:
        monitor = HealthMonitor()
        monitor.record_success("ollama", 10.0)
        health = monitor.record_failure("ollama")
        self.assertFalse(health.available)
        self.assertEqual(health.failures, 1)
        self.assertEqual(health.latency_ms, 10.0)

    def test_record_failure_without_prior_state(self) -> None:
        monitor = HealthMonitor()
        health = monitor.record_failure("ollama")
        self.assertFalse(health.available)
        self.assertEqual(health.failures, 1)
        self.assertIsNone(health.latency_ms)
        self.assertIsNone(health.last_successful_request)

    async def test_check_available_provider(self) -> None:
        monitor = HealthMonitor()
        provider = MockProvider(available=True)
        health = await monitor.check(provider)
        self.assertTrue(health.available)
        self.assertEqual(health.provider, "mock")
        self.assertEqual(health.failures, 0)

    async def test_check_provider_raising_exception_records_failure(self) -> None:
        monitor = HealthMonitor()

        class BrokenProvider:
            name = "broken"

            async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse:
                raise NotImplementedError

            async def health_check(self) -> ProviderHealth:
                raise ProviderUnavailableError("broken")

        health = await monitor.check(BrokenProvider())
        self.assertFalse(health.available)
        self.assertEqual(health.failures, 1)
        self.assertEqual(health.provider, "broken")


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------


class MockProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        shutdown_logging()

    async def test_generate_returns_expected_content(self) -> None:
        provider = MockProvider(response_content="expected text")
        req = request()
        model_def = model("mock", "test-model")
        response = await provider.generate(req, model_def)
        self.assertEqual(response.content, "expected text")
        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.model_name, "test-model")

    async def test_generate_tracks_requests(self) -> None:
        provider = MockProvider()
        model_def = model("mock", "tracked-model")
        req = request()
        await provider.generate(req, model_def)
        self.assertEqual(len(provider.requests), 1)
        self.assertIs(provider.requests[0][0], req)
        self.assertIs(provider.requests[0][1], model_def)

    async def test_generate_raises_error_when_unavailable(self) -> None:
        provider = MockProvider(available=False)
        with self.assertRaises(ProviderUnavailableError):
            await provider.generate(request(), model("mock", "unavailable"))

    async def test_health_check_available(self) -> None:
        provider = MockProvider(available=True)
        health = await provider.health_check()
        self.assertTrue(health.available)
        self.assertEqual(health.failures, 0)
        self.assertIsNotNone(health.last_successful_request)

    async def test_health_check_unavailable(self) -> None:
        provider = MockProvider(available=False)
        health = await provider.health_check()
        self.assertFalse(health.available)
        self.assertEqual(health.failures, 1)
        self.assertIsNone(health.last_successful_request)


# ---------------------------------------------------------------------------
# ModelDefinition.supports()
# ---------------------------------------------------------------------------


class ModelDefinitionSupportsTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def test_supports_subset_capabilities(self) -> None:
        m = model("test", "m", capabilities=frozenset({ModelCapability.CHAT, ModelCapability.CODING}))
        self.assertTrue(m.supports(frozenset({ModelCapability.CHAT})))

    def test_supports_exact_capability_set(self) -> None:
        caps = frozenset({ModelCapability.CHAT, ModelCapability.CODING})
        m = model("test", "m", capabilities=caps)
        self.assertTrue(m.supports(caps))

    def test_missing_capability_returns_false(self) -> None:
        m = model("test", "m", capabilities=frozenset({ModelCapability.CHAT}))
        self.assertFalse(m.supports(frozenset({ModelCapability.CODING})))

    def test_reasoning_via_flag(self) -> None:
        m = ModelDefinition(
            provider="test",
            model_name="reasoning-model",
            context_window=8192,
            capabilities=frozenset({ModelCapability.CHAT}),
            supports_reasoning=True,
        )
        self.assertTrue(m.supports(frozenset({ModelCapability.REASONING})))

    def test_structured_output_via_flag(self) -> None:
        m = ModelDefinition(
            provider="test",
            model_name="so-model",
            context_window=8192,
            capabilities=frozenset({ModelCapability.CHAT}),
            supports_structured_output=True,
        )
        self.assertTrue(m.supports(frozenset({ModelCapability.STRUCTURED_OUTPUT})))

    def test_embeddings_via_flag(self) -> None:
        m = ModelDefinition(
            provider="test",
            model_name="emb-model",
            context_window=8192,
            capabilities=frozenset({ModelCapability.CHAT}),
            supports_embeddings=True,
        )
        self.assertTrue(m.supports(frozenset({ModelCapability.EMBEDDINGS})))

    def test_function_calling_in_capabilities(self) -> None:
        m = model(
            "test", "fc-model", capabilities=frozenset({ModelCapability.CHAT, ModelCapability.FUNCTION_CALLING})
        )
        self.assertTrue(m.supports(frozenset({ModelCapability.FUNCTION_CALLING})))

    def test_multiple_flags_combined(self) -> None:
        m = ModelDefinition(
            provider="test",
            model_name="multi-model",
            context_window=8192,
            capabilities=frozenset({ModelCapability.CHAT, ModelCapability.CODING}),
            supports_reasoning=True,
            supports_structured_output=True,
        )
        self.assertTrue(m.supports(frozenset({ModelCapability.REASONING, ModelCapability.STRUCTURED_OUTPUT, ModelCapability.CHAT})))


# ---------------------------------------------------------------------------
# Routing edge cases  (allow_fallback=False, ProviderTimeoutError)
# ---------------------------------------------------------------------------


class RouterEdgeCaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        shutdown_logging()

    async def test_allow_fallback_false_raises_on_unavailable_provider(self) -> None:
        router = ModelRouter()
        provider = MockProvider(available=False)
        router.register_provider(provider)
        router.register_model(model("mock", "only-model"))
        with self.assertRaises(ProviderUnavailableError):
            await router.generate(request(allow_fallback=False))

    async def test_provider_timeout_triggers_fallback(self) -> None:
        router = ModelRouter()

        class TimeoutProvider:
            name = "timeout"

            async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse:
                raise ProviderTimeoutError("simulated timeout")

            async def health_check(self) -> ProviderHealth:
                return ProviderHealth(provider=self.name, available=True)

        fallback = MockProvider(response_content="fallback ok")
        fallback.name = "fallback"

        router.register_provider(TimeoutProvider())
        router.register_provider(fallback)
        router.register_model(model("timeout", "primary", priority=1))
        router.register_model(model("fallback", "backup", priority=2))

        response = await router.generate(request())
        self.assertEqual(response.content, "fallback ok")
        self.assertEqual(response.provider, "fallback")

    async def test_provider_timeout_without_fallback_raises_error(self) -> None:
        router = ModelRouter()

        class TimeoutProvider:
            name = "timeout"

            async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse:
                raise ProviderTimeoutError("simulated timeout")

            async def health_check(self) -> ProviderHealth:
                return ProviderHealth(provider=self.name, available=True)

        router.register_provider(TimeoutProvider())
        router.register_model(model("timeout", "primary"))

        with self.assertRaises(ProviderUnavailableError):
            await router.generate(request(allow_fallback=False))


# ---------------------------------------------------------------------------
# Optional existing behaviors  (stream, structured_output, from_settings, latency)
# ---------------------------------------------------------------------------


class RouterOptionalBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        shutdown_logging()

    async def test_latency_propagation(self) -> None:
        router = ModelRouter()
        provider = MockProvider(response_content="latency-test")
        router.register_provider(provider)
        router.register_model(model("mock", "latency-model"))
        response = await router.generate(request())
        self.assertGreater(response.latency_ms, 0)

    async def test_stream_filtering_excludes_non_streaming_models(self) -> None:
        router = ModelRouter()
        provider = MockProvider()
        router.register_provider(provider)
        streaming = ModelDefinition(
            provider="mock",
            model_name="streaming-model",
            context_window=8192,
            supports_streaming=True,
        )
        non_streaming = model("mock", "non-streaming")
        router.register_model(streaming)
        router.register_model(non_streaming)

        response = await router.generate(request(stream=True))
        self.assertEqual(response.model_name, "streaming-model")

    async def test_structured_output_requires_capability(self) -> None:
        router = ModelRouter()
        provider = MockProvider()
        router.register_provider(provider)
        so_model = ModelDefinition(
            provider="mock",
            model_name="so-model",
            context_window=8192,
            capabilities=frozenset({ModelCapability.CHAT, ModelCapability.STRUCTURED_OUTPUT}),
        )
        chat_only = model("mock", "chat-only")
        router.register_model(so_model)
        router.register_model(chat_only)

        response = await router.generate(request(structured_output=True))
        self.assertEqual(response.model_name, "so-model")

    async def test_from_settings_with_all_providers_disabled(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.ollama.enabled = False
        settings.openrouter.enabled = False

        router = ModelRouter.from_settings(settings)
        self.assertEqual(len(router.providers.all()), 0)

    async def test_from_settings_with_ollama_enabled(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.openrouter.enabled = False

        router = ModelRouter.from_settings(settings)
        providers = router.providers.all()
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "ollama")

    async def test_from_settings_with_openrouter_enabled(self) -> None:
        settings = Settings(config_dir="missing-config")
        settings.ollama.enabled = False
        settings.openrouter.enabled = True
        settings.openrouter.api_key = SecretStr("test-api-key")

        router = ModelRouter.from_settings(settings)
        providers = router.providers.all()
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "openrouter")
