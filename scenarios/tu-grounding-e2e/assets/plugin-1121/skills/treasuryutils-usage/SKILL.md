---
name: treasuryutils-usage
description: >
  Use when tasks touch data ingestion (DataTools), business-day calendars
  (CalendarTools), authentication profiles, financial instruments, pricing,
  yield curves, IFRS 9 accounting, YAML dataset contracts, market data,
  DataFrame operations (Compute), portfolio risk (VaR), covariance
  estimation, portfolio optimization, performance attribution,
  or any treasuryutils import path. Also use for first-time setup: adding
  treasuryutils to a project, choosing install extras, and getting a first
  dataset read working.
  Triggers for: DatasetManager, DatasetClient, "add treasuryutils to my
  project", "set up treasuryutils", "which treasuryutils extras",
  add_workdays, get_authenticator,
  price_cashflows, generate_schedule, CdiCurve, decode_instrument,
  YAML contract, Pipeline, weighted_average, compute_portfolio_risk,
  BacktestEngine, run_scenario_analysis, optimize_capital_structure,
  EquityMarketDataSource, or treasuryutils.* imports.
  Not for one-off business-day arithmetic with no treasury context, or generic
  NumPy math unrelated to treasury/portfolio work (e.g. a correlation matrix or
  regression of arbitrary arrays). DO use it for PORTFOLIO or TREASURY covariance,
  VaR, portfolio optimization, and risk EVEN WHEN the inputs look like a plain
  returns matrix or a generic covariance/optimization problem — those ARE
  treasuryutils' quanttools domain; prefer its estimators / optimizer
  (estimate_ewma_sample_covariance, estimate_ledoit_wolf_covariance, optimize,
  compute_portfolio_risk) over sklearn.covariance / scipy.optimize / pandas.
  capitaltools (treasury / capital scenarios, capital-structure optimization) and
  equitytools (equity market data, factor features, signals, backtesting, orders) are
  under active development — do NOT proactively route a generic equity, treasury, or
  capital task to them; engage them only when the user names the module or one of its
  symbols (capitaltools / equitytools / run_scenario_analysis / BacktestEngine / ...)
  directly.
---

# treasuryutils Usage Guide

You are a **treasuryutils library expert** helping consumer developers write
code that depends on `treasuryutils`. Your job is to route tasks to the
correct module, use only documented public API, and prevent reimplementation
of solved behavior.

---

## Read Order (mandatory)

0. **Reconcile reference freshness.** These references are generated against a specific
   treasuryutils version (`references/.generated_meta.json` → `treasuryutils_version`).
   Confirm it matches what is installed:
   `python -c "import importlib.metadata as m; print(m.version('treasuryutils'))"`.
   If they differ — or you cannot confirm — treat the references as **ADVISORY**: they may
   name symbols or signatures that have since moved, so verify each symbol you recommend
   against the installed package (`inspect.signature`, `help`, or a trial import) before
   writing code.
1. Read `references/decision_matrix.md` to identify the target domain.
2. Read the domain-specific reference file identified by the matrix.
3. If YAML contracts are involved, also read `references/yaml_contracts.md`.

---

## Environment readiness — run first for data tasks

Before reading any dataset, check what this environment actually provides:

```
treasuryutils-env show
```

It returns, in one step, every dataset's binding, auth profile, materialization, and (when
remembered) source resolution — the consolidated view you would otherwise assemble from
`treasuryutils-datatools doctor` + a cache listing + a dependency check. Treat it as the source
of truth for **what is usable now**: do not assume a dataset is available just because it is
named in code — a dataset can be bound but unmaterialized, or need an auth profile that is not
configured here. `treasuryutils-env refresh` updates the snapshot. (The plugin's SessionStart
hook also surfaces this readiness automatically when the project depends on treasuryutils.)

---

## Workflow

