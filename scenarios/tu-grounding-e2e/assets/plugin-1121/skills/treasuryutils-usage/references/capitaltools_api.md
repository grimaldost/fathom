# CapitalTools API Reference (generated)

- treasuryutils_version: `1.5.2.dev174+g64f80dc79`
- generated_at_utc: `2026-07-09T20:04:53.120267+00:00`
- install_extras: `treasuryutils[datatools,quant-math,quant-optimizer]`

## `treasuryutils.capitaltools`

_No public callables discovered._

## `treasuryutils.capitaltools.attribution`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_period_waterfall` | function | `(current: 'pl.DataFrame', prior: 'pl.DataFrame') -> 'pl.DataFrame'` | Period-over-period bridge: prior + delta = current for each component. · Input columns: current{wide-format; shared numeric columns are bridged (no fixed names)}; prior{same schema as current} |
| `compute_treasury_cost_attribution` | function | `(pnl_attribution: 'pl.DataFrame', positions: 'pl.DataFrame', *, group_by: 'str', ref_date: 'date \| None') -> 'pl.DataFrame'` | Aggregate PnL decomposition by group (entity, instrument_type, currency). · Input columns: pnl_attribution{deal_id, pnl_total}; positions{deal_id, notional -- plus the column named by group_by (default entity_id)} |

## `treasuryutils.capitaltools.attribution.cost_attribution`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_period_waterfall` | function | `(current: 'pl.DataFrame', prior: 'pl.DataFrame') -> 'pl.DataFrame'` | Period-over-period bridge: prior + delta = current for each component. · Input columns: current{wide-format; shared numeric columns are bridged (no fixed names)}; prior{same schema as current} |
| `compute_treasury_cost_attribution` | function | `(pnl_attribution: 'pl.DataFrame', positions: 'pl.DataFrame', *, group_by: 'str', ref_date: 'date \| None') -> 'pl.DataFrame'` | Aggregate PnL decomposition by group (entity, instrument_type, currency). · Input columns: pnl_attribution{deal_id, pnl_total}; positions{deal_id, notional -- plus the column named by group_by (default entity_id)} |

## `treasuryutils.capitaltools.bridge`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `extract_cost_vector` | function | `(pricing_summary: 'pl.DataFrame', positions: 'pl.DataFrame', cdi_curve: 'InterestRateCurve', ref_date: 'date') -> 'CostVector'` | Extract the cost of each instrument in the portfolio. |
| `extract_current_weights` | function | `(position_values: 'pl.DataFrame') -> 'tuple[list[str], np.ndarray]'` | Extract current portfolio weights from position values. |
| `extract_dv01_vector` | function | `(risk_metrics: 'pl.DataFrame', positions: 'pl.DataFrame') -> 'np.ndarray'` | Extract the position-scaled DV01 vector. |

## `treasuryutils.capitaltools.bridge.cost_vector`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `extract_cost_vector` | function | `(pricing_summary: 'pl.DataFrame', positions: 'pl.DataFrame', cdi_curve: 'InterestRateCurve', ref_date: 'date') -> 'CostVector'` | Extract the cost of each instrument in the portfolio. |

## `treasuryutils.capitaltools.bridge.risk_sensitivities`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `extract_current_weights` | function | `(position_values: 'pl.DataFrame') -> 'tuple[list[str], np.ndarray]'` | Extract current portfolio weights from position values. |
| `extract_dv01_vector` | function | `(risk_metrics: 'pl.DataFrame', positions: 'pl.DataFrame') -> 'np.ndarray'` | Extract the position-scaled DV01 vector. |

