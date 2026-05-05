"""Tests for Sprint 14 — ServiceCircuitBreaker and Supabase Storage integration."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from app.core.service_circuit_breaker import (
    CircuitState,
    ServiceCircuitBreaker,
    ServiceCircuitBreakerConfig,
    ServiceCircuitBreakerOpenError,
)
from app.services.supabase_storage import (
    SupabaseStorageError,
    SupabaseStorageService,
    SupabaseStorageUnavailableError,
    _is_retryable_storage_error,
)


# ---------------------------------------------------------------------------
# ServiceCircuitBreaker unit tests
# ---------------------------------------------------------------------------


class TestServiceCircuitBreaker:
    """Core state-machine tests for the generic circuit breaker."""

    def _make_breaker(self, **overrides) -> ServiceCircuitBreaker:
        config = ServiceCircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=1.0,
            retries=0,  # no retries so we can control per-call outcomes
            backoff_base_ms=10,
            max_backoff_ms=50,
        )
        for key, value in overrides.items():
            setattr(config, key, value)
        return ServiceCircuitBreaker("test_service", config, sleep_func=lambda _: None)

    def test_starts_closed(self):
        cb = self._make_breaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available is True

    def test_successful_calls_stay_closed(self):
        cb = self._make_breaker()
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = self._make_breaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(self._failing_callable)
        assert cb.state == CircuitState.OPEN
        assert cb.is_available is False

    def test_open_rejects_calls(self):
        cb = self._make_breaker(failure_threshold=2)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(self._failing_callable)
        with pytest.raises(ServiceCircuitBreakerOpenError) as exc_info:
            cb.call(lambda: 42)
        assert exc_info.value.service == "test_service"

    def test_transitions_to_half_open_after_timeout(self):
        fake_time = [100.0]
        cb = self._make_breaker(failure_threshold=2, recovery_timeout_seconds=5.0)

        # Patch monotonic to control time
        with patch("app.core.service_circuit_breaker.time.monotonic", side_effect=lambda: fake_time[0]):
            for _ in range(2):
                with pytest.raises(ValueError):
                    cb.call(self._failing_callable)
            assert cb.state == CircuitState.OPEN

            # Advance time past recovery timeout
            fake_time[0] = 106.0
            assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self):
        fake_time = [100.0]
        cb = self._make_breaker(failure_threshold=2, recovery_timeout_seconds=5.0)

        with patch("app.core.service_circuit_breaker.time.monotonic", side_effect=lambda: fake_time[0]):
            for _ in range(2):
                with pytest.raises(ValueError):
                    cb.call(self._failing_callable)
            fake_time[0] = 106.0
            result = cb.call(lambda: "recovered")
            assert result == "recovered"
            assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        fake_time = [100.0]
        cb = self._make_breaker(failure_threshold=2, recovery_timeout_seconds=5.0)

        with patch("app.core.service_circuit_breaker.time.monotonic", side_effect=lambda: fake_time[0]):
            for _ in range(2):
                with pytest.raises(ValueError):
                    cb.call(self._failing_callable)
            fake_time[0] = 106.0
            with pytest.raises(ValueError):
                cb.call(self._failing_callable)
            assert cb.state == CircuitState.OPEN

    def test_retries_before_recording_failure(self):
        cb = self._make_breaker(retries=2, failure_threshold=3)
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("transient")
            return "success"

        result = cb.call(flaky)
        assert result == "success"
        assert call_count == 3
        assert cb.state == CircuitState.CLOSED

    def test_retryable_filter(self):
        cb = self._make_breaker(retries=2, failure_threshold=10)

        # Non-retryable exceptions should propagate immediately
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            cb.call(always_fail, retryable=lambda exc: isinstance(exc, ValueError))
        assert call_count == 1  # No retries for non-retryable

    def test_success_resets_failure_count(self):
        cb = self._make_breaker(failure_threshold=3)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(self._failing_callable)
        # One success should reset the counter
        cb.call(lambda: "ok")
        # Two more failures should NOT open the circuit (counter was reset)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(self._failing_callable)
        assert cb.state == CircuitState.CLOSED

    def test_thread_safety(self):
        cb = self._make_breaker(failure_threshold=100, retries=0)
        errors: list[Exception] = []

        def worker():
            try:
                for _ in range(50):
                    try:
                        cb.call(lambda: 1)
                    except ServiceCircuitBreakerOpenError:
                        pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    @staticmethod
    def _failing_callable():
        raise ValueError("boom")


# ---------------------------------------------------------------------------
# Retryable storage error classification
# ---------------------------------------------------------------------------


class TestRetryableStorageError:
    def test_http_500_is_retryable(self):
        from urllib.error import HTTPError

        exc = HTTPError("http://example.com", 500, "Internal Server Error", {}, None)
        assert _is_retryable_storage_error(exc) is True

    def test_http_403_is_not_retryable(self):
        from urllib.error import HTTPError

        exc = HTTPError("http://example.com", 403, "Forbidden", {}, None)
        assert _is_retryable_storage_error(exc) is False

    def test_url_error_is_retryable(self):
        from urllib.error import URLError

        exc = URLError("connection refused")
        assert _is_retryable_storage_error(exc) is True

    def test_wrapped_storage_error_with_http_503_is_retryable(self):
        from urllib.error import HTTPError

        inner = HTTPError("http://example.com", 503, "Service Unavailable", {}, None)
        outer = SupabaseStorageError("wrapped")
        outer.__cause__ = inner
        assert _is_retryable_storage_error(outer) is True

    def test_generic_exception_is_not_retryable(self):
        assert _is_retryable_storage_error(RuntimeError("random")) is False


# ---------------------------------------------------------------------------
# SupabaseStorageService circuit breaker integration
# ---------------------------------------------------------------------------


class TestSupabaseStorageCircuitBreakerIntegration:
    """Verify SupabaseStorageService properly wraps calls with circuit breaker."""

    def _make_service(self) -> SupabaseStorageService:
        with patch("app.services.supabase_storage.get_settings") as mock_settings:
            settings = MagicMock()
            settings.supabase_url = "https://test.supabase.co"
            settings.supabase_service_role_key = "test-key"
            mock_settings.return_value = settings
            service = SupabaseStorageService()
        # Override the circuit breaker sleep to avoid actual delays
        service._circuit_breaker._sleep = lambda _: None
        service._circuit_breaker.config = ServiceCircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=1.0,
            retries=0,
            backoff_base_ms=10,
        )
        return service

    def test_is_available_initially_true(self):
        service = self._make_service()
        assert service.is_available() is True

    def test_is_available_false_after_circuit_opens(self):
        import time as _time

        service = self._make_service()
        # Force circuit open with a recent failure time so it doesn't auto-promote to HALF_OPEN
        service._circuit_breaker._state = CircuitState.OPEN
        service._circuit_breaker._last_failure_time = _time.monotonic()
        service._circuit_breaker.config = ServiceCircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=9999.0,  # Very long so it stays OPEN
            retries=0,
        )
        assert service.is_available() is False

    def test_raises_unavailable_when_circuit_open(self):
        import time as _time

        service = self._make_service()
        service._circuit_breaker._state = CircuitState.OPEN
        service._circuit_breaker._last_failure_time = _time.monotonic()
        service._circuit_breaker.config = ServiceCircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout_seconds=9999.0,
            retries=0,
        )

        with pytest.raises(SupabaseStorageUnavailableError):
            service.delete_cv_pdf(path="1/2.pdf")


# ---------------------------------------------------------------------------
# Health endpoint integration
# ---------------------------------------------------------------------------


class TestHealthEndpointStorageStatus:
    """Verify /health reflects storage circuit breaker status."""

    def test_health_includes_storage_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["storage"] == "ok"

    def test_health_includes_storage_degraded(self, client):
        import time as _time

        from app.services.supabase_storage import get_supabase_storage_service

        storage_service = get_supabase_storage_service()
        original_state = storage_service._circuit_breaker._state
        original_config = storage_service._circuit_breaker.config
        original_failure_time = storage_service._circuit_breaker._last_failure_time
        try:
            storage_service._circuit_breaker._state = CircuitState.OPEN
            storage_service._circuit_breaker._last_failure_time = _time.monotonic()
            storage_service._circuit_breaker.config = ServiceCircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout_seconds=9999.0,
                retries=0,
            )
            response = client.get("/health")
            assert response.status_code == 200
            body = response.json()
            assert body["storage"] == "degraded"
        finally:
            storage_service._circuit_breaker._state = original_state
            storage_service._circuit_breaker.config = original_config
            storage_service._circuit_breaker._last_failure_time = original_failure_time
