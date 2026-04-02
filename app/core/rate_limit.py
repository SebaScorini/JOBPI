from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.rate_limit_redis import RedisRateLimiter
from app.models import User


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def enforce(
        self,
        request: Request,
        policy: RateLimitPolicy,
        user: User | None = None,
        email: str | None = None,
    ) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        if user is not None and settings.is_trusted_user(getattr(user, "email", None)):
            return

        subject = _build_subject(request=request, user=user)
        bucket_key = f"{policy.name}:{subject}"
        now = time.time()
        cutoff = now - policy.window_seconds

        with self._lock:
            bucket = self._events[bucket_key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= policy.limit:
                retry_after = max(1, int(bucket[0] + policy.window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)


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


_limiter: InMemoryRateLimiter | RedisRateLimiter | None = None
_limiter_signature: str | None = None


def get_rate_limiter() -> InMemoryRateLimiter | RedisRateLimiter:
    global _limiter, _limiter_signature

    settings = get_settings()
    signature = settings.redis_url or "in-memory"
    if _limiter is not None and _limiter_signature == signature:
        return _limiter

    if settings.redis_url:
        logger.info("rate_limiter_backend backend=redis")
        _limiter = RedisRateLimiter(
            redis_url=settings.redis_url,
            fallback_limiter=InMemoryRateLimiter(),
        )
    else:
        logger.info("rate_limiter_backend backend=in_memory")
        _limiter = InMemoryRateLimiter()
    _limiter_signature = signature
    return _limiter


def enforce_rate_limit(
    request: Request,
    policy: RateLimitPolicy,
    user: User | None = None,
    email: str | None = None,
) -> None:
    get_rate_limiter().enforce(request=request, policy=policy, user=user, email=email)
