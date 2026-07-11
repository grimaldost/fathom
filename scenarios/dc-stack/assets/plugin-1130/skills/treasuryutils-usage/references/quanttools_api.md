# QuantTools API Reference (generated)

- treasuryutils_version: `1.8.0`
- generated_at_utc: `2026-07-10T16:08:46.035900+00:00`
- install_extras: `treasuryutils[datatools,quant-math,quant-optimizer]`

## `treasuryutils.quanttools`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ADFResult` | class | `(statistic: 'float', pvalue: 'float', used_lag: 'int', n_obs: 'int') -> None` | Result of the Augmented Dickey-Fuller test. |
| `Alert` | class | `(level: 'str', limit_type: 'str', current_value: 'float', limit_value: 'float', action: 'str', message: 'str') -> None` | Immutable risk-limit breach notification. |
| `BarPanel` | class | `(df: 'pl.DataFrame', security_ids: 'list[str]', start_date: 'date', end_date: 'date') -> None` | OHLCV + adjustment factor panel for N securities over T days. |
| `build_constraints` | function | `(limits: 'list[LimitDefinition]', n_assets: 'int', weights_var: 'Any', *, current_weights: 'np.ndarray \| None', group_mapping: 'dict[str, list[int]] \| None') -> 'list[Any]'` | Translate LimitDefinition objects into cvxpy constraints. |
| `check_limit_breach` | function | `(current_value: 'float', limit_value: 'float', limit_type: 'str', *, alert_threshold_pct: 'float', breach_action: 'str') -> 'Alert \| None'` | Check whether current_value breaches or approaches a hard limit. |
| `CointegrationResult` | class | `(hedge_ratio: 'float', statistic: 'float', pvalue: 'float') -> None` | Result of the Engle-Granger cointegration test. |
| `compute_calmar_ratio` | function | `(annual_return: 'float', max_drawdown: 'float') -> 'float'` | annual_return / max_drawdown. |
| `compute_cost_attribution` | function | `(cost_components: 'dict[str, float]') -> 'dict[str, float]'` | Validate cost components and return them unchanged. |
| `compute_factor_attribution` | function | `(portfolio_weights: 'np.ndarray', factor_exposures: 'np.ndarray', factor_returns: 'np.ndarray', *, factor_names: 'list[str]') -> 'dict[str, float]'` | Contribution per factor: (S w_i * exposure_{i,k}) * factor_return_k. |
| `compute_factor_exposures` | function | `(weights: 'np.ndarray', factor_loadings: 'np.ndarray', *, factor_names: 'list[str]') -> 'dict[str, float]'` | Portfolio factor exposures as weighted sum of asset loadings. |
| `compute_group_attribution` | function | `(position_returns: 'dict[str, float]', group_labels: 'dict[str, str]', position_weights: 'dict[str, float]') -> 'dict[str, float]'` | Contribution per group: S(w_i * r_i) for all i in group g. |
| `compute_max_drawdown` | function | `(cumulative_returns: 'np.ndarray', *, mode: "Literal['peak_to_trough', 'inception_to_trough']") -> 'tuple[float, int]'` | Maximum drawdown. |
| `compute_portfolio_risk` | function | `(weights: 'np.ndarray', covariance: 'CovarianceEstimate', *, confidence_level: 'float', security_ids: 'list[str] \| None') -> 'PortfolioRiskResult'` | Parametric portfolio risk metrics under a normal returns assumption. |
| `compute_sharpe_ratio` | function | `(excess_returns: 'np.ndarray', *, annualization: 'float') -> 'float'` | mean(excess) / std(excess) * sqrt(annualization). |
| `compute_sortino_ratio` | function | `(excess_returns: 'np.ndarray', *, annualization: 'float') -> 'float'` | mean(excess) / downside_std * sqrt(annualization). |
| `compute_turnover` | function | `(weights_today: 'np.ndarray', weights_yesterday: 'np.ndarray') -> 'float'` | One-way turnover: sum(\|Δw\|) / 2. |
| `CostModel` | class | `(linear_cost_bps: 'float', market_impact_bps: 'float') -> None` | Transaction cost parameters. |
| `CovarianceEstimate` | class | `(matrix: 'np.ndarray', n_obs: 'int', method: 'str') -> None` | Daily covariance matrix estimate with estimation metadata. |
| `estimate_trade_cost` | function | `(weight_change: 'np.ndarray', cost_model: 'CostModel') -> 'float'` | Estimate total portfolio-level transaction cost. |
| `FeaturePanel` | class | `(df: 'pl.DataFrame', universe_id: 'str', feature_date: 'date') -> None` | Cross-sectional feature table: one row per security, N feature columns. |
| `LimitDefinition` | class | `(limit_type: 'LimitType', limit: 'float', scope: 'list[int] \| None', group_id: 'str \| None') -> None` | Portfolio constraint specification. |
| `LimitType` | enum | `MAX_WEIGHT='MAX_WEIGHT', MIN_WEIGHT='MIN_WEIGHT', MAX_GROSS_EXPOSURE='MAX_GROSS_EXPOSURE', MAX_GROUP_WEIGHT='MAX_GROUP_WEIGHT', MAX_TURNOVER='MAX_TURNOVER', FULLY_INVESTED='FULLY_INVESTED'` | Portfolio constraint type. |
| `optimize` | function | `(alpha: 'np.ndarray', covariance: 'CovarianceEstimate', current_weights: 'np.ndarray', constraints: 'list[LimitDefinition]', *, cost_model: 'CostModel \| None', risk_aversion: 'float', mode: 'str', security_ids: 'list[str] \| None', portfolio_id: 'str', ref_date: 'date \| None') -> 'TargetPortfolio'` | Run portfolio optimization and return a TargetPortfolio result. |
| `optimize_equal_weight` | function | `(n_assets: 'int') -> 'np.ndarray'` | Allocate 1/N to each asset, ignoring alpha entirely. |
| `optimize_minimum_variance` | function | `(covariance: 'CovarianceEstimate', constraints: 'list[Any]') -> 'np.ndarray'` | Minimize portfolio variance subject to constraints. |
| `optimize_risk_parity` | function | `(covariance: 'CovarianceEstimate') -> 'np.ndarray'` | Find weights that equalize marginal risk contributions (long-only). |
| `PortfolioRiskResult` | class | `(portfolio_variance: 'float', portfolio_volatility_annual: 'float', var: 'float', es: 'float', confidence_level: 'float', risk_contributions: 'np.ndarray', security_ids: 'list[str] \| None') -> None` | Parametric portfolio risk metrics under a normal returns assumption. |
| `SignalVector` | class | `(df: 'pl.DataFrame', strategy_id: 'str', model_id: 'str', model_version: 'int', ref_date: 'date') -> None` | Alpha vector output from a signal generator. |
| `TargetPortfolio` | class | `(target_weights: 'np.ndarray', current_weights: 'np.ndarray', risk_contributions: 'np.ndarray', estimated_costs_bps: 'np.ndarray', trade_justified: 'np.ndarray', portfolio_id: 'str', ref_date: 'date \| None', security_ids: 'list[str] \| None') -> None` | Portfolio optimization result. |

