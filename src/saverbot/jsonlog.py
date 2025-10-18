"""Structured JSON logging for saverbot."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from saverbot.config import config


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a single-line JSON string."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logger(name: str) -> logging.Logger:
    """Set up a JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)

    # Remove any existing handlers
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger
