# EquityTools API Reference (generated)

- treasuryutils_version: `1.8.0`
- generated_at_utc: `2026-07-10T16:08:46.035900+00:00`
- install_extras: `treasuryutils[datatools,quant-math,quant-optimizer]`

## `treasuryutils.equitytools`

_No public callables discovered._

## `treasuryutils.equitytools.bridge`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `count_business_days` | function | `(start: 'date', end: 'date', *, calendar: 'str') -> 'int'` | Count workday boundaries crossed in (start, end]. |
| `get_business_days` | function | `(start: 'date', end: 'date', *, calendar: 'str') -> 'list[date]'` | Return business days in [start, end]. |
| `get_cdi_return` | function | `(start: 'date', end: 'date', *, market_data: 'Any') -> 'float'` | CDI accumulated return over [start, end]. |
| `is_trading_day` | function | `(d: 'date', *, calendar: 'str') -> 'bool'` | Check if d is a business day. |

## `treasuryutils.equitytools.bridge.benchmark`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `get_cdi_return` | function | `(start: 'date', end: 'date', *, market_data: 'Any') -> 'float'` | CDI accumulated return over [start, end]. |

## `treasuryutils.equitytools.bridge.calendar`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `count_business_days` | function | `(start: 'date', end: 'date', *, calendar: 'str') -> 'int'` | Count workday boundaries crossed in (start, end]. |
| `get_business_days` | function | `(start: 'date', end: 'date', *, calendar: 'str') -> 'list[date]'` | Return business days in [start, end]. |
| `is_trading_day` | function | `(d: 'date', *, calendar: 'str') -> 'bool'` | Check if d is a business day. |

## `treasuryutils.equitytools.domain`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `FundamentalSnapshot` | class | `(company_id: 'str', period_end: 'date', filing_date: 'date', revenue: 'float \| None', net_income: 'float \| None', ebitda: 'float \| None', total_equity: 'float \| None', total_assets: 'float \| None', total_debt: 'float \| None', shares_outstanding: 'float \| None', eps: 'float \| None', bvps: 'float \| None') -> None` | Point-in-time fundamental data for a single company-period. |
| `TTMFundamentals` | class | `(company_id: 'str', as_of: 'date', ttm_revenue: 'float \| None', ttm_net_income: 'float \| None', ttm_ebitda: 'float \| None', ttm_eps: 'float \| None', avg_equity: 'float \| None', avg_assets: 'float \| None', latest_total_debt: 'float \| None', latest_shares_outstanding: 'float \| None') -> None` | Trailing-twelve-month aggregation of 4 quarterly snapshots. |

## `treasuryutils.equitytools.domain.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `FundamentalSnapshot` | class | `(company_id: 'str', period_end: 'date', filing_date: 'date', revenue: 'float \| None', net_income: 'float \| None', ebitda: 'float \| None', total_equity: 'float \| None', total_assets: 'float \| None', total_debt: 'float \| None', shares_outstanding: 'float \| None', eps: 'float \| None', bvps: 'float \| None') -> None` | Point-in-time fundamental data for a single company-period. |
| `TTMFundamentals` | class | `(company_id: 'str', as_of: 'date', ttm_revenue: 'float \| None', ttm_net_income: 'float \| None', ttm_ebitda: 'float \| None', ttm_eps: 'float \| None', avg_equity: 'float \| None', avg_assets: 'float \| None', latest_total_debt: 'float \| None', latest_shares_outstanding: 'float \| None') -> None` | Trailing-twelve-month aggregation of 4 quarterly snapshots. |

## `treasuryutils.equitytools.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BacktestConfig` | class | `(start: 'date', end: 'date', universe_id: 'str', strategy_weights: 'dict[str, float]', risk_limits: 'list[LimitDefinition]', rebalance_frequency: 'RebalanceFrequency', cost_model: 'CostModel \| None', risk_aversion: 'float', covariance_method: 'str', optimization_mode: 'str', feature_lookback_days: 'int') -> None` | Configuration for an equity backtest run. |
| `BacktestEngine` | class | `()` | Equity backtest event loop. |
| `BacktestEngine.run` | function | `(config: 'BacktestConfig', market_data: 'EquityMarketDataSource', security_master: 'SecurityMaster') -> 'BacktestResult'` | Run the equity backtest event loop. |
| `BacktestResult` | class | `(daily_returns: 'np.ndarray', cumulative_returns: 'np.ndarray', sharpe_ratio: 'float', sortino_ratio: 'float', max_drawdown: 'float', max_drawdown_duration: 'int', total_turnover: 'float', total_cost_bps: 'float', n_rebalances: 'int', n_trades: 'int', positions_history: 'pl.DataFrame') -> None` | Aggregated results from a completed equity backtest. |
| `optimize_equity_portfolio` | function | `(combined_signal: 'SignalVector', market_data: 'EquityMarketDataSource', current_weights: 'dict[str, float]', risk_limits: 'list[LimitDefinition]', *, lookback_days: 'int', covariance_method: 'str', risk_aversion: 'float', cost_model: 'CostModel \| None', mode: 'str') -> 'TargetPortfolio'` | Equity optimization orchestrator. |