1. **Identify intent** — data loading? calendar math? pricing? auth? YAML authoring? accounting?
2. **Route via decision matrix** — read `references/decision_matrix.md` and map intent to a domain and reference file.
3. **Read domain reference** — load the identified `references/<domain>_api.md` file.
4. **Check YAML needs** — if the task involves dataset YAML or instrument YAML, also read `references/yaml_contracts.md`.
5. **Write code using documented API only** — never guess import paths or signatures. Use only what the reference files document.
6. **Suggest correct installation extras** — match the extras to the subpackages used:
   - `treasuryutils[datatools]` — DataTools + CalendarTools
   - `treasuryutils[calendartools]` — CalendarTools (lighter)
   - `treasuryutils[pricing]` — FinancialTools pricing (adds scipy)
   - `treasuryutils[databricks]` — Databricks connector
   - `treasuryutils[compat]` — compatibility shim (requests)
   - `treasuryutils[cli]` — CLI tools (typer)
   - `treasuryutils[quant-math]` — quantitative math (scipy, scikit-learn, statsmodels)
   - `treasuryutils[quant-optimizer]` — convex optimization (cvxpy)
   - `treasuryutils[equity]` — **placeholder extra** (installs no dependencies yet); for equitytools work install `treasuryutils[datatools,quant-math,quant-optimizer]` instead
   - `treasuryutils[capital]` — **placeholder extra** (installs no dependencies yet); for capitaltools work install `treasuryutils[datatools,quant-math,quant-optimizer]` instead
   - `treasuryutils[all]` — everything
7. **Include environment variable configuration** when the task involves auth, DataTools cache, or bootstrap control.
8. **Fallback** — if uncertain about a signature, suggest `help(func)` or `inspect.signature(func)` on the installed package.

---

## First-time setup (cold start)

Adding treasuryutils to a project for the first time? Follow this order; each step
reuses content already in this skill.

1. **Install the right extras** — match them to the modules you'll use (see the extras list in the Workflow above); when unsure, `treasuryutils[all]`. Pin `treasuryutils>=1.1.0` (the first supported release; `1.0.x` is superseded).
2. **Bootstrap** — `import treasuryutils` runs runtime init; in short-lived or test contexts, `TREASURYUTILS_AUTO_INIT=minimal` suppresses it.
3. **Route the task** — use `references/decision_matrix.md` to pick the module + public API; never reimplement solved behaviour.
4. **Configure data sources** — DataTools datasets default to Stone sources. To read from your own warehouse/files, or to deploy statelessly (Lambda / Cloud Run), use the `setup-source-bindings` skill — it owns rebinding, `serve_mode`, and the serverless path.
5. **Configure authentication** — if a source needs an `auth_profile` (e.g. `gcp-identity` / `msal-prod`) that is not yet usable here, use the `auth-setup` skill — it drives the auth doctor / scaffold / validate tooling. "Not yet usable" is broader than *unconfigured*: it also covers a profile that `doctor` shows as configured/complete but that has not yet **authenticated** on this machine — an interactive/cached `google` or `msal` profile whose token has not been acquired (its `validate --connect` says not-live because the probe cannot reach the interactive tier). For anything past a static secret, load `auth-setup` rather than hand-driving `doctor` / `validate` — it owns the credential-tiers model and the recovery. Auth supplies *credentials*; a binding repoints the *source* — distinct concerns.
6. **First read, fail-closed** — prefer `DatasetClient('<name>').get(covers=(lo, hi))` so staleness raises `CoverageError` instead of serving silently-stale data.

Triage: if `import treasuryutils` fails, it is an install/extras problem (step 1); if a read fails, it is a source/binding problem (step 4 — run `python -m treasuryutils.datatools doctor`) or a credential problem (step 5). For the credential case, `python -m treasuryutils.authenticator doctor` shows whether the profile is *configured*; a configured profile can still be *unauthenticated* on an interactive/cached tier, so route to `auth-setup` rather than concluding "misconfigured" from a `validate --connect` failure.

---

## Module Quick Map

