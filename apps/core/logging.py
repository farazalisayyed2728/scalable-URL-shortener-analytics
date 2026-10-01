import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable to hold request_id safely across threads and async tasks
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)

# Standard LogRecord attributes to ignore when extracting custom extra metadata
STANDARD_LOG_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}

# Sensitive keys to redact automatically from log extra fields
SENSITIVE_KEYS = {"password", "token", "access", "refresh", "authorization", "secret"}


class RequestIDFilter(logging.Filter):
    """
    Logging filter that injects the current request_id from contextvars
    into every log record automatically.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "no_request_id"
        return True


class JSONLogFormatter(logging.Formatter):
    """
    Formats log records into structured, single-line JSON objects.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "no_request_id"),
        }

        # Include custom extra metadata passed via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_RECORD_ATTRS and not key.startswith("_"):
                if key.lower() in SENSITIVE_KEYS:
                    log_payload[key] = "[REDACTED]"
                else:
                    log_payload[key] = value

        # Include exception stack traces if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)