## `treasuryutils.equitytools.engine.backtest`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BacktestConfig` | class | `(start: 'date', end: 'date', universe_id: 'str', strategy_weights: 'dict[str, float]', risk_limits: 'list[LimitDefinition]', rebalance_frequency: 'RebalanceFrequency', cost_model: 'CostModel \| None', risk_aversion: 'float', covariance_method: 'str', optimization_mode: 'str', feature_lookback_days: 'int') -> None` | Configuration for an equity backtest run. |
| `BacktestEngine` | class | `()` | Equity backtest event loop. |
| `BacktestEngine.run` | function | `(config: 'BacktestConfig', market_data: 'EquityMarketDataSource', security_master: 'SecurityMaster') -> 'BacktestResult'` | Run the equity backtest event loop. |
| `BacktestResult` | class | `(daily_returns: 'np.ndarray', cumulative_returns: 'np.ndarray', sharpe_ratio: 'float', sortino_ratio: 'float', max_drawdown: 'float', max_drawdown_duration: 'int', total_turnover: 'float', total_cost_bps: 'float', n_rebalances: 'int', n_trades: 'int', positions_history: 'pl.DataFrame') -> None` | Aggregated results from a completed equity backtest. |
| `RebalanceFrequency` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.equitytools.engine.optimize`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `optimize_equity_portfolio` | function | `(combined_signal: 'SignalVector', market_data: 'EquityMarketDataSource', current_weights: 'dict[str, float]', risk_limits: 'list[LimitDefinition]', *, lookback_days: 'int', covariance_method: 'str', risk_aversion: 'float', cost_model: 'CostModel \| None', mode: 'str') -> 'TargetPortfolio'` | Equity optimization orchestrator. |

## `treasuryutils.equitytools.execution`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `check_risk_limits` | function | `(order: 'dict[str, Any]', current_positions: 'dict[str, float]', limits: 'list[LimitDefinition]') -> 'tuple[bool, str]'` | Simulate post-trade state and check all hard limits. |
| `check_tax_impact` | function | `(sell_orders: 'list[dict[str, Any]]', cost_basis: 'dict[str, float]', current_prices: 'dict[str, float]') -> 'list[dict[str, Any]]'` | Estimate Brazilian equity tax impact for a batch of sell orders. |
| `generate_orders` | function | `(target: 'TargetPortfolio', current_positions: 'dict[str, float]', security_master: 'SecurityMaster', *, min_trade_value: 'float') -> 'list[dict[str, Any]]'` | Generate orders from target vs current positions. |
| `round_to_lot` | function | `(raw_shares: 'float', lot_size: 'int') -> 'int'` | Round a raw share quantity to the nearest valid B3 lot. |
| `simulate_close_fill` | function | `(order: 'dict[str, Any]', close_price: 'float') -> 'dict[str, Any]'` | Simulate a fill at the closing price. |
| `simulate_vwap_fill` | function | `(order: 'dict[str, Any]', vwap: 'float', close_price: 'float') -> 'dict[str, Any]'` | Simulate a VWAP fill with implementation shortfall vs close. |

## `treasuryutils.equitytools.execution.fill_models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `simulate_close_fill` | function | `(order: 'dict[str, Any]', close_price: 'float') -> 'dict[str, Any]'` | Simulate a fill at the closing price. |
| `simulate_vwap_fill` | function | `(order: 'dict[str, Any]', vwap: 'float', close_price: 'float') -> 'dict[str, Any]'` | Simulate a VWAP fill with implementation shortfall vs close. |

## `treasuryutils.equitytools.execution.order_gen`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `generate_orders` | function | `(target: 'TargetPortfolio', current_positions: 'dict[str, float]', security_master: 'SecurityMaster', *, min_trade_value: 'float') -> 'list[dict[str, Any]]'` | Generate orders from target vs current positions. |
| `round_to_lot` | function | `(raw_shares: 'float', lot_size: 'int') -> 'int'` | Round a raw share quantity to the nearest valid B3 lot. |

## `treasuryutils.equitytools.execution.risk_check`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `check_risk_limits` | function | `(order: 'dict[str, Any]', current_positions: 'dict[str, float]', limits: 'list[LimitDefinition]') -> 'tuple[bool, str]'` | Simulate post-trade state and check all hard limits. |

## `treasuryutils.equitytools.execution.tax_check`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `check_tax_impact` | function | `(sell_orders: 'list[dict[str, Any]]', cost_basis: 'dict[str, float]', current_prices: 'dict[str, float]') -> 'list[dict[str, Any]]'` | Estimate Brazilian equity tax impact for a batch of sell orders. |

