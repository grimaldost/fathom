# Feature: retry with exponential backoff

Add a `retry` function to the `retrier` package, exported at the top level so it
imports as:

```python
from retrier import retry
```

## Signature

```python
import random
import time

retry(
    fn,
    *,
    attempts: int,
    base_delay: float,
    max_delay: float,
    retry_on: tuple = (Exception,),
    jitter: bool = False,
    sleep=time.sleep,
    rand=random.random,
)
```

Call `fn()` and return its result. `sleep` and `rand` are injectable so the
behavior can be tested without real time or real randomness.

## Required behavior

1. **Attempts are total calls.** `attempts` is the total number of times `fn`
   may be called. `attempts=1` means call `fn` once and, on failure, re-raise
   immediately — **no sleep**.
2. **Backoff with a cap.** Between a failed attempt and the next retry, wait by
   calling `sleep(delay)`. For the kth retry gap (k = 0 for the wait after the
   first failed attempt):

   ```
   delay = min(max_delay, base_delay * 2 ** k)
   ```

   The cap matters — `base_delay * 2 ** k` grows without bound, so the `min`
   keeps it at `max_delay`.
3. **Jitter is bounded.** When `jitter` is true, apply *full jitter*:
   `delay = rand() * delay`, where `rand()` returns a value in `[0, 1)`. The
   delay passed to `sleep` must always stay within
   `[0, min(max_delay, base_delay * 2 ** k)]` — never negative, never above the
   cap.
4. **Error propagation.**
   - If `fn` raises an exception that is **not** an instance of any type in
     `retry_on`, re-raise it immediately without retrying or sleeping.
   - After the final attempt fails, re-raise the exception from that **last**
     attempt (not a wrapped or generic error).

## Example

```python
calls = []
def flaky():
    calls.append(1)
    if len(calls) < 3:
        raise ValueError("boom")
    return "ok"

retry(flaky, attempts=5, base_delay=1.0, max_delay=30.0)
# -> "ok"  (fn called 3 times; slept after the 1st and 2nd failures)
```

## Constraints

- Standard library only; add no dependencies.
- Keep the existing helpers and the baseline tests passing.
- Add unit tests under `tests/` covering the happy path **and** each case above:
  zero-retry (`attempts=1`), jitter bounds, and error propagation.
