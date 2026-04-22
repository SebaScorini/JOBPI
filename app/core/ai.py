from concurrent.futures import Executor, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
import json
import logging
import re
import time
from typing import Any, Callable, TypeVar

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from dspy.utils.exceptions import AdapterParseError
from json_repair import loads as repair_json_loads

from app.core.circuit_breaker import AICircuitBreaker
from app.core.config import build_dspy_lm_kwargs, get_settings, normalize_dspy_model
from app.models.ai_schemas import AIOutputValidationFailure, AIParsedResult, AIValidationIssue
from app.services.job_preprocessing import estimate_payload_tokens


AI_TIMEOUT_DETAIL = "AI request timed out. Please try again."
AI_PROVIDER_UNAVAILABLE_DETAIL = "AI provider is temporarily unavailable. Please try again in a moment."
MAX_LM_TOKENS = 4000
DEFAULT_SHARED_LM_MAX_TOKENS = 400
_ai_circuit_breaker = AICircuitBreaker()
T = TypeVar("T", bound=BaseModel)


def clamp_lm_max_tokens(value: int) -> int:
    return max(50, min(MAX_LM_TOKENS, value))


@contextmanager
def dspy_lm_override(*, max_tokens: int, model: str | None = None) -> Any:
    settings = get_settings()
    resolved_model = normalize_dspy_model(
        model or settings.dspy_model,
        settings.openrouter_base_url,
    )
    lm = dspy.LM(
        model=resolved_model,
        api_key=settings.openrouter_api_key,
        api_base=settings.openrouter_base_url,
        temperature=min(max(settings.dspy_temperature, 0.25), 0.55),
        max_tokens=clamp_lm_max_tokens(max_tokens),
        **build_dspy_lm_kwargs(api_base=settings.openrouter_base_url),
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
    effective_model = (
        kwargs.get("model")
        if isinstance(kwargs.get("model"), str) and kwargs.get("model")
        else get_settings().dspy_model
    )
    start = time.perf_counter()
    logger.info(
        "ai_call_start operation=%s retry_count=%s model=%s max_tokens=%s estimated_input_chars=%s estimated_input_tokens=%s",
        operation,
        retry_count,
        effective_model,
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
            "ai_call_complete operation=%s retry_count=%s model=%s max_tokens=%s latency_ms=%.1f estimated_input_chars=%s estimated_input_tokens=%s provider_input_tokens=%s provider_output_tokens=%s provider_total_tokens=%s",
            operation,
            retry_count,
            effective_model,
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
                "ai_output_truncated operation=%s retry_count=%s model=%s max_tokens=%s latency_ms=%.1f",
                operation,
                retry_count,
                effective_model,
                effective_max_tokens,
                latency_ms,
            )
        return result
    except AdapterParseError as exc:
        future.cancel()
        latency_ms = (time.perf_counter() - start) * 1000
        recovered = _recover_adapter_parse_error(exc)
        if recovered is not None:
            logger.warning(
                "ai_output_repaired operation=%s retry_count=%s model=%s max_tokens=%s latency_ms=%.1f",
                operation,
                retry_count,
                effective_model,
                effective_max_tokens,
                latency_ms,
            )
            return recovered
        logger.warning(
            "ai_parse_error operation=%s retry_count=%s model=%s max_tokens=%s latency_ms=%.1f",
            operation,
            retry_count,
            effective_model,
            effective_max_tokens,
            latency_ms,
        )
        raise
    except FuturesTimeoutError as exc:
        future.cancel()
        latency_ms = (time.perf_counter() - start) * 1000
        logger.warning(
            "ai_timeout operation=%s retry_count=%s model=%s timeout_seconds=%s latency_ms=%.1f max_tokens=%s estimated_input_chars=%s estimated_input_tokens=%s",
            operation,
            retry_count,
            effective_model,
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
    attempt_kwargs_builder_with_exception: Callable[[int, Exception | None], dict[str, Any]] | None = None,
    model_for_attempt: Callable[[int, Exception | None], str | None] | None = None,
    **kwargs,
) -> Any:
    def _token_budget_for_attempt(attempt: int) -> int | None:
        if lm_max_tokens is None:
            return None
        if attempt > 0 and retry_lm_max_tokens is not None:
            return clamp_lm_max_tokens(retry_lm_max_tokens)
        return clamp_lm_max_tokens(lm_max_tokens)

    def _model_for_attempt(attempt: int, previous_exception: Exception | None) -> str | None:
        if model_for_attempt is None:
            return None
        return model_for_attempt(attempt, previous_exception)

    def _kwargs_for_attempt(attempt: int, previous_exception: Exception | None) -> dict[str, Any]:
        if attempt_kwargs_builder_with_exception is not None:
            return attempt_kwargs_builder_with_exception(attempt, previous_exception)
        if attempt_kwargs_builder is not None:
            return attempt_kwargs_builder(attempt)
        return kwargs

    def _attempt_context(attempt: int, previous_exception: Exception | None) -> dict[str, Any]:
        attempt_model = _kwargs_for_attempt(attempt, previous_exception).get("model")
        return {"model": attempt_model if isinstance(attempt_model, str) else _model_for_attempt(attempt, previous_exception)}

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
            **_kwargs_for_attempt(0, None),
        ),
        callable_with_attempt=lambda attempt: run_ai_call_with_timeout(
            executor=executor,
            timeout_seconds=timeout_seconds,
            operation=operation,
            logger=logger,
            callable_=callable_,
            lm_max_tokens=_token_budget_for_attempt(attempt),
            retry_count=attempt,
            **_kwargs_for_attempt(attempt, None),
        ),
        callable_with_attempt_and_exception=lambda attempt, previous_exception: run_ai_call_with_timeout(
            executor=executor,
            timeout_seconds=timeout_seconds,
            operation=operation,
            logger=logger,
            callable_=callable_,
            lm_max_tokens=_token_budget_for_attempt(attempt),
            retry_count=attempt,
            **_kwargs_for_attempt(attempt, previous_exception),
        ),
        retryable=_is_retryable_ai_exception,
        describe_exception=_describe_ai_exception,
        token_budget=clamp_lm_max_tokens(lm_max_tokens) if lm_max_tokens is not None else None,
        token_budget_for_attempt=_token_budget_for_attempt,
        attempt_context_builder=_attempt_context,
    )


