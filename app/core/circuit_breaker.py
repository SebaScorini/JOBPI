from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any, Callable


@dataclass(frozen=True)
class CircuitBreakerConfig:
    max_retries: int = 3
    initial_backoff_ms: int = 100
    max_backoff_ms: int = 5000


class CircuitBreakerOpenError(RuntimeError):
    def __init__(self, operation: str, attempts: int) -> None:
        super().__init__(f"Circuit breaker opened for {operation} after {attempts} attempts.")
        self.operation = operation
        self.attempts = attempts


class AICircuitBreaker:
    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        *,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config or CircuitBreakerConfig()
        self._sleep = sleep_func or time.sleep

    def call(
        self,
        *,
        operation: str,
        logger: logging.Logger,
        callable_: Callable[[], Any],
        callable_with_attempt: Callable[[int], Any] | None = None,
        retryable: Callable[[Exception], bool],
        token_budget: int | None = None,
        token_budget_for_attempt: Callable[[int], int | None] | None = None,
    ) -> Any:
        attempt = 0
        while True:
            try:
                if callable_with_attempt is not None:
                    return callable_with_attempt(attempt)
                return callable_()
            except Exception as exc:
                if not retryable(exc):
                    raise

                current_token_budget = (
                    token_budget_for_attempt(attempt)
                    if token_budget_for_attempt is not None
                    else token_budget
                )
                next_token_budget = (
                    token_budget_for_attempt(attempt + 1)
                    if token_budget_for_attempt is not None
                    else token_budget
                )

                if attempt >= self.config.max_retries:
                    logger.error(
                        "ai_circuit_open operation=%s attempts=%s token_budget=%s",
                        operation,
                        attempt + 1,
                        current_token_budget,
                    )
                    raise CircuitBreakerOpenError(operation=operation, attempts=attempt + 1) from exc

                delay_ms = min(
                    self.config.max_backoff_ms,
                    self.config.initial_backoff_ms * (2**attempt),
                )
                logger.warning(
                    "ai_retry operation=%s retry=%s delay_ms=%s token_budget=%s next_token_budget=%s",
                    operation,
                    attempt + 1,
                    delay_ms,
                    current_token_budget,
                    next_token_budget,
                )
                self._sleep(delay_ms / 1000)
                attempt += 1