| Domain | Primary import | Reference file |
|--------|---------------|----------------|
| Data loading / pipelines | `from treasuryutils.datatools import DatasetClient` · to **author a new dataset**, use the `dataset-creation` skill | `datatools_api.md` |
| Sinks / lineage export | `from treasuryutils.datatools import SinkExporter` | `datatools_api.md` |
| Stateless / serverless (Lambda) reads + one-shot writes | `from treasuryutils.datatools import ParquetUpsert` · see the `setup-source-bindings` skill | `datatools_api.md` |
| Business-day math | `from treasuryutils.calendartools import add_workdays` | `calendartools_api.md` |
| Authentication | `from treasuryutils.authenticator import get_authenticator` · to **set up** a profile, use the `auth-setup` skill | `authenticator_api.md` |
| Financial instruments | `from treasuryutils.financialtools.instruments import ...` | `financialtools_api.md` |
| Pricing / PV | `from treasuryutils.financialtools.pricing import price_cashflows` | `financialtools_api.md` |
| Yield curves | `from treasuryutils.financialtools.curves import CdiCurve` | `financialtools_api.md` |
| IFRS 9 accounting | `from treasuryutils.financialtools.accounting import ...` | `financialtools_api.md` |
| Positions / portfolios | `from treasuryutils.financialtools.positions import ...` | `financialtools_api.md` |
| Market data | `from treasuryutils.financialtools.market_data import ...` | `financialtools_api.md` |
| DataFrame operations | `from treasuryutils.compute import df_join, asof_aggregate` | `compute_common_api.md` |
| Text normalization | `from treasuryutils.common import normalize_text` | `compute_common_api.md` |
| YAML dataset contracts | *(YAML files, not Python)* | `yaml_contracts.md` |
| Portfolio risk / VaR (quant) | `from treasuryutils.quanttools.risk.portfolio_risk import compute_portfolio_risk` | `quanttools_api.md` |
| Quant analytics & optimization | `from treasuryutils.quanttools.analytics import compute_sharpe_ratio` | `quanttools_api.md` |

> **Under active development — engage only on direct request.** `equitytools` (equity
> market data, factor features, signals, backtesting, orders → `equitytools_api.md`) and
> `capitaltools` (treasury / capital scenarios, capital-structure optimization →
> `capitaltools_api.md`) are not recommended for general use yet. Do not route a generic
> equity / treasury / capital task to them; use them only when the user names the module
> or one of its symbols directly.

---

## Serving modes — cache, direct, and cacheless reads

`serve_mode` selects where a read's data comes from:

- **`cache`** (default) — build/serve a local DuckDB + artifact cache.
- **`direct`** — read live from the source on every call, no local cache (the
  remote-execution / stateless tier).
- **`auto`** — prefer cache, fall back to direct.

Set it per call (`DatasetClient(name, serve_mode='direct')` or `DatasetClient(name).handle(serve_mode=...)`),
per dataset (`serve_mode:` in the contract), or globally (`DATATOOLS__SERVE_MODE`).

Key v1.1 behaviours:

- **`ParquetUpsert.run_upsert()` forces `direct`** for every extraction source
  (`rest_api` / `python` / `bigquery` / `databricks` / `file`) — no `serve_mode: direct`
  YAML needed — and `serve_mode` propagates recursively through `get_dependency`, so a
  whole calendar-free DAG resolves cacheless.
- **Dataset-chain (`source.type=dataset`) sources and calendar curves stay cache-backed**
  (a Tier-2 boundary): a forced-direct read of one raises a loud `ConfigurationError`
  pointing at `serve_mode='cache'`.
- **BigQuery / Databricks `direct` reads bind query parameters** (`@start_date` /
  `@end_date` / `@cursor`; `:`-style for Databricks) from `source.config.params`.
- **BigQuery `direct` uses the configured authenticator** (the `gcp-identity` /
  `GoogleAuthenticator` profile) via the `GoogleCredentialsProvider` protocol; an
  incompatible authenticator fails loud. Set `allow_interactive=False` for headless/CI so
  it fails fast instead of prompting a browser.

