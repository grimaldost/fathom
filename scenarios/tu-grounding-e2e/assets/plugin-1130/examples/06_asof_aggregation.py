"""As-of (point-in-time) aggregation over SCD-2 position validity intervals.

Scenario
--------
A treasury book is versioned slowly-changing-dimension style: each position has a
validity interval ``[valid_from, valid_to)``, and a position is *revised* by
closing the current version and opening a new one. To report the book "as of" a
date you must pick exactly the version active on that date -- not the latest, not
the first. ``asof_aggregate`` does that selection and the grouped aggregation in
one pass.

What this demonstrates
----------------------
- Selecting the rows whose half-open interval ``[start, end)`` is active on an
  as-of date, then aggregating per group.
- A ``SumMeasure`` (total notional) and a ``WeightedAvgMeasure`` (notional-weighted
  rate) computed together.
- Point-in-time correctness across two dates: a mid-life revision and an expiry.
- Group cardinality (a real footgun): a group appears once it has a position whose
  interval *started* on or before the as-of date -- its value is 0 if those positions
  have all since closed. A group whose positions all begin *later* is omitted entirely,
  not reported as zero. So 0 means "existed, now empty", never "has not started yet".

treasuryutils APIs
------------------
- ``treasuryutils.compute.asof_aggregate``
- ``treasuryutils.compute.WindowSpec`` -- the ``(position_date, start_col, end_col)`` window
- ``treasuryutils.compute.SumMeasure`` / ``treasuryutils.compute.WeightedAvgMeasure``

Why treasuryutils, not hand-rolled
----------------------------------
The half-open active condition (``start <= asof < end``, with ``end = null`` meaning
"still open") is the classic SCD-2 footgun: an off-by-one on the boundary silently
double-counts a revised position on its cutover day. ``asof_aggregate`` encodes the
interval logic and the weighted-average denominator once, and is backend-dispatched
(Polars / pandas / Spark). See ``references/compute_common_api.md``.

Install
-------
``treasuryutils`` (core -- Polars only; no extras needed)

Run
---
``python examples/06_asof_aggregation.py``

Expected output (deterministic)
-------------------------------
    === As-of (point-in-time) position aggregation ===

    Positions (SCD-2 validity intervals [valid_from, valid_to)):
      TREASURY  BOND_A  2024-01-01..2024-03-01  notional=1,000,000  rate=10.50%
      TREASURY  BOND_A  2024-03-01..(open)      notional=1,200,000  rate=10.80%
      TREASURY  BOND_B  2024-01-15..(open)      notional=  500,000  rate=11.20%
      LIQUIDITY BILL_C  2024-02-01..2024-02-20  notional=  300,000  rate=10.00%

    As of 2024-02-15:
      LIQUIDITY  total_notional=  300,000  wavg_rate=10.0000%
      TREASURY   total_notional=1,500,000  wavg_rate=10.7333%
      (BOND_A's revision starts 2024-03-01, so only the 1.0M version is active.)

    As of 2024-03-15:
      LIQUIDITY  total_notional=        0  wavg_rate= 0.0000%
      TREASURY   total_notional=1,700,000  wavg_rate=10.9176%
      (BILL_C closed 2024-02-20, so LIQUIDITY nets to 0 -- it existed, then emptied.)

``asof_aggregate`` may emit a benign narwhals "Sortedness ... cannot be checked" warning
on stderr; it does not affect the result shown above (which is stdout).
"""

from __future__ import annotations

from datetime import date

import polars as pl

from treasuryutils.compute import (
    SumMeasure,
    WeightedAvgMeasure,
    WindowSpec,
    asof_aggregate,
)


def _positions() -> pl.DataFrame:
    """A small SCD-2 book: BOND_A is revised on 2024-03-01; BILL_C matures 2024-02-20."""
    return pl.DataFrame(
        {
            'portfolio': ['TREASURY', 'TREASURY', 'TREASURY', 'LIQUIDITY'],
            'instrument': ['BOND_A', 'BOND_A', 'BOND_B', 'BILL_C'],
            'valid_from': [date(2024, 1, 1), date(2024, 3, 1), date(2024, 1, 15), date(2024, 2, 1)],
            'valid_to': [date(2024, 3, 1), None, None, date(2024, 2, 20)],
            'notional': [1_000_000.0, 1_200_000.0, 500_000.0, 300_000.0],
            'rate': [0.105, 0.108, 0.112, 0.100],
        }
    )


def _report(positions: pl.DataFrame, asof: date) -> pl.DataFrame:
    """Total notional and notional-weighted rate per portfolio, active as of *asof*."""
    aggregated = asof_aggregate(
        positions,
        window=WindowSpec(position_date=asof, start_col='valid_from', end_col='valid_to'),
        group_cols='portfolio',
        measures=[
            SumMeasure(value_col='notional', out='total_notional'),
            WeightedAvgMeasure(
                value_col='rate', weight_cols=['notional'], out='wavg_rate', fill_value=0.0
            ),
        ],
    )
    result: pl.DataFrame = aggregated.sort('portfolio')
    return result


def main() -> None:
    positions = _positions()

    print('=== As-of (point-in-time) position aggregation ===\n')
    print('Positions (SCD-2 validity intervals [valid_from, valid_to)):')
    for row in positions.iter_rows(named=True):
        end = (row['valid_to'].isoformat() if row['valid_to'] is not None else '(open)').ljust(10)
        print(
            f'  {row["portfolio"]:<9} {row["instrument"]:<7} '
            f'{row["valid_from"].isoformat()}..{end}  '
            f'notional={row["notional"]:>9,.0f}  rate={row["rate"]:.2%}'
        )

    checkpoints = [
        (
            date(2024, 2, 15),
            "BOND_A's revision starts 2024-03-01, so only the 1.0M version is active.",
        ),
        (
            date(2024, 3, 15),
            'BILL_C closed 2024-02-20, so LIQUIDITY nets to 0 -- it existed, then emptied.',
        ),
    ]
    for asof, note in checkpoints:
        print(f'\nAs of {asof.isoformat()}:')
        for row in _report(positions, asof).iter_rows(named=True):
            print(
                f'  {row["portfolio"]:<9}  total_notional={row["total_notional"]:>9,.0f}  '
                f'wavg_rate={row["wavg_rate"]:>8.4%}'
            )
        print(f'  ({note})')


if __name__ == '__main__':
    main()
