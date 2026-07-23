"""Shared scaffolding for the examples -- NOT part of any lesson.

Several examples need a business-day calendar. In production you do **not** build one
by hand: ``get_calendar('calendar_brazil')`` loads the maintained holiday set from a
bound DataTools source (see the ``setup-source-bindings`` skill). The helpers here
construct a small calendar entirely in memory so the examples run with no data setup.

These functions only assemble inputs for treasuryutils; they are deliberately kept out
of the example bodies so each example shows the library API, not the plumbing.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import TYPE_CHECKING, TypeVar

import polars as pl

from treasuryutils.calendartools import Calendar
from treasuryutils.datatools import (
    CoverageError,
    PipelineExecutionError,
    SourceAccessError,
    SourceExtractionError,
)
from treasuryutils.dtypes import DEFAULT_TIME_UNIT
from treasuryutils.financialtools.market_data import MarketDataError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_T = TypeVar('_T')

# The fail-closed data-access errors a live Stone read can raise (the taxonomy the
# treasuryutils-usage skill documents). Hitting one is expected when auth / source
# bindings / data files are not yet wired, so the examples catch exactly these, fall
# back to synthetic data, and print the recovery steps -- never a raw traceback.
_STONE_DATA_ERRORS: tuple[type[Exception], ...] = (
    SourceExtractionError,
    PipelineExecutionError,
    SourceAccessError,
    CoverageError,
    MarketDataError,
)

# Set TU_EXAMPLES_OFFLINE=1 to skip the live-Stone read and go straight to synthetic data.
# The smoke test sets it so example output stays deterministic without credentials; humans
# leave it unset to exercise the real flow against bound Stone sources.
EXAMPLES_OFFLINE: bool = os.getenv('TU_EXAMPLES_OFFLINE', '') not in ('', '0', 'false', 'False')

# A representative subset of Brazilian national holidays (2024 + New Year 2025).
BRAZIL_HOLIDAYS = frozenset(
    {
        date(2024, 1, 1),  # New Year
        date(2024, 2, 12),  # Carnival Monday
        date(2024, 2, 13),  # Carnival Tuesday
        date(2024, 3, 29),  # Good Friday
        date(2024, 4, 21),  # Tiradentes
        date(2024, 5, 1),  # Labour Day
        date(2024, 5, 30),  # Corpus Christi
        date(2024, 9, 7),  # Independence
        date(2024, 10, 12),  # Our Lady of Aparecida
        date(2024, 11, 2),  # All Souls
        date(2024, 11, 15),  # Republic
        date(2024, 12, 25),  # Christmas
        date(2025, 1, 1),  # New Year
    }
)


def business_calendar(name: str, start: date, end: date, holidays: frozenset[date]) -> Calendar:
    """Build a validated ``Calendar`` from a holiday set.

    Mirrors the table ``get_calendar('calendar_brazil')`` loads from a bound source: one
    row per calendar day with the workday flag plus the pre-computed next/last workday
    and cumulative workday index that the calendar backends use for O(1) lookups.
    """
    dates = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    is_wd = [day.weekday() < 5 and day not in holidays for day in dates]
    workdays = [day for day, flag in zip(dates, is_wd, strict=True) if flag]
    num_by_date = {day: index for index, day in enumerate(workdays)}

    last_wd: list[date | None] = []
    next_wd: list[date | None] = []
    wd_num: list[int | None] = []
    last_num: list[int | None] = []
    next_num: list[int | None] = []
    for day, flag in zip(dates, is_wd, strict=True):
        if flag:
            last_wd.append(day)
            next_wd.append(day)
            wd_num.append(num_by_date[day])
            last_num.append(num_by_date[day])
            next_num.append(num_by_date[day])
        else:
            before = [w for w in workdays if w <= day]
            after = [w for w in workdays if w >= day]
            prev_wd = before[-1] if before else None
            following_wd = after[0] if after else None
            last_wd.append(prev_wd)
            next_wd.append(following_wd)
            wd_num.append(None)
            last_num.append(num_by_date[prev_wd] if prev_wd is not None else None)
            next_num.append(num_by_date[following_wd] if following_wd is not None else None)

    def _dt(values: list[date | None] | list[date]) -> pl.Series:
        return pl.Series(values).cast(pl.Datetime(time_unit=DEFAULT_TIME_UNIT))

    frame = pl.DataFrame(
        {
            'date': _dt(dates),
            'is_workday': is_wd,
            'last_workday': _dt(last_wd),
            'next_workday': _dt(next_wd),
            'workday_num': wd_num,
            'last_workday_num': last_num,
            'next_workday_num': next_num,
        }
    )
    return Calendar(frame, name=name)


def stone_or_synthetic(
    what: str,
    real: Callable[[], _T],
    synthetic: Callable[[], _T],
    *,
    recovery: Sequence[str],
) -> tuple[_T, str]:
    """Build from a live Stone source, falling back to synthetic data on a data-access failure.

    Returns ``(value, mode)`` where ``mode`` is ``'stone'`` or ``'synthetic'``. The dual-mode
    examples LEAD with the real flow (bound sources + auth) and degrade gracefully so they
    always run and teach the recovery path. Honors ``TU_EXAMPLES_OFFLINE``; on a fail-closed
    data error the ``recovery`` lines are printed before falling back.
    """
    if EXAMPLES_OFFLINE:
        print(f'[offline] {what}: TU_EXAMPLES_OFFLINE set -> using synthetic data')
        return synthetic(), 'synthetic'
    try:
        value = real()
    except _STONE_DATA_ERRORS as exc:
        detail = next((line for line in str(exc).splitlines() if line.strip()), type(exc).__name__)
        print(f'[fallback] {what}: live Stone read unavailable -> synthetic data')
        print(f'    {type(exc).__name__}: {detail}')
        for line in recovery:
            print(f'    - {line}')
        return synthetic(), 'synthetic'
    print(f'[stone] {what}: read from a live Stone source')
    return value, 'stone'
