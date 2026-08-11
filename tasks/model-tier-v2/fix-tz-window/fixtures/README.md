# daycal

Local-day arithmetic for a scheduler. All instants are **UTC minute stamps**:
whole minutes since 0001-01-01T00:00Z, so they can be compared and subtracted
without a date library.

## The local clock

`tz.offset_minutes(local_day)` gives the UTC offset in force from local midnight of
that day. This deployment runs one hour ahead of standard time from 2026-03-09
through 2026-11-01 and on standard time otherwise. **The clock changes at local
midnight**, so the local day before a change is one hour short and the local day
that ends at a change is one hour long: 2026-03-08 is a 23-hour day and 2026-11-01
is a 25-hour day. Every other day is 24 hours.

## Day windows

A local day runs from its own local midnight to the **next** local midnight.

- `window.local_midnight_utc(local_day)` — the UTC minute stamp of local midnight
  at the start of that day.
- `window.day_window(local_day)` — `(start, end)`, the UTC minute stamps bounding
  the local day. Consecutive windows tile the calendar exactly: the end of one day
  is the start of the next, with no gap and no overlap.
- `report.hours_in_day(local_day)` — how many hours long that local day is.
- `report.slots(local_day, count)` — the local day split into `count` equal,
  contiguous slots that together cover exactly the day's window.

Run the tests: `python -m unittest discover -s tests -t .`
