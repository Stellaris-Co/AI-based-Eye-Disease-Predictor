"""
Structured logging configuration.

Replaces ad-hoc print() statements with structured, JSON-renderable log events that
carry consistent fields (timestamp, level, logger name, plus whatever context each
call site attaches). This is what makes "what happened in production at 3am" an
actually answerable question instead of a grep through unstructured text.

Falls back to Python's standard logging (still readable, just not JSON) if
structlog isn't installed, so importing this module is always safe even before
`pip install structlog` has been run.
"""
from __future__ import annotations

import logging
import sys

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


def configure_logging(json_output: bool = True) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    if not STRUCTLOG_AVAILABLE:
        logging.getLogger(__name__).warning(
            "structlog is not installed — falling back to standard logging "
            "without structured fields. Install structlog for production use."
        )
        return

    renderer = structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "ophthalmoai"):
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return _StdlibLoggerAdapter(logging.getLogger(name))


class _StdlibLoggerAdapter:

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _fmt(self, event: str, **kwargs) -> str:
        if not kwargs:
            return event
        context = " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{event} | {context}"

    def info(self, event: str, **kwargs):
        self._logger.info(self._fmt(event, **kwargs))

    def warning(self, event: str, **kwargs):
        self._logger.warning(self._fmt(event, **kwargs))

    def error(self, event: str, **kwargs):
        self._logger.error(self._fmt(event, **kwargs))

    def exception(self, event: str, **kwargs):
        self._logger.exception(self._fmt(event, **kwargs))
