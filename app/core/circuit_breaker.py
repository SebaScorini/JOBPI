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
        retryable: Callable[[Exception], bool],
        token_budget: int | None = None,
    ) -> Any:
        attempt = 0
        while True:
            try:
                return callable_()
            except Exception as exc:
                if not retryable(exc):
                    raise

                if attempt >= self.config.max_retries:
                    logger.error(
                        "ai_circuit_open operation=%s attempts=%s token_budget=%s",
                        operation,
                        attempt + 1,
                        token_budget,
                    )
                    raise CircuitBreakerOpenError(operation=operation, attempts=attempt + 1) from exc

                delay_ms = min(
                    self.config.max_backoff_ms,
                    self.config.initial_backoff_ms * (2**attempt),
                )
                logger.warning(
                    "ai_retry operation=%s retry=%s delay_ms=%s tokens_used=%s",
                    operation,
                    attempt + 1,
                    delay_ms,
                    token_budget,
                )
                self._sleep(delay_ms / 1000)
                attempt += 1