## `treasuryutils.quanttools.analytics`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Alert` | class | `(level: 'str', limit_type: 'str', current_value: 'float', limit_value: 'float', action: 'str', message: 'str') -> None` | Immutable risk-limit breach notification. |
| `check_limit_breach` | function | `(current_value: 'float', limit_value: 'float', limit_type: 'str', *, alert_threshold_pct: 'float', breach_action: 'str') -> 'Alert \| None'` | Check whether current_value breaches or approaches a hard limit. |
| `compute_calmar_ratio` | function | `(annual_return: 'float', max_drawdown: 'float') -> 'float'` | annual_return / max_drawdown. |
| `compute_cost_attribution` | function | `(cost_components: 'dict[str, float]') -> 'dict[str, float]'` | Validate cost components and return them unchanged. |
| `compute_factor_attribution` | function | `(portfolio_weights: 'np.ndarray', factor_exposures: 'np.ndarray', factor_returns: 'np.ndarray', *, factor_names: 'list[str]') -> 'dict[str, float]'` | Contribution per factor: (S w_i * exposure_{i,k}) * factor_return_k. |
| `compute_group_attribution` | function | `(position_returns: 'dict[str, float]', group_labels: 'dict[str, str]', position_weights: 'dict[str, float]') -> 'dict[str, float]'` | Contribution per group: S(w_i * r_i) for all i in group g. |
| `compute_max_drawdown` | function | `(cumulative_returns: 'np.ndarray', *, mode: "Literal['peak_to_trough', 'inception_to_trough']") -> 'tuple[float, int]'` | Maximum drawdown. |
| `compute_sharpe_ratio` | function | `(excess_returns: 'np.ndarray', *, annualization: 'float') -> 'float'` | mean(excess) / std(excess) * sqrt(annualization). |
| `compute_sortino_ratio` | function | `(excess_returns: 'np.ndarray', *, annualization: 'float') -> 'float'` | mean(excess) / downside_std * sqrt(annualization). |
| `compute_turnover` | function | `(weights_today: 'np.ndarray', weights_yesterday: 'np.ndarray') -> 'float'` | One-way turnover: sum(\|Δw\|) / 2. |

