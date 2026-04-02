from datetime import timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.circuit_breaker import AICircuitBreaker, CircuitBreakerOpenError
from app.core.rate_limit import InMemoryRateLimiter, RateLimitPolicy, get_rate_limiter
from app.core.rate_limit_redis import RedisRateLimiter
from app.core.security import _legacy_encode_jwt, create_access_token, decode_access_token
from app.core.config import get_settings


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )


def test_ai_circuit_breaker_retries_then_succeeds():
    breaker = AICircuitBreaker(sleep_func=lambda _: None)
    attempts = {"count": 0}

    def flaky_call():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HTTPException(status_code=503, detail="temporary")
        return "ok"

    result = breaker.call(
        operation="job_analysis",
        logger=__import__("logging").getLogger(__name__),
        callable_=flaky_call,
        retryable=lambda exc: isinstance(exc, HTTPException) and exc.status_code == 503,
        token_budget=500,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_ai_circuit_breaker_opens_after_max_retries():
    breaker = AICircuitBreaker(sleep_func=lambda _: None)
    attempts = {"count": 0}

    def always_fail():
        attempts["count"] += 1
        raise HTTPException(status_code=504, detail="timeout")

    with pytest.raises(CircuitBreakerOpenError):
        breaker.call(
            operation="cover_letter_generation",
            logger=__import__("logging").getLogger(__name__),
            callable_=always_fail,
            retryable=lambda exc: isinstance(exc, HTTPException) and exc.status_code == 504,
            token_budget=1200,
        )

    assert attempts["count"] == 4


def test_redis_rate_limiter_falls_back_to_in_memory_on_redis_error(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    get_settings.cache_clear()

    class RecordingFallbackLimiter:
        def __init__(self) -> None:
            self.calls = 0

        def enforce(self, request, policy, user=None, email=None) -> None:
            self.calls += 1

    class BrokenRedisClient:
        def incr(self, key: str) -> int:
            raise __import__("redis").ConnectionError("redis down")

    fallback = RecordingFallbackLimiter()
    limiter = RedisRateLimiter(
        redis_url="redis://example",
        fallback_limiter=fallback,
        client=BrokenRedisClient(),
    )
    request = _build_request()
    policy = RateLimitPolicy(name="auth_login", limit=1, window_seconds=60)

    limiter.enforce(request=request, policy=policy)
    limiter.enforce(request=request, policy=policy)

    assert fallback.calls == 2
    get_settings.cache_clear()


def test_get_rate_limiter_uses_in_memory_when_redis_url_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_settings.cache_clear()
    __import__("app.core.rate_limit", fromlist=["_limiter"])._limiter = None
    __import__("app.core.rate_limit", fromlist=["_limiter_signature"])._limiter_signature = None

    limiter = get_rate_limiter()

    assert isinstance(limiter, InMemoryRateLimiter)


def test_decode_access_token_accepts_legacy_signed_token(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    legacy_token = _legacy_encode_jwt(
        {"sub": "123", "exp": 9999999999, "iat": 9999990000},
        settings.secret_key,
    )

    payload = decode_access_token(legacy_token)

    assert payload["sub"] == "123"


def test_create_access_token_round_trips_with_pyjwt():
    token = create_access_token("42", expires_delta=timedelta(minutes=5))

    payload = decode_access_token(token)

    assert payload["sub"] == "42"
