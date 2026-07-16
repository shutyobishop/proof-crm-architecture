"""Sanitized example — Retry with Exponential Backoff.

Shows the storage retry pattern used for external API calls.
3 attempts with exponential backoff (1s → 2s → 4s).
"""

import time
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ═══════════════════════════════════════════════════════════════
#  Exception stubs — in production these come from real libraries
# ═══════════════════════════════════════════════════════════════

class TransientError(Exception):
    """Errors that might succeed on retry — network blips, timeouts."""
    pass


class PermanentError(Exception):
    """Errors that will never succeed — auth failures, bad requests."""
    pass


# ═══════════════════════════════════════════════════════════════
#  Retry decorator
# ═══════════════════════════════════════════════════════════════

def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (TransientError,),
):
    """Decorator: retry a function with exponential backoff.

    Args:
        max_attempts: Total attempts before giving up (default: 3)
        base_delay: Initial wait in seconds (default: 1s)
        backoff_factor: Multiplier per attempt (default: 2x)
        retryable_exceptions: Which exception types to retry on

    Backoff schedule (defaults):
        Attempt 1 → fail → wait 1s
        Attempt 2 → fail → wait 2s
        Attempt 3 → fail → raise RuntimeError
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait = base_delay * (backoff_factor ** attempt)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt+1}/{max_attempts}): "
                            f"{e} — retrying in {wait:.1f}s"
                        )
                        time.sleep(wait)
                    else:
                        raise RuntimeError(
                            f"{func.__name__} failed after {max_attempts} attempts"
                        ) from e
                except PermanentError:
                    raise  # Don't retry permanent failures

            raise RuntimeError("Unreachable")  # type safety
        return wrapper  # type: ignore[return-value]
    return decorator


# ═══════════════════════════════════════════════════════════════
#  Usage example
# ═══════════════════════════════════════════════════════════════

@retry(max_attempts=3, retryable_exceptions=(TransientError,))
def fetch_from_storage(path: str) -> bytes:
    """Fetch a file from external storage.

    Retries on TransientError (network, timeout).
    Fails immediately on PermanentError (auth, not found).
    """
    # Simulate an external call that might fail transiently
    if path == "flaky":
        raise TransientError("Connection reset by peer")
    if path == "forbidden":
        raise PermanentError("Access denied")
    return b"file contents"


@retry(max_attempts=5, base_delay=0.5)
def query_external_api(endpoint: str) -> dict:
    """Query an external API with more attempts, shorter initial delay.

    Backoff: 0.5s → 1s → 2s → 4s → 8s = 5 attempts total.
    """
    if endpoint == "flaky-api":
        raise TransientError("503 Service Unavailable")
    return {"status": "ok", "data": []}