## `treasuryutils.quanttools.analytics.attribution`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_cost_attribution` | function | `(cost_components: 'dict[str, float]') -> 'dict[str, float]'` | Validate cost components and return them unchanged. |
| `compute_factor_attribution` | function | `(portfolio_weights: 'np.ndarray', factor_exposures: 'np.ndarray', factor_returns: 'np.ndarray', *, factor_names: 'list[str]') -> 'dict[str, float]'` | Contribution per factor: (S w_i * exposure_{i,k}) * factor_return_k. |
| `compute_group_attribution` | function | `(position_returns: 'dict[str, float]', group_labels: 'dict[str, str]', position_weights: 'dict[str, float]') -> 'dict[str, float]'` | Contribution per group: S(w_i * r_i) for all i in group g. |

## `treasuryutils.quanttools.analytics.monitoring`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Alert` | class | `(level: 'str', limit_type: 'str', current_value: 'float', limit_value: 'float', action: 'str', message: 'str') -> None` | Immutable risk-limit breach notification. |
| `check_limit_breach` | function | `(current_value: 'float', limit_value: 'float', limit_type: 'str', *, alert_threshold_pct: 'float', breach_action: 'str') -> 'Alert \| None'` | Check whether current_value breaches or approaches a hard limit. |

## `treasuryutils.quanttools.analytics.performance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_calmar_ratio` | function | `(annual_return: 'float', max_drawdown: 'float') -> 'float'` | annual_return / max_drawdown. |
| `compute_inception_to_trough_drawdown` | function | `(cumulative_returns: 'np.ndarray') -> 'tuple[float, int]'` | Explicit alias for the inception-to-trough variant. |
| `compute_max_drawdown` | function | `(cumulative_returns: 'np.ndarray', *, mode: "Literal['peak_to_trough', 'inception_to_trough']") -> 'tuple[float, int]'` | Maximum drawdown. |
| `compute_sharpe_ratio` | function | `(excess_returns: 'np.ndarray', *, annualization: 'float') -> 'float'` | mean(excess) / std(excess) * sqrt(annualization). |
| `compute_sortino_ratio` | function | `(excess_returns: 'np.ndarray', *, annualization: 'float') -> 'float'` | mean(excess) / downside_std * sqrt(annualization). |
| `compute_turnover` | function | `(weights_today: 'np.ndarray', weights_yesterday: 'np.ndarray') -> 'float'` | One-way turnover: sum(\|Δw\|) / 2. |