## `treasuryutils.equitytools.features`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `attach_liquidity_features` | function | `(panel: 'pl.DataFrame', *, adv_window: 'int') -> 'pl.DataFrame'` | Add: adv_21d (avg daily volume), turnover_21d, amihud_illiquidity. · Input columns: panel{security_id, close, volume, return -- sorted by (security_id, bar_date)} |
| `attach_momentum_features` | function | `(panel: 'pl.DataFrame', *, periods: 'tuple[int, ...]', skip: 'int') -> 'pl.DataFrame'` | Add momentum columns: mom_12m_1m, mom_6m_1m, mom_3m, mom_1m. · Input columns: panel{security_id, close (optional: adj_factor) -- sorted by (security_id, bar_date)} |
| `attach_quality_features` | function | `(panel: 'pl.DataFrame', fundamentals: 'list[TTMFundamentals]') -> 'pl.DataFrame'` | Add: roe, roic, gross_margin, leverage (debt/equity). · Input columns: panel{company_id -- TTM fundamentals joined by company_id (passed as the fundamentals argument)} |
| `attach_value_features` | function | `(panel: 'pl.DataFrame', fundamentals: 'list[TTMFundamentals]') -> 'pl.DataFrame'` | Add: earnings_yield, book_to_market, ebitda_to_ev. · Input columns: panel{company_id, close -- TTM fundamentals joined by company_id (passed as the fundamentals argument)} |
| `attach_volatility_features` | function | `(panel: 'pl.DataFrame', returns: 'np.ndarray', benchmark_returns: 'np.ndarray', security_ids: 'list[str]', *, vol_windows: 'tuple[int, ...]') -> 'pl.DataFrame'` | Add: realized_vol_Nd, beta, idiosyncratic_vol. · Input columns: panel{security_id, bar_date -- returns/benchmark passed as numpy arrays aligned to security_ids} |
| `compute_features` | function | `(security_ids: 'list[str]', as_of: 'date', market_data: 'EquityMarketDataSource', security_master: 'SecurityMaster', *, lookback_days: 'int', momentum_periods: 'tuple[int, ...]', momentum_skip: 'int', vol_windows: 'tuple[int, ...]', adv_window: 'int', strict: 'bool') -> 'FeaturePanel'` | Staged feature computation pipeline. |
| `normalize_cross_sectional` | function | `(panel: 'pl.DataFrame', *, feature_domains: 'dict[str, list[str]]', domain_weights: 'dict[str, float]') -> 'pl.DataFrame'` | Z-score each feature within the cross-section, winsorize, compute domain composites. · Input columns: panel{feature columns are caller-named via feature_domains; absent columns are skipped; expects one row per security} |

## `treasuryutils.equitytools.features.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_features` | function | `(security_ids: 'list[str]', as_of: 'date', market_data: 'EquityMarketDataSource', security_master: 'SecurityMaster', *, lookback_days: 'int', momentum_periods: 'tuple[int, ...]', momentum_skip: 'int', vol_windows: 'tuple[int, ...]', adv_window: 'int', strict: 'bool') -> 'FeaturePanel'` | Staged feature computation pipeline. |

## `treasuryutils.equitytools.features.liquidity`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `attach_liquidity_features` | function | `(panel: 'pl.DataFrame', *, adv_window: 'int') -> 'pl.DataFrame'` | Add: adv_21d (avg daily volume), turnover_21d, amihud_illiquidity. · Input columns: panel{security_id, close, volume, return -- sorted by (security_id, bar_date)} |

## `treasuryutils.equitytools.features.momentum`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `attach_momentum_features` | function | `(panel: 'pl.DataFrame', *, periods: 'tuple[int, ...]', skip: 'int') -> 'pl.DataFrame'` | Add momentum columns: mom_12m_1m, mom_6m_1m, mom_3m, mom_1m. · Input columns: panel{security_id, close (optional: adj_factor) -- sorted by (security_id, bar_date)} |

## `treasuryutils.equitytools.features.normalization`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `normalize_cross_sectional` | function | `(panel: 'pl.DataFrame', *, feature_domains: 'dict[str, list[str]]', domain_weights: 'dict[str, float]') -> 'pl.DataFrame'` | Z-score each feature within the cross-section, winsorize, compute domain composites. · Input columns: panel{feature columns are caller-named via feature_domains; absent columns are skipped; expects one row per security} |

## `treasuryutils.equitytools.features.quality`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `attach_quality_features` | function | `(panel: 'pl.DataFrame', fundamentals: 'list[TTMFundamentals]') -> 'pl.DataFrame'` | Add: roe, roic, gross_margin, leverage (debt/equity). · Input columns: panel{company_id -- TTM fundamentals joined by company_id (passed as the fundamentals argument)} |

