Users of the `money` package report that `fast.round_half_up(0.5)` returns `0.0`
and `fast.round_half_up(0.125, 2)` returns `0.12`. Per the package README those
should be `1.0` and `0.13` — half rounds away from zero — and the `exact` backend
already returns them. Find and fix the bug so the package behaves as documented.
Preserve the existing public API, and keep the shipped test suite passing.