def build_ai_failure_http_exception(
    *,
    exc: Exception,
    logger: logging.Logger,
    operation: str,
    default_detail: str,
) -> HTTPException:
    if isinstance(exc, AIOutputValidationFailure):
        logger.warning(
            "ai_call_failed operation=%s reason=%s schema_name=%s issue_count=%s issue_fields=%s raw_output_preview=%s",
            operation,
            exc.failure_category,
            exc.schema_name,
            len(exc.issues),
            ",".join(issue.field_path for issue in exc.issues) or "<none>",
            _safe_snapshot_preview(exc.raw_output),
        )
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=default_detail,
        )
    if looks_like_ai_auth_error(exc):
        logger.warning("ai_call_failed operation=%s reason=auth", operation)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis is not configured.",
        )
    if _looks_like_provider_unavailable(exc):
        logger.warning("ai_call_failed operation=%s reason=provider_unavailable", operation)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AI_PROVIDER_UNAVAILABLE_DETAIL,
        )
    logger.exception("ai_call_failed operation=%s", operation, exc_info=exc)
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


def _describe_ai_exception(exc: Exception) -> str:
    if isinstance(exc, AIOutputValidationFailure):
        return exc.failure_category
    if looks_like_ai_auth_error(exc):
        return "auth"
    if _looks_like_provider_unavailable(exc):
        return "provider_unavailable"
    if isinstance(exc, HTTPException):
        if exc.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            return "timeout"
        return f"http_{exc.status_code}"
    return type(exc).__name__


def use_provider_fallback_model(attempt: int, previous_exception: Exception | None) -> str | None:
    settings = get_settings()
    if attempt > 0 and previous_exception is not None:
        reason = _describe_ai_exception(previous_exception)
        if reason in {"provider_unavailable", "parse_failed", "schema_validation_failed", "AdapterParseError"}:
            return settings.dspy_provider_fallback_model
    return settings.dspy_model


