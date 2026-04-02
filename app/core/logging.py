from __future__ import annotations

import contextvars
import logging
from typing import Any

from pythonjsonlogger.json import JsonFormatter


TRACE_ID_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
REQUEST_PATH_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_path", default=None)
REQUEST_METHOD_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_method", default=None)
USER_ID_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = getattr(record, "trace_id", None) or TRACE_ID_CONTEXT.get()
        record.path = getattr(record, "path", None) or REQUEST_PATH_CONTEXT.get()
        record.method = getattr(record, "method", None) or REQUEST_METHOD_CONTEXT.get()
        record.user_id = getattr(record, "user_id", None) or USER_ID_CONTEXT.get()
        record.status_code = getattr(record, "status_code", None)
        record.duration_ms = getattr(record, "duration_ms", None)
        return True


def bind_request_context(trace_id: str, path: str, method: str) -> dict[str, contextvars.Token[Any]]:
    return {
        "trace_id": TRACE_ID_CONTEXT.set(trace_id),
        "path": REQUEST_PATH_CONTEXT.set(path),
        "method": REQUEST_METHOD_CONTEXT.set(method),
    }


def bind_user_context(user_id: str | int | None) -> contextvars.Token[Any]:
    value = None if user_id is None else str(user_id)
    return USER_ID_CONTEXT.set(value)


def reset_context(tokens: dict[str, contextvars.Token[Any]]) -> None:
    TRACE_ID_CONTEXT.reset(tokens["trace_id"])
    REQUEST_PATH_CONTEXT.reset(tokens["path"])
    REQUEST_METHOD_CONTEXT.reset(tokens["method"])


def reset_user_context(token: contextvars.Token[Any]) -> None:
    USER_ID_CONTEXT.reset(token)


def get_request_context() -> dict[str, str | None]:
    return {
        "trace_id": TRACE_ID_CONTEXT.get(),
        "path": REQUEST_PATH_CONTEXT.get(),
        "method": REQUEST_METHOD_CONTEXT.get(),
        "user_id": USER_ID_CONTEXT.get(),
    }


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(user_id)s %(method)s %(path)s %(status_code)s %(duration_ms)s"
        )
    )
    handler.addFilter(RequestContextFilter())
    return handler


def _configure_named_logger(name: str, handler: logging.Handler) -> None:
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.propagate = False


def setup_logging() -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_jobpi_json_logging", False):
        return

    handler = _build_handler()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    root_logger._jobpi_json_logging = True  # type: ignore[attr-defined]

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        _configure_named_logger(logger_name, handler)
