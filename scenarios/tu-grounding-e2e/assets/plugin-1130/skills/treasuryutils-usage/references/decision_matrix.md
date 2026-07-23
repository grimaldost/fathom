# treasuryutils Decision Matrix

Use this file to route tasks to the correct domain and reference file.
Always consult this matrix before writing code.

> **Worked patterns:** for an end-to-end, runnable demonstration of a domain, read the
> matching script in the plugin's `examples/` directory (see `examples/README.md`) before
> writing new code — e.g. portfolio risk → `examples/04_portfolio_risk.py`, IFRS 9 ECL →
> `examples/03_ifrs9_ecl.py`, yield-curve pricing → `examples/02_cdi_curve_and_pricing.py`.

> **Prerequisite for any DataTools-backed task (data loading, yield curves, business-day
> calendars).** The canonical datasets (`cdi_daily`, `di_curve`, `calendar_brazil` →
> `holidays_brazil`, …) are **unbound primitives** out of the box, and several use a
> proprietary `bigquery`/`databricks` driver — so a first read *fails* until the source is
> reachable and auth is configured. Before routing such a task, do **not** assume "no `.env`
> / no binding is needed": run `python -m treasuryutils.datatools doctor` to see the real
> bound/unbound state, then configure auth with the **`auth-setup`** skill (e.g. the
> `gcp-identity` profile for the BigQuery defaults). Stone-internal consumers reach the default
> sources with their own credentials; **`setup-source-bindings`** rebinding is only needed to
> point a dataset at a non-default source.

---

## Domain Routing

> **Modules under active development — `capitaltools` and `equitytools`.** These two
> domains are NOT recommended for general use yet. Do **not** proactively route a generic
> equity, treasury, or capital-structure task to them. Engage them **only when the user
> explicitly names the module (`capitaltools` / `equitytools`) or one of its symbols**;
> their API references (`capitaltools_api.md`, `equitytools_api.md`) remain available for
> that direct use.

