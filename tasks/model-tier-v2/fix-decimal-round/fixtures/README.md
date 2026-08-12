# money

Rounding for money amounts, in two interchangeable backends.

## The rounding rule

One rule, for both backends:

> Round to the requested number of decimal places, **half away from zero**. `0.5`
> rounds to `1`, `-0.5` rounds to `-1`, `0.125` at two places rounds to `0.13`,
> `-0.125` at two places rounds to `-0.13`.

Note this is *not* Python's built-in `round`, which rounds a tie to the nearest even
number.

## The backends

- `exact.round_half_up(value, places=0)` — decimal arithmetic. Slow, always right.
- `fast.round_half_up(value, places=0)` — float arithmetic. Cheap enough for a hot
  loop.

**The two backends must agree.** `fast` may be quicker, but it may not be different:
for any value and any number of places, `fast.round_half_up` returns what
`exact.round_half_up` returns. Callers pick a backend for speed, never for a
different answer.

- `total.line_total(quantity, unit_price, backend="fast")` — the rounded total for
  a line of an order, to two places, through the named backend.

Run the tests: `python -m unittest discover -s tests -t .`
