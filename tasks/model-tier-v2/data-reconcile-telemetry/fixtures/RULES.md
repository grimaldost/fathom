# Reconciliation rules

## Matching (`recon.match.match`)

- **M1** — a reading matches a device when `abs(reading.at - device.seen_at)` is
  **less than or equal to** that device's `tolerance`. The bound is inclusive.
- **M2** — when more than one device is eligible for a reading, take the one with
  the smallest `abs(reading.at - device.seen_at)`; on a tie take the **earlier**
  `seen_at`; on a further tie take the **lower** device `id`.
- **M3** — a device accounts for at most one reading, and readings are considered in
  ascending `at`, then ascending `id`. The order the readings arrive in is not an
  order.

## Gaps (`recon.gaps.gaps`)

- **G1** — a gap is a reading with no match. Every unmatched reading is listed, in
  ascending `at` then ascending `id`. Two readings that share an `at` are two gaps.

## Summary (`recon.report.summarise`)

- **S1** — `summarise` returns `{"readings": n, "matched": m, "gaps": g}` where `n`
  is the number of readings it was given and `m + g == n`.

## Worked example

    readings = [Reading(2, 140, 6.0), Reading(1, 100, 5.0)]
    devices  = [Device("d1", 120, 25)]

Both readings are within `d1`'s tolerance of 25. M3 considers them in ascending `at`,
so reading 1 is offered the device first and takes it; `d1` is then spent and reading 2
has nothing left. The answer is `[(1, "d1")]`, reading 2 is the one gap, and the
summary is `{"readings": 2, "matched": 1, "gaps": 1}`.

The list the readings arrived in says otherwise, and that is the point of M3.
