# Configuration

AICOS configuration is validated by `backend.aicos.settings.Settings`. Values
are merged in this order, with earlier sources taking precedence:

1. Explicit `Settings(...)` values
2. Environment variables
3. `.env` in the working directory
4. `config/base.yaml`
5. The active profile file: `config/development.yaml` or `config/production.yaml`

Select a profile with `AICOS_PROFILE=development` or
`AICOS_PROFILE=production`. Copy `.env.example` to `.env` for local overrides;
never commit `.env` files containing secrets.

Nested environment values use double underscores. For example:

```bash
AICOS_LOGGING__LEVEL=DEBUG
AICOS_SQLITE__PATH=data/aicos.local.db
AICOS_OPENROUTER__ENABLED=true
AICOS_OPENROUTER__API_KEY=your-secret
```

All LLM model identifiers are optional configuration values. Components must
obtain model access through the Model Router and must not hardcode models or
provider credentials.
