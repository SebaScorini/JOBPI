from concurrent.futures import Executor, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
import logging
from typing import Any, Callable

import dspy
from fastapi import HTTPException, status

from app.core.circuit_breaker import AICircuitBreaker
from app.core.config import get_settings


AI_TIMEOUT_DETAIL = "AI request timed out. Please try again."
AI_PROVIDER_UNAVAILABLE_DETAIL = "AI provider is temporarily unavailable. Please try again in a moment."
MAX_LM_TOKENS = 4000
DEFAULT_SHARED_LM_MAX_TOKENS = 400
_ai_circuit_breaker = AICircuitBreaker()


def clamp_lm_max_tokens(value: int) -> int:
    return max(50, min(MAX_LM_TOKENS, value))


@contextmanager
def dspy_lm_override(*, max_tokens: int) -> Any:
    settings = get_settings()
    lm = dspy.LM(
        model=settings.dspy_model,
        api_key=settings.openrouter_api_key,
        api_base=settings.openrouter_base_url,
        temperature=min(max(settings.dspy_temperature, 0.2), 0.4),
        max_tokens=clamp_lm_max_tokens(max_tokens),
        extra_body={"reasoning": {"enabled": False}},
    )
    with dspy.context(lm=lm):
        yield


def run_ai_call_with_timeout(
    *,
    executor: Executor,
    timeout_seconds: int,
    operation: str,
    logger: logging.Logger,
    callable_: Callable[..., Any],
    lm_max_tokens: int | None = None,
    **kwargs,
) -> Any:
    future = executor.submit(callable_, **kwargs)
    try:
        result = future.result(timeout=timeout_seconds)
        if lm_max_tokens is not None and _is_likely_truncated_result(result):
            logger.warning(
                "ai_output_truncated operation=%s max_tokens=%s",
                operation,
                clamp_lm_max_tokens(lm_max_tokens),
            )
        return result
    except FuturesTimeoutError as exc:
        logger.warning("ai_timeout operation=%s timeout_seconds=%s", operation, timeout_seconds)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=AI_TIMEOUT_DETAIL,
        ) from exc


def run_ai_call_with_circuit_breaker(
    *,
    executor: Executor,
    timeout_seconds: int,
    operation: str,
    logger: logging.Logger,
    callable_: Callable[..., Any],
    lm_max_tokens: int | None = None,
    **kwargs,
) -> Any:
    return _ai_circuit_breaker.call(
        operation=operation,
        logger=logger,
        callable_=lambda: run_ai_call_with_timeout(
            executor=executor,
            timeout_seconds=timeout_seconds,
            operation=operation,
            logger=logger,
            callable_=callable_,
            lm_max_tokens=lm_max_tokens,
            **kwargs,
        ),
        retryable=_is_retryable_ai_exception,
        token_budget=clamp_lm_max_tokens(lm_max_tokens) if lm_max_tokens is not None else None,
    )


def build_ai_failure_http_exception(
    *,
    exc: Exception,
    logger: logging.Logger,
    operation: str,
    default_detail: str,
) -> HTTPException:
    logger.exception("ai_call_failed operation=%s", operation, exc_info=exc)
    if _looks_like_provider_unavailable(exc):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_PROVIDER_UNAVAILABLE_DETAIL,
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=default_detail,
    )


def _looks_like_provider_unavailable(exc: BaseException | None) -> bool:
    current = exc
    while current is not None:
        message = f"{type(current).__name__}: {current}".lower()
        if any(
            token in message
            for token in (
                "openrouterexception",
                "connection refused",
                "failed to connect",
                "connection error",
                "winerror 10061",
                "temporarily unavailable",
                "service unavailable",
            )
        ):
            return True
        current = current.__cause__
    return False


def _is_retryable_ai_exception(exc: Exception) -> bool:
    if isinstance(exc, HTTPException):
        return exc.status_code in {
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_504_GATEWAY_TIMEOUT,
        }
    return _looks_like_provider_unavailable(exc)


def _is_likely_truncated_result(value: object) -> bool:
    return _contains_truncation_signal(value, depth=0, seen=set())


def _contains_truncation_signal(value: object, *, depth: int, seen: set[int]) -> bool:
    if depth > 5:
        return False

    value_id = id(value)
    if value_id in seen:
        return False
    seen.add(value_id)

    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"finish_reason", "stop_reason"} and _is_truncation_reason(item):
                return True
            if key_text in {"warning", "warnings", "message", "detail"} and _has_truncation_text(item):
                return True
            if _contains_truncation_signal(item, depth=depth + 1, seen=seen):
                return True
        return False

    if isinstance(value, (list, tuple, set)):
        return any(_contains_truncation_signal(item, depth=depth + 1, seen=seen) for item in value)

    if isinstance(value, str):
        return _has_truncation_text(value)

    if hasattr(value, "__dict__"):
        return _contains_truncation_signal(vars(value), depth=depth + 1, seen=seen)

    return False


def _is_truncation_reason(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return value.lower() in {"length", "max_tokens", "max_output_tokens", "token_limit"}


def _has_truncation_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return "truncat" in lowered or "max token" in lowered or "max_tokens" in lowered