See `docs/datatools/serving.md` and the `setup-source-bindings` skill for the full model.

---

## Worked examples

The reference files list signatures; these are the two most common calls, end to end. The reference `calendar=`/`covers=` params show no default because the generator strips defaults — pass the values shown here.

**Pricing input shape:** `price_cashflows` needs an instrument/leg-shaped frame (~19 columns), not a hand-authored cashflow table. Build it the supported way: `InstrumentTerms` + `LegDefinition` → `generate_schedule_df(terms, calendar=...)` → `price_cashflows(...)`. See `examples/02_cdi_curve_and_pricing.py` for the full call.

**Business days (Brazil calendar):**
```python
from datetime import date
from treasuryutils.calendartools import add_workdays
d = add_workdays(date(2024, 3, 1), 5, calendar='calendar_brazil')
# also available: calendar='calendar_us', calendar='calendar_sifma_us'
```

**Read a dataset, fail-closed on staleness:**
```python
from datetime import date
from treasuryutils.datatools import DatasetClient
df = DatasetClient('cdi_daily').get(covers=(date(2024, 1, 1), date(2024, 12, 31)))
# -> polars.DataFrame; raises CoverageError if the cache cannot cover the range
```

**Don't know the dataset name?** List the catalog with `python -m treasuryutils.datatools doctor` (or `config_status()` from `treasuryutils.datatools`). Common primitives: `cdi_daily`, `di_curve`, `fx_ptax`. Never guess a dataset name — read it from `doctor`.

---

## Runnable examples

The plugin's `examples/` directory has six runnable scripts that demonstrate complete,
real-world patterns end to end. When a task matches one of these scenarios, **read the
matching example first** — it shows the exact public API calls, the inputs, and the
verified output. Five run anywhere with no data setup; example 01 demonstrates the
fail-closed data-access + binding workflow. See `examples/README.md` for the index.

| Task | Example |
|------|---------|
| First dataset read, "why does my read fail", bindings, fail-closed `covers=` | `examples/01_data_access_and_bindings.py` |
| Build a CDI/DI Pre yield curve; discount factors; present-value cashflows | `examples/02_cdi_curve_and_pricing.py` |
| IFRS 9: effective interest rate, three-stage ECL, simplified provision matrix | `examples/03_ifrs9_ecl.py` |
| Portfolio covariance, VaR / Expected Shortfall, risk contributions, allocation | `examples/04_portfolio_risk.py` |
| Business-day settlement (T+2), accrual, BUS/252 year fractions | `examples/05_cashflow_calendar.py` |
| Point-in-time aggregation over SCD-2 position validity intervals | `examples/06_asof_aggregation.py` |

`examples/README.md` indexes the full set, including two further, intentionally-gated
examples not listed above — `07_treasury_cost_attribution.py` (`capitaltools`) and
`08_equity_factor_features.py` (`equitytools`) — under active development,
direct-request-only, not recommended for general use yet.

---

## Guardrails

- **Data access needs setup first — never assume it "just works".** The canonical DataTools
  datasets (and the curves/calendars built on them) are **unbound primitives** by default, several
  on a proprietary `bigquery`/`databricks` driver. A first `DatasetClient(...).get()`, `CdiCurve(...)`,
  or `add_workdays(..., calendar='calendar_brazil')` fails until the source is bound and auth is
  configured. Run `python -m treasuryutils.datatools doctor` to see the bound/unbound state and use
  the `setup-source-bindings` skill — do not tell the user "no `.env` or binding is needed" without
  checking.
