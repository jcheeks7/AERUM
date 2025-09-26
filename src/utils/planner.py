import time
import threading
from typing import Any, Callable, Dict, Optional


def _resolve_key(state: Dict[str, Any], key: str) -> Any:
    """Retrieve a nested value from the state using dot-separated keys."""
    current: Any = state
    for part in key.split('.'):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def check_conditions(state: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
    """Verify that every condition matches the current state."""
    if not conditions:
        return True

    for key, expected in conditions.items():
        value = _resolve_key(state, key) if isinstance(key, str) else None
        if callable(expected):
            if not expected(value):
                return False
        elif isinstance(expected, (list, tuple, set)):
            if value not in expected:
                return False
        else:
            if value != expected:
                return False
    return True


def retry_action(action_fn: Callable[[int], Any], retries: int, delay: float):
    """Execute an action function with retry support."""
    attempts = max(1, int(retries) if retries is not None else 1)
    last_exception: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            return action_fn(attempt)
        except Exception as exc:  # pragma: no cover - generic handler
            last_exception = exc
            if attempt < attempts and delay:
                time.sleep(delay)
    if last_exception is not None:
        raise last_exception
    return None


def timeout_wrapper(action_fn: Callable[[], Any], timeout: float):
    """Execute an action function and enforce a timeout."""
    if timeout is None or timeout <= 0:
        return action_fn()

    result_container: Dict[str, Any] = {}
    exception_container: Dict[str, BaseException] = {}

    def target():
        try:
            result_container['result'] = action_fn()
        except BaseException as exc:  # pragma: no cover - propagate
            exception_container['exception'] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout)

    if worker.is_alive():
        raise TimeoutError(f"Action exceeded timeout of {timeout} seconds")

    if 'exception' in exception_container:
        raise exception_container['exception']

    return result_container.get('result')