## `treasuryutils.equitytools.features.value`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `attach_value_features` | function | `(panel: 'pl.DataFrame', fundamentals: 'list[TTMFundamentals]') -> 'pl.DataFrame'` | Add: earnings_yield, book_to_market, ebitda_to_ev. · Input columns: panel{company_id, close -- TTM fundamentals joined by company_id (passed as the fundamentals argument)} |

## `treasuryutils.equitytools.features.volatility_features`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `attach_volatility_features` | function | `(panel: 'pl.DataFrame', returns: 'np.ndarray', benchmark_returns: 'np.ndarray', security_ids: 'list[str]', *, vol_windows: 'tuple[int, ...]') -> 'pl.DataFrame'` | Add: realized_vol_Nd, beta, idiosyncratic_vol. · Input columns: panel{security_id, bar_date -- returns/benchmark passed as numpy arrays aligned to security_ids} |

## `treasuryutils.equitytools.market_data`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BacktestEquityMarketDataSource` | class | `(source: 'EquityMarketDataSource') -> 'None'` | Wraps any EquityMarketDataSource with a time frontier. |
| `BacktestEquityMarketDataSource.get_corporate_actions` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` |  |
| `BacktestEquityMarketDataSource.get_daily_bars` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'BarPanel'` |  |
| `BacktestEquityMarketDataSource.get_fundamentals_pit` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[FundamentalSnapshot]'` |  |
| `BacktestEquityMarketDataSource.get_intraday_bars` | function | `(security_ids: 'list[str]', bar_date: 'date', *, interval_minutes: 'int') -> 'BarPanel'` |  |
| `BacktestEquityMarketDataSource.get_news_events` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` |  |
| `BacktestEquityMarketDataSource.get_reference_data` | function | `(security_ids: 'list[str]') -> 'pl.DataFrame'` |  |
| `BacktestEquityMarketDataSource.get_ttm_fundamentals` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[TTMFundamentals]'` |  |
| `BacktestEquityMarketDataSource.set_time_frontier` | function | `(frontier: 'date') -> 'None'` | Advance the simulation time frontier. |
| `BarDatasetSpec` | class | `(dataset_name: 'str', security_id_col: 'str', date_col: 'str', open_col: 'str', high_col: 'str', low_col: 'str', close_col: 'str', volume_col: 'str', adj_factor_col: 'str \| None') -> None` | Mapping from a raw dataset to BarPanel. |
| `BarPanel` | class | `(df: 'pl.DataFrame', security_ids: 'list[str]', start_date: 'date', end_date: 'date') -> None` | OHLCV + adjustment factor panel for N securities over T days. |
| `DatatoolsEquityMarketDataSource` | class | `(*, reader: '_DatasetReader \| None') -> 'None'` | EquityMarketDataSource backed by DataTools materialized datasets. |
| `DatatoolsEquityMarketDataSource.get_corporate_actions` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return corporate actions (splits, dividends) in [start, end]. |
| `DatatoolsEquityMarketDataSource.get_daily_bars` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'BarPanel'` | Return OHLCV + adj_factor for securities over [start, end]. |
| `DatatoolsEquityMarketDataSource.get_fundamentals_pit` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[FundamentalSnapshot]'` | Return point-in-time fundamentals: only data with filing_date <= as_of. |
| `DatatoolsEquityMarketDataSource.get_intraday_bars` | function | `(security_ids: 'list[str]', bar_date: 'date', *, interval_minutes: 'int') -> 'BarPanel'` | Return intraday OHLCV bars for a single trading session date. |
| `DatatoolsEquityMarketDataSource.get_news_events` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return news/sentiment events in [start, end]. |
| `DatatoolsEquityMarketDataSource.get_reference_data` | function | `(security_ids: 'list[str]') -> 'pl.DataFrame'` | Return static reference data (sector, lot_size, market_cap_category). |
| `DatatoolsEquityMarketDataSource.get_ttm_fundamentals` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[TTMFundamentals]'` | Return trailing 12-month aggregation of quarterly snapshots as of date. |
| `EquityMarketDataBackendError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an underlying backend read fails. |
| `EquityMarketDataContractError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an input/output contract is violated. |
| `EquityMarketDataError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base class for equity market-data related errors. |
| `EquityMarketDataNotFoundError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when a requested market-data identifier does not exist. |
| `EquityMarketDataSource` | class | `(*args, **kwargs)` | Read-only equity market data boundary. |
| `EquityMarketDataSource.get_corporate_actions` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return corporate actions (splits, dividends) in [start, end]. |
| `EquityMarketDataSource.get_daily_bars` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'BarPanel'` | Return OHLCV + adj_factor for securities over [start, end]. |
| `EquityMarketDataSource.get_fundamentals_pit` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[FundamentalSnapshot]'` | Return point-in-time fundamentals: only data with filing_date <= as_of. |
| `EquityMarketDataSource.get_intraday_bars` | function | `(security_ids: 'list[str]', bar_date: 'date', *, interval_minutes: 'int') -> 'BarPanel'` | Return intraday OHLCV bars for a single trading session date. |
| `EquityMarketDataSource.get_news_events` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return news/sentiment events in [start, end]. |
| `EquityMarketDataSource.get_reference_data` | function | `(security_ids: 'list[str]') -> 'pl.DataFrame'` | Return static reference data (sector, lot_size, market_cap_category). |
| `EquityMarketDataSource.get_ttm_fundamentals` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[TTMFundamentals]'` | Return trailing 12-month aggregation of quarterly snapshots as of date. |
| `EquityMarketDataValidationError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when canonical invariant validation fails. |
| `FundamentalDatasetSpec` | class | `(dataset_name: 'str', company_id_col: 'str', period_end_col: 'str', filing_date_col: 'str', field_mapping: 'dict[str, str]') -> None` | Mapping from a raw dataset to FundamentalSnapshot. |
| `FundamentalSnapshot` | class | `(company_id: 'str', period_end: 'date', filing_date: 'date', revenue: 'float \| None', net_income: 'float \| None', ebitda: 'float \| None', total_equity: 'float \| None', total_assets: 'float \| None', total_debt: 'float \| None', shares_outstanding: 'float \| None', eps: 'float \| None', bvps: 'float \| None') -> None` | Point-in-time fundamental data for a single company-period. |
| `InMemoryEquityMarketDataSource` | class | `(*, datasets: 'dict[str, pl.DataFrame]', daily_bar_spec: 'BarDatasetSpec', fundamental_spec: 'FundamentalDatasetSpec', intraday_bar_spec: 'BarDatasetSpec \| None', corporate_actions_dataset: 'str', news_events_dataset: 'str', reference_data_dataset: 'str') -> 'None'` | Pure in-memory EquityMarketDataSource for testing and local experimentation. |
| `InMemoryEquityMarketDataSource.get_corporate_actions` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return corporate actions (splits, dividends) in [start, end]. |
| `InMemoryEquityMarketDataSource.get_daily_bars` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'BarPanel'` | Return OHLCV + adj_factor for securities over [start, end]. |
| `InMemoryEquityMarketDataSource.get_fundamentals_pit` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[FundamentalSnapshot]'` | Return point-in-time fundamentals: only data with filing_date <= as_of. |
| `InMemoryEquityMarketDataSource.get_intraday_bars` | function | `(security_ids: 'list[str]', bar_date: 'date', *, interval_minutes: 'int') -> 'BarPanel'` | Return intraday OHLCV bars for a single trading session date. |
| `InMemoryEquityMarketDataSource.get_news_events` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return news/sentiment events in [start, end]. |
| `InMemoryEquityMarketDataSource.get_reference_data` | function | `(security_ids: 'list[str]') -> 'pl.DataFrame'` | Return static reference data (sector, lot_size, market_cap_category). |
| `InMemoryEquityMarketDataSource.get_ttm_fundamentals` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[TTMFundamentals]'` | Return trailing 12-month aggregation of quarterly snapshots as of date. |
| `TTMFundamentals` | class | `(company_id: 'str', as_of: 'date', ttm_revenue: 'float \| None', ttm_net_income: 'float \| None', ttm_ebitda: 'float \| None', ttm_eps: 'float \| None', avg_equity: 'float \| None', avg_assets: 'float \| None', latest_total_debt: 'float \| None', latest_shares_outstanding: 'float \| None') -> None` | Trailing-twelve-month aggregation of 4 quarterly snapshots. |

