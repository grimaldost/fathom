"""CDI / DI Pre yield curve: build a term structure and present-value a note.

Scenario
--------
A Brazilian treasury desk has the DI Pre term structure (annualized rates at a set of
business-day tenors) and needs two things from it: discount factors at any horizon, and
the present value of a note's cashflows.

What this demonstrates
----------------------
- The **real Stone flow**: a ``CdiCurve`` reads the bound ``di_pre`` curve (derived from the
  ``di_curve`` BigQuery source) and the ``cdi_accumulated`` index (from ``cdi_daily``) via a
  ``DatatoolsMarketDataSource``, with the maintained ``calendar_brazil``.
- Querying the curve: ``get_rate`` (annualized spot yield) and ``get_discount_factor``.
- Present-valuing a set of cashflows: ``PV = sum(CF * DF)``.
- Why curve node maturities must be calendar-aligned (business-day offsets), so the
  curve's BUS/252 day count reproduces the quoted rates.

Dual-mode
---------
The example LEADS with the live Stone read: it materializes ``di_pre`` (the full
historical term-structure surface -- a heavy first build) and ``cdi_accumulated``, then
reads them through a ``DatatoolsMarketDataSource``. If the bound sources / auth / calendar
data are not reachable, it prints the recovery steps and falls back to a self-contained
``InMemoryMarketDataSource`` with synthetic nodes so the curve math still runs. Set
``TU_EXAMPLES_OFFLINE=1`` to force the synthetic path (deterministic, no credentials, no
build) -- the smoke test does this.

treasuryutils APIs
------------------
- ``treasuryutils.financialtools.curves.CdiCurve`` -> ``get_rate`` / ``get_discount_factor``
- ``treasuryutils.financialtools.market_data.DatatoolsMarketDataSource`` (live: ``di_pre`` +
  ``cdi_accumulated``) / ``InMemoryMarketDataSource`` (synthetic fallback)
- ``treasuryutils.calendartools.add_workdays`` (calendar-aligned node maturities)

Why treasuryutils, not hand-rolled
----------------------------------
A CDI curve is not just interpolation: the x-axis is BUS/252 business-day time, the
discount factors compound on the Brazilian calendar, and a rate quoted at "252 business
days" only round-trips if the maturity date really is 252 business days out. ``CdiCurve``
ties the day count, interpolation, and calendar together so a quoted rate and its
discount factor are consistent. See ``references/financialtools_api.md``.

Install
-------
``treasuryutils[pricing]`` (plus ``treasuryutils[datatools]`` for the live path)

Run
---
``python examples/02_cdi_curve_and_pricing.py``            (live Stone, synthetic fallback)
``TU_EXAMPLES_OFFLINE=1 python examples/02_cdi_curve_and_pricing.py``   (synthetic only)

Expected output (synthetic / offline path, deterministic)
---------------------------------------------------------
    === CDI / DI Pre curve (as of 2024-02-15, source=synthetic) ===

    Term structure (calendar-aligned business-day tenors):
       21bd  ->  2024-03-15   quoted=10.20%   get_rate=10.2000%   DF=0.991939
       ...
    Present value of a note (1,000,000 notional):
      ...
      -> PV = 993,850.86
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import polars as pl
from _support import BRAZIL_HOLIDAYS, business_calendar, stone_or_synthetic

from treasuryutils.calendartools import add_workdays, to_pydate
from treasuryutils.datatools import DatasetClient
from treasuryutils.financialtools.curves import CdiCurve
from treasuryutils.financialtools.domain.identifiers import CompoundingType
from treasuryutils.financialtools.market_data import (
    CurveDatasetSpec,
    DatatoolsMarketDataSource,
    IndexDatasetSpec,
    InMemoryMarketDataSource,
)

if TYPE_CHECKING:
    from treasuryutils.calendartools import Calendar

REF_DATE = date(2024, 2, 15)
TENORS_BD = [21, 63, 126, 252, 504]
QUOTED_RATES = [0.1020, 0.1060, 0.1090, 0.1110, 0.1130]
CALENDAR_NAME = 'calendar_brazil'


def _synthetic_market_data(maturities: list[date]) -> InMemoryMarketDataSource:
    """Assemble synthetic DI Pre term-structure nodes and a realized-CDI index.

    Same canonical shape as the bound ``di_pre`` / ``cdi_accumulated`` datasets the live
    ``DatatoolsMarketDataSource`` reads, so the curve code path is identical.
    """
    curve_nodes = pl.DataFrame(
        {
            'ref_date': [REF_DATE] * len(TENORS_BD),
            'maturity_date': maturities,
            'duration_bd': TENORS_BD,
            'rate_annual': QUOTED_RATES,
        }
    )
    index_dates = pl.date_range(date(2024, 1, 1), REF_DATE, '1d', eager=True)
    accumulated = pl.DataFrame(
        {
            'ref_date': index_dates,
            'cumulated_overnight_rate': [1.0 + 0.00035 * i for i in range(len(index_dates))],
        }
    )
    return InMemoryMarketDataSource(
        datasets={'di_pre': curve_nodes, 'di_accumulated': accumulated},
        curve_specs={
            'di_pre': CurveDatasetSpec(
                dataset_name='di_pre',
                ref_date_col='ref_date',
                maturity_date_col='maturity_date',
                x_expr=(pl.col('duration_bd').cast(pl.Float64) / 252.0),
                y_col='rate_annual',
            )
        },
        index_specs={
            'cdi_accumulated': IndexDatasetSpec(
                dataset_name='di_accumulated',
                ref_date_col='ref_date',
                level_col='cumulated_overnight_rate',
            )
        },
    )


def _build_curve() -> tuple[CdiCurve, str | Calendar, str]:
    """Build a ``CdiCurve``, preferring live Stone data and falling back to synthetic."""

    def _real() -> tuple[CdiCurve, str | Calendar]:
        # The DatatoolsMarketDataSource reader serves derived datasets from the cache; it
        # does not build them. So materialize the curve inputs first from their real Stone
        # sources: di_pre <- di_curve (BigQuery / gcp-identity) + calendar_brazil, and
        # cdi_accumulated <- cdi_daily (BigQuery / gcp-identity). di_pre is the full
        # historical term-structure surface, so this first build is the heavy step;
        # later runs serve it from cache. A missing binding / auth / calendar file makes
        # this raise a fail-closed error here, and we fall back.
        covers = (date(2024, 1, 2), date(2024, 3, 1))
        for dataset in ('di_pre', 'cdi_accumulated'):
            DatasetClient(dataset, update_on_start=True).get(covers=covers)
        curve = CdiCurve(market_data=DatatoolsMarketDataSource(), calendar=CALENDAR_NAME)
        probe_maturity = to_pydate(add_workdays(REF_DATE, TENORS_BD[0], calendar=CALENDAR_NAME))
        curve.get_discount_factor(REF_DATE, probe_maturity)
        return curve, CALENDAR_NAME

    def _synthetic() -> tuple[CdiCurve, str | Calendar]:
        calendar = business_calendar(
            'demo_brazil', date(2023, 12, 1), date(2026, 6, 1), BRAZIL_HOLIDAYS
        )
        maturities = [
            to_pydate(add_workdays(REF_DATE, tenor, calendar=calendar)) for tenor in TENORS_BD
        ]
        curve = CdiCurve(market_data=_synthetic_market_data(maturities), calendar=calendar)
        return curve, calendar

    (curve, calendar), mode = stone_or_synthetic(
        'CDI / DI-Pre curve + calendar_brazil',
        _real,
        _synthetic,
        recovery=[
            'doctor: `python -m treasuryutils.datatools doctor` (or `config_status()`)',
            "BigQuery di_curve needs auth profile 'gcp-identity' -> use the auth-setup skill",
            'calendar_brazil needs the holidays_brazil parquet reachable '
            '(set BASE_DATA_PATH / allow_outside_base)',
            'or rebind di_pre / cdi to sources you can reach (setup-source-bindings skill)',
        ],
    )
    return curve, calendar, mode


def main() -> None:
    curve, calendar, mode = _build_curve()

    # Node maturities are real business-day offsets, or the BUS/252 day count would not
    # reproduce the quoted rates (see the module docstring).
    maturities = [
        to_pydate(add_workdays(REF_DATE, tenor, calendar=calendar)) for tenor in TENORS_BD
    ]

    print(f'=== CDI / DI Pre curve (as of {REF_DATE.isoformat()}, source={mode}) ===\n')
    print('Term structure (calendar-aligned business-day tenors):')
    for tenor, maturity, quoted in zip(TENORS_BD, maturities, QUOTED_RATES, strict=True):
        spot = float(
            curve.get_rate(REF_DATE, maturity, compounding=CompoundingType.DISCRETE_ANNUAL)
        )
        discount = float(curve.get_discount_factor(REF_DATE, maturity))
        if mode == 'synthetic':
            print(
                f'  {tenor:>3}bd  ->  {maturity.isoformat()}   quoted={quoted:.2%}   '
                f'get_rate={spot:.4%}   DF={discount:.6f}'
            )
        else:
            print(
                f'  {tenor:>3}bd  ->  {maturity.isoformat()}   '
                f'get_rate={spot:.4%}   DF={discount:.6f}'
            )

    # Present value of a note: a 50,000 coupon at ~3 months, principal + coupon at ~1 year.
    cashflows = [(maturities[1], 50_000.0), (maturities[3], 1_050_000.0)]
    print('\nPresent value of a note (1,000,000 notional):')
    present_value = 0.0
    for pay_date, amount in cashflows:
        discount = float(curve.get_discount_factor(REF_DATE, pay_date))
        tenor = TENORS_BD[maturities.index(pay_date)]
        contribution = amount * discount
        present_value += contribution
        print(
            f'  {amount:<10,.0f} at {pay_date.isoformat()} ({tenor}bd)   '
            f'x DF {discount:.6f}  = {contribution:>13,.2f}'
        )
    print(f'  -> PV = {present_value:,.2f}')


if __name__ == '__main__':
    main()
