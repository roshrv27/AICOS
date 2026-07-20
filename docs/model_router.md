# Model Router

`backend.aicos.llm` is the only supported path from AICOS components to a
language-model provider. Consumers depend on `ModelRouter` (or the
`ModelRouterPort`) and never import an Ollama, OpenRouter, or future provider
SDK directly.

## Architecture

- `ModelRouter` selects and executes a route.
- `ModelRegistry` contains typed, enabled model metadata.
- `ProviderRegistry` contains provider-neutral adapters.
- `HealthMonitor` records availability, latency, failures, and successful
  requests; unhealthy providers are deprioritized during routing.
- `providers/` contains optional HTTP adapters for Ollama and OpenRouter plus
  `MockProvider` for deterministic tests.

The abstraction is async and provider-neutral. Adding another provider means
implementing the `LLMProvider` contract and registering it; callers do not
change.

## Register providers and models

```python
from backend.aicos.llm import ModelCapability, ModelDefinition, ModelRouter
from backend.aicos.llm.providers import MockProvider

router = ModelRouter()
router.register_provider(MockProvider())
router.register_model(ModelDefinition(
    provider="mock",
    model_name="configured-at-deployment",
    capabilities=frozenset({ModelCapability.CHAT}),
    context_window=8192,
))
```

Model names are deployment metadata, not routing logic. The registry stores
provider, model name, capabilities, context window, streaming/reasoning/
structured-output/embedding support, priority, enabled state, and local status.

## Route a request

```python
from backend.aicos.llm import ChatMessage, ModelRequest, RoutingStrategy

response = await router.generate(ModelRequest(
    messages=(ChatMessage(role="user", content="Hello"),),
    strategy=RoutingStrategy.LOCAL_FIRST,
))
```

Routing supports an explicit preferred model, local-first selection, provider
preferences, capability matching, and ordered fallback. Required capabilities
rather than model names determine eligibility. Failed or unhealthy providers
are avoided when another eligible route exists.

## Health, responses, and DI

Call `await router.check_health()` to refresh all registered provider states.
Responses normalize text, optional structured output, usage metadata, latency,
and future-ready stream chunks.

At the composition root, register the router as a DI singleton from validated
Settings:

```python
from backend.aicos.llm import register_model_router

register_model_router(container, settings)
```

`ModelRouter.from_settings()` configures optional Ollama/OpenRouter adapters
without hardcoding a model name or API key. Register model definitions from
validated deployment configuration before serving requests.
