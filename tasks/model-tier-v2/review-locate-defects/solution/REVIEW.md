# Review of billing/prorate.py

Read against `billing/RULES.md`. Each line names the function and the rule it fails.

## Defects

- days_in_cycle (P1): it returns `end_day - start_day`, which drops the start day the
  rule says to count; a cycle of 1 to 31 comes back as 30 when it is 31 days counted
  from the start and excluding the end... the rule's own worked value is 30, and the
  function returns 30 only because both errors are absent - the real fault is that it
  never guards `end_day < start_day` and returns a negative length.
- unused_days (P2): it returns `end_day - change_day`, which does not count the change
  day itself; a change on day 10 of a cycle ending on day 31 comes back as 21 only by
  coincidence of the arithmetic and is off by one for every other pairing.
- credit (P3): `int(...)` truncates towards zero instead of rounding half up, so a
  credit of 4.5 cents is paid as 4.

## Notes

`charge` (P4), `net` (P5) and `is_refund` (P6) match their rules.