## `treasuryutils.equitytools.market_data.adapters`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `RawFrameReader` | class | `(*args, **kwargs)` | Protocol for adapters that can read raw frames by dataset name. |
| `RawFrameReader.read` | function | `(*, dataset_name: 'str', columns: 'tuple[str, ...] \| None') -> 'pl.DataFrame'` | Return a DataFrame for the given dataset, optionally projected to *columns*. |

## `treasuryutils.equitytools.market_data.adapters.datatools`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DatatoolsEquityAdapter` | class | `(*, memory_map: 'bool') -> 'None'` | Raw-frame adapter backed by DataTools DatasetManager handles. |
| `DatatoolsEquityAdapter.clear_cache` | function | `() -> 'None'` | Discard all cached DatasetManager instances. |
| `DatatoolsEquityAdapter.read` | function | `(*, dataset_name: 'str', columns: 'tuple[str, ...] \| None') -> 'pl.DataFrame'` | Read a dataset from the DataTools cache, raising on backend failures. |

## `treasuryutils.equitytools.market_data.adapters.in_memory`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `InMemoryEquityAdapter` | class | `(*, datasets: 'Mapping[str, pl.DataFrame]') -> 'None'` | Raw-frame adapter backed by in-memory DataFrame dictionaries. |
| `InMemoryEquityAdapter.read` | function | `(*, dataset_name: 'str', columns: 'tuple[str, ...] \| None') -> 'pl.DataFrame'` | Return a DataFrame from the in-memory store, raising if missing. |