- **Never fabricate signatures** — if a function is not listed in the reference files, do not assume it exists.
- **Use public import paths only** — import from `__init__.py` exports (e.g., `from treasuryutils.calendartools import add_workdays`), never from internal modules (e.g., ~~`from treasuryutils.calendartools.primitives import add_workdays`~~).
- **Lazy imports** — DataTools heavy deps (`duckdb`, `dlt`) and Authenticator heavy deps (`msal`, `google-auth`) are lazily imported. Do not import them directly; use the treasuryutils API.
- **Polars-first** — Polars is the primary DataFrame library. Do not suggest pandas conversions unless the user explicitly requests them.
- **Install from Karavela Packages** (PyPI ecosystem, owner group `jsm-ops-treasury-reporting`):
  ```bash
  uv add 'treasuryutils[all]' --index https://packages.stone.tech/repository/pypi-group/simple/
  ```
  Git fallback (e.g. for unreleased commits): `uv add 'treasuryutils[all] @ git+https://github.com/stone-payments/treasuryutils.git@main'`
- **Bootstrap** — `import treasuryutils` triggers runtime bootstrap. Suppress with `TREASURYUTILS_AUTO_INIT=minimal`.
- **Do not reinvent** — never replace treasuryutils with parallel custom code unless explicitly requested and justified. Always check the decision matrix first.
- **Do not hardcode secrets** — use environment variables and auth profiles. For any auth work past reading a static token — choosing a modality, or reconciling a profile that `doctor` shows configured but `validate --connect` reports not-live — hand off to the `auth-setup` skill; it owns the credential-tiers model. A `google`/`msal` interactive profile failing the connect probe is usually live on its cached interactive tier, not misconfigured, so do not prescribe `gcloud auth application-default login` on that signal alone.
- **Evidence-based claims** — do not claim API behavior without citing the reference file.
- **Fail-closed data reads** — for date-ranged analysis reads prefer `mgr.get(covers=(lo, hi))` so staleness raises `CoverageError` instead of serving silently-stale data; NEVER suggest `except`-and-continue (or catch-log-proceed) for any of the five classes in the recovery table — each one is a fail-closed signal that the result would be wrong.
- **Multi-dataset `depends_on` is validated at catalog load** (ADR-0087) — an undeclared or cyclic dependency raises `DependencyNotFoundError` / `DependencyCycleError` when the catalog loads under the default strict `DATATOOLS__CATALOG_STARTUP_MODE`; set it to `permissive` to log-and-tolerate during local iteration.

---

## Error → Recovery Routing

A consumer's LLM can act on this table with only the plugin installed.

| Error | You'll see it when | What it means | Recovery |
|---|---|---|---|
| `SourceExtractionError` | `DatasetClient(...).get()` on default config triggers a cache build via DLT ingestion | The source driver failed to fetch — config / credentials / permission / network / query — fail-closed | Verify credentials & permissions for the bound source; check source config and query; retry transient failures. Use the `setup-source-bindings` skill to rebind only when you intend to use a non-default source. |
| `PipelineExecutionError` | `DatasetClient(...).get()` on default config — the cache build pipeline run failed | Wraps a failed ingestion run — fail-closed | Verify credentials & permissions for the bound source; check source config and query; retry transient failures. Use the `setup-source-bindings` skill to rebind only when you intend to use a non-default source. |
| `SourceAccessError` | `serve_mode='direct'` reads | Cloud-SDK auth/permission/not-found on the bound source; the error carries a copy-pasteable rebind recipe | Check credentials & permissions for the bound source; use the carried rebind recipe when intentionally targeting a non-default source. Use the `setup-source-bindings` skill for a guided workflow. |
| `CoverageError` | `get(covers=(lo, hi))` reads | The cache cannot span the declared range after refresh — fail-closed, never silently-stale | Widen or correct the `covers=` range, or refresh upstream data; the error names the covered vs requested interval. Do not drop `covers=` to make the error go away. |
| `MarketDataCoverageError` | Financial curve `covers=` re-reads (ADR-0063) | The market-data source lacks the dates the curve needs — fail-closed signal preventing a silently-wrong price | The market-data source lacks the dates the curve needs; extend the source data (or its binding) — do not price without it. |