## `treasuryutils.quanttools.domain`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ADFResult` | class | `(statistic: 'float', pvalue: 'float', used_lag: 'int', n_obs: 'int') -> None` | Result of the Augmented Dickey-Fuller test. |
| `BarPanel` | class | `(df: 'pl.DataFrame', security_ids: 'list[str]', start_date: 'date', end_date: 'date') -> None` | OHLCV + adjustment factor panel for N securities over T days. |
| `CointegrationResult` | class | `(hedge_ratio: 'float', statistic: 'float', pvalue: 'float') -> None` | Result of the Engle-Granger cointegration test. |
| `CovarianceEstimate` | class | `(matrix: 'np.ndarray', n_obs: 'int', method: 'str') -> None` | Daily covariance matrix estimate with estimation metadata. |
| `FeaturePanel` | class | `(df: 'pl.DataFrame', universe_id: 'str', feature_date: 'date') -> None` | Cross-sectional feature table: one row per security, N feature columns. |
| `LimitDefinition` | class | `(limit_type: 'LimitType', limit: 'float', scope: 'list[int] \| None', group_id: 'str \| None') -> None` | Portfolio constraint specification. |
| `LimitType` | enum | `MAX_WEIGHT='MAX_WEIGHT', MIN_WEIGHT='MIN_WEIGHT', MAX_GROSS_EXPOSURE='MAX_GROSS_EXPOSURE', MAX_GROUP_WEIGHT='MAX_GROUP_WEIGHT', MAX_TURNOVER='MAX_TURNOVER', FULLY_INVESTED='FULLY_INVESTED'` | Portfolio constraint type. |
| `PortfolioRiskResult` | class | `(portfolio_variance: 'float', portfolio_volatility_annual: 'float', var: 'float', es: 'float', confidence_level: 'float', risk_contributions: 'np.ndarray', security_ids: 'list[str] \| None') -> None` | Parametric portfolio risk metrics under a normal returns assumption. |
| `SignalVector` | class | `(df: 'pl.DataFrame', strategy_id: 'str', model_id: 'str', model_version: 'int', ref_date: 'date') -> None` | Alpha vector output from a signal generator. |
| `TargetPortfolio` | class | `(target_weights: 'np.ndarray', current_weights: 'np.ndarray', risk_contributions: 'np.ndarray', estimated_costs_bps: 'np.ndarray', trade_justified: 'np.ndarray', portfolio_id: 'str', ref_date: 'date \| None', security_ids: 'list[str] \| None') -> None` | Portfolio optimization result. |

## `treasuryutils.quanttools.domain.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ADFResult` | class | `(statistic: 'float', pvalue: 'float', used_lag: 'int', n_obs: 'int') -> None` | Result of the Augmented Dickey-Fuller test. |
| `BarPanel` | class | `(df: 'pl.DataFrame', security_ids: 'list[str]', start_date: 'date', end_date: 'date') -> None` | OHLCV + adjustment factor panel for N securities over T days. |
| `CointegrationResult` | class | `(hedge_ratio: 'float', statistic: 'float', pvalue: 'float') -> None` | Result of the Engle-Granger cointegration test. |
| `CovarianceEstimate` | class | `(matrix: 'np.ndarray', n_obs: 'int', method: 'str') -> None` | Daily covariance matrix estimate with estimation metadata. |
| `FeaturePanel` | class | `(df: 'pl.DataFrame', universe_id: 'str', feature_date: 'date') -> None` | Cross-sectional feature table: one row per security, N feature columns. |
| `LimitDefinition` | class | `(limit_type: 'LimitType', limit: 'float', scope: 'list[int] \| None', group_id: 'str \| None') -> None` | Portfolio constraint specification. |
| `LimitType` | enum | `MAX_WEIGHT='MAX_WEIGHT', MIN_WEIGHT='MIN_WEIGHT', MAX_GROSS_EXPOSURE='MAX_GROSS_EXPOSURE', MAX_GROUP_WEIGHT='MAX_GROUP_WEIGHT', MAX_TURNOVER='MAX_TURNOVER', FULLY_INVESTED='FULLY_INVESTED'` | Portfolio constraint type. |
| `PortfolioRiskResult` | class | `(portfolio_variance: 'float', portfolio_volatility_annual: 'float', var: 'float', es: 'float', confidence_level: 'float', risk_contributions: 'np.ndarray', security_ids: 'list[str] \| None') -> None` | Parametric portfolio risk metrics under a normal returns assumption. |
| `SignalVector` | class | `(df: 'pl.DataFrame', strategy_id: 'str', model_id: 'str', model_version: 'int', ref_date: 'date') -> None` | Alpha vector output from a signal generator. |
| `TargetPortfolio` | class | `(target_weights: 'np.ndarray', current_weights: 'np.ndarray', risk_contributions: 'np.ndarray', estimated_costs_bps: 'np.ndarray', trade_justified: 'np.ndarray', portfolio_id: 'str', ref_date: 'date \| None', security_ids: 'list[str] \| None') -> None` | Portfolio optimization result. |