## `treasuryutils.capitaltools.constraints`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_counterparty_limits` | function | `(counterparty_map: 'dict[str, list[int]]', max_per_counterparty: 'float') -> 'list[LimitDefinition]'` | Translate per-counterparty exposure caps into MAX_GROUP_WEIGHT limits. |
| `build_de_ratio_limit` | function | `(max_de_ratio: 'float', equity: 'float') -> 'LimitDefinition'` | Translate a D/E ratio covenant into a MAX_GROSS_EXPOSURE limit. |
| `build_floating_rate_limit` | function | `(max_float_pct: 'float', float_indices: 'list[int]', *, weighting: "Literal['notional', 'dv01']", dv01_per_index: 'list[float] \| None') -> 'LimitDefinition'` | Translate a floating-rate exposure cap into a portfolio limit. |
| `build_fx_exposure_limit` | function | `(max_fx_pct: 'float', fx_indices: 'list[int]') -> 'LimitDefinition'` | Translate an FX exposure ceiling into a MAX_GROUP_WEIGHT limit. |
| `build_maturity_ladder_limits` | function | `(maturity_buckets: 'dict[str, list[int]]', min_per_bucket: 'dict[str, float]') -> 'list[LimitDefinition]'` | Translate maturity-bucket floor requirements into MIN_WEIGHT limits. |

## `treasuryutils.capitaltools.constraints.concentration`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_counterparty_limits` | function | `(counterparty_map: 'dict[str, list[int]]', max_per_counterparty: 'float') -> 'list[LimitDefinition]'` | Translate per-counterparty exposure caps into MAX_GROUP_WEIGHT limits. |

## `treasuryutils.capitaltools.constraints.covenant`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_de_ratio_limit` | function | `(max_de_ratio: 'float', equity: 'float') -> 'LimitDefinition'` | Translate a D/E ratio covenant into a MAX_GROSS_EXPOSURE limit. |
| `compute_covenant_headroom` | function | `(limit: 'float', current: 'float', direction: 'CovenantDirection \| None') -> 'float'` | Fractional headroom remaining before a covenant threshold is breached. |
| `CovenantDirection` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.capitaltools.constraints.maturity`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_maturity_ladder_limits` | function | `(maturity_buckets: 'dict[str, list[int]]', min_per_bucket: 'dict[str, float]') -> 'list[LimitDefinition]'` | Translate maturity-bucket floor requirements into MIN_WEIGHT limits. |

## `treasuryutils.capitaltools.constraints.policy`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_floating_rate_limit` | function | `(max_float_pct: 'float', float_indices: 'list[int]', *, weighting: "Literal['notional', 'dv01']", dv01_per_index: 'list[float] \| None') -> 'LimitDefinition'` | Translate a floating-rate exposure cap into a portfolio limit. |
| `build_fx_exposure_limit` | function | `(max_fx_pct: 'float', fx_indices: 'list[int]') -> 'LimitDefinition'` | Translate an FX exposure ceiling into a MAX_GROUP_WEIGHT limit. |

## `treasuryutils.capitaltools.domain`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CapitalIdentifier` | enum | `` | Base for capital management domain enums. |
| `ConstraintType` | enum | `COVENANT_DE_RATIO='COVENANT_DE_RATIO', MAX_COUNTERPARTY='MAX_COUNTERPARTY', MIN_LIQUIDITY_RATIO='MIN_LIQUIDITY_RATIO', MAX_FX_EXPOSURE='MAX_FX_EXPOSURE', MAX_FLOATING_RATE='MAX_FLOATING_RATE', MATURITY_LADDER='MATURITY_LADDER'` | Treasury portfolio constraint type. |
| `CostAttributionResult` | class | `(ref_date: 'date', by_entity: 'dict[str, float]', by_instrument_type: 'dict[str, float]', by_currency: 'dict[str, float]', total: 'float') -> None` | Transaction cost breakdown by grouping dimension. |
| `CostVector` | class | `(instrument_ids: 'list[str]', costs: 'list[float]', ref_date: 'date', method: 'str') -> None` | Transaction cost estimates aligned with an instrument list. |
| `ScenarioDataSource` | enum | `SYNTHETIC='SYNTHETIC', HISTORICAL_REPLAY='HISTORICAL_REPLAY', OVERRIDE='OVERRIDE'` | Where a scenario's perturbation values come from. |
| `ScenarioDefinition` | class | `(scenario_id: 'str', scenario_type: 'ScenarioType', parameters: 'dict[str, float]', description: 'str') -> None` | Definition of a stress/sensitivity scenario. |
| `ScenarioResult` | class | `(scenario_id: 'str', ref_date: 'date', base_value: 'float', scenario_value: 'float', change: 'float', covenant_impact: 'dict[str, float]') -> None` | Outcome of a single scenario run. |
| `ScenarioType` | enum | `PARALLEL_SHIFT='PARALLEL_SHIFT', TWIST='TWIST', STEEPENER='STEEPENER', FLATTENER='FLATTENER', BUTTERFLY='BUTTERFLY', BEAR_FLATTENER='BEAR_FLATTENER', USER_SHIFTS='USER_SHIFTS', INVERSION='INVERSION'` | Yield-curve shock recipe (industry-standard vocabulary). |
| `TreasuryConstraint` | class | `(constraint_type: 'ConstraintType', limit_value: 'float', scope: 'str', entity_id: 'str', effective_date: 'date') -> None` | Single treasury policy constraint. |
| `TreasuryFeatureRow` | class | `(ref_date: 'date', features: 'dict[str, float]') -> None` | Cross-sectional treasury feature vector for a single reference date. |

