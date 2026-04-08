from __future__ import annotations

import logging
from typing import Any

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover - optional local dependency
    redis = None  # type: ignore[assignment]
from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.models import User


logger = logging.getLogger(__name__)


class RedisRateLimiter:
    def __init__(
        self,
        *,
        redis_url: str,
        fallback_limiter: Any,
        client: redis.Redis | None = None,
    ) -> None:
        if redis is None:
            raise RuntimeError("redis_package_missing")
        self.redis_url = redis_url
        self._fallback_limiter = fallback_limiter
        self._client = client or redis.Redis.from_url(redis_url, decode_responses=True)

    def enforce(
        self,
        request: Request,
        policy: Any,
        user: User | None = None,
        email: str | None = None,
    ) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        if user is not None and settings.is_trusted_user(getattr(user, "email", None)):
            return

        subject = _build_subject(request=request, user=user)
        key = f"ratelimit:{policy.name}:{subject}"

        try:
            current_count, ttl_seconds = self._increment(key=key, window_seconds=policy.window_seconds)
        except redis.RedisError as exc:
            logger.warning(
                "redis_rate_limit_unavailable policy=%s reason=%s",
                policy.name,
                type(exc).__name__,
            )
            self._fallback_limiter.enforce(request=request, policy=policy, user=user, email=email)
            return

        if current_count > policy.limit:
            retry_after = max(1, ttl_seconds if ttl_seconds > 0 else policy.window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    def _increment(self, *, key: str, window_seconds: int) -> tuple[int, int]:
        current_count = int(self._client.incr(key))
        ttl_seconds = int(self._client.ttl(key))

        if current_count == 1 or ttl_seconds < 0:
            self._client.expire(key, window_seconds)
            ttl_seconds = window_seconds

        return current_count, ttl_seconds


def _build_subject(request: Request, user: User | None) -> str:
    if user is not None:
        return f"user:{user.id}"

    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip()
    if client_ip:
        return f"ip:{client_ip}"

    if request.client and request.client.host:
        return f"ip:{request.client.host}"

    return "ip:unknown"