## `treasuryutils.quanttools.engine`

_No public callables discovered._

## `treasuryutils.quanttools.engine.backtest_core`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_deflated_sharpe` | function | `(observed_sharpe: 'float', n_trials: 'int', n_observations: 'int', *, skewness: 'float', kurtosis: 'float') -> 'float'` | Bailey & López de Prado (2014) deflated Sharpe ratio. |
| `compute_min_backtest_years` | function | `(sharpe: 'float', *, confidence: 'float') -> 'float'` | Minimum years of backtest history for statistical significance. |
| `generate_walk_forward_windows` | function | `(start: 'date', end: 'date', *, train_years: 'int', val_years: 'int', step_years: 'int', mode: 'str', step: 'StepMode', step_freq: 'str', calendar_name: 'str') -> 'list[WalkForwardWindow]'` | Generate walk-forward windows for backtesting. |
| `iterate_business_days` | function | `(start: 'date', end: 'date', *, calendar: 'str \| None') -> 'Iterator[date]'` | Yield business days in [start, end] using calendartools. |
| `StepMode` | callable | `(*args, **kwargs)` |  |
| `WalkForwardWindow` | class | `(train_start: 'date', train_end: 'date', val_start: 'date', val_end: 'date', test_start: 'date', test_end: 'date') -> None` | One walk-forward split with train / validation / test boundaries. |

## `treasuryutils.quanttools.math`

_No public callables discovered._

## `treasuryutils.quanttools.math.covariance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `estimate_ewma_covariance` | function | `(returns: 'np.ndarray', *, lambda_: 'float \| None', freq: 'str', seeding: "Literal['prior_window', 'first_obs', 'full_sample', 'user']", seed_window: 'int', user_seed: 'np.ndarray \| None') -> 'CovarianceEstimate'` | Exponentially weighted moving average covariance estimator. |
| `estimate_ewma_sample_covariance` | function | `(returns: 'np.ndarray', *, alpha: 'float', window: 'int') -> 'CovarianceEstimate'` | EWMA weighted-sample covariance matrix from a (T, N) returns matrix. |
| `estimate_ledoit_wolf_covariance` | function | `(returns: 'np.ndarray') -> 'CovarianceEstimate'` | Ledoit-Wolf shrinkage covariance estimator. |
| `estimate_sample_covariance` | function | `(returns: 'np.ndarray', *, ddof: 'int') -> 'CovarianceEstimate'` | Sample covariance matrix from a (T, N) returns matrix. |

## `treasuryutils.quanttools.math.normalization`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `percentile_rank` | function | `(values: 'np.ndarray', *, axis: 'int') -> 'np.ndarray'` | Percentile rank within the cross-section, in ``[0.0, 1.0]``. |
| `robust_z_score` | function | `(values: 'np.ndarray', *, axis: 'int') -> 'np.ndarray'` | MAD-based robust z-score: ``(x - median) / (1.4826 * MAD)``. |
| `winsorize` | function | `(values: 'np.ndarray', *, bounds: 'float', axis: 'int') -> 'np.ndarray'` | Clip values at ``±bounds`` standard deviations from the mean. |
| `z_score` | function | `(values: 'np.ndarray', *, axis: 'int') -> 'np.ndarray'` | Standard z-score: ``(x - mean) / std``. |

