"""Generic circuit breaker for external service calls (non-AI).

State machine:
  CLOSED     → normal operation; failures counted
  OPEN       → calls rejected immediately after *failure_threshold* consecutive failures
  HALF_OPEN  → one probe call allowed after *recovery_timeout_seconds*; success resets,
               failure re-opens
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ServiceCircuitBreakerConfig:
    """Tuning knobs for the circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    retries: int = 2
    backoff_base_ms: int = 100
    max_backoff_ms: int = 2000


class ServiceCircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open and rejecting calls."""

    def __init__(self, service: str) -> None:
        super().__init__(f"Circuit breaker open for {service} — service temporarily unavailable.")
        self.service = service


class ServiceCircuitBreaker:
    """Thread-safe circuit breaker for external HTTP service calls."""

    def __init__(
        self,
        service_name: str,
        config: ServiceCircuitBreakerConfig | None = None,
        *,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.service_name = service_name
        self.config = config or ServiceCircuitBreakerConfig()
        self._sleep = sleep_func or time.sleep

        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._resolve_state()

    @property
    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def call(
        self,
        callable_: Callable[..., T],
        *args: Any,
        retryable: Callable[[Exception], bool] | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute *callable_* with circuit-breaker protection.

        Retries up to ``config.retries`` times for exceptions where
        *retryable* returns ``True``.  Non-retryable exceptions propagate
        immediately.
        """
        state = self.state
        if state == CircuitState.OPEN:
            logger.warning(
                "service_circuit_open service=%s consecutive_failures=%s",
                self.service_name,
                self._consecutive_failures,
            )
            raise ServiceCircuitBreakerOpenError(self.service_name)

        is_retryable = retryable or (lambda _: True)
        max_attempts = 1 + self.config.retries

        for attempt in range(max_attempts):
            try:
                result = callable_(*args, **kwargs)
                self._record_success()
                return result
            except Exception as exc:
                if not is_retryable(exc) or attempt >= max_attempts - 1:
                    self._record_failure()
                    raise
                delay_ms = min(
                    self.config.max_backoff_ms,
                    self.config.backoff_base_ms * (2**attempt),
                )
                logger.warning(
                    "service_retry service=%s attempt=%s delay_ms=%s reason=%s",
                    self.service_name,
                    attempt + 1,
                    delay_ms,
                    type(exc).__name__,
                )
                self._sleep(delay_ms / 1000)

        # Should never reach here, but satisfy type checker
        raise RuntimeError("circuit_breaker_exhausted")  # pragma: no cover

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_state(self) -> CircuitState:
        """Determine actual state, promoting OPEN → HALF_OPEN after timeout."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.config.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    "service_circuit_half_open service=%s elapsed_seconds=%.1f",
                    self.service_name,
                    elapsed,
                )
        return self._state

    def _record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("service_circuit_closed service=%s", self.service_name)
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0

    def _record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "service_circuit_reopened service=%s",
                    self.service_name,
                )
            elif self._consecutive_failures >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "service_circuit_opened service=%s consecutive_failures=%s",
                    self.service_name,
                    self._consecutive_failures,
                )
