# Troubleshooting — silent divergence that survives a cache rebuild

Escalation path for the **"Silent divergence — suspect a stale cache first"** section of the
`treasuryutils-usage` skill. Use this **only after** you have already run the remedy there
(`cache clear <derived>` + its leaves → `ensure_fresh(full_refresh='recursive')` → `cache smoke`)
and the values are **still** wrong. At that point the cause is no longer a transient stale cache —
it is either the **source data itself** (e.g. a tz-aware `date` column that shifts a day under a
non-UTC session) or a genuine **build bug** — and the fix belongs to the maintainer.

Don't keep guessing. Run the diagnostic below and paste its **whole output** into the
treasuryutils issue/report. It is **read-only, secret-free, and non-mutating**: it reads the source
file and the cached DuckDB table directly and never calls `is_workday()` / `.get()` (those go
through `DatasetClient.get()`, which evaluates provenance + dependency freshness and can trigger a
rebuild that *masks* the very value you are trying to capture). **Run it under the same session
timezone your builds use** — a UTC session (common in CI containers) can hide a tz-shift.

## The diagnostic

```python
# tu_calendar_diagnostic.py -- READ-ONLY, secret-free, non-mutating.
# Run AFTER a `cache clear` + recursive rebuild that did NOT fix the divergence, and under the
# SAME session timezone your builds use. Paste the whole output into the treasuryutils report.
import datetime as dt
import os
import platform
import sys
import traceback

CAL, LEAF = "calendar_brazil", "holidays_brazil"  # the calendar in question + its leaf source
PROBE = dt.date(2025, 1, 1)  # <-- set to the date that diverges for YOU
CONTROL = {dt.date(2025, 1, 1): False, dt.date(2024, 12, 31): True, dt.date(2025, 12, 25): False}

import treasuryutils

print("== env ==")
print("treasuryutils:", getattr(treasuryutils, "__version__", "?"), "| python:", sys.version.split()[0])
print("platform:", platform.platform(), "| session tz:", dt.datetime.now().astimezone().tzname())

print("\n== SOURCE: dtype + raw value vs CAST(date AS DATE) -- the discriminator ==")
try:
    from treasuryutils.datatools import DatasetClient

    cfg = (DatasetClient(LEAF).meta or {}).get("source") or {}
    cfg = cfg[0] if isinstance(cfg, list) and cfg else cfg
    conf = cfg.get("config") or {}
    raw_path = conf.get("path")
    print("source.type:", cfg.get("type"), "| raw path:", raw_path)
    if raw_path:
        import duckdb
        import polars as pl

        try:  # datatools-facing re-export; fall back to the defining module
            from treasuryutils.datatools._path_security import resolve_data_path
        except ImportError:
            from treasuryutils.datatools._shared.path_security import resolve_data_path

        path = str(resolve_data_path(raw_path, allow_outside_base=True))  # resolve like the builder
        print("resolved path:", path)
        print("polars date dtype:", pl.read_parquet(path).schema.get("date"),
              "(tz-aware => shift risk; naive => safe)")
        con = duckdb.connect(":memory:")
        print("duckdb typeof(date):",
              con.execute(f"SELECT typeof(date) FROM read_parquet('{path}') LIMIT 1").fetchone()[0])
        lo, hi = PROBE - dt.timedelta(days=3), PROBE + dt.timedelta(days=2)
        rows = con.execute(
            f"SELECT date AS raw, CAST(date AS DATE) AS cast_date FROM read_parquet('{path}') "
            f"WHERE date BETWEEN TIMESTAMP '{lo}' AND TIMESTAMP '{hi}' ORDER BY 1"
        ).fetchall()
        print(f"rows near {PROBE} (raw value | after CAST):")
        for raw, cast_date in rows:
            print(f"  {raw!r}  ->  {cast_date.isoformat()}")
        print("tell: a raw wall-clock earlier than midnight / a non-UTC zone in tzinfo, AND a CAST a "
              "day earlier => tz-aware source shifting under this session")
    else:
        print("(leaf is not a `file` source -> the tz-shift discriminator does not apply; "
              "send the CACHE block + the dataset's source type)")
except Exception:  # noqa: BLE001
    print("!! SOURCE block failed -- this is a diagnostic-script error, not a data finding:")
    traceback.print_exc()

print("\n== CACHE: served values + build provenance (read directly, no refresh) ==")
try:
    import duckdb

    from treasuryutils.datatools import DatasetClient
    from treasuryutils.datatools.cache.paths import duckdb_db_path, resolve_root

    db = duckdb_db_path(resolve_root(os.environ.get("DATATOOLS__DATA_CACHE_DIR")))
    print("lakehouse duckdb:", db, "| exists:", db.exists())
    if db.exists():
        con = duckdb.connect(str(db), read_only=True)
        tbl = DatasetClient(CAL).cache_table_name  # physical table (== CAL unless cache_table_name is set)
        print(f"cached table: data.{tbl} | date typeof:",
              con.execute(f"SELECT typeof(date) FROM data.{tbl} LIMIT 1").fetchone()[0])
        for d, exp in CONTROL.items():
            r = con.execute(f"SELECT is_workday FROM data.{tbl} WHERE date=DATE '{d}'").fetchone()
            got = r[0] if r else "ABSENT"
            print(f"  cached is_workday({d}) = {got}  expected {exp}  {'OK' if got == exp else 'WRONG'}")
        try:  # provenance in its own guard so a failure here doesn't hide the served values above
            print("build provenance:", con.execute(
                "SELECT dataset_name, last_updated, build_binding_fingerprint FROM _dataset_state "
                f"WHERE dataset_name IN ('{CAL}','{LEAF}')").fetchall())
        except Exception:  # noqa: BLE001
            print("  (provenance read failed -- diagnostic-script error, not a data finding:)")
            traceback.print_exc()
except Exception:  # noqa: BLE001
    print("!! CACHE block failed -- this is a diagnostic-script error, not a data finding:")
    traceback.print_exc()

print("\n== END -- paste all of the above into the report (no secrets included) ==")
```