## `treasuryutils.quanttools.math.returns`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `adjusted_price` | function | `(raw_price: 'Numeric', adj_factor: 'Numeric') -> 'Numeric'` | ``raw_price * adj_factor``. Applies the corporate action adjustment chain. |
| `arithmetic_return` | function | `(price_end: 'Numeric', price_start: 'Numeric') -> 'Numeric'` | ``(P_end / P_start) - 1``. Standard single-period return. |
| `cumulative_return` | function | `(prices: 'np.ndarray') -> 'np.ndarray'` | Cumulative return series from price array. First element is 0.0. |
| `excess_return` | function | `(portfolio_return: 'Numeric', benchmark_return: 'Numeric') -> 'Numeric'` | Arithmetic difference: ``portfolio - benchmark``. |
| `log_return` | function | `(price_end: 'Numeric', price_start: 'Numeric') -> 'Numeric'` | ``ln(P_end / P_start)``. Additive across time periods. |
| `returns_from_prices` | function | `(df: 'pl.DataFrame', *, price_col: 'str', adj_factor_col: 'str \| None', return_type: "Literal['arithmetic', 'log']", group_col: 'str \| None') -> 'pl.DataFrame'` | Compute returns from a price DataFrame. |

## `treasuryutils.quanttools.math.statistics`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `adf_test` | function | `(series: 'np.ndarray') -> 'ADFResult'` | Augmented Dickey-Fuller test for stationarity. |
| `ADFResult` | class | `(statistic: 'float', pvalue: 'float', used_lag: 'int', n_obs: 'int') -> None` | Result of the Augmented Dickey-Fuller test. |
| `CointegrationResult` | class | `(hedge_ratio: 'float', statistic: 'float', pvalue: 'float') -> None` | Result of the Engle-Granger cointegration test. |
| `engle_granger_test` | function | `(series_a: 'np.ndarray', series_b: 'np.ndarray') -> 'CointegrationResult'` | Engle-Granger two-step cointegration test. |
| `half_life` | function | `(series: 'np.ndarray', *, intercept: 'bool', demeaned: 'bool') -> 'float'` | Mean-reversion half-life from AR(1) regression. |
| `hurst_exponent` | function | `(series: 'np.ndarray', *, max_lag: 'int') -> 'float'` | Hurst exponent via R/S (Rescaled Range) analysis on increments. |

## `treasuryutils.quanttools.math.volatility`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_beta` | function | `(security_returns: 'np.ndarray', benchmark_returns: 'np.ndarray', *, window: 'int') -> 'tuple[np.ndarray, np.ndarray]'` | Rolling OLS beta and idiosyncratic volatility. |
| `ewma_volatility` | function | `(log_returns: 'np.ndarray', *, lambda_: 'float \| None', freq: 'str', annualize: 'bool', annualization_factor: 'float') -> 'np.ndarray'` | RiskMetrics EWMA: σ²_t = λ·σ²_{t-1} + (1-λ)·r²_t. |
| `parkinson_volatility` | function | `(high: 'np.ndarray', low: 'np.ndarray', *, window: 'int', annualize: 'bool', annualization_factor: 'float') -> 'np.ndarray'` | Parkinson (1980): σ² = (1/(4*ln(2))) * rolling_mean(ln(H/L)^2). |
| `realized_volatility` | function | `(log_returns: 'np.ndarray', *, window: 'int', annualize: 'bool', annualization_factor: 'float') -> 'np.ndarray'` | Rolling std(returns[t-window:t]) * sqrt(annualization_factor). |
| `yang_zhang_volatility` | function | `(open_: 'np.ndarray', high: 'np.ndarray', low: 'np.ndarray', close: 'np.ndarray', *, window: 'int', annualize: 'bool', annualization_factor: 'float') -> 'np.ndarray'` | Yang-Zhang (2000) three-component estimator. |

