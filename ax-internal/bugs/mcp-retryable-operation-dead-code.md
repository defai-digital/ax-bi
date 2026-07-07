# RetryableOperation context manager cannot retry (dead code)

Classification: confirmed
Severity: LOW
Component: `superset/mcp_service/utils/retry_utils.py`

## Summary

`RetryableOperation` is a context manager intended to retry an operation on
transient failures, but its retry mechanism cannot work: a Python `with`
block body executes exactly once on entry. `__exit__` returning `True`
suppresses the exception, but there is no way for `__exit__` to re-enter
the `with` body. The operation therefore runs at most once, and any
retryable exception is silently swallowed (suppressed without being reraised)
once `max_attempts` is reached — instead of propagating to the caller.

The class is also currently dead code: a repo-wide search for
`RetryableOperation` returns only its own definition (no callers), so there
is no runtime impact today. The two decorator-based helpers in the same
module (`retry_on_exception`, `async_retry_on_exception`) are the real retry
mechanisms and are correct.

## Evidence

`superset/mcp_service/utils/retry_utils.py:230-281`:

```python
class RetryableOperation:
    def __enter__(self) -> "RetryableOperation":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        ...
        if self.current_attempt >= self.max_attempts:
            # Max attempts reached
            return False   # <-- propagates (correct)

        ...
        time.sleep(delay)
        return True  # Suppress the exception and continue
        # ^^ "continue" is impossible: the with-body will not re-run.
        # On the FIRST failure this swallows the exception silently and
        # continues execution AFTER the with-block, skipping the retry.

    def should_retry(self) -> bool:
        return self.current_attempt < self.max_attempts
```

The only matches for `RetryableOperation` in the repository are the class
definition itself (`retry_utils.py:207`) and its `__enter__` (`:230`) — no
production or test usage. `retry_on_exception` / `async_retry_on_exception`
are used instead and work correctly.

## Suggested Fix

Remove `RetryableOperation`. It is dead code with a non-functional retry
contract; keeping it risks a future caller adopting it and silently losing
retry semantics. The decorator helpers already cover the use case. If a
context-manager-style API is ever wanted, it must wrap an explicit loop
(e.g. a generator or a `while` inside the caller), not rely on `__exit__`
re-entry, which Python does not support.
