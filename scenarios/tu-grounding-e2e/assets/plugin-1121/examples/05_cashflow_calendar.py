"""Business-day calendars: settlement dates, accrual periods, and BUS/252 year fractions.

Scenario
--------
A Brazilian treasury desk settles trades T+2 *business* days and accrues interest on
the BUS/252 convention (business days / 252). Both depend on a holiday calendar:
Carnival, Corpus Christi, and the national holidays are non-workdays, so plain
calendar-day arithmetic gives the wrong settlement date and the wrong accrual.

What this demonstrates
----------------------
- ``is_workday`` -- is a date a business day on this calendar?
- ``add_workdays`` -- T+2 settlement that rolls over holidays and weekends.
- ``net_workdays`` -- business days elapsed between two dates (the accrual count).
- ``year_fraction`` with ``DayCountConvention.BUS_252`` -- the Brazilian day count.
- Loading the maintained calendar with ``get_calendar('calendar_brazil')``.

Dual-mode
---------
This LEADS with the maintained calendar: ``get_calendar('calendar_brazil')`` loads the
holiday set from the bound ``holidays_brazil`` data. If that source is not reachable, it
prints the recovery steps and falls back to a small in-memory calendar so the example
still runs. Set ``TU_EXAMPLES_OFFLINE=1`` to force the synthetic calendar.

treasuryutils APIs
------------------
- ``treasuryutils.calendartools.get_calendar`` (the maintained ``calendar_brazil``)
- ``treasuryutils.calendartools.add_workdays`` / ``net_workdays`` / ``is_workday``
- ``treasuryutils.calendartools.year_fraction`` + ``DayCountConvention.BUS_252``

Why treasuryutils, not hand-rolled
----------------------------------
``numpy.busday_offset`` only knows weekday masks and a flat holiday list; it does not
give you BUS/252 year fractions, the roll conventions, or a validated calendar that
the pricing and accounting modules share. Mismatched calendars between settlement and
accrual are a classic silent error. See ``references/calendartools_api.md``.

Install
-------
``treasuryutils[calendartools]`` (plus ``treasuryutils[datatools]`` for the live calendar)

Run
---
``python examples/05_cashflow_calendar.py``            (live calendar_brazil, synthetic fallback)
``TU_EXAMPLES_OFFLINE=1 python examples/05_cashflow_calendar.py``   (synthetic only)

Expected output (synthetic / offline path, deterministic)
---------------------------------------------------------
    === Business-day calendar (Brazil, 2024, source=synthetic) ===

    Carnival Monday 2024-02-12 is a workday? False

    Settlement: a trade executes Thu 2024-02-08, settles T+2 business days
      -> settlement date = 2024-02-14   (Carnival Mon/Tue 2024-02-12..13 are skipped)

    Accrual: business days elapsed 2024-02-08 -> 2024-02-16
      -> 4 business days   (the weekend and the two Carnival holidays do not count)

    Day count: year_fraction(2024-01-02 -> 2024-07-01, BUS/252)
      -> 0.492063   (= 124 business days / 252)
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from _support import BRAZIL_HOLIDAYS, business_calendar, stone_or_synthetic

from treasuryutils.calendartools import (
    add_workdays,
    get_calendar,
    is_workday,
    net_workdays,
    to_pydate,
    year_fraction,
)
from treasuryutils.calendartools.day_count import DayCountConvention

if TYPE_CHECKING:
    from treasuryutils.calendartools import Calendar


def _resolve_calendar() -> tuple[Calendar, str]:
    """Load the maintained calendar_brazil, falling back to an in-memory calendar."""
    return stone_or_synthetic(
        'calendar_brazil',
        lambda: get_calendar('calendar_brazil'),
        lambda: business_calendar(
            'demo_brazil', date(2023, 12, 1), date(2024, 12, 31), BRAZIL_HOLIDAYS
        ),
        recovery=[
            'doctor: `python -m treasuryutils.datatools doctor` (or `config_status()`)',
            'calendar_brazil derives from holidays_brazil -- make that data reachable '
            '(set BASE_DATA_PATH / allow_outside_base, or bind it via setup-source-bindings)',
        ],
    )


def main() -> None:
    calendar, mode = _resolve_calendar()

    print(f'=== Business-day calendar (Brazil, 2024, source={mode}) ===\n')

    carnival_monday = date(2024, 2, 12)
    is_open = bool(is_workday(carnival_monday, calendar=calendar))
    print(f'Carnival Monday {carnival_monday.isoformat()} is a workday? {is_open}\n')

    trade_date = date(2024, 2, 8)
    settlement = add_workdays(trade_date, 2, calendar=calendar)
    settlement_day = to_pydate(settlement).isoformat()
    print(f'Settlement: a trade executes Thu {trade_date.isoformat()}, settles T+2 business days')
    print(
        f'  -> settlement date = {settlement_day}   (Carnival Mon/Tue 2024-02-12..13 are skipped)\n'
    )

    accrual_start, accrual_end = date(2024, 2, 8), date(2024, 2, 16)
    elapsed = int(net_workdays(accrual_start, accrual_end, calendar=calendar))
    print(
        f'Accrual: business days elapsed {accrual_start.isoformat()} -> {accrual_end.isoformat()}'
    )
    print(
        f'  -> {elapsed} business days   (the weekend and the two Carnival holidays do not count)\n'
    )

    yf_start, yf_end = date(2024, 1, 2), date(2024, 7, 1)
    yf = float(year_fraction(yf_start, yf_end, DayCountConvention.BUS_252, calendar=calendar))
    print(f'Day count: year_fraction({yf_start.isoformat()} -> {yf_end.isoformat()}, BUS/252)')
    print(f'  -> {yf:.6f}   (= {round(yf * 252)} business days / 252)')


if __name__ == '__main__':
    main()