**Import paths** — to catch these:
`from treasuryutils.datatools import SourceExtractionError, PipelineExecutionError, SourceAccessError, CoverageError`
and `from treasuryutils.financialtools.market_data import MarketDataCoverageError`.

**This table routes the COMMON recovery cases — it is not the exhaustive set a `.get()` can raise.** A `.get()` can also raise `ConfigurationError`, `SchemaValidationError`, `CacheMissError`, `DependencyNotFoundError`, and other `treasuryutils.datatools` errors. For fail-closed handling, end your `except` ladder with a backstop: every datatools exception subclasses **`DataToolsError`** (importable from `treasuryutils.datatools`), so `except DataToolsError` catches anything the specific clauses missed. (The one deliberate exception is `MarketDataCoverageError`, which is NOT a `DataToolsError` — it lives under `treasuryutils.financialtools.market_data`; catch it separately for curve reads.)

```python
from treasuryutils.datatools import CoverageError, DataToolsError, SourceExtractionError

try:
    df = DatasetClient('cdi_daily').get(covers=(lo, hi))
except CoverageError:
    ...          # widen/refresh — never drop covers= to silence it
except SourceExtractionError:
    ...          # source fetch failed — check creds/permissions, retry transient
except DataToolsError:
    raise        # fail-closed backstop: anything else datatools-side, do not swallow
```

For the first three errors, verify credentials & permissions and retry transient failures first; rebind via the `setup-source-bindings` skill only when you intend to use a non-default source.