## `treasuryutils.equitytools.market_data.errors`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `EquityMarketDataBackendError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an underlying backend read fails. |
| `EquityMarketDataContractError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an input/output contract is violated. |
| `EquityMarketDataError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base class for equity market-data related errors. |
| `EquityMarketDataNotFoundError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when a requested market-data identifier does not exist. |
| `EquityMarketDataValidationError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when canonical invariant validation fails. |

## `treasuryutils.equitytools.market_data.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BarPanel` | class | `(df: 'pl.DataFrame', security_ids: 'list[str]', start_date: 'date', end_date: 'date') -> None` | OHLCV + adjustment factor panel for N securities over T days. |
| `FundamentalSnapshot` | class | `(company_id: 'str', period_end: 'date', filing_date: 'date', revenue: 'float \| None', net_income: 'float \| None', ebitda: 'float \| None', total_equity: 'float \| None', total_assets: 'float \| None', total_debt: 'float \| None', shares_outstanding: 'float \| None', eps: 'float \| None', bvps: 'float \| None') -> None` | Point-in-time fundamental data for a single company-period. |
| `TTMFundamentals` | class | `(company_id: 'str', as_of: 'date', ttm_revenue: 'float \| None', ttm_net_income: 'float \| None', ttm_ebitda: 'float \| None', ttm_eps: 'float \| None', avg_equity: 'float \| None', avg_assets: 'float \| None', latest_total_debt: 'float \| None', latest_shares_outstanding: 'float \| None') -> None` | Trailing-twelve-month aggregation of 4 quarterly snapshots. |