## `treasuryutils.quanttools.optimizer`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_constraints` | function | `(limits: 'list[LimitDefinition]', n_assets: 'int', weights_var: 'Any', *, current_weights: 'np.ndarray \| None', group_mapping: 'dict[str, list[int]] \| None') -> 'list[Any]'` | Translate LimitDefinition objects into cvxpy constraints. |
| `CostModel` | class | `(linear_cost_bps: 'float', market_impact_bps: 'float') -> None` | Transaction cost parameters. |
| `estimate_trade_cost` | function | `(weight_change: 'np.ndarray', cost_model: 'CostModel') -> 'float'` | Estimate total portfolio-level transaction cost. |
| `optimize` | function | `(alpha: 'np.ndarray', covariance: 'CovarianceEstimate', current_weights: 'np.ndarray', constraints: 'list[LimitDefinition]', *, cost_model: 'CostModel \| None', risk_aversion: 'float', mode: 'str', security_ids: 'list[str] \| None', portfolio_id: 'str', ref_date: 'date \| None') -> 'TargetPortfolio'` | Run portfolio optimization and return a TargetPortfolio result. |
| `optimize_equal_weight` | function | `(n_assets: 'int') -> 'np.ndarray'` | Allocate 1/N to each asset, ignoring alpha entirely. |
| `optimize_minimum_variance` | function | `(covariance: 'CovarianceEstimate', constraints: 'list[Any]') -> 'np.ndarray'` | Minimize portfolio variance subject to constraints. |
| `optimize_risk_parity` | function | `(covariance: 'CovarianceEstimate') -> 'np.ndarray'` | Find weights that equalize marginal risk contributions (long-only). |

## `treasuryutils.quanttools.optimizer.constraints`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_constraints` | function | `(limits: 'list[LimitDefinition]', n_assets: 'int', weights_var: 'Any', *, current_weights: 'np.ndarray \| None', group_mapping: 'dict[str, list[int]] \| None') -> 'list[Any]'` | Translate LimitDefinition objects into cvxpy constraints. |

## `treasuryutils.quanttools.optimizer.cost_model`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CostModel` | class | `(linear_cost_bps: 'float', market_impact_bps: 'float') -> None` | Transaction cost parameters. |
| `estimate_trade_cost` | function | `(weight_change: 'np.ndarray', cost_model: 'CostModel') -> 'float'` | Estimate total portfolio-level transaction cost. |

## `treasuryutils.quanttools.optimizer.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `optimize` | function | `(alpha: 'np.ndarray', covariance: 'CovarianceEstimate', current_weights: 'np.ndarray', constraints: 'list[LimitDefinition]', *, cost_model: 'CostModel \| None', risk_aversion: 'float', mode: 'str', security_ids: 'list[str] \| None', portfolio_id: 'str', ref_date: 'date \| None') -> 'TargetPortfolio'` | Run portfolio optimization and return a TargetPortfolio result. |

## `treasuryutils.quanttools.optimizer.modes`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `optimize_equal_weight` | function | `(n_assets: 'int') -> 'np.ndarray'` | Allocate 1/N to each asset, ignoring alpha entirely. |
| `optimize_minimum_variance` | function | `(covariance: 'CovarianceEstimate', constraints: 'list[Any]') -> 'np.ndarray'` | Minimize portfolio variance subject to constraints. |
| `optimize_risk_parity` | function | `(covariance: 'CovarianceEstimate') -> 'np.ndarray'` | Find weights that equalize marginal risk contributions (long-only). |

## `treasuryutils.quanttools.risk`

_No public callables discovered._

## `treasuryutils.quanttools.risk.portfolio_risk`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_factor_exposures` | function | `(weights: 'np.ndarray', factor_loadings: 'np.ndarray', *, factor_names: 'list[str]') -> 'dict[str, float]'` | Portfolio factor exposures as weighted sum of asset loadings. |
| `compute_portfolio_risk` | function | `(weights: 'np.ndarray', covariance: 'CovarianceEstimate', *, confidence_level: 'float', security_ids: 'list[str] \| None') -> 'PortfolioRiskResult'` | Parametric portfolio risk metrics under a normal returns assumption. |

## `treasuryutils.quanttools.risk.risk_model`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `RiskModel` | class | `(*args, **kwargs)` | Structural protocol for portfolio risk model providers. |
| `RiskModel.compute_risk` | function | `(weights: 'np.ndarray', covariance: 'CovarianceEstimate') -> 'PortfolioRiskResult'` | Compute portfolio risk metrics from *weights* and *covariance*. |
| `RiskModel.estimate_covariance` | function | `(security_ids: 'list[str]', as_of: 'date') -> 'CovarianceEstimate'` | Estimate the covariance matrix for *security_ids* as of *as_of*. |
