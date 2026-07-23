# treasuryutils examples

Six recommended runnable scripts (plus two in-development examples, 07–08, noted below)
that show how to use `treasuryutils` for real treasury and portfolio tasks. Each script
is a single file with a docstring that states the scenario, the exact public APIs it
calls, why the library beats a hand-rolled version, the install extras it needs, and its
expected output.

These double as demonstrations for the `treasuryutils-usage` skill: when a task matches
one of the scenarios below, read the matching example for a worked, end-to-end pattern
before writing new code.

## The examples

| # | File | Scenario | Key APIs | Runs |
|---|------|----------|----------|------|
| 01 | [`01_data_access_and_bindings.py`](01_data_access_and_bindings.py) | Doctor-first data access; fail-closed reads; what to do when a read fails | `config_status`, `DatasetClient.get(covers=...)`, `SourceExtractionError`/`PipelineExecutionError` | needs setup* |
| 02 | [`02_cdi_curve_and_pricing.py`](02_cdi_curve_and_pricing.py) | Build a CDI/DI Pre yield curve and present-value a note | `CdiCurve`, `InMemoryMarketDataSource`, `add_workdays` | anywhere |
| 03 | [`03_ifrs9_ecl.py`](03_ifrs9_ecl.py) | IFRS 9: effective interest rate, three-stage ECL, simplified provision matrix | `solve_eir`, `compute_ecl_for_instrument`, `compute_simplified_ecl` | anywhere |
| 04 | [`04_portfolio_risk.py`](04_portfolio_risk.py) | Covariance → parametric VaR / Expected Shortfall → risk parity | `estimate_ledoit_wolf_covariance`, `compute_portfolio_risk`, `optimize` | anywhere |
| 05 | [`05_cashflow_calendar.py`](05_cashflow_calendar.py) | Business-day settlement, accrual, and BUS/252 year fractions | `add_workdays`, `net_workdays`, `year_fraction`, `Calendar` | anywhere |
| 06 | [`06_asof_aggregation.py`](06_asof_aggregation.py) | Point-in-time aggregation over SCD-2 position validity intervals | `asof_aggregate`, `WindowSpec`, `WeightedAvgMeasure`, `SumMeasure` | anywhere |

\* Example 01 deliberately runs against the default, *unbound* configuration to show the
fail-closed behavior and recovery routing — it exits cleanly and prints what to do next.
The other five are fully self-contained: they synthesize their own inputs and produce
real output with no data setup.

> **`capitaltools` and `equitytools` are under active development.** The directory also
> contains `07_treasury_cost_attribution.py` (`capitaltools`) and
> `08_equity_factor_features.py` (`equitytools`); they are intentionally **not** listed
> above and are not recommended for general use yet. Use them only if you are working
> directly with those modules.

## Running them

Each script is standalone — run it directly. `examples/04_portfolio_risk.py` is rooted at
the plugin root (`plugins/treasuryutils-consumer/`), so run from there:

```bash
python examples/04_portfolio_risk.py
# or, from this directory:
python 04_portfolio_risk.py
```

In a uv-managed checkout, prefer `uv run python` (mirroring the example docstrings) so the
interpreter resolves `treasuryutils` — bare `python` may not see it without an active venv:

```bash
uv run python examples/04_portfolio_risk.py
```

Install the extras named in the script's docstring (e.g. `treasuryutils[quant-math]` for
example 04). `treasuryutils[all]` covers every example.

> **Windows tip:** these examples print plain ASCII, but if *your own* script prints a
> Polars DataFrame, set `PYTHONIOENCODING=utf-8` — the default `cp1252` console cannot
> render Polars' box-drawing characters and will raise `UnicodeEncodeError`.

## A note on `_support.py`

[`_support.py`](_support.py) is **scaffolding, not a lesson**. Examples 02 and 05 need a
business-day calendar; in production you load one with `get_calendar('calendar_brazil')`
from a bound DataTools source (see the `setup-source-bindings` skill). `_support.py`
builds a small calendar in memory instead, so those examples run with no data setup. It
is kept out of the example bodies on purpose, so each example shows the library API rather
than the plumbing.