| User wants to... | Domain | Reference file | Key entry points |
|---|---|---|---|
| Load, sync, or cache a dataset | DataTools | `datatools_api.md` | `DatasetClient`, `Pipeline`, `ParquetUpsert` |
| Create or edit a dataset YAML contract | DataTools + YAML | `datatools_api.md` + `yaml_contracts.md` | `DatasetConfig`, `SourceConfig`, `SourceBinding` |
| Orchestrate multi-dataset pipelines | DataTools | `datatools_api.md` | `Pipeline`, `DatasetClient` |
| Read parquet without caching (stateless / serverless) | DataTools | `datatools_api.md` | `ParquetUpsert` (despite the name, it does stateless **reads** as well as one-shot writes) |
| Read a dataset with a freshness guarantee | DataTools | `datatools_api.md` | `get(covers=)`, `CoverageError` |
| Read live from the source, no local cache (serverless/CI) | DataTools | `datatools_api.md` | `serve_mode='direct'`, `DatasetClient`, `ParquetUpsert` |
| Choose where reads come from (cache / direct / auto) | DataTools | `datatools_api.md` | `serve_mode='cache'`, `serve_mode='direct'`, `DATATOOLS__SERVE_MODE` |
| Check if a date is a business day | CalendarTools | `calendartools_api.md` | `is_workday`, `add_workdays` |
| Add/subtract business days | CalendarTools | `calendartools_api.md` | `add_workdays`, `forward_workday`, `backward_workday` |
| Count business days between two dates | CalendarTools | `calendartools_api.md` | `net_workdays` |
| Roll dates by convention | CalendarTools | `calendartools_api.md` | `roll_date` |
| Compute day-count fractions | CalendarTools | `calendartools_api.md` | `year_fraction`, `DayCountConvention` |
| Generate workday ranges | CalendarTools | `calendartools_api.md` | `wdate_range` |
| Get an auth token | Authenticator | `authenticator_api.md` | `get_authenticator` |
| Configure auth profiles | Authenticator | `authenticator_api.md` | `MsalAuthProfile`, `GoogleAuthProfile`, `DatabricksAuthProfile` |
| Define a financial instrument | FinancialTools | `financialtools_api.md` | `Instrument`, `InstrumentTerms`, `decode_instrument` |
| Decode instruments from YAML | FinancialTools + YAML | `financialtools_api.md` + `yaml_contracts.md` | `decode_instrument`, `decode_instruments` |
| Generate a cashflow schedule | FinancialTools | `financialtools_api.md` | `generate_schedule`, `generate_schedule_df` |
| Price cashflows / compute PV — needs an instrument/leg-shaped frame built via `generate_schedule_df(terms, calendar=...)`, not a hand-authored cashflow table | FinancialTools | `financialtools_api.md` | `price_cashflows`, `price_cashflows_summary` |
| Build a yield curve | FinancialTools | `financialtools_api.md` | `CdiCurve`, `SofrCurve`, `IpcaCurve`, `CupomCambialCurve` |
| Compute risk metrics (DV01, duration) | FinancialTools | `financialtools_api.md` | `compute_risk_metrics` |
| Classify instruments (IFRS 9) | FinancialTools | `financialtools_api.md` | `classify_instruments`, `classify_measurement` |
| Compute amortized cost / EIR | FinancialTools | `financialtools_api.md` | `compute_amortized_cost`, `solve_eir` |
| Compute expected credit loss (ECL) | FinancialTools | `financialtools_api.md` | `compute_ecl`, `assess_stage` |
| Fair value accounting (FVTPL, FVOCI) | FinancialTools | `financialtools_api.md` | `compute_fair_value_changes`, `compute_fvoci` |
| Hedge accounting | FinancialTools | `financialtools_api.md` | `compute_cash_flow_hedge`, `compute_fair_value_hedge` |
| Period-end processing | FinancialTools | `financialtools_api.md` | `process_period_end` |
| Manage positions and portfolios | FinancialTools | `financialtools_api.md` | `Position`, `Portfolio`, `scale_by_position` |
| Load market data for pricing | FinancialTools | `financialtools_api.md` | `DatatoolsMarketDataSource`, `InMemoryMarketDataSource` |
| DataFrame joins, filters, aggregation | Compute | `compute_common_api.md` | `df_join`, `df_filter`, `asof_aggregate` |
| Weighted averages | Compute | `compute_common_api.md` | `weighted_average`, `WeightedAverageSpec` |
| Rank / percentile / z-score a metric across a cross-section (per-row, row-preserving) | Compute | `compute_common_api.md` | `df_cross_sectional_agg` with `RankAgg` (1-based ordinal ties) / `PercentileRankAgg` (range (0,1], average ties) / `ZScoreAgg` (**population std, ddof=0**) |
| Normalize or transform text | Common | `compute_common_api.md` | `normalize_text`, `to_snake_case` |
| Configure runtime / env variables | Config | `datatools_api.md` | `TREASURYUTILS_AUTO_INIT`, `DATATOOLS__*` env vars |
| Compute portfolio VaR / statistical portfolio risk | QuantTools | `quanttools_api.md` | `compute_portfolio_risk`, `PortfolioRiskResult` |
| Estimate a covariance matrix (EWMA, Ledoit-Wolf) | QuantTools | `quanttools_api.md` | `estimate_ewma_sample_covariance`, `estimate_ledoit_wolf_covariance`, `CovarianceEstimate` |
| Optimize portfolio weights | QuantTools | `quanttools_api.md` | `optimize`, `optimize_risk_parity`, `build_constraints`; for `MINIMUM_VARIANCE`/`MEAN_VARIANCE` add `LimitDefinition(LimitType.FULLY_INVESTED, 1.0)` to be fully invested; budget-free `MINIMUM_VARIANCE` fails closed (raises, not a silent all-zero portfolio); see `examples/04_portfolio_risk.py` |
| Performance / attribution analytics (Sharpe, drawdown) | QuantTools | `quanttools_api.md` | `compute_sharpe_ratio`, `compute_max_drawdown`, `compute_factor_attribution` |
| Walk-forward backtest windows / deflated Sharpe | QuantTools | `quanttools_api.md` | `generate_walk_forward_windows`, `compute_deflated_sharpe` |
| **DIRECT REQUEST ONLY** — equity strategy work (market data, factor features, signals, backtesting, orders). `equitytools` is under active development: route here only when the user names `equitytools` or one of these symbols directly, never for a generic equity task | EquityTools | `equitytools_api.md` | `EquityMarketDataSource`, `BacktestEngine`, `generate_orders` |
| **DIRECT REQUEST ONLY** — treasury/capital scenarios, capital-structure optimization, treasury cost attribution. `capitaltools` is under active development: route here only when the user names `capitaltools` or one of these symbols directly, never for a generic treasury/capital task | CapitalTools | `capitaltools_api.md` | `run_scenario_analysis`, `optimize_capital_structure`, `compute_treasury_cost_attribution` |
| Discover available datasets / check data source setup | DataTools | `datatools_api.md` | `config_status`, `validate_bindings`, `scaffold_bindings` |
| Recover from a data-access or staleness error | DataTools | `datatools_api.md` + `financialtools_api.md` | `SourceExtractionError`, `PipelineExecutionError`, `SourceAccessError`, `CoverageError`, `MarketDataCoverageError` |
| Write a dataset out to an external sink | DataTools | `datatools_api.md` | `SinkExporter`, `DatasetSinkManager`, `SinkConfig`, `SinkResult` |
| Compose a derived dataset over another (Chain-of-Datasets; virtual or cached) | DataTools + YAML | `datatools_api.md` + `yaml_contracts.md` | `DatasetChainProvider`, `materialize` |
| Rebuild a derived dataset when an upstream's content changes (ADR-0085) | DataTools + YAML | `datatools_api.md` + `yaml_contracts.md` | `refresh_on_build` |
| Diagnose a dependency error at catalog load (missing / cyclic depends_on) | DataTools | `datatools_api.md` | `DependencyNotFoundError`, `DependencyCycleError`, `DependencyError` |
| Emit DataHub lineage from the bound catalog | DataTools | `datatools_api.md` | `export_lineage` |

