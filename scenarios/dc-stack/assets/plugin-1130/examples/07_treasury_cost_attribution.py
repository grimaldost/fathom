"""Treasury cost attribution + a period-over-period P&L waterfall.

Scenario
--------
A treasury desk closes the month and wants to answer two questions about its
funding/carry P&L: (1) "which entities (or instrument types, or currencies) drove
the notional-weighted cost this period?" and (2) "how did each P&L component move
versus last month?". ``capitaltools`` answers both from plain position + P&L tables
-- no data bindings, no auth, pure offline compute.

What this demonstrates
----------------------
- ``compute_treasury_cost_attribution`` joins a P&L decomposition to a position
  snapshot on ``deal_id``, weights each instrument's ``pnl_total`` by its notional
  share of the book, and aggregates per group. Run here across all three supported
  dimensions (``entity_id`` -> labelled ``entity``, ``instrument_type``, ``currency``).
- ``build_period_waterfall`` bridges a wide-format prior vs. current table so
  ``prior + delta = current`` per component -- the standard month-over-month story.
- The input COLUMN CONTRACTS (the schemas the reference signatures don't spell out).

treasuryutils APIs
------------------
- ``treasuryutils.capitaltools.attribution.compute_treasury_cost_attribution``
  -- ``pnl_attribution`` needs ``deal_id`` (Utf8) + ``pnl_total`` (Float64);
     ``positions`` needs ``deal_id`` (Utf8) + ``notional`` (Float64) + the ``group_by`` column.
- ``treasuryutils.capitaltools.attribution.build_period_waterfall``
  -- wide-format ``current`` / ``prior`` (each numeric column = one component).

Why treasuryutils, not hand-rolled
----------------------------------
The notional-weighting + group decomposition (and the accounting identity that the
group contributions reconcile to the weighted total) is exactly the kind of thing a
hand-rolled groupby gets subtly wrong -- a wrong denominator, or weighting by P&L
instead of notional. ``compute_treasury_cost_attribution`` delegates to the audited
``quanttools`` group-contribution primitive. See ``references/capitaltools_api.md``.

Install
-------
``treasuryutils[capital]``

Run
---
``python examples/07_treasury_cost_attribution.py``

Expected output (deterministic)
-------------------------------
    === Treasury cost attribution + period waterfall ===

    Positions (deal_id, entity, instrument, ccy, notional):
      D1  FUNDING_DESK  NTNF      BRL   5,000,000
      D2  FUNDING_DESK  LTN       BRL   3,000,000
      D3  TREASURY_BR   NTNF      BRL   2,000,000
      D4  TREASURY_BR   LFT       BRL   8,000,000
      D5  TREASURY_BR   USD_BOND  USD   1,000,000
      total notional = 19,000,000

    P&L attribution (deal_id, pnl_total):
      D1 -10,000   D2 -5,000   D3 -8,000   D4 -1,500   D5 +2,000

    Notional-weighted cost contribution by entity:
      FUNDING_DESK     -3,421.05
      TREASURY_BR      -1,368.42
      (weighted total = -4,789.47)

    By instrument_type:
      LFT                -631.58
      LTN                -789.47
      NTNF             -3,473.68
      USD_BOND            105.26

    By currency:
      BRL              -4,894.74
      USD                105.26
      (every dimension reconciles to the weighted total: currency=-4,789.47, instrument=-4,789.47)

    Period waterfall (prior + delta = current):
      carry      50,000.00  ->  55,000.00   (delta  +5,000.00)
      rates     -20,000.00  -> -28,000.00   (delta  -8,000.00)
      fx          3,000.00  ->   1,500.00   (delta  -1,500.00)
      net total  33,000.00  ->  28,500.00   (delta  -4,500.00)
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from treasuryutils.capitaltools.attribution import (
    build_period_waterfall,
    compute_treasury_cost_attribution,
)


def _positions() -> pl.DataFrame:
    """A 5-instrument book. Required: deal_id, notional + the group_by columns."""
    return pl.DataFrame(
        {
            'deal_id': ['D1', 'D2', 'D3', 'D4', 'D5'],
            'entity_id': [
                'FUNDING_DESK',
                'FUNDING_DESK',
                'TREASURY_BR',
                'TREASURY_BR',
                'TREASURY_BR',
            ],
            'instrument_type': ['NTNF', 'LTN', 'NTNF', 'LFT', 'USD_BOND'],
            'currency': ['BRL', 'BRL', 'BRL', 'BRL', 'USD'],
            'notional': [5_000_000.0, 3_000_000.0, 2_000_000.0, 8_000_000.0, 1_000_000.0],
        }
    )


def _pnl_attribution() -> pl.DataFrame:
    """P&L decomposition keyed by deal_id. Required: deal_id, pnl_total."""
    return pl.DataFrame(
        {
            'deal_id': ['D1', 'D2', 'D3', 'D4', 'D5'],
            'pnl_total': [-10_000.0, -5_000.0, -8_000.0, -1_500.0, 2_000.0],
        }
    )


def _print_attribution(title: str, result: pl.DataFrame) -> None:
    """Print an attribution result as ASCII (never print the DataFrame directly)."""
    print(title)
    for row in result.sort('group_value').iter_rows(named=True):
        print(f'  {row["group_value"]:<14} {row["cost_contribution"]:>12,.2f}')


def main() -> None:
    print('=== Treasury cost attribution + period waterfall ===\n')

    positions = _positions()
    pnl = _pnl_attribution()
    ref_date = dt.date(2024, 6, 30)

    print('Positions (deal_id, entity, instrument, ccy, notional):')
    for row in positions.iter_rows(named=True):
        print(
            f'  {row["deal_id"]}  {row["entity_id"]:<12}  {row["instrument_type"]:<8}  '
            f'{row["currency"]}  {row["notional"]:>11,.0f}'
        )
    print(f'  total notional = {positions["notional"].sum():,.0f}\n')

    pnl_cells = '   '.join(
        f'{d} {p:+,.0f}' for d, p in zip(pnl['deal_id'], pnl['pnl_total'], strict=True)
    )
    print(f'P&L attribution (deal_id, pnl_total):\n  {pnl_cells}\n')

    # --- Cost attribution across the three supported dimensions ---------------
    by_entity = compute_treasury_cost_attribution(
        pnl, positions, group_by='entity_id', ref_date=ref_date
    )
    by_instrument = compute_treasury_cost_attribution(pnl, positions, group_by='instrument_type')
    by_currency = compute_treasury_cost_attribution(pnl, positions, group_by='currency')

    weighted_total = float(by_entity['cost_contribution'].sum())
    _print_attribution('Notional-weighted cost contribution by entity:', by_entity)
    print(f'  (weighted total = {weighted_total:,.2f})\n')
    _print_attribution('By instrument_type:', by_instrument)
    print()
    _print_attribution('By currency:', by_currency)

    # The group contributions reconcile to the same weighted total in EVERY
    # dimension (the accounting identity the primitive guarantees) -- the by-currency
    # and by-instrument sums equal the by-entity weighted total above.
    print(
        f'  (every dimension reconciles to the weighted total: '
        f'currency={float(by_currency["cost_contribution"].sum()):,.2f}, '
        f'instrument={float(by_instrument["cost_contribution"].sum()):,.2f})'
    )

    # --- Period-over-period waterfall (wide-format component columns) ---------
    prior = pl.DataFrame({'carry': [50_000.0], 'rates': [-20_000.0], 'fx': [3_000.0]})
    current = pl.DataFrame({'carry': [55_000.0], 'rates': [-28_000.0], 'fx': [1_500.0]})
    waterfall = build_period_waterfall(current, prior)

    # Each component's bridge identity (prior + delta == current) holds by construction.
    print('\nPeriod waterfall (prior + delta = current):')
    for row in waterfall.iter_rows(named=True):
        prior_v, delta, current_v = row['prior_value'], row['delta'], row['current_value']
        print(
            f'  {row["component"]:<9} {prior_v:>11,.2f}  -> {current_v:>11,.2f}'
            f'   (delta {delta:>+11,.2f})'
        )
    net_prior = float(waterfall['prior_value'].sum())
    net_current = float(waterfall['current_value'].sum())
    print(
        f'  net total {net_prior:>11,.2f}  -> {net_current:>11,.2f}'
        f'   (delta {net_current - net_prior:>+11,.2f})'
    )


if __name__ == '__main__':
    main()