def looks_like_ai_auth_error(exc: BaseException | None) -> bool:
    current = exc
    while current is not None:
        message = f"{type(current).__name__}: {current}".lower()
        if any(
            token in message
            for token in (
                "authenticationerror",
                "unauthorized",
                "invalid api key",
                "incorrect api key",
                "no api key provided",
                "api key not found",
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


def run_structured_ai_call(
    *,
    schema: type[T],
    executor: Executor,
    timeout_seconds: int,
    operation: str,
    logger: logging.Logger,
    callable_: Callable[..., Any],
    lm_max_tokens: int | None = None,
    retry_lm_max_tokens: int | None = None,
    attempt_kwargs_builder: Callable[[int], dict[str, Any]] | None = None,
    **kwargs,
) -> AIParsedResult[T]:
    attempt_kwargs_builder_with_exception = kwargs.pop("attempt_kwargs_builder_with_exception", None)
    max_structured_attempts = 2 if retry_lm_max_tokens is not None else 1
    previous_validation_exception: AIOutputValidationFailure | None = None

    for structured_attempt in range(max_structured_attempts):
        def _structured_attempt_kwargs(attempt: int, previous_exception: Exception | None) -> dict[str, Any]:
            effective_attempt = attempt + structured_attempt
            effective_exception = previous_exception or previous_validation_exception
            if attempt_kwargs_builder_with_exception is not None:
                return attempt_kwargs_builder_with_exception(effective_attempt, effective_exception)
            if attempt_kwargs_builder is not None:
                return attempt_kwargs_builder(effective_attempt)
            return kwargs

        result = run_ai_call_with_circuit_breaker(
            executor=executor,
            timeout_seconds=timeout_seconds,
            operation=operation,
            logger=logger,
            callable_=callable_,
            lm_max_tokens=lm_max_tokens,
            retry_lm_max_tokens=retry_lm_max_tokens,
            attempt_kwargs_builder_with_exception=_structured_attempt_kwargs,
            **kwargs,
        )
        try:
            return validate_ai_output(
                result=result,
                schema=schema,
                operation=operation,
                logger=logger,
            )
        except AIOutputValidationFailure as exc:
            previous_validation_exception = exc
            if structured_attempt >= max_structured_attempts - 1:
                raise

            current_budget = clamp_lm_max_tokens(lm_max_tokens) if lm_max_tokens is not None else None
            next_budget = clamp_lm_max_tokens(retry_lm_max_tokens) if retry_lm_max_tokens is not None else current_budget
            current_model = _structured_attempt_kwargs(0, None).get("model")
            next_model = _structured_attempt_kwargs(0, exc).get("model")
            logger.warning(
                "ai_retry operation=%s retry=%s delay_ms=0 token_budget=%s next_token_budget=%s model=%s next_model=%s reason=%s",
                operation,
                structured_attempt + 1,
                current_budget,
                next_budget,
                current_model,
                next_model,
                exc.failure_category,
            )

    raise RuntimeError("structured_ai_call_exhausted")


def validate_ai_output(
    *,
    result: object,
    schema: type[T],
    operation: str,
    logger: logging.Logger,
) -> AIParsedResult[T]:
    try:
        raw_output = _serialize_ai_output(result)
        raw_output = _normalize_ai_output_payload(raw_output)
    except Exception as exc:  # pragma: no cover - defensive serialization guard
        logger.warning(
            "ai_schema_validation operation=%s schema_name=%s parse_success=false schema_validation_success=false failure_category=parse_failed truncation_detected=%s",
            operation,
            schema.__name__,
            _is_likely_truncated_result(result),
        )
        raise AIOutputValidationFailure(
            operation=operation,
            schema_name=schema.__name__,
            failure_category="parse_failed",
            raw_output={"serialization_error": f"{type(exc).__name__}: {exc}"},
        ) from exc

    try:
        payload = schema.model_validate(raw_output)
    except ValidationError as exc:
        issues = [
            AIValidationIssue(
                field_path=".".join(str(part) for part in error.get("loc", ())) or "<root>",
                message=error.get("msg", "validation error"),
                input_value=_stringify_issue_value(error.get("input")),
            )
            for error in exc.errors()
        ]
        logger.warning(
            "ai_schema_validation operation=%s schema_name=%s parse_success=true schema_validation_success=false failure_category=schema_validation_failed issue_count=%s issue_fields=%s truncation_detected=%s raw_output_preview=%s",
            operation,
            schema.__name__,
            len(issues),
            ",".join(issue.field_path for issue in issues) or "<none>",
            _is_likely_truncated_result(raw_output),
            _safe_snapshot_preview(raw_output),
        )
        raise AIOutputValidationFailure(
            operation=operation,
            schema_name=schema.__name__,
            failure_category="schema_validation_failed",
            raw_output=raw_output,
            issues=issues,
        ) from exc

    logger.info(
        "ai_schema_validation operation=%s schema_name=%s parse_success=true schema_validation_success=true failure_category=none truncation_detected=%s",
        operation,
        schema.__name__,
        _is_likely_truncated_result(raw_output),
    )
    return AIParsedResult(payload=payload, raw_output=raw_output, schema_name=schema.__name__)


def _normalize_ai_output_payload(value: object) -> object:
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text:
        return value

    candidate = _extract_json_candidate(text)
    if candidate is None:
        return value

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return value


def _normalize_ai_output_for_schema(value: object, *, schema: type[T]) -> object:
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        value = value[0]

    if not isinstance(value, dict):
        return value

    allowed_keys = _schema_input_keys(schema)
    if not allowed_keys:
        return value

    filtered = {key: item for key, item in value.items() if key in allowed_keys}
    return filtered if filtered else value


def _schema_input_keys(schema: type[T]) -> set[str]:
    keys: set[str] = set()
    for name, field in schema.model_fields.items():
        keys.add(name)
        alias = getattr(field, "alias", None)
        if isinstance(alias, str) and alias:
            keys.add(alias)
        validation_alias = getattr(field, "validation_alias", None)
        if isinstance(validation_alias, str) and validation_alias:
            keys.add(validation_alias)
        elif hasattr(validation_alias, "choices"):
            keys.update(str(choice) for choice in validation_alias.choices if isinstance(choice, str) and choice)
    return keys


def _extract_json_candidate(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fence_match:
        fenced = fence_match.group(1).strip()
        if fenced:
            return fenced

    if stripped[0] in "[{" and stripped[-1] in "]}":
        return stripped

    start_candidates = [index for index in (stripped.find("{"), stripped.find("[")) if index >= 0]
    end_candidates = [index for index in (stripped.rfind("}"), stripped.rfind("]")) if index >= 0]
    if start_candidates and end_candidates:
        start = min(start_candidates)
        end = max(end_candidates)
        if end > start:
            return stripped[start : end + 1]

    return None


def _serialize_ai_output(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _serialize_ai_output(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_ai_output(item) for item in value]
    if hasattr(value, "toDict") and callable(getattr(value, "toDict")):
        return _serialize_ai_output(value.toDict())
    if hasattr(value, "items") and callable(getattr(value, "items")):
        try:
            return {str(key): _serialize_ai_output(item) for key, item in value.items()}
        except TypeError:
            pass
    if hasattr(value, "model_dump"):
        return _serialize_ai_output(value.model_dump())
    if hasattr(value, "__dict__"):
        return {str(key): _serialize_ai_output(item) for key, item in vars(value).items() if not str(key).startswith("_")}
    return str(value)


def _safe_snapshot_preview(value: object, *, limit: int = 1600) -> str:
    try:
        serialized = json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        serialized = json.dumps(_serialize_ai_output(value), ensure_ascii=True, sort_keys=True)
    if len(serialized) <= limit:
        return serialized
    return serialized[:limit].rstrip() + "...<truncated>"


_DSPY_SECTION_RE = re.compile(r"\[\[\s*##\s*(?P<field>[^#]+?)\s*##\s*\]\]", re.IGNORECASE)
_ADAPTER_LM_RESPONSE_RE = re.compile(
    r"LM Response:\s*(?P<response>.*?)(?:\n\nExpected to find output fields:|\n\nActual output fields parsed from the LM response:|\Z)",
    re.DOTALL,
)


def _recover_adapter_parse_error(exc: AdapterParseError) -> object | None:
    raw_response = _extract_lm_response_text(str(exc))
    if not raw_response:
        return None

    for parser in (_parse_dspy_sectioned_output, _repair_json_output):
        recovered = parser(raw_response)
        if recovered is not None:
            return recovered

    return None


def _extract_lm_response_text(message: str) -> str | None:
    match = _ADAPTER_LM_RESPONSE_RE.search(message)
    if match is None:
        return None
    response = match.group("response").strip()
    return response or None


def _repair_json_output(text: str) -> object | None:
    stripped = text.strip()
    if not stripped:
        return None

    try:
        return repair_json_loads(stripped)
    except Exception:
        return None


def _parse_dspy_sectioned_output(text: str) -> object | None:
    matches = list(_DSPY_SECTION_RE.finditer(text))
    if not matches:
        return None

    parsed: dict[str, object] = {}
    for index, match in enumerate(matches):
        field = match.group("field").strip().lower()
        if field == "completed":
            continue

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if not content:
            continue
        parsed[field] = _parse_dspy_section_content(content, field=field)

    return parsed or None


def _parse_dspy_section_content(content: str, *, field: str) -> object:
    cleaned = content.strip().strip("`").strip()
    cleaned = re.sub(r"^[:\-\s]+", "", cleaned)
    if not cleaned:
        return ""

    list_fields = {
        "req_skills",
        "required_skills",
        "nice_skills",
        "nice_to_have_skills",
        "responsibilities",
        "prep",
        "how_to_prepare",
        "learn",
        "learning_path",
        "gaps",
        "missing_skills",
        "resume",
        "resume_tips",
        "interview",
        "interview_tips",
        "projects",
        "portfolio_project_ideas",
        "strengths",
        "missing_skills",
        "resume_improvements",
        "ats_improvements",
        "recruiter_improvements",
        "rewritten_bullets",
        "interview_focus",
        "next_steps",
    }

    if cleaned.startswith("[") or cleaned.startswith("{"):
        try:
            return repair_json_loads(cleaned)
        except Exception:
            pass

    if field in list_fields:
        lines = [line.strip(" -•\t") for line in cleaned.splitlines() if line.strip(" -•\t")]
        if len(lines) > 1:
            return lines
        if len(lines) == 1:
            return lines[0]
        return []

    if "\n" in cleaned:
        return " ".join(line.strip() for line in cleaned.splitlines() if line.strip())

    return cleaned


def _stringify_issue_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= 240 else text[:240].rstrip() + "...<truncated>"
