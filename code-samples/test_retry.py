"""Tests for the retry decorator example."""

import pytest
from unittest.mock import MagicMock, patch

from example_retry import (
    retry,
    TransientError,
    PermanentError,
    fetch_from_storage,
    query_external_api,
)


class TestRetryDecorator:
    def test_success_first_attempt(self):
        """Function that succeeds immediately returns normally."""
        @retry()
        def succeed():
            return "ok"

        result = succeed()
        assert result == "ok"

    def test_retry_on_transient_then_succeed(self):
        """Succeeds on 3rd attempt after 2 transient failures."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TransientError("Not ready yet")
            return "finally"

        result = flaky()
        assert result == "finally"
        assert call_count[0] == 3

    def test_exhausts_retries(self):
        """Raises RuntimeError after max_attempts exhausted."""
        @retry(max_attempts=3, base_delay=0.01)
        def always_fails():
            raise TransientError("Always broken")

        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            always_fails()

    def test_no_retry_on_permanent_error(self):
        """PermanentError is raised immediately, no retry."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01)
        def forbidden():
            call_count[0] += 1
            raise PermanentError("Access denied")

        with pytest.raises(PermanentError):
            forbidden()
        assert call_count[0] == 1  # Should NOT retry

    def test_custom_attempts(self):
        """max_attempts controls total attempts."""
        call_count = [0]

        @retry(max_attempts=5, base_delay=0.01)
        def five_attempts():
            call_count[0] += 1
            if call_count[0] < 5:
                raise TransientError("fail")
            return "ok"

        result = five_attempts()
        assert result == "ok"
        assert call_count[0] == 5

    def test_exponential_backoff_bounds(self):
        """Backoff times follow 2^attempt pattern."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01)
        def flaky():
            call_count[0] += 1
            raise TransientError("fail")

        with pytest.raises(RuntimeError):
            flaky()

        assert call_count[0] == 3  # All attempts executed


class TestIntegrationExamples:
    def test_fetch_from_storage_success(self):
        """Normal path returns file contents."""
        result = fetch_from_storage("valid-path")
        assert result == b"file contents"

    def test_fetch_from_storage_flaky(self):
        """Transient errors exhaust retries."""
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            fetch_from_storage("flaky")

    def test_fetch_from_storage_forbidden(self):
        """Permanent error raised immediately."""
        with pytest.raises(PermanentError, match="Access denied"):
            fetch_from_storage("forbidden")

    def test_query_external_api_success(self):
        """Normal API call returns dict."""
        result = query_external_api("healthy-api")
        assert result["status"] == "ok"

    def test_query_external_api_flaky(self):
        """API flakiness exhausts retries."""
        with pytest.raises(RuntimeError, match="failed after 5 attempts"):
            query_external_api("flaky-api")