## `treasuryutils.capitaltools.domain.identifiers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CapitalIdentifier` | enum | `` | Base for capital management domain enums. |
| `ConstraintType` | enum | `COVENANT_DE_RATIO='COVENANT_DE_RATIO', MAX_COUNTERPARTY='MAX_COUNTERPARTY', MIN_LIQUIDITY_RATIO='MIN_LIQUIDITY_RATIO', MAX_FX_EXPOSURE='MAX_FX_EXPOSURE', MAX_FLOATING_RATE='MAX_FLOATING_RATE', MATURITY_LADDER='MATURITY_LADDER'` | Treasury portfolio constraint type. |
| `ScenarioDataSource` | enum | `SYNTHETIC='SYNTHETIC', HISTORICAL_REPLAY='HISTORICAL_REPLAY', OVERRIDE='OVERRIDE'` | Where a scenario's perturbation values come from. |
| `ScenarioType` | enum | `PARALLEL_SHIFT='PARALLEL_SHIFT', TWIST='TWIST', STEEPENER='STEEPENER', FLATTENER='FLATTENER', BUTTERFLY='BUTTERFLY', BEAR_FLATTENER='BEAR_FLATTENER', USER_SHIFTS='USER_SHIFTS', INVERSION='INVERSION'` | Yield-curve shock recipe (industry-standard vocabulary). |

## `treasuryutils.capitaltools.domain.index_taxonomy`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `IndexEntry` | class | `(name: 'str', type: 'IndexType', currency: 'str', description: 'str', sgs_series: 'int \| None', domestic: 'bool') -> None` | One entry in the Brazilian fixed-income index taxonomy. |

## `treasuryutils.capitaltools.domain.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CostAttributionResult` | class | `(ref_date: 'date', by_entity: 'dict[str, float]', by_instrument_type: 'dict[str, float]', by_currency: 'dict[str, float]', total: 'float') -> None` | Transaction cost breakdown by grouping dimension. |
| `CostVector` | class | `(instrument_ids: 'list[str]', costs: 'list[float]', ref_date: 'date', method: 'str') -> None` | Transaction cost estimates aligned with an instrument list. |
| `ScenarioDefinition` | class | `(scenario_id: 'str', scenario_type: 'ScenarioType', parameters: 'dict[str, float]', description: 'str') -> None` | Definition of a stress/sensitivity scenario. |
| `ScenarioResult` | class | `(scenario_id: 'str', ref_date: 'date', base_value: 'float', scenario_value: 'float', change: 'float', covenant_impact: 'dict[str, float]') -> None` | Outcome of a single scenario run. |
| `TreasuryConstraint` | class | `(constraint_type: 'ConstraintType', limit_value: 'float', scope: 'str', entity_id: 'str', effective_date: 'date') -> None` | Single treasury policy constraint. |
| `TreasuryFeatureRow` | class | `(ref_date: 'date', features: 'dict[str, float]') -> None` | Cross-sectional treasury feature vector for a single reference date. |

## `treasuryutils.capitaltools.features`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_treasury_features` | function | `(rate_history: 'pl.DataFrame', portfolio_state: 'pl.DataFrame', ref_date: 'date', *, lookback_years: 'int') -> 'pl.DataFrame'` | Daily risk environment indicators with historical z-scores. |

