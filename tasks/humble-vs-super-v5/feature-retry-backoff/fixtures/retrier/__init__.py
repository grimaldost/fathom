"""retrier — retry helpers (starting project).

The package currently ships only a small time helper. The
retry-with-exponential-backoff helper described in SPEC.md (``retry``) is the
feature to implement; once added it should be exported here so
``from retrier import retry`` works.
"""

from .clock import elapsed

__all__ = ["elapsed"]