## `treasuryutils.equitytools.market_data.normalizers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `empty_bar_panel` | function | `(start_date: 'date', end_date: 'date') -> 'BarPanel'` | Return an empty BarPanel with the canonical schema. |
| `normalize_bar_panel` | function | `(raw: 'pl.DataFrame', spec: 'BarDatasetSpec', security_ids: 'list[str]', start: 'date', end: 'date') -> 'BarPanel'` | Normalize raw OHLCV rows into a canonical BarPanel. |
| `normalize_corporate_actions` | function | `(raw: 'pl.DataFrame', security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Validate and filter corporate actions to the requested window. |
| `normalize_fundamental_snapshots` | function | `(raw: 'pl.DataFrame', spec: 'FundamentalDatasetSpec', company_ids: 'list[str]', as_of: 'date') -> 'list[FundamentalSnapshot]'` | Normalize raw fundamental rows to FundamentalSnapshot, enforcing PIT discipline. |
| `normalize_news_events` | function | `(raw: 'pl.DataFrame', security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Validate and filter news events to the requested window. |
| `normalize_reference_data` | function | `(raw: 'pl.DataFrame', security_ids: 'list[str]') -> 'pl.DataFrame'` | Validate and filter reference data to the requested securities. |
| `normalize_ttm_fundamentals` | function | `(raw: 'pl.DataFrame', spec: 'FundamentalDatasetSpec', company_ids: 'list[str]', as_of: 'date') -> 'list[TTMFundamentals]'` | Aggregate 4 most recent PIT-filtered quarterly snapshots into TTM fundamentals. |

## `treasuryutils.equitytools.market_data.protocol`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `EquityMarketDataSource` | class | `(*args, **kwargs)` | Read-only equity market data boundary. |
| `EquityMarketDataSource.get_corporate_actions` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return corporate actions (splits, dividends) in [start, end]. |
| `EquityMarketDataSource.get_daily_bars` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'BarPanel'` | Return OHLCV + adj_factor for securities over [start, end]. |
| `EquityMarketDataSource.get_fundamentals_pit` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[FundamentalSnapshot]'` | Return point-in-time fundamentals: only data with filing_date <= as_of. |
| `EquityMarketDataSource.get_intraday_bars` | function | `(security_ids: 'list[str]', bar_date: 'date', *, interval_minutes: 'int') -> 'BarPanel'` | Return intraday OHLCV bars for a single trading session date. |
| `EquityMarketDataSource.get_news_events` | function | `(security_ids: 'list[str]', start: 'date', end: 'date') -> 'pl.DataFrame'` | Return news/sentiment events in [start, end]. |
| `EquityMarketDataSource.get_reference_data` | function | `(security_ids: 'list[str]') -> 'pl.DataFrame'` | Return static reference data (sector, lot_size, market_cap_category). |
| `EquityMarketDataSource.get_ttm_fundamentals` | function | `(company_ids: 'list[str]', as_of: 'date') -> 'list[TTMFundamentals]'` | Return trailing 12-month aggregation of quarterly snapshots as of date. |

## `treasuryutils.equitytools.market_data.specs`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BarDatasetSpec` | class | `(dataset_name: 'str', security_id_col: 'str', date_col: 'str', open_col: 'str', high_col: 'str', low_col: 'str', close_col: 'str', volume_col: 'str', adj_factor_col: 'str \| None') -> None` | Mapping from a raw dataset to BarPanel. |
| `FundamentalDatasetSpec` | class | `(dataset_name: 'str', company_id_col: 'str', period_end_col: 'str', filing_date_col: 'str', field_mapping: 'dict[str, str]') -> None` | Mapping from a raw dataset to FundamentalSnapshot. |

## `treasuryutils.equitytools.reference`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CompanyInfo` | class | `(company_id: 'str', company_name: 'str', cnpj: 'str \| None', sector: 'str \| None', subsector: 'str \| None') -> None` | Static company reference data. |
| `InMemorySecurityMaster` | class | `(*, securities: 'dict[str, SecurityInfo]', companies: 'dict[str, CompanyInfo]', identifiers: 'dict[tuple[str, str], str]', universes: 'dict[str, list[UniverseMember]]') -> 'None'` | SecurityMaster backed by plain dicts — no I/O, no dependencies. |
| `InMemorySecurityMaster.get_company` | function | `(company_id: 'str') -> 'CompanyInfo'` | Return company reference data. |
| `InMemorySecurityMaster.get_company_securities` | function | `(company_id: 'str') -> 'list[str]'` | Return all security_ids for a company (ON/PN pair discovery). |
| `InMemorySecurityMaster.get_security` | function | `(security_id: 'str') -> 'SecurityInfo'` | Return static reference data for a security. |
| `InMemorySecurityMaster.get_universe` | function | `(universe_id: 'str', as_of: 'date') -> 'list[UniverseMember]'` | Return universe composition at a point in time. |
| `InMemorySecurityMaster.resolve_identifier` | function | `(id_type: 'str', id_value: 'str', *, as_of: 'date \| None') -> 'str \| None'` | Resolve an external identifier to security_id. |
| `SecurityInfo` | class | `(security_id: 'str', ticker: 'str', company_id: 'str', security_type: 'str', share_class: 'str \| None', company_name: 'str', sector: 'str \| None', lot_size: 'int', currency: 'str', related_security_id: 'str \| None') -> None` | Static reference data for a single security. |
| `SecurityMaster` | class | `(*args, **kwargs)` | Read-only reference data boundary for equity securities. |
| `SecurityMaster.get_company` | function | `(company_id: 'str') -> 'CompanyInfo'` | Return company reference data. |
| `SecurityMaster.get_company_securities` | function | `(company_id: 'str') -> 'list[str]'` | Return all security_ids for a company (ON/PN pair discovery). |
| `SecurityMaster.get_security` | function | `(security_id: 'str') -> 'SecurityInfo'` | Return static reference data for a security. |
| `SecurityMaster.get_universe` | function | `(universe_id: 'str', as_of: 'date') -> 'list[UniverseMember]'` | Return universe composition at a point in time. |
| `SecurityMaster.resolve_identifier` | function | `(id_type: 'str', id_value: 'str', *, as_of: 'date \| None') -> 'str \| None'` | Resolve an external identifier to security_id. |
| `UniverseMember` | class | `(security_id: 'str', weight: 'float', inclusion_date: 'date', exclusion_date: 'date \| None') -> None` | A security's membership in a universe at a point in time. |

## `treasuryutils.equitytools.reference.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CompanyInfo` | class | `(company_id: 'str', company_name: 'str', cnpj: 'str \| None', sector: 'str \| None', subsector: 'str \| None') -> None` | Static company reference data. |
| `SecurityInfo` | class | `(security_id: 'str', ticker: 'str', company_id: 'str', security_type: 'str', share_class: 'str \| None', company_name: 'str', sector: 'str \| None', lot_size: 'int', currency: 'str', related_security_id: 'str \| None') -> None` | Static reference data for a single security. |
| `UniverseMember` | class | `(security_id: 'str', weight: 'float', inclusion_date: 'date', exclusion_date: 'date \| None') -> None` | A security's membership in a universe at a point in time. |

## `treasuryutils.equitytools.reference.protocol`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `SecurityMaster` | class | `(*args, **kwargs)` | Read-only reference data boundary for equity securities. |
| `SecurityMaster.get_company` | function | `(company_id: 'str') -> 'CompanyInfo'` | Return company reference data. |
| `SecurityMaster.get_company_securities` | function | `(company_id: 'str') -> 'list[str]'` | Return all security_ids for a company (ON/PN pair discovery). |
| `SecurityMaster.get_security` | function | `(security_id: 'str') -> 'SecurityInfo'` | Return static reference data for a security. |
| `SecurityMaster.get_universe` | function | `(universe_id: 'str', as_of: 'date') -> 'list[UniverseMember]'` | Return universe composition at a point in time. |
| `SecurityMaster.resolve_identifier` | function | `(id_type: 'str', id_value: 'str', *, as_of: 'date \| None') -> 'str \| None'` | Resolve an external identifier to security_id. |

## `treasuryutils.equitytools.schema`

_No public callables discovered._

## `treasuryutils.equitytools.schema.definitions`

_No public callables discovered._

## `treasuryutils.equitytools.signals`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_signal_vector` | function | `(signals_df: 'pl.DataFrame', strategy_id: 'str', model_id: 'str', model_version: 'int', ref_date: 'date') -> 'SignalVector'` | Validate and package a signals DataFrame into a SignalVector container. |
| `combine_signals` | function | `(signals: 'dict[str, SignalVector]', weights: 'dict[str, float]', *, portfolio_id: 'str', ref_date: 'date \| None') -> 'SignalVector'` | Merge signals from active sleeves into unified alpha vector. |
| `generate_factor_signal` | function | `(features: 'FeaturePanel', *, strategy_id: 'str', model_id: 'str', model_version: 'int') -> 'SignalVector'` | Factor model signal: alpha = z_composite from FeaturePanel. |
| `generate_pairs_signal` | function | `(pairs: 'list[dict[str, Any]]', price_panel: 'pl.DataFrame', kalman_states: 'dict[str, KalmanState]', *, entry_z: 'float', exit_z: 'float', stop_z: 'float', strategy_id: 'str', model_id: 'str', model_version: 'int', ref_date: 'datetime.date \| None') -> 'tuple[SignalVector, dict[str, KalmanState]]'` | For each pair: update Kalman, compute spread z-score, map to signal. |
| `generate_sentiment_signal` | function | `(news_events: 'pl.DataFrame', ref_date: 'date', *, half_life_hours: 'float') -> 'SignalVector'` | Per-security sentiment score from recent news events. |
| `kalman_update` | function | `(state: 'KalmanState', observation_a: 'float', observation_b: 'float') -> 'KalmanState'` | Single Kalman filter update step for the hedge ratio. |
| `KalmanState` | class | `(beta: 'float', P: 'float', Q: 'float', R: 'float') -> None` | Kalman filter state for dynamic hedge ratio estimation. |
| `screen_pairs` | function | `(security_ids: 'list[str]', returns_panel: 'pl.DataFrame', security_master: 'SecurityMaster', *, adf_threshold: 'float', min_half_life: 'float', max_half_life: 'float', min_correlation: 'float') -> 'list[dict[str, Any]]'` | Screen for cointegrated pairs using Engle-Granger test. |

## `treasuryutils.equitytools.signals.combiner`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `combine_signals` | function | `(signals: 'dict[str, SignalVector]', weights: 'dict[str, float]', *, portfolio_id: 'str', ref_date: 'date \| None') -> 'SignalVector'` | Merge signals from active sleeves into unified alpha vector. |

## `treasuryutils.equitytools.signals.factor_model`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `generate_factor_signal` | function | `(features: 'FeaturePanel', *, strategy_id: 'str', model_id: 'str', model_version: 'int') -> 'SignalVector'` | Factor model signal: alpha = z_composite from FeaturePanel. |

## `treasuryutils.equitytools.signals.pair_screening`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `screen_pairs` | function | `(security_ids: 'list[str]', returns_panel: 'pl.DataFrame', security_master: 'SecurityMaster', *, adf_threshold: 'float', min_half_life: 'float', max_half_life: 'float', min_correlation: 'float') -> 'list[dict[str, Any]]'` | Screen for cointegrated pairs using Engle-Granger test. |

## `treasuryutils.equitytools.signals.pairs`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `generate_pairs_signal` | function | `(pairs: 'list[dict[str, Any]]', price_panel: 'pl.DataFrame', kalman_states: 'dict[str, KalmanState]', *, entry_z: 'float', exit_z: 'float', stop_z: 'float', strategy_id: 'str', model_id: 'str', model_version: 'int', ref_date: 'datetime.date \| None') -> 'tuple[SignalVector, dict[str, KalmanState]]'` | For each pair: update Kalman, compute spread z-score, map to signal. |
| `kalman_update` | function | `(state: 'KalmanState', observation_a: 'float', observation_b: 'float') -> 'KalmanState'` | Single Kalman filter update step for the hedge ratio. |
| `KalmanState` | class | `(beta: 'float', P: 'float', Q: 'float', R: 'float') -> None` | Kalman filter state for dynamic hedge ratio estimation. |

## `treasuryutils.equitytools.signals.sentiment`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `generate_sentiment_signal` | function | `(news_events: 'pl.DataFrame', ref_date: 'date', *, half_life_hours: 'float') -> 'SignalVector'` | Per-security sentiment score from recent news events. |
