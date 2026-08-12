Users of the `daycal` package report that `report.hours_in_day(date(2026, 3, 8))`
returns `24.0`. Per the package README that local day is 23 hours long — the clock
moves at local midnight on 2026-03-09. Find and fix the bug so the package behaves
as documented for every day of the year. Preserve the existing public API, and keep
the shipped test suite passing.
