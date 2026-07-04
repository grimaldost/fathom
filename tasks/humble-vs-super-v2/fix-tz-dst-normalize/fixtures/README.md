# eastern

Convert US/Eastern wall-clock times to UTC.

- `to_utc(year, month, day, hour, minute=0)` — returns a UTC ISO-8601 `Z` timestamp.

US/Eastern is UTC-4 during daylight saving time and UTC-5 otherwise. US DST runs from
02:00 on the second Sunday of March to 02:00 on the first Sunday of November.

Run the tests: `python -m unittest discover -s tests -t .`
