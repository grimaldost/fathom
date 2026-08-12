# Review of billing/prorate.py

## Defects

- days_in_cycle (P1): the start day is not counted and a reversed cycle is not guarded.
- unused_days (P2): the change day itself is not counted, so the count is off by one.
- credit (P3): `int(...)` truncates towards zero rather than rounding half up.
- charge (P4): the half-up branch should be double-checked.
- net (P5): the charge and credit are taken over the same cycle, which may be wrong.
- is_refund (P6): a zero net is arguably a refund.