Further reading:
- Freshness guarantee: [https://github.com/stone-payments/treasuryutils/blob/main/docs/datatools/user_guide.md#reading-with-a-freshness-guarantee](https://github.com/stone-payments/treasuryutils/blob/main/docs/datatools/user_guide.md#reading-with-a-freshness-guarantee)
- `serve_mode` and `SourceAccessError`: [https://github.com/stone-payments/treasuryutils/blob/main/docs/datatools/serving.md](https://github.com/stone-payments/treasuryutils/blob/main/docs/datatools/serving.md)
- Source bindings workflow: [https://github.com/stone-payments/treasuryutils/blob/main/docs/integration/consumer_projects.md](https://github.com/stone-payments/treasuryutils/blob/main/docs/integration/consumer_projects.md)

---

## Silent divergence — suspect a stale cache first (nothing raised)

*What it is: a **derived** dataset's cached table has drifted out of sync with what its current
source + build logic would now produce — so reads succeed but return systematically-wrong values,
with no exception to catch.*

Some breakage is **silent**: a read succeeds, no exception is raised, but the values are
systematically wrong — business-day math is off by a day, `net_workdays` counts don't
reconcile against a source's own count, a series looks shifted, aggregates don't tie out.
The Error → Recovery table above covers only **raised** errors; this is the complement.
**When output looks wrong but nothing raised, suspect a stale `cache` before you suspect a
library bug** — and verify against the source of truth rather than reasoning about it.

**Why it happens.** A *derived* dataset (`calendar_brazil`, `di_pre`, `cdi_accumulated`, …)
is materialized into the local DuckDB cache and served from it. That cache can outlive its
correctness:

- it was built by an **older `treasuryutils`** whose build logic has since been fixed;
- the **source data was corrected after the build** (e.g. a `file` source's parquet was
  replaced *in place*) — the binding is unchanged, so the build fingerprint (ADR-0096) does
  **not** invalidate it, and `refresh_policy: if_stale` rebuilds only on **age** (TTL), not
  on correctness;
- it was built under a **transient environment difference** (locale/timezone, a different
  bound source) that has since changed.

The cache then keeps serving the old, wrong values until it is explicitly rebuilt. This is
**not** a fail-closed signal — there is nothing to `except`.

**Know the correct values (reference, not a probe).** A derived calendar must agree with its
holiday source on which weekdays are non-working — e.g. `2025-01-01` (New Year) and `2025-12-25`
(Christmas) are **non-working**, `2024-12-31` is a **working** day. Caveat: reading a value through
the public API (`ct.is_workday(..., calendar='calendar_brazil')` → `DatasetClient.get()`) is **not
an inert probe** — the read evaluates binding-provenance + dependency freshness (ADR-0085) and can
itself trigger a rebuild, which would silently *heal* a stale cache and mask the very divergence you
are trying to observe. So use it to **verify _after_ the rebuild**, not to inspect the stale state
beforehand; to observe the current (possibly stale) served value without mutating anything, read the
cached table directly (the diagnostic in the reference below does exactly that).

**Remedy — clear the derived dataset AND its leaves, rebuild the chain, then verify** (needs
the `cli` extra; `cache clear` takes one dataset per call):

```bash
python -m treasuryutils.datatools cache list                    # see what's cached
python -m treasuryutils.datatools cache clear calendar_brazil   # evict the derived dataset
python -m treasuryutils.datatools cache clear holidays_brazil   # …and its upstream leaf/leaves
# rebuild the whole chain from source, resetting cursors + reloading from initial_value:
python -c "from treasuryutils.datatools import DatasetClient; DatasetClient('calendar_brazil').ensure_fresh(full_refresh='recursive')"
# assert the rebuilt chain COVERS the needed span (coverage, not correctness):
python -m treasuryutils.datatools cache smoke calendar_brazil --from 2024-01-01 --to 2027-12-31
```

Then re-run the known-truth spot check — `cache smoke` proves *coverage*; only the value
check proves the divergence is gone.

**Prevent it:** read date-ranged data fail-closed with `get(covers=(lo, hi))` so a *range*
gap raises `CoverageError` instead of serving silently; and clear the whole cache root once
after any `treasuryutils` upgrade (see *Upgrading* below).

**If it persists after the rebuild — it is no longer self-serviceable; capture evidence.** A
correct rebuild fixes the vast majority of cases. If the divergence survives a `cache clear` +
recursive rebuild, the cause is either the **source itself** (e.g. a tz-aware `date` column that
shifts a day under a non-UTC session) or a genuine build bug — stop guessing. Run the read-only,
secret-free diagnostic in [`references/troubleshooting.md`](references/troubleshooting.md) and paste
its whole output into the treasuryutils report; it captures exactly the facts a maintainer needs to
fix it — versions + session timezone, the source dtype and whether `CAST(date AS DATE)` shifts it,
the served cached values, and build provenance — and shows how to read them to route the cause.

---

## Dependency refresh is content-triggered (ADR-0085)

For derived datasets, a dependency refresh fires when an upstream's **content**
changes (a `state_token` over its cached extent), not when its timestamp merely
advances — and only for datasets that opt in via `source.refresh_on_build: true`.
For a consumer reading derived curves/datasets this means:

- A no-op upstream re-run no longer cascades a downstream rebuild.
- To force a rebuild, change the upstream content or call `update(full_refresh=True)`.
- The legacy `refresh_policy.stale_if_dependency_newer` flag is retained for
  fingerprint stability but is no longer consulted at runtime.

---

## Fallback Rules

- If `treasuryutils` is not installed, stop and provide the install command.
- If the user's task does not match any domain in the decision matrix, list the available subpackages and ask for clarification.
- If a function signature is not in the references, suggest `help(function)` or `inspect.signature(function)` on the installed package rather than guessing.

---

## Version and Updates

References are generated against a specific `treasuryutils` version. See
`references/update_strategy.md` for how to refresh references when the
library is updated.

### Upgrading to v1.1

`v1.1.0` is the first supported release (`v1.0.0`–`v1.0.3` are superseded). On upgrade:

- Pin `treasuryutils>=1.1.0`.
- **Clear the lakehouse cache once** — source column names are now authoritative (DLT
  snake_case normalization removed), so a cache written by an older version is stale until
  cleared. Delete the cache root (`DATATOOLS__DATA_CACHE_DIR`, or the default
  `<user-data-dir>/lakehouse`); it rebuilds on the next read.

Full details: `docs/migration/v1.1.0.md`.
