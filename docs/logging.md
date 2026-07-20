# Logging

AICOS uses Python's standard `logging` module and configures it through
`logging.config.dictConfig`. Logging is configured entirely from the typed
`logging` section of the Settings system.

## Use

```python
from backend.aicos.logging import get_logger, logging_context

logger = get_logger("agents.worker")
with logging_context(correlation_id="request-123", execution_duration_ms=18.4):
    logger.info("work completed")
```

The available subsystem logger roots are `supervisor`, `agents`, `event_bus`,
`database`, `mcp`, `llm`, `api`, and `system`. Dotted child names, such as
`agents.worker`, inherit the same configuration.

## Output and configuration

Console and rotating file handlers can be enabled independently. JSON output
is the default and includes timestamp, level, logger, module, message, and any
bound correlation ID, execution duration, or exception trace. Text output is
available for development.

```yaml
logging:
  level: INFO
  format: json
  console_enabled: true
  file_enabled: true
  file_path: data/logs/aicos.log
  max_bytes: 10485760
  backup_count: 5
```

Use the existing configuration override mechanism for deployment-specific
values, for example `AICOS_LOGGING__LEVEL=DEBUG`. Never place secrets or
sensitive prompt content in log messages.