## `treasuryutils.capitaltools.features.treasury_features`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_treasury_features` | function | `(rate_history: 'pl.DataFrame', portfolio_state: 'pl.DataFrame', ref_date: 'date', *, lookback_years: 'int') -> 'pl.DataFrame'` | Daily risk environment indicators with historical z-scores. |

## `treasuryutils.capitaltools.optimization`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `optimize_capital_structure` | function | `(pricing_summary: 'pl.DataFrame', positions: 'pl.DataFrame', risk_metrics: 'pl.DataFrame', position_values: 'pl.DataFrame', cdi_curve: 'Any', constraints: 'list[TreasuryConstraint]', rate_covariance: 'CovarianceEstimate', *, risk_aversion: 'float', cost_model: 'CostModel \| None', ref_date: 'date \| None', counterparty_maps: 'dict[str, dict[str, list[int]]] \| None') -> 'TargetPortfolio'` | Capital structure optimization orchestrator. |

## `treasuryutils.capitaltools.optimization.capital_structure`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `optimize_capital_structure` | function | `(pricing_summary: 'pl.DataFrame', positions: 'pl.DataFrame', risk_metrics: 'pl.DataFrame', position_values: 'pl.DataFrame', cdi_curve: 'Any', constraints: 'list[TreasuryConstraint]', rate_covariance: 'CovarianceEstimate', *, risk_aversion: 'float', cost_model: 'CostModel \| None', ref_date: 'date \| None', counterparty_maps: 'dict[str, dict[str, list[int]]] \| None') -> 'TargetPortfolio'` | Capital structure optimization orchestrator. |

## `treasuryutils.capitaltools.risk`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_treasury_risk` | function | `(dv01_vector: 'np.ndarray', rate_covariance: 'CovarianceEstimate', *, confidence_level: 'float', positions: 'pl.DataFrame \| None', ref_date: 'date \| None') -> 'pl.DataFrame'` | Treasury portfolio risk metrics. |
| `estimate_rate_covariance` | function | `(rate_history: 'pl.DataFrame', *, window: 'int', method: 'str', as_of: 'date \| None') -> 'CovarianceEstimate'` | Estimate covariance of rate CHANGES (not levels). |

## `treasuryutils.capitaltools.risk.rate_covariance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `estimate_rate_covariance` | function | `(rate_history: 'pl.DataFrame', *, window: 'int', method: 'str', as_of: 'date \| None') -> 'CovarianceEstimate'` | Estimate covariance of rate CHANGES (not levels). |

## `treasuryutils.capitaltools.risk.treasury_risk`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_treasury_risk` | function | `(dv01_vector: 'np.ndarray', rate_covariance: 'CovarianceEstimate', *, confidence_level: 'float', positions: 'pl.DataFrame \| None', ref_date: 'date \| None') -> 'pl.DataFrame'` | Treasury portfolio risk metrics. |

## `treasuryutils.capitaltools.scenarios`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_scenario_curves` | function | `(scenario: 'ScenarioDefinition', base_curves: 'dict[str, Any]', ref_date: 'date') -> 'dict[str, Any]'` | Build scenario curves from base curves at the given anchor date. |
| `run_scenario_analysis` | function | `(scenarios: 'list[ScenarioDefinition]', cashflows: 'pl.DataFrame', positions: 'pl.DataFrame', base_curves: 'dict[str, Any]', ref_date: 'date') -> 'pl.DataFrame'` | Stress-test the portfolio by repricing with scenario-modified curves. |

## `treasuryutils.capitaltools.scenarios.builder`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_scenario_curves` | function | `(scenario: 'ScenarioDefinition', base_curves: 'dict[str, Any]', ref_date: 'date') -> 'dict[str, Any]'` | Build scenario curves from base curves at the given anchor date. |

## `treasuryutils.capitaltools.scenarios.runner`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `run_scenario_analysis` | function | `(scenarios: 'list[ScenarioDefinition]', cashflows: 'pl.DataFrame', positions: 'pl.DataFrame', base_curves: 'dict[str, Any]', ref_date: 'date') -> 'pl.DataFrame'` | Stress-test the portfolio by repricing with scenario-modified curves. |

## `treasuryutils.capitaltools.schema`

_No public callables discovered._

## `treasuryutils.capitaltools.schema.definitions`

_No public callables discovered._
