"""Structured logging setup (JSON in production, readable lines in development)."""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str, *, json_output: bool) -> None:
    """Configure structlog and the standard library logger once per process."""
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )
    logging.basicConfig(level=level.upper(), stream=sys.stdout, format="%(message)s")


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structured logger."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
