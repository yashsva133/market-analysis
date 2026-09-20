"""Structured JSON logging with correlation IDs."""
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variables for tracing requests and pipelines
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)
source_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("source_id", default=None)
company_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("company_id", default=None)
event_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("event_id", default=None)


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Add correlation context if set
        corr_id = correlation_id_var.get()
        if corr_id:
            log_entry["correlation_id"] = corr_id
        src_id = source_id_var.get()
        if src_id:
            log_entry["source_id"] = src_id
        cmp_id = company_id_var.get()
        if cmp_id:
            log_entry["company_id"] = cmp_id
        ev_id = event_id_var.get()
        if ev_id:
            log_entry["event_id"] = ev_id

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Attach extra dictionary data if passed
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["data"] = record.extra_data

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Get a structured JSON logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
