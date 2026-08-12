# Proration rules

The cycle runs from `start_day` up to but not including `end_day`, and days are
integers. Money is in whole cents throughout.

- **P1 `days_in_cycle`** — the number of days in the cycle, counting the start day
  and not the end day. For a cycle of `start_day = 1`, `end_day = 31` that is 30.
- **P2 `unused_days`** — the whole days remaining after a change on `change_day`,
  **counting the change day itself**. Changing on day 10 of a cycle that ends on
  day 31 leaves 21 unused days, not 21 minus one and not 22.
- **P3 `credit`** — `amount_cents * unused / cycle`, rounded **half up**. A cycle
  length of zero or less is a credit of zero.
- **P4 `charge`** — `amount_cents * unused / cycle`, rounded **half up**. A cycle
  length of zero or less is a charge of zero.
- **P5 `net`** — the new plan's charge less the old plan's credit, over the same
  cycle and the same unused-day count.
- **P6 `is_refund`** — a net below zero is a refund. Exactly zero is not a refund.