Set `CAL` / `LEAF` to the calendar you are debugging and its leaf (e.g. `calendar_us` /
`holidays_us`), and `PROBE` to the date that diverges for you. It needs the same extras your project
already uses (`polars`, `duckdb` — both come with the `datatools` extra), **not** the `cli` extra.

## How to read the output — it routes the cause

The `SOURCE` block is the discriminator. Two branches (run under a **non-UTC** session — a UTC
session hides the shift):

**Branch A — the SOURCE is the cause (tz-aware date shifted by the session TZ).**

```
== SOURCE: dtype + raw value vs CAST(date AS DATE) -- the discriminator ==
polars date dtype: Datetime(time_unit='ns', time_zone='UTC') (tz-aware => shift risk; naive => safe)
duckdb typeof(date): TIMESTAMP WITH TIME ZONE
rows near 2025-01-01 (raw value | after CAST):
  datetime.datetime(2024, 12, 31, 21, 0, tzinfo=zoneinfo.ZoneInfo(key='America/Sao_Paulo'))  ->  2024-12-31
```

The source `date` is **tz-aware** (stored UTC midnight). Under a UTC-3 session DuckDB returns it
converted to the session zone — a `21:00` wall-clock on the **previous** day — and `CAST(... AS
DATE)` lands on `2024-12-31`. That shift then propagates into the derived calendar. (Under a **UTC**
session the same value reads as `2025-01-01 00:00 UTC` and does **not** shift — which is why you
must run this under the session your builds use.) **Fix is source-side / library-side:** rewrite the
source parquet with **tz-naive** dates, or the calendar builder must normalize the holiday `date` to
a tz-naive `DATE` before the join. Send this output — it names the exact cause.

**Branch B — the SOURCE is fine, so it's a build/cache bug.**

```
== SOURCE: dtype + raw value vs CAST(date AS DATE) -- the discriminator ==
polars date dtype: Datetime(time_unit='ns', time_zone=None) (tz-aware => shift risk; naive => safe)
duckdb typeof(date): TIMESTAMP_NS
rows near 2025-01-01 (raw value | after CAST):
  datetime.datetime(2025, 1, 1, 0, 0)  ->  2025-01-01                # <- naive, no shift
== CACHE: served values + build provenance ...
  cached is_workday(2025-01-01) = True  expected False  WRONG        # <- still wrong after a rebuild
build provenance: [('calendar_brazil', datetime.datetime(...recent...), '...')]
```

The source is **naive** and `CAST` is correct, yet the freshly-rebuilt cache still serves a wrong
value. That points at the **build logic**, not the data — a genuine bug. The `build provenance`
`last_updated` substantiates that this is the rebuilt output (not a stale serve). Send this output.

If instead the cached values are all `OK`, the divergence you saw earlier was a stale cache that the
rebuild already fixed — no report needed.

> **Note on the shipped Brazil calendar.** `holidays_brazil` already `CAST(date AS DATE)` in its own
> source query, so its built column is naive and any tz shift is baked in at **build** time under the
> build session's TZ (not at read time). Branch A therefore bites a **custom/rebound** holiday source
> that does *not* pre-cast, or a build that ran under a non-UTC session — for the shipped contract the
> decisive evidence is the CACHE block's served values, not the SOURCE probe.

**No secrets are printed** — only the source *path*, dtypes, public dates, and a non-secret build
fingerprint. Do not add credential values before sending.