**Choosing between similar-sounding domains:**
- Instrument-level rates risk (DV01, duration, carry) → FinancialTools.
- Statistical portfolio risk (VaR, covariance, Sharpe) → QuantTools.
- Treasury cash / capital scenarios and debt-mix decisions → CapitalTools — **only when explicitly requested** (under active development; do not route a generic treasury/capital task here).
- Full equity strategy work (signals, backtests, orders) → EquityTools — **only when explicitly requested** (under active development; do not route a generic equity task here).

---

## Decision Flow

### Path 1: Reuse Existing API (default)

Use when a documented symbol already satisfies the requirement.

**Required evidence:**
- Consulted module(s) and symbol(s) from the domain reference
- Why the selected behavior matches the requirement

### Path 2: Extend Using Configuration

Use when behavior exists but needs configuration changes (YAML, env vars, profile aliases).

**Required evidence:**
- Existing API being used
- Configuration delta required (YAML fields, env vars)
- Compatibility impact

### Path 3: Custom Implementation (last resort)

Use only when no suitable API exists.

**Required evidence:**
- Modules and symbols searched
- Why candidate symbols are insufficient
- Why custom code is required
- Integration/contract tests added or updated

---

## YAML-Specific Flow

Before creating or editing YAML contracts:

1. Read `yaml_contracts.md` and choose the nearest baseline template.
2. Validate fields against the documented schema.
3. Customize only after baseline and schema checks.

If no baseline template is used, document the reason.

---

## Anti-Reinvention Checklist

### External-library equivalents — prefer treasuryutils

A famous external library is the most common reinvention trap: it looks "standard," so it gets
reached for even when treasuryutils provides the same thing with treasury-appropriate
conventions/seeding. If you are about to import any of these, STOP and use the treasuryutils symbol
instead (unless the user explicitly asks for the external one):

| If tempted to use… | Use treasuryutils instead |
|---|---|
| `sklearn.covariance.LedoitWolf` / `OAS` / `EmpiricalCovariance` / `ShrunkCovariance` | treasuryutils covariance estimators (`estimate_ledoit_wolf_covariance`, `estimate_ewma_sample_covariance`) |
| `pandas.DataFrame.ewm().cov()` / a hand-rolled EWMA recursion | `estimate_ewma_sample_covariance` (RiskMetrics seeding + frequency handling) |
| `scipy.optimize.minimize` / raw `cvxpy` for portfolio weights | `treasuryutils.quanttools.optimize` (+ `build_constraints`) |
| `numpy_financial.irr` / a hand-rolled IRR/EIR solver | `treasuryutils.financialtools.accounting.solve_eir` |
| `numpy.busday_count` / `numpy.busday_offset` + a holiday list | `treasuryutils.calendartools.net_workdays` / `add_workdays` |
| a hand-rolled day-count `(d2 - d1) / 360` | `treasuryutils.calendartools.year_fraction` + `DayCountConvention` |
| `numpy.cov` for a returns covariance when observations < assets | a treasuryutils shrinkage estimator (raw sample covariance is singular here) |

Before implementing custom code, verify:

1. Read the domain reference file for the target module.
2. For YAML tasks, also read `yaml_contracts.md`.
3. Searched for equivalent behavior in documented symbols.
4. Verified signature/behavior evidence from the reference — then **confirmed it against the installed package** (Read-Order step 0): a stale reference can cite a symbol or signature that has since moved.
5. Checked local usage patterns in the consumer project.
6. Documented either: reuse path (why existing API suffices) or custom-gap justification (why custom code is needed).

If any answer is "no", complete that step first.
