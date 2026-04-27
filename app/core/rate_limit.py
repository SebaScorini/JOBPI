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

        subjects = _build_subjects(request=request, user=user, email=email)
        now = time.time()
        cutoff = now - policy.window_seconds

        with self._lock:
            retry_after: int | None = None
            buckets: list[Deque[float]] = []
            for subject in subjects:
                bucket = self._events[f"{policy.name}:{subject}"]
                while bucket and bucket[0] <= cutoff:
                    bucket.popleft()
                buckets.append(bucket)
                if len(bucket) >= policy.limit:
                    retry_after = max(
                        retry_after or 0,
                        max(1, int(bucket[0] + policy.window_seconds - now)),
                    )

            if retry_after is not None:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            for bucket in buckets:
                bucket.append(now)


def _build_subjects(request: Request, user: User | None, email: str | None) -> list[str]:
    subjects: list[str] = []
    client_subject = _client_subject(request)
    if user is not None:
        subjects.append(f"user:{user.id}")
        subjects.append(f"user_ip:{user.id}:{client_subject}")
        return list(dict.fromkeys(subjects))

    normalized_email = _normalize_email(email)
    if normalized_email:
        subjects.append(f"email:{normalized_email}")

    subjects.append(client_subject)
    return list(dict.fromkeys(subjects))


def _client_subject(request: Request) -> str:
    if request.client and request.client.host:
        return f"ip:{request.client.host}"

    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip()
    if client_ip:
        return f"ip:{client_ip}"

    return "ip:unknown"


def _normalize_email(email: str | None) -> str:
    if not isinstance(email, str):
        return ""
    return email.strip().lower()


_limiter: InMemoryRateLimiter | RedisRateLimiter | None = None
_limiter_signature: str | None = None


def get_rate_limiter() -> InMemoryRateLimiter | RedisRateLimiter:
    global _limiter, _limiter_signature

    settings = get_settings()
    signature = settings.redis_url or "in-memory"
    if _limiter is not None and _limiter_signature == signature:
        return _limiter

    if settings.redis_url:
        try:
            logger.info("rate_limiter_backend backend=redis")
            _limiter = RedisRateLimiter(
                redis_url=settings.redis_url,
                fallback_limiter=InMemoryRateLimiter(),
            )
        except RuntimeError as exc:
            logger.warning(
                "rate_limiter_backend backend=in_memory reason=%s",
                str(exc),
            )
            _limiter = InMemoryRateLimiter()
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
