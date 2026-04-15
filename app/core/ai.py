from concurrent.futures import Executor, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
import logging
import time
from typing import Any, Callable

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status

from app.core.circuit_breaker import AICircuitBreaker
from app.core.config import get_settings, normalize_dspy_model
from app.services.job_preprocessing import estimate_payload_tokens


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
        model=normalize_dspy_model(settings.dspy_model, settings.openrouter_base_url),
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
    retry_count: int = 0,
    **kwargs,
) -> Any:
    estimated_input_chars = _estimate_payload_chars(kwargs)
    estimated_input_tokens = estimate_payload_tokens(kwargs)
    effective_max_tokens = clamp_lm_max_tokens(lm_max_tokens) if lm_max_tokens is not None else None
    start = time.perf_counter()
    logger.info(
        "ai_call_start operation=%s retry_count=%s max_tokens=%s estimated_input_chars=%s estimated_input_tokens=%s",
        operation,
        retry_count,
        effective_max_tokens,
        estimated_input_chars,
        estimated_input_tokens,
    )
    future = executor.submit(callable_, **kwargs)
    try:
        result = future.result(timeout=timeout_seconds)
        latency_ms = (time.perf_counter() - start) * 1000
        usage = _extract_usage_metrics(result)
        logger.info(
            "ai_call_complete operation=%s retry_count=%s max_tokens=%s latency_ms=%.1f estimated_input_chars=%s estimated_input_tokens=%s provider_input_tokens=%s provider_output_tokens=%s provider_total_tokens=%s",
            operation,
            retry_count,
            effective_max_tokens,
            latency_ms,
            estimated_input_chars,
            estimated_input_tokens,
            usage["input_tokens"],
            usage["output_tokens"],
            usage["total_tokens"],
        )
        if lm_max_tokens is not None and _is_likely_truncated_result(result):
            logger.warning(
                "ai_output_truncated operation=%s retry_count=%s max_tokens=%s latency_ms=%.1f",
                operation,
                retry_count,
                effective_max_tokens,
                latency_ms,
            )
        return result
    except FuturesTimeoutError as exc:
        future.cancel()
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "ai_timeout operation=%s retry_count=%s timeout_seconds=%s latency_ms=%.1f max_tokens=%s estimated_input_chars=%s estimated_input_tokens=%s",
            operation,
            retry_count,
            timeout_seconds,
            latency_ms,
            effective_max_tokens,
            estimated_input_chars,
            estimated_input_tokens,
        )
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
    retry_lm_max_tokens: int | None = None,
    attempt_kwargs_builder: Callable[[int], dict[str, Any]] | None = None,
    **kwargs,
) -> Any:
    def _token_budget_for_attempt(attempt: int) -> int | None:
        if lm_max_tokens is None:
            return None
        if attempt > 0 and retry_lm_max_tokens is not None:
            return clamp_lm_max_tokens(retry_lm_max_tokens)
        return clamp_lm_max_tokens(lm_max_tokens)

    return _ai_circuit_breaker.call(
        operation=operation,
        logger=logger,
        callable_=lambda: run_ai_call_with_timeout(
            executor=executor,
            timeout_seconds=timeout_seconds,
            operation=operation,
            logger=logger,
            callable_=callable_,
            lm_max_tokens=_token_budget_for_attempt(0),
            retry_count=0,
            **(attempt_kwargs_builder(0) if attempt_kwargs_builder is not None else kwargs),
        ),
        callable_with_attempt=lambda attempt: run_ai_call_with_timeout(
            executor=executor,
            timeout_seconds=timeout_seconds,
            operation=operation,
            logger=logger,
            callable_=callable_,
            lm_max_tokens=_token_budget_for_attempt(attempt),
            retry_count=attempt,
            **(attempt_kwargs_builder(attempt) if attempt_kwargs_builder is not None else kwargs),
        ),
        retryable=_is_retryable_ai_exception,
        token_budget=clamp_lm_max_tokens(lm_max_tokens) if lm_max_tokens is not None else None,
        token_budget_for_attempt=_token_budget_for_attempt,
    )


def build_ai_failure_http_exception(
    *,
    exc: Exception,
    logger: logging.Logger,
    operation: str,
    default_detail: str,
) -> HTTPException:
    logger.exception("ai_call_failed operation=%s", operation, exc_info=exc)
    if looks_like_ai_auth_error(exc):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis is not configured.",
        )
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
    if looks_like_ai_auth_error(exc):
        return False
    if isinstance(exc, HTTPException):
        return exc.status_code in {
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_504_GATEWAY_TIMEOUT,
        }
    return _looks_like_provider_unavailable(exc)


def looks_like_ai_auth_error(exc: BaseException | None) -> bool:
    current = exc
    while current is not None:
        message = f"{type(current).__name__}: {current}".lower()
        if any(
            token in message
            for token in (
                "authenticationerror",
                "unauthorized",
                "401",
                "invalid api key",
                "api key",
                "user not found",
                "incorrect api key",
                "auth",
            )
        ):
            return True
        current = current.__cause__
    return False


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


def _estimate_payload_chars(payload: dict[str, object]) -> int:
    return len(_stringify_payload(payload))


def _stringify_payload(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_stringify_payload(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_stringify_payload(item) for item in value)
    return str(value)


def _extract_usage_metrics(value: object) -> dict[str, int | None]:
    usage = _find_usage_payload(value, depth=0, seen=set())
    if not usage:
        return {"input_tokens": None, "output_tokens": None, "total_tokens": None}

    input_tokens = _coerce_usage_int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("promptTokens")
        or usage.get("cache_read_input_tokens")
    )
    output_tokens = _coerce_usage_int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("completionTokens")
    )
    total_tokens = _coerce_usage_int(usage.get("total_tokens") or usage.get("totalTokens"))

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _find_usage_payload(value: object, *, depth: int, seen: set[int]) -> dict[str, object] | None:
    if depth > 5:
        return None

    value_id = id(value)
    if value_id in seen:
        return None
    seen.add(value_id)

    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == "usage" and isinstance(item, dict):
                return item
            nested = _find_usage_payload(item, depth=depth + 1, seen=seen)
            if nested is not None:
                return nested
        return None

    if isinstance(value, (list, tuple, set)):
        for item in value:
            nested = _find_usage_payload(item, depth=depth + 1, seen=seen)
            if nested is not None:
                return nested
        return None

    if hasattr(value, "__dict__"):
        return _find_usage_payload(vars(value), depth=depth + 1, seen=seen)

    return None


def _coerce_usage_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
