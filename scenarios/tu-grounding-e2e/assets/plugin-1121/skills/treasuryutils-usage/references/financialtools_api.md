# FinancialTools API Reference (generated)

- treasuryutils_version: `1.5.2.dev174+g64f80dc79`
- generated_at_utc: `2026-07-09T20:04:53.120267+00:00`
- install_extras: `treasuryutils[pricing]`

## `treasuryutils.financialtools`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Agreement` | class | `(*, agreement_id: typing.Annotated[str, MinLen(min_length=1)], agreement_type: treasuryutils.financialtools.domain.identifiers.AgreementType, entity_id: typing.Annotated[str, MinLen(min_length=1)], counterparty_entity_id: typing.Annotated[str, MinLen(min_length=1)], effective_date: datetime.date, maturity_date: datetime.date \| None, notional_limit: typing.Annotated[decimal.Decimal, Gt(gt=0)], currency: treasuryutils.financialtools.domain.identifiers.Currency, base_index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, base_spread: decimal.Decimal \| None, allowed_instrument_types: tuple[treasuryutils.financialtools.domain.identifiers.InstrumentType, ...] \| None, min_tenor_days: int \| None, max_tenor_days: int \| None, status: treasuryutils.financialtools.domain.identifiers.AgreementStatus) -> None` | Master framework that groups instruments by commercial relationship. |
| `AmortizationType` | enum | `BULLET='BULLET', SAC='SAC', PRICE='PRICE', CUSTOM='CUSTOM'` | Principal repayment pattern for an instrument leg. |
| `BookClassification` | class | `(*, instrument_id: typing.Annotated[str, MinLen(min_length=1)], book: str, desk: str \| None, strategy: str \| None) -> None` | Managerial/business classification for reporting and grouping. |
| `build_cashflow_projection` | function | `(priced_cashflows: 'Any', positions_df: 'Any', *, fx_rates: 'dict[str, float] \| None', base_currency: 'str', instrument_col: 'str', validate: 'bool') -> 'Any'` | Build FX-aware cashflow projection from priced cashflows. |
| `build_unified_position` | function | `(position_values: 'Any', pnl_attribution: 'Any \| None', risk_metrics: 'Any \| None', period_settlements: 'Any \| None', leg_decomposition: 'Any \| None', period_results: 'Any \| None', *, metadata: 'Any \| None', ref_date_prev: 'Any', validate: 'bool') -> 'Any'` | Assemble unified position from pre-computed pipeline outputs. |
| `CashFlowSchedule` | class | `(*, schedule_id: str, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, terms_id: str, terms_version: int, cashflows: treasuryutils.financialtools.instruments.models.DataFrameLike) -> None` | Versioned expected cash-flow schedule. |
| `compute_key_rate_risk` | function | `(cashflow_df: 'Any', ref_date: 'date', *, discount_curve: 'Any', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', bump_size: 'float', vertices: 'Sequence[date] \| None', validate: 'bool') -> 'Any'` | Compute key-rate DV01 per curve vertex and deal. |
| `compute_pnl_attribution` | function | `(summary_current: 'Any', summary_previous: 'Any', risk_previous: 'Any', *, rate_change: 'float \| Any', overnight_rate: 'float', overnight_rate_previous: 'float', ref_date: 'date', dollar_convexity: 'float \| Any', is_new_deal_mask: 'Any \| None', fx_rate: 'float \| Any', fx_rate_previous: 'float \| Any', present_value_ccy: 'float \| Any', accrued_interest_ccy: 'float \| Any', bump_size: 'float', convexity: 'float \| Any', validate: 'bool') -> 'Any'` | Decompose daily P&L into carry, rate, convexity, FX, and residual components. |
| `compute_portfolio_risk` | function | `(key_rate_dv01: 'Any', rate_history: 'np.ndarray', *, portfolio_id: 'str', ref_date: 'date', confidence_level: 'float', ewma_decay: 'float', observation_window: 'int', base_currency: 'str', fx_rates: 'Mapping[str, float] \| None') -> 'dict[str, Any]'` | Compute parametric VaR and DV01 aggregates for a portfolio. |
| `compute_portfolio_risk_from_df` | function | `(key_rate_dv01_df: 'Any', rate_change_df: 'Any', *, portfolio_id: 'str', ref_date: 'date', confidence_level: 'float', ewma_decay: 'float', observation_window: 'int', base_currency: 'str', fx_rates: 'Mapping[str, float] \| None', validate: 'bool') -> 'Any'` | Compute portfolio VaR from DataFrames. |
| `compute_risk_metrics` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', bump_size: 'float', bump_projection: 'bool', validate: 'bool') -> 'Any'` | Compute duration and DV01 via bump-and-revalue per (deal_id, ref_date). |
| `decode_instrument` | function | `(source: 'str \| Path \| dict[str, Any]', *, id_generator: 'IdGenerator \| None', seen_names: 'dict[str, int] \| None', generate_schedule: 'bool', calendar: 'object') -> 'DecodedInstrument'` | Decode a human-friendly YAML into the full graph of Pydantic models. |
| `decode_instruments` | function | `(sources: 'list[str \| Path \| dict[str, Any]]', *, id_generator: 'IdGenerator \| None', generate_schedule: 'bool', calendar: 'object') -> 'list[DecodedInstrument]'` | Decode multiple YAML definitions, sharing a single ID generator. |
| `DecodedInstrument` | class | `(instrument: 'Instrument', terms: 'InstrumentTerms', schedule: 'CashFlowSchedule \| None', position: 'Position \| None', book_classification: 'BookClassification \| None', accounting_designation: 'AccountingDesignation \| None', measurement_config: 'MeasurementConfig \| None', ecl_parameters: 'ECLParameters \| None') -> None` | All domain objects decoded from a single YAML instrument definition. |
| `EntityGroup` | class | `(*, group_id: str, parent_entity_id: str, child_entity_id: str, ownership_pct: typing.Annotated[decimal.Decimal, Gt(gt=0), Le(le=1)], consolidation_method: treasuryutils.financialtools.domain.identifiers.ConsolidationMethod, effective_date: datetime.date) -> None` | Ownership relationship between entities for consolidation. |
| `extract_period_settlements` | function | `(priced_cashflows: 'Any', ref_date: 'date', ref_date_prev: 'date') -> 'Any'` | Extract settled cashflows in the period (ref_date_prev, ref_date]. |
| `generate_schedule` | function | `(terms: 'InstrumentTerms', *, calendar: 'object', schedule_version: 'int \| None') -> 'CashFlowSchedule'` | Generate a versioned authored cash-flow schedule from contract terms. |
| `generate_schedule_df` | function | `(terms: 'InstrumentTerms', *, calendar: 'object') -> 'Any'` | Generate a validated cashflow DataFrame directly from contract terms. |
| `generate_schedules` | function | `(terms_list: 'Sequence[InstrumentTerms]', *, calendar: 'object') -> 'Any'` | Generate validated cashflow DataFrame for multiple instruments. |
| `Instrument` | class | `(*, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, currency: treasuryutils.financialtools.domain.identifiers.Currency, trade_date: datetime.date, issuer: str \| None, isin: str \| None, name: str \| None, status: treasuryutils.financialtools.domain.identifiers.InstrumentStatus, external_id: str \| None, external_source: str \| None, contractual_features: treasuryutils.financialtools.instruments.models.ContractualFeatures \| None) -> None` | Static instrument identity. |
| `InstrumentTerms` | class | `(*, terms_id: str, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, effective_date: datetime.date, maturity_date: datetime.date, notional: decimal.Decimal, legs: typing.Annotated[tuple[treasuryutils.financialtools.instruments.models.LegDefinition, ...], MinLen(min_length=1)]) -> None` | Versioned contractual terms for an instrument. |
| `LegalEntity` | class | `(*, entity_id: typing.Annotated[str, MinLen(min_length=1)], entity_name: str, entity_type: treasuryutils.financialtools.domain.identifiers.EntityType, country: str, functional_currency: treasuryutils.financialtools.domain.identifiers.Currency, tax_id: str \| None) -> None` | A legal entity that can hold positions. |
| `LegDefinition` | class | `(*, leg_id: str, direction: Literal[-1, 1], currency: treasuryutils.financialtools.domain.identifiers.Currency, notional: typing.Annotated[decimal.Decimal, Gt(gt=0)], leg_type: treasuryutils.financialtools.domain.identifiers.RateType, day_count: treasuryutils.calendartools.day_count.conventions.DayCountConvention, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType, spread_method: treasuryutils.financialtools.domain.identifiers.SpreadMethod, payment_frequency: treasuryutils.financialtools.instruments.models.PaymentFrequency, business_day_conv: Union[Literal['following', 'preceding', 'modified_following', 'modified_preceding'], str], amortization_type: treasuryutils.financialtools.instruments.models.AmortizationType, fixed_rate: decimal.Decimal \| None, index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, index_perc: decimal.Decimal, spread: decimal.Decimal, name: str \| None, fixing_convention: treasuryutils.financialtools.domain.identifiers.FixingConvention, fixing_lag: typing.Annotated[int, Ge(ge=0)], payment_delay: typing.Annotated[int, Ge(ge=0)]) -> None` | Rules for generating a single leg cash-flow schedule. |
| `PaymentFrequency` | enum | `DAILY='DAILY', MONTHLY='MONTHLY', QUARTERLY='QUARTERLY', SEMIANNUAL='SEMIANNUAL', ANNUAL='ANNUAL', AT_MATURITY='AT_MATURITY'` | Coupon or amortization payment frequency for an instrument leg. |
| `Portfolio` | class | `(*, portfolio_id: typing.Annotated[str, MinLen(min_length=1)], portfolio_name: str, portfolio_type: treasuryutils.financialtools.domain.identifiers.PortfolioType, business_unit: str \| None) -> None` | Logical grouping of positions by business purpose. |
| `Position` | class | `(*, position_id: typing.Annotated[str, MinLen(min_length=1)], instrument_id: typing.Annotated[str, MinLen(min_length=1)], portfolio_id: typing.Annotated[str, MinLen(min_length=1)], entity_id: typing.Annotated[str, MinLen(min_length=1)], counterparty_entity_id: str \| None, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: treasuryutils.financialtools.domain.identifiers.PositionReason, settlement_date: datetime.date, acquisition_price: typing.Annotated[decimal.Decimal, Gt(gt=0)], acquisition_cost: decimal.Decimal, transaction_costs: decimal.Decimal, quantity: typing.Annotated[decimal.Decimal, Ge(ge=0)], status: treasuryutils.financialtools.domain.identifiers.PositionStatus) -> None` | Ownership of an instrument — SCD-2 versioned. |
| `price_cashflows` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', validate: 'bool') -> 'Any'` | Compute priced cashflows — one row per (ref_date, period). |
| `price_cashflows_scd` | function | `(schedule_versions: 'Sequence[tuple[Any, date, date \| None]]', ref_dates: 'Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object') -> 'Any'` | Price cashflows across SCD schedule versions. |
| `price_cashflows_summary` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', validate: 'bool') -> 'Any'` | Aggregate priced cashflows into a leg-level summary. |
| `process_period_end` | function | `(cashflow_df: 'Any', positions_df: 'Any', ref_date: 'date', *, designations: 'Sequence[AccountingDesignation]', measurement_configs: 'Sequence[MeasurementConfig]', discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', ecl_params: 'Sequence[ECLParameters] \| None', hedge_relationships: 'Sequence[HedgeRelationship] \| None', previous_period_state: 'dict[str, Any] \| None', validate: 'bool') -> 'Any'` | Run IFRS 9 period-end accounting for all positions. |
| `resolve_as_of` | function | `(versions: 'Sequence[T]', *, as_of: 'date') -> 'T'` | Resolve the unique version active on a reference date. |
| `scale_attribution_by_position` | function | `(attribution_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit P&L attribution by position quantity. |
| `scale_by_position` | function | `(pricing: 'Any', positions: 'Any', *, quantity_column: 'str', instrument_id_column: 'str', value_columns: 'list[str] \| None', validate: 'bool') -> 'Any'` | Scale per-unit pricing results by position quantity. |
| `scale_key_rate_risk_by_position` | function | `(key_rate_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit key-rate DV01 by position quantity. |
| `scale_risk_by_position` | function | `(risk_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit risk metrics by position quantity. |
| `summarize_leg_values` | function | `(summary: 'Any', *, base_currency: 'str', fx_rates: 'dict[str, float] \| None', fx_rate: 'float \| None') -> 'Any'` | Decompose leg-level pricing into BRL vs foreign currency components. |
| `Versioned` | class | `(*args, **kwargs)` | Protocol for entities with SCD-2 style validity windows. |

## `treasuryutils.financialtools.accounting`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AccountingDesignation` | class | `(*, designation_id: typing.Annotated[str, MinLen(min_length=1)], position_id: typing.Annotated[str, MinLen(min_length=1)], version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: treasuryutils.financialtools.domain.identifiers.DesignationReason, classification: treasuryutils.financialtools.domain.identifiers.MeasurementCategory, business_model: treasuryutils.financialtools.domain.identifiers.BusinessModel, sppi_result: treasuryutils.financialtools.domain.identifiers.SPPIResult, fair_value_option: bool, designation_reason: str \| None) -> None` | IFRS 9 classification designation for a position (SCD-2 versioned). |
| `assert_no_poci_consistency` | function | `(ecl_parameters: 'Sequence[ECLParameters]', *, policy_allows_poci: 'bool') -> 'None'` | Assert that POCI assets are absent when policy declares them out of scope. |
| `assess_credit_state` | function | `(*, is_poci: 'bool', is_credit_impaired: 'bool', is_simplified_approach: 'bool', sicr_triggered: 'bool', days_past_due: 'int') -> 'CreditState'` | Resolve the credit-state dispatch axis from per-position attributes. |
| `assess_effectiveness` | function | `(hedging_fv_changes: 'Any', hedged_fv_changes: 'Any', *, method: 'str') -> 'EffectivenessAssessment'` | Assess hedge effectiveness (IFRS 9.6.4.1, B6.4.1--B6.4.17). |
| `assess_stage` | function | `(current_pd_lifetime: 'float \| Any', initial_recognition_pd_lifetime: 'float \| Any', days_past_due: 'int \| Any', indicators: 'Sequence[SICRIndicator] \| None', *, policy: 'SICRPolicy \| None', is_low_credit_risk: 'bool \| Any') -> 'Any'` | Assign ECL stages per IFRS 9.5.5 with the holistic SICR test. |
| `batch_solve_eir` | function | `(cashflow_df: 'Any', initial_amounts: 'dict[str, float]', *, compounding: 'CompoundingType', day_count: 'DayCountConvention', origin_date_col: 'str', cashflow_col: 'str', date_col: 'str', deal_id_col: 'str', calendar: 'Any \| None', tolerance: 'float', max_iterations: 'int') -> 'dict[str, float]'` | Solve EIR for multiple instruments in batch. |
| `classify_instruments` | function | `(cashflow_df: 'Any', business_model_df: 'Any', *, fair_value_option_df: 'Any \| None') -> 'Any'` | Classify a cashflow DataFrame per IFRS 9. |
| `classify_measurement` | function | `(sppi_col: 'Any', business_model_col: 'Any', *, fair_value_option_col: 'Any \| None') -> 'Any'` | Classify instruments by SPPI result, business model, and fair-value option. |
| `classify_sppi` | function | `(instrument_type: 'InstrumentType \| str', features: 'ContractualFeatures \| None', *, benchmark_scenarios: 'Sequence[dict[str, Any]] \| None') -> 'SPPIEvaluation'` | Run the SPPI test for a single instrument. |
| `compute_amortized_cost` | function | `(schedule_df: 'Any', *, eir_map: 'dict[str, float]', initial_gca_map: 'dict[str, float]', compounding: 'CompoundingType', floating_at_par_deals: 'set[str] \| None', credit_state_map: 'dict[str, CreditState] \| None', initial_loss_allowance_map: 'dict[str, float] \| None', deal_id_col: 'str', position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute the amortized cost schedule for one or more instruments. |
| `compute_cash_flow_hedge` | function | `(hedge: 'HedgeRelationship', hedging_instrument_fv_change: 'float \| None', hedged_item_pv_change: 'float \| None', *, cumulative_hedging_change: 'float', cumulative_hedged_change: 'float', previous_cfh_oci_reserve: 'float', previous_cum_recycled: 'float') -> 'dict[str, float]'` | Compute cash flow hedge period-end entries (IFRS 9.6.5.11). |
| `compute_day1_pnl_release` | function | `(*, deferred_balance: 'float', deferral_inception_date: 'date', period_end: 'date', inputs_now_observable: 'bool', instrument_term_years: 'float', method: 'ReleaseMethod') -> 'Day1PnLRelease'` | Compute the cumulative release of a deferred Day-1 P&L reserve. |
| `compute_ecl` | function | `(ecl_params: 'Any', cashflow_df: 'Any', ref_date: 'date', *, previous_ecl: 'Any \| None', position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute Expected Credit Loss for a batch of positions. |
| `compute_ecl_for_instrument` | function | `(stage: 'str \| None', pd_12m: 'float', pd_lifetime: 'float', lgd: 'float', ead: 'float', discount_rate: 'float', remaining_life_years: 'float', *, credit_state: 'CreditState \| str \| None', cum_lifetime_ecl_recognized: 'float', periods_per_year: 'int', return_outcome: 'bool') -> 'float \| ECLOutcome'` | Compute ECL for a single instrument with credit-state dispatch. |
| `compute_fair_value_changes` | function | `(current_fv: 'Any', previous_fv: 'Any \| None', *, position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute period fair value changes for FVTPL instruments. |
| `compute_fair_value_hedge` | function | `(hedge: 'HedgeRelationship', hedging_instrument_fv_change: 'float', hedged_item_fv_change_for_risk: 'float') -> 'dict[str, float]'` | Compute fair value hedge period-end entries (IFRS 9.6.5.8--6.5.10). |
| `compute_fvoci` | function | `(schedule_df: 'Any', current_fair_values: 'Any', *, eir_map: 'dict[str, float]', initial_gca_map: 'dict[str, float]', previous_oci_reserves: 'Any \| None', compounding: 'CompoundingType', floating_at_par_deals: 'set[str] \| None', position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute dual-track FVOCI measurement. |
| `compute_hedge_results_batch` | function | `(hedge_relationships: 'Sequence[HedgeRelationship]', hedging_fv_changes: 'Any', hedged_risk_pv_changes: 'Any', *, ref_dates: 'Sequence[Any] \| None', previous_state: 'Any \| None', validate: 'bool') -> 'tuple[Any, Any]'` | Compute hedge results + new cumulative state for a period. |
| `compute_poci_period` | function | `(*, cum_lifetime_ecl_current: 'float', cum_lifetime_ecl_initial: 'float') -> 'dict[str, float]'` | POCI period accounting per IFRS 9.5.5.13-14. |
| `compute_simplified_ecl` | function | `(receivables_df: 'Any', *, method: "Literal['provision_matrix', 'dcf']", aging_buckets: 'dict[str, float] \| None') -> 'pl.DataFrame'` | Compute lifetime ECL for trade / contract / lease receivables. |
| `crystallize_on_derecognition` | function | `(*, deferred_balance: 'float', derecognition_date: 'date', deferral_inception_date: 'date') -> 'Day1PnLRelease'` | Release the residual deferred Day-1 P&L on derecognition. |
| `crystallize_on_input_observability` | function | `(*, deferred_balance: 'float', transition_date: 'date', deferral_inception_date: 'date') -> 'Day1PnLRelease'` | Release the residual deferred Day-1 P&L on Level transfer. |
| `Day1PnLRelease` | class | `(period_recognition: 'float', closing_deferred: 'float') -> None` | Period-level outcome of the Day-1 P&L deferred-reserve roll-forward. |
| `derecognize_unamortised` | function | `(remaining_balance: 'float') -> 'dict[str, float]'` | Recognise unamortised basis adjustment immediately on derecognition (B5.4.6). |
| `discontinue_cash_flow_hedge` | function | `(cfh_oci_reserve: 'float', *, hedged_cashflows_still_expected: 'bool') -> 'dict[str, float]'` | Handle cash flow hedge discontinuation (IFRS 9.6.5.12). |
| `discontinue_fair_value_hedge` | function | `(hedge_id: 'str', relationship_version: 'int', discontinuation_date: 'date', *, post_adjustment_carrying_amount: 'float', cumulative_basis_adjustment: 'float', remaining_cashflows: 'NDArray[np.float64]', cashflow_times: 'NDArray[np.float64]', compounding: 'CompoundingType', day_count: 'DayCountConvention', calendar: 'Any \| None', start_date: 'date \| None', discontinued_proportion: 'float', eir: 'Any') -> 'pl.DataFrame'` | Compute basis-adjustment amortisation schedule on FVH discontinuation. |
| `ECLOutcome` | class | `(ecl_amount: 'float', pd_used: 'float', interest_basis: "Literal['gross', 'net']", eir_used: 'float', cumulative_changes_recognized: 'float \| None', rationale: 'str') -> None` | Structured outcome of a single-instrument ECL computation. |
| `ECLParameters` | class | `(*, ecl_id: typing.Annotated[str, MinLen(min_length=1)], position_id: typing.Annotated[str, MinLen(min_length=1)], version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, stage: treasuryutils.financialtools.domain.identifiers.ECLStage, pd_12month: typing.Annotated[decimal.Decimal, Ge(ge=0), Le(le=1)], pd_lifetime: typing.Annotated[decimal.Decimal, Ge(ge=0), Le(le=1)], initial_recognition_pd_lifetime: typing.Annotated[decimal.Decimal \| None, Ge(ge=0), Le(le=1)], lgd: typing.Annotated[decimal.Decimal, Ge(ge=0), Le(le=1)], discount_rate: typing.Annotated[decimal.Decimal, Gt(gt=-1)], sicr_triggered: bool, days_past_due: typing.Annotated[int, Ge(ge=0)], is_low_credit_risk: bool, is_poci: bool, is_credit_impaired: bool, is_default: bool, is_simplified_approach: bool, credit_adjusted_eir: decimal.Decimal \| None, original_eir: decimal.Decimal \| None) -> None` | ECL impairment parameters per position (SCD-2 versioned). |
| `EffectivenessAssessment` | class | `(method_used: 'str', sample_size: 'int \| None', offset_ratio: 'float \| None', r_squared: 'float \| None', slope: 'float \| None', within_heuristic_band: 'bool', sources_of_ineffectiveness: 'list[str]') -> None` | Result of a hedge effectiveness assessment per IFRS 9.6.4.1. |
| `HedgeRelationship` | class | `(*, hedge_id: typing.Annotated[str, MinLen(min_length=1)], version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, hedge_type: treasuryutils.financialtools.domain.identifiers.HedgeType, hedged_item_position_id: typing.Annotated[str, MinLen(min_length=1)], hedging_instrument_position_id: typing.Annotated[str, MinLen(min_length=1)], hedged_risk: treasuryutils.financialtools.domain.identifiers.HedgedRisk, hedge_ratio: typing.Annotated[decimal.Decimal, Gt(gt=0)], designation_date: datetime.date, effectiveness_test_method: treasuryutils.financialtools.domain.identifiers.EffectivenessTestMethod, status: treasuryutils.financialtools.domain.identifiers.HedgeStatus, relationship_version: typing.Annotated[int, Ge(ge=1)]) -> None` | IFRS 9 Chapter 6 hedge designation (SCD-2 versioned). |
| `initial_recognition_fvtpl` | function | `(transaction_price: 'float', transaction_costs: 'float', fair_value: 'float', *, is_observable_inputs: 'bool', inception_date: 'date') -> 'dict[str, Any]'` | Compute Day-1 entries for FVTPL instruments per IFRS 9.5.1.1 and B5.1.2A. |
| `initial_recognition_poci` | function | `(purchase_price: 'float', expected_cashflows: 'NDArray[np.float64]', cashflow_times: 'NDArray[np.float64]', expected_credit_losses: 'NDArray[np.float64]', compounding: 'CompoundingType') -> 'dict[str, float]'` | Solve the credit-adjusted EIR for a POCI asset (IFRS 9.5.4.1(a)). |
| `MeasurementConfig` | class | `(*, position_id: typing.Annotated[str, MinLen(min_length=1)], classification: treasuryutils.financialtools.domain.identifiers.MeasurementCategory, initial_recognition_amount: decimal.Decimal \| None, transaction_costs: decimal.Decimal, original_eir: decimal.Decimal \| None, is_floating_rate: bool, benchmark_index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, spread_over_benchmark: decimal.Decimal \| None, fair_value_level: treasuryutils.financialtools.domain.identifiers.FairValueLevel \| None, is_observable_inputs: bool, day1_pnl_deferred: decimal.Decimal, day1_pnl_inception_date: datetime.date \| None, fair_value_level_at_inception: treasuryutils.financialtools.domain.identifiers.FairValueLevel \| None) -> None` | Configuration for how an instrument is measured each period. |
| `process_period_end` | function | `(cashflow_df: 'Any', positions_df: 'Any', ref_date: 'date', *, designations: 'Sequence[AccountingDesignation]', measurement_configs: 'Sequence[MeasurementConfig]', discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', ecl_params: 'Sequence[ECLParameters] \| None', hedge_relationships: 'Sequence[HedgeRelationship] \| None', previous_period_state: 'dict[str, Any] \| None', validate: 'bool') -> 'Any'` | Run IFRS 9 period-end accounting for all positions. |
| `rebalance_hedge` | function | `(hedge: 'HedgeRelationship', new_ratio: 'Any', ref_date: 'date', *, new_reason: 'str') -> 'tuple[HedgeRelationship, HedgeRelationship]'` | Close current SCD-2 version and open a new one with bumped ``relationship_version``. |
| `recalculate_on_modification` | function | `(*_args: 'Any', **_kwargs: 'Any') -> 'pl.DataFrame'` | Recompute FVH discontinuation schedule on hedged-item modification (stub). |
| `recycle_oci` | function | `(oci_reserves: 'Any', derecognized_positions: 'Any', *, position_id_col: 'str', validate: 'bool') -> 'Any'` | Recycle cumulative OCI to P&L on derecognition. |
| `solve_eir` | function | `(cashflow_amounts: 'NDArray[np.float64]', cashflow_times: 'NDArray[np.float64]', initial_amount: 'float', compounding: 'CompoundingType', *, tolerance: 'float', max_iterations: 'int') -> 'float'` | Solve for the Effective Interest Rate using Newton-Raphson. |
| `solve_eir_from_df` | function | `(cashflow_df: 'Any', *, initial_amount: 'float', origin_date: 'Any', compounding: 'CompoundingType', day_count: 'DayCountConvention', cashflow_col: 'str', date_col: 'str', calendar: 'Any \| None', tolerance: 'float', max_iterations: 'int') -> 'float'` | Solve EIR from a cashflow DataFrame for a single instrument. |

## `treasuryutils.financialtools.accounting.amortized_cost`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_amortized_cost` | function | `(schedule_df: 'Any', *, eir_map: 'dict[str, float]', initial_gca_map: 'dict[str, float]', compounding: 'CompoundingType', floating_at_par_deals: 'set[str] \| None', credit_state_map: 'dict[str, CreditState] \| None', initial_loss_allowance_map: 'dict[str, float] \| None', deal_id_col: 'str', position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute the amortized cost schedule for one or more instruments. |

## `treasuryutils.financialtools.accounting.classification`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CapFloorEvaluator` | class | `()` | B4.1.13 Instrument C / B4.1.15 — cap, floor, and collar features. |
| `CapFloorEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate caps, floors, and collars under B4.1.13 Instrument C / B4.1.15. |
| `classify_instruments` | function | `(cashflow_df: 'Any', business_model_df: 'Any', *, fair_value_option_df: 'Any \| None') -> 'Any'` | Classify a cashflow DataFrame per IFRS 9. |
| `classify_measurement` | function | `(sppi_col: 'Any', business_model_col: 'Any', *, fair_value_option_col: 'Any \| None') -> 'Any'` | Classify instruments by SPPI result, business model, and fair-value option. |
| `classify_sppi` | function | `(instrument_type: 'InstrumentType \| str', features: 'ContractualFeatures \| None', *, benchmark_scenarios: 'Sequence[dict[str, Any]] \| None') -> 'SPPIEvaluation'` | Run the SPPI test for a single instrument. |
| `classify_sppi_batch` | function | `(instrument_type_col: 'Any', *, features_col: 'Sequence[ContractualFeatures \| None] \| None') -> 'Any'` | Vectorized SPPI test producing a column of ``SPPIResult`` strings. |
| `CLIEvaluator` | class | `()` | B4.1.20-B4.1.26 — contractually linked instruments (tranches). |
| `CLIEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate contractually linked instruments per B4.1.20-B4.1.26. |
| `ContingentEvaluator` | class | `()` | B4.1.10 / B4.1.10A — contingent cash-flow features. |
| `ContingentEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate contingent cash-flow features against B4.1.10 / B4.1.10A. |
| `ConversionEvaluator` | class | `()` | B4.1.7 / B4.1.14 Instrument F — conversion features. |
| `ConversionEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate convertible-bond conversion features under B4.1.7 / B4.1.14. |
| `CurrencyMismatchEvaluator` | class | `()` | B4.1.13 Instrument A vs G — inflation-linkage currency mismatch. |
| `CurrencyMismatchEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate inflation-linkage currency mismatch. |
| `LeverageEvaluator` | class | `()` | B4.1.9 / B4.1.18 — contractual leverage on the variable component. |
| `LeverageEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate contractual leverage under B4.1.9 / B4.1.18. |
| `ModifiedTVMEvaluator` | class | `()` | B4.1.9B-E — modified time value of money. |
| `ModifiedTVMEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate modified time-value-of-money features under B4.1.9B-E. |
| `NonRecourseEvaluator` | class | `()` | B4.1.16 / B4.1.16A — non-recourse loan look-through. |
| `NonRecourseEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate non-recourse look-through under B4.1.16 / B4.1.16A. |
| `PrepaymentEvaluator` | class | `()` | B4.1.11(b) / B4.1.12 — prepayment options. |
| `PrepaymentEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Evaluate prepayment options against B4.1.11(b) / B4.1.12. |
| `SPPIEvaluation` | class | `(result: "Literal['PASS', 'FAIL', 'REQUIRES_BENCHMARK_TEST']", binding_paragraph: 'str', rationale: 'str', benchmark_test_inputs: 'dict[str, Any] \| None') -> None` | Result of evaluating one feature (or the overall instrument) against IFRS 9. |
| `SPPIEvaluator` | class | `(*args, **kwargs)` | Single-feature SPPI evaluator (Chain-of-Responsibility node). |
| `SPPIEvaluator.evaluate` | function | `(features: 'ContractualFeatures') -> 'SPPIEvaluation'` | Return an evaluation for one feature aspect of *features*. |

## `treasuryutils.financialtools.accounting.ecl`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `assert_no_poci_consistency` | function | `(ecl_parameters: 'Sequence[ECLParameters]', *, policy_allows_poci: 'bool') -> 'None'` | Assert that POCI assets are absent when policy declares them out of scope. |
| `assess_credit_state` | function | `(*, is_poci: 'bool', is_credit_impaired: 'bool', is_simplified_approach: 'bool', sicr_triggered: 'bool', days_past_due: 'int') -> 'CreditState'` | Resolve the credit-state dispatch axis from per-position attributes. |
| `assess_stage` | function | `(current_pd_lifetime: 'float \| Any', initial_recognition_pd_lifetime: 'float \| Any', days_past_due: 'int \| Any', indicators: 'Sequence[SICRIndicator] \| None', *, policy: 'SICRPolicy \| None', is_low_credit_risk: 'bool \| Any') -> 'Any'` | Assign ECL stages per IFRS 9.5.5 with the holistic SICR test. |
| `assess_stage_batch` | function | `(positions_df: 'Any', policy: 'SICRPolicy \| None', *, current_pd_col: 'str', initial_pd_col: 'str', dpd_col: 'str', low_credit_risk_col: 'str \| None', indicator_columns: 'Sequence[str] \| None', indicator_weights: 'dict[str, float] \| None', rebuttal_col: 'str \| None') -> 'Any'` | Vectorized stage assignment over a Polars positions DataFrame. |
| `compute_ecl` | function | `(ecl_params: 'Any', cashflow_df: 'Any', ref_date: 'date', *, previous_ecl: 'Any \| None', position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute Expected Credit Loss for a batch of positions. |
| `compute_ecl_for_instrument` | function | `(stage: 'str \| None', pd_12m: 'float', pd_lifetime: 'float', lgd: 'float', ead: 'float', discount_rate: 'float', remaining_life_years: 'float', *, credit_state: 'CreditState \| str \| None', cum_lifetime_ecl_recognized: 'float', periods_per_year: 'int', return_outcome: 'bool') -> 'float \| ECLOutcome'` | Compute ECL for a single instrument with credit-state dispatch. |
| `ECLOutcome` | class | `(ecl_amount: 'float', pd_used: 'float', interest_basis: "Literal['gross', 'net']", eir_used: 'float', cumulative_changes_recognized: 'float \| None', rationale: 'str') -> None` | Structured outcome of a single-instrument ECL computation. |
| `SICRIndicator` | class | `(name: 'IndicatorName', fired: 'bool', weight: 'float', rationale: 'str', rebuttal_basis: 'RebuttalBasis') -> None` | One B5.5.17 indicator measurement for a position at a reporting date. |
| `SICRPolicy` | class | `(treat_30dpd_as_hard_backstop: 'bool', rebuttal_evidence_required: 'tuple[RebuttalBasis, ...]', low_credit_risk_exemption: 'bool', indicator_combination: 'IndicatorCombination', weighted_threshold: 'float', pd_relative_threshold: 'float') -> None` | Documented accounting policy for SICR detection (IFRS 7.35F). |

## `treasuryutils.financialtools.accounting.eir`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `batch_solve_eir` | function | `(cashflow_df: 'Any', initial_amounts: 'dict[str, float]', *, compounding: 'CompoundingType', day_count: 'DayCountConvention', origin_date_col: 'str', cashflow_col: 'str', date_col: 'str', deal_id_col: 'str', calendar: 'Any \| None', tolerance: 'float', max_iterations: 'int') -> 'dict[str, float]'` | Solve EIR for multiple instruments in batch. |
| `solve_eir` | function | `(cashflow_amounts: 'NDArray[np.float64]', cashflow_times: 'NDArray[np.float64]', initial_amount: 'float', compounding: 'CompoundingType', *, tolerance: 'float', max_iterations: 'int') -> 'float'` | Solve for the Effective Interest Rate using Newton-Raphson. |
| `solve_eir_from_df` | function | `(cashflow_df: 'Any', *, initial_amount: 'float', origin_date: 'Any', compounding: 'CompoundingType', day_count: 'DayCountConvention', cashflow_col: 'str', date_col: 'str', calendar: 'Any \| None', tolerance: 'float', max_iterations: 'int') -> 'float'` | Solve EIR from a cashflow DataFrame for a single instrument. |

## `treasuryutils.financialtools.accounting.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `process_period_end` | function | `(cashflow_df: 'Any', positions_df: 'Any', ref_date: 'date', *, designations: 'Sequence[AccountingDesignation]', measurement_configs: 'Sequence[MeasurementConfig]', discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', ecl_params: 'Sequence[ECLParameters] \| None', hedge_relationships: 'Sequence[HedgeRelationship] \| None', previous_period_state: 'dict[str, Any] \| None', validate: 'bool') -> 'Any'` | Run IFRS 9 period-end accounting for all positions. |

## `treasuryutils.financialtools.accounting.fair_value`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_fair_value_changes` | function | `(current_fv: 'Any', previous_fv: 'Any \| None', *, position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute period fair value changes for FVTPL instruments. |
| `initial_recognition_fvtpl` | function | `(transaction_price: 'float', transaction_costs: 'float', fair_value: 'float', *, is_observable_inputs: 'bool', inception_date: 'date') -> 'dict[str, Any]'` | Compute Day-1 entries for FVTPL instruments per IFRS 9.5.1.1 and B5.1.2A. |

## `treasuryutils.financialtools.accounting.fvoci`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_fvoci` | function | `(schedule_df: 'Any', current_fair_values: 'Any', *, eir_map: 'dict[str, float]', initial_gca_map: 'dict[str, float]', previous_oci_reserves: 'Any \| None', compounding: 'CompoundingType', floating_at_par_deals: 'set[str] \| None', position_id_col: 'str', validate: 'bool') -> 'Any'` | Compute dual-track FVOCI measurement. |
| `recycle_oci` | function | `(oci_reserves: 'Any', derecognized_positions: 'Any', *, position_id_col: 'str', validate: 'bool') -> 'Any'` | Recycle cumulative OCI to P&L on derecognition. |

## `treasuryutils.financialtools.accounting.hedge`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `assess_effectiveness` | function | `(hedging_fv_changes: 'Any', hedged_fv_changes: 'Any', *, method: 'str') -> 'EffectivenessAssessment'` | Assess hedge effectiveness (IFRS 9.6.4.1, B6.4.1--B6.4.17). |
| `compute_cash_flow_hedge` | function | `(hedge: 'HedgeRelationship', hedging_instrument_fv_change: 'float \| None', hedged_item_pv_change: 'float \| None', *, cumulative_hedging_change: 'float', cumulative_hedged_change: 'float', previous_cfh_oci_reserve: 'float', previous_cum_recycled: 'float') -> 'dict[str, float]'` | Compute cash flow hedge period-end entries (IFRS 9.6.5.11). |
| `compute_fair_value_hedge` | function | `(hedge: 'HedgeRelationship', hedging_instrument_fv_change: 'float', hedged_item_fv_change_for_risk: 'float') -> 'dict[str, float]'` | Compute fair value hedge period-end entries (IFRS 9.6.5.8--6.5.10). |
| `compute_hedge_results_batch` | function | `(hedge_relationships: 'Sequence[HedgeRelationship]', hedging_fv_changes: 'Any', hedged_risk_pv_changes: 'Any', *, ref_dates: 'Sequence[Any] \| None', previous_state: 'Any \| None', validate: 'bool') -> 'tuple[Any, Any]'` | Compute hedge results + new cumulative state for a period. |
| `derecognize_unamortised` | function | `(remaining_balance: 'float') -> 'dict[str, float]'` | Recognise unamortised basis adjustment immediately on derecognition (B5.4.6). |
| `discontinue_cash_flow_hedge` | function | `(cfh_oci_reserve: 'float', *, hedged_cashflows_still_expected: 'bool') -> 'dict[str, float]'` | Handle cash flow hedge discontinuation (IFRS 9.6.5.12). |
| `discontinue_fair_value_hedge` | function | `(hedge_id: 'str', relationship_version: 'int', discontinuation_date: 'date', *, post_adjustment_carrying_amount: 'float', cumulative_basis_adjustment: 'float', remaining_cashflows: 'NDArray[np.float64]', cashflow_times: 'NDArray[np.float64]', compounding: 'CompoundingType', day_count: 'DayCountConvention', calendar: 'Any \| None', start_date: 'date \| None', discontinued_proportion: 'float', eir: 'Any') -> 'pl.DataFrame'` | Compute basis-adjustment amortisation schedule on FVH discontinuation. |
| `EffectivenessAssessment` | class | `(method_used: 'str', sample_size: 'int \| None', offset_ratio: 'float \| None', r_squared: 'float \| None', slope: 'float \| None', within_heuristic_band: 'bool', sources_of_ineffectiveness: 'list[str]') -> None` | Result of a hedge effectiveness assessment per IFRS 9.6.4.1. |
| `rebalance_hedge` | function | `(hedge: 'HedgeRelationship', new_ratio: 'Any', ref_date: 'date', *, new_reason: 'str') -> 'tuple[HedgeRelationship, HedgeRelationship]'` | Close current SCD-2 version and open a new one with bumped ``relationship_version``. |
| `recalculate_on_modification` | function | `(*_args: 'Any', **_kwargs: 'Any') -> 'pl.DataFrame'` | Recompute FVH discontinuation schedule on hedged-item modification (stub). |

## `treasuryutils.financialtools.accounting.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AccountingDesignation` | class | `(*, designation_id: typing.Annotated[str, MinLen(min_length=1)], position_id: typing.Annotated[str, MinLen(min_length=1)], version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: treasuryutils.financialtools.domain.identifiers.DesignationReason, classification: treasuryutils.financialtools.domain.identifiers.MeasurementCategory, business_model: treasuryutils.financialtools.domain.identifiers.BusinessModel, sppi_result: treasuryutils.financialtools.domain.identifiers.SPPIResult, fair_value_option: bool, designation_reason: str \| None) -> None` | IFRS 9 classification designation for a position (SCD-2 versioned). |
| `ECLParameters` | class | `(*, ecl_id: typing.Annotated[str, MinLen(min_length=1)], position_id: typing.Annotated[str, MinLen(min_length=1)], version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, stage: treasuryutils.financialtools.domain.identifiers.ECLStage, pd_12month: typing.Annotated[decimal.Decimal, Ge(ge=0), Le(le=1)], pd_lifetime: typing.Annotated[decimal.Decimal, Ge(ge=0), Le(le=1)], initial_recognition_pd_lifetime: typing.Annotated[decimal.Decimal \| None, Ge(ge=0), Le(le=1)], lgd: typing.Annotated[decimal.Decimal, Ge(ge=0), Le(le=1)], discount_rate: typing.Annotated[decimal.Decimal, Gt(gt=-1)], sicr_triggered: bool, days_past_due: typing.Annotated[int, Ge(ge=0)], is_low_credit_risk: bool, is_poci: bool, is_credit_impaired: bool, is_default: bool, is_simplified_approach: bool, credit_adjusted_eir: decimal.Decimal \| None, original_eir: decimal.Decimal \| None) -> None` | ECL impairment parameters per position (SCD-2 versioned). |
| `HedgeRelationship` | class | `(*, hedge_id: typing.Annotated[str, MinLen(min_length=1)], version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, hedge_type: treasuryutils.financialtools.domain.identifiers.HedgeType, hedged_item_position_id: typing.Annotated[str, MinLen(min_length=1)], hedging_instrument_position_id: typing.Annotated[str, MinLen(min_length=1)], hedged_risk: treasuryutils.financialtools.domain.identifiers.HedgedRisk, hedge_ratio: typing.Annotated[decimal.Decimal, Gt(gt=0)], designation_date: datetime.date, effectiveness_test_method: treasuryutils.financialtools.domain.identifiers.EffectivenessTestMethod, status: treasuryutils.financialtools.domain.identifiers.HedgeStatus, relationship_version: typing.Annotated[int, Ge(ge=1)]) -> None` | IFRS 9 Chapter 6 hedge designation (SCD-2 versioned). |
| `MeasurementConfig` | class | `(*, position_id: typing.Annotated[str, MinLen(min_length=1)], classification: treasuryutils.financialtools.domain.identifiers.MeasurementCategory, initial_recognition_amount: decimal.Decimal \| None, transaction_costs: decimal.Decimal, original_eir: decimal.Decimal \| None, is_floating_rate: bool, benchmark_index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, spread_over_benchmark: decimal.Decimal \| None, fair_value_level: treasuryutils.financialtools.domain.identifiers.FairValueLevel \| None, is_observable_inputs: bool, day1_pnl_deferred: decimal.Decimal, day1_pnl_inception_date: datetime.date \| None, fair_value_level_at_inception: treasuryutils.financialtools.domain.identifiers.FairValueLevel \| None) -> None` | Configuration for how an instrument is measured each period. |

## `treasuryutils.financialtools.builders`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CdiAccumulatedBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, cdi_daily_data: 'pl.DataFrame \| None') -> 'None'` | Builds the historical accumulated CDI index. |
| `CdiAccumulatedBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the accumulated CDI index via cumulative product of daily factors. |
| `CupomCambialCurveBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, di_pre_data: 'pl.DataFrame \| None', market_fixings_data: 'pl.DataFrame \| None', frc_raw_data: 'pl.DataFrame \| None') -> 'None'` | Builds the Cupom Cambial term structure. |
| `CupomCambialCurveBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the Cupom Cambial term structure from DI, FX fixings, and FRC quotes. |
| `DiPreCurveBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, calendar: 'str', di_curve_data: 'pl.DataFrame \| None') -> 'None'` | Builds the Pre-Fixed DI Curve (absolute dates). |
| `DiPreCurveBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the DI Pre curve with absolute maturity dates and period rates. |
| `FixingFilterBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, fixing_name: 'str', market_fixings_data: 'pl.DataFrame \| None') -> 'None'` | Filters market_fixings by a specific fixing_name. |
| `FixingFilterBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build a (ref_date, rate) series filtered to the configured fixing_name. |
| `FxSpotBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, market_fixings_data: 'pl.DataFrame \| None') -> 'None'` | Derives USD/BRL spot rate from first_future and casado fixings. |
| `FxSpotBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build USD/BRL spot rate series: spot = (DOL1 - CASADO) / 1000. |
| `SofrAccumulatedBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, market_fixings_data: 'pl.DataFrame \| None') -> 'None'` | Builds the historical accumulated SOFR index. |
| `SofrAccumulatedBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the accumulated SOFR index via cumulative product of daily factors. |
| `SofrCurveBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, sofr_curve_raw_data: 'pl.DataFrame \| None') -> 'None'` | Builds the SOFR term structure with absolute dates. |
| `SofrCurveBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the SOFR term structure with absolute maturity dates and period rates. |

## `treasuryutils.financialtools.builders.cdi`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CdiAccumulatedBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, cdi_daily_data: 'pl.DataFrame \| None') -> 'None'` | Builds the historical accumulated CDI index. |
| `CdiAccumulatedBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the accumulated CDI index via cumulative product of daily factors. |
| `DiPreCurveBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, calendar: 'str', di_curve_data: 'pl.DataFrame \| None') -> 'None'` | Builds the Pre-Fixed DI Curve (absolute dates). |
| `DiPreCurveBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the DI Pre curve with absolute maturity dates and period rates. |

## `treasuryutils.financialtools.builders.cupom_cambial`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CupomCambialCurveBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, di_pre_data: 'pl.DataFrame \| None', market_fixings_data: 'pl.DataFrame \| None', frc_raw_data: 'pl.DataFrame \| None') -> 'None'` | Builds the Cupom Cambial term structure. |
| `CupomCambialCurveBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the Cupom Cambial term structure from DI, FX fixings, and FRC quotes. |

## `treasuryutils.financialtools.builders.fx`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `FixingFilterBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, fixing_name: 'str', market_fixings_data: 'pl.DataFrame \| None') -> 'None'` | Filters market_fixings by a specific fixing_name. |
| `FixingFilterBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build a (ref_date, rate) series filtered to the configured fixing_name. |
| `FxSpotBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, market_fixings_data: 'pl.DataFrame \| None') -> 'None'` | Derives USD/BRL spot rate from first_future and casado fixings. |
| `FxSpotBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build USD/BRL spot rate series: spot = (DOL1 - CASADO) / 1000. |

## `treasuryutils.financialtools.builders.sofr`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `SofrAccumulatedBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, market_fixings_data: 'pl.DataFrame \| None') -> 'None'` | Builds the historical accumulated SOFR index. |
| `SofrAccumulatedBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the accumulated SOFR index via cumulative product of daily factors. |
| `SofrCurveBuilder` | class | `(manager_ref: 'DependencyReader \| None', *, sofr_curve_raw_data: 'pl.DataFrame \| None') -> 'None'` | Builds the SOFR term structure with absolute dates. |
| `SofrCurveBuilder.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame'` | Build the SOFR term structure with absolute maturity dates and period rates. |

## `treasuryutils.financialtools.curves`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BaseCurve` | class | `(*args, **kwargs)` | Abstract base for interest-rate curves with backend-dispatched execution. |
| `BaseCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `BaseCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `BaseCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `BaseCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `BaseCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `BaseCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `BaseCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `BaseCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |
| `CdiCurve` | class | `(*, market_data: 'MarketDataSource \| None', index_id: 'str', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | CDI/DI Pre curve — Brazilian overnight rate. |
| `CdiCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `CdiCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `CdiCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `CdiCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `CdiCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `CdiCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `CdiCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `CdiCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |
| `CompoundingType` | enum | `SIMPLE='SIMPLE', CONTINUOUS='CONTINUOUS', DISCRETE_ANNUAL='DISCRETE_ANNUAL', SEMI_ANNUAL='SEMI_ANNUAL'` | How rates compound into accumulation factors A_i. |
| `CupomCambialCurve` | class | `(*, market_data: 'MarketDataSource \| None', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | Cupom Cambial curve — USD-denominated BRL interest rate (projection-only). |
| `CupomCambialCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `CupomCambialCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `CupomCambialCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `CupomCambialCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `CupomCambialCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `CupomCambialCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Not supported — Cupom Cambial has no overnight index. |
| `CupomCambialCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `CupomCambialCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |
| `CurveCoverageError` | class | `(curve_id: 'str', *, missing_ref_dates: 'Sequence[object]', covered: 'tuple[object, object] \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when the curve panel has no node for one or more requested ``ref_date``s. |
| `CurveDomainError` | class | `(regime: 'UndefinedRegime', *, code: 'str') -> 'None'` | Raised when a curve method is queried in a regime where its value is undefined. |
| `InterestRateCurve` | class | `(*args, **kwargs)` | Universal interface for interest rate curves. |
| `InterestRateCurve.bump` | function | `(parallel_shift: float, **kwargs: Any) -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `InterestRateCurve.get_accumulated_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, start_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, end_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType) -> float \| typing.Any` | Return the accumulated rate over the period [start_date, end_date]. |
| `InterestRateCurve.get_discount_factor` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, *, on_undefined: Literal['raise', 'nan', 'zero']) -> float \| typing.Any` | Return the discount factor DF(ref_date, date). |
| `InterestRateCurve.get_forward_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, start: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, end: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType) -> float \| typing.Any` | Return the implied forward rate F(start, end). |
| `InterestRateCurve.get_overnight_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple) -> float \| typing.Any` | Return the overnight rate for the given reference date. |
| `InterestRateCurve.get_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, *, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType, on_undefined: Literal['raise', 'nan', 'zero']) -> float \| typing.Any` | Return the spot yield r(t) for a given compounding convention. |
| `IpcaCurve` | class | `(*, market_data: 'MarketDataSource \| None', index_id: 'str', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | IPCA curve — Brazilian inflation-linked real rate (NTN-B implied). |
| `IpcaCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `IpcaCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `IpcaCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `IpcaCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `IpcaCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `IpcaCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `IpcaCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `IpcaCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |
| `SofrCurve` | class | `(*, market_data: 'MarketDataSource \| None', index_id: 'str', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | SOFR curve — USD secured overnight financing rate. |
| `SofrCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `SofrCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `SofrCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `SofrCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `SofrCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `SofrCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `SofrCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `SofrCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |

## `treasuryutils.financialtools.curves.cdi`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CdiCurve` | class | `(*, market_data: 'MarketDataSource \| None', index_id: 'str', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | CDI/DI Pre curve — Brazilian overnight rate. |
| `CdiCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `CdiCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `CdiCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `CdiCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `CdiCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `CdiCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `CdiCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `CdiCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |

## `treasuryutils.financialtools.curves.cupom_cambial`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CupomCambialCurve` | class | `(*, market_data: 'MarketDataSource \| None', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | Cupom Cambial curve — USD-denominated BRL interest rate (projection-only). |
| `CupomCambialCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `CupomCambialCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `CupomCambialCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `CupomCambialCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `CupomCambialCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `CupomCambialCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Not supported — Cupom Cambial has no overnight index. |
| `CupomCambialCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `CupomCambialCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |

## `treasuryutils.financialtools.curves.errors`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CurveCoverageError` | class | `(curve_id: 'str', *, missing_ref_dates: 'Sequence[object]', covered: 'tuple[object, object] \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when the curve panel has no node for one or more requested ``ref_date``s. |
| `CurveDomainError` | class | `(regime: 'UndefinedRegime', *, code: 'str') -> 'None'` | Raised when a curve method is queried in a regime where its value is undefined. |
| `MapBatchesCurveCoverageError` | class | `(message: 'str') -> 'None'` | A reconstruct-safe :class:`CurveCoverageError` for the polars ``map_batches`` boundary. |
| `MapBatchesCurveDomainError` | class | `(message: 'str') -> 'None'` | A reconstruct-safe :class:`CurveDomainError` for the polars ``map_batches`` boundary. |
| `UndefinedRegime` | enum | `INVERTED_TENOR='inverted_tenor', NO_INDEX_PAST='no_index_past'` | A curve regime that has no defined value (ADR-0100 §1). |

## `treasuryutils.financialtools.curves.ipca`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `IpcaCurve` | class | `(*, market_data: 'MarketDataSource \| None', index_id: 'str', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | IPCA curve — Brazilian inflation-linked real rate (NTN-B implied). |
| `IpcaCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `IpcaCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `IpcaCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `IpcaCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `IpcaCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `IpcaCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `IpcaCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `IpcaCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |

## `treasuryutils.financialtools.curves.protocol`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `InterestRateCurve` | class | `(*args, **kwargs)` | Universal interface for interest rate curves. |
| `InterestRateCurve.bump` | function | `(parallel_shift: float, **kwargs: Any) -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `InterestRateCurve.get_accumulated_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, start_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, end_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType) -> float \| typing.Any` | Return the accumulated rate over the period [start_date, end_date]. |
| `InterestRateCurve.get_discount_factor` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, *, on_undefined: Literal['raise', 'nan', 'zero']) -> float \| typing.Any` | Return the discount factor DF(ref_date, date). |
| `InterestRateCurve.get_forward_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, start: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, end: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType) -> float \| typing.Any` | Return the implied forward rate F(start, end). |
| `InterestRateCurve.get_overnight_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple) -> float \| typing.Any` | Return the overnight rate for the given reference date. |
| `InterestRateCurve.get_rate` | function | `(ref_date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, date: datetime.date \| datetime.datetime \| str \| int \| float \| list \| tuple, *, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType, on_undefined: Literal['raise', 'nan', 'zero']) -> float \| typing.Any` | Return the spot yield r(t) for a given compounding convention. |

## `treasuryutils.financialtools.curves.sofr`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `SofrCurve` | class | `(*, market_data: 'MarketDataSource \| None', index_id: 'str', curve_id: 'str', interpolation: 'InterpolationMethod', day_count: 'DayCountConvention', calendar: 'str \| Calendar', quote_compounding: 'CompoundingType', _panel_override: 'Any \| None') -> 'None'` | SOFR curve — USD secured overnight financing rate. |
| `SofrCurve.bump` | function | `(parallel_shift: 'float', **kwargs: 'Any') -> 'InterestRateCurve'` | Return a new curve instance with rates shifted by ``parallel_shift``. |
| `SofrCurve.bump_at_vertex` | function | `(ref_date: 'date', vertex_date: 'date', shift: 'float') -> 'InterestRateCurve'` | Return a new curve with a single vertex bumped. |
| `SofrCurve.get_accumulated_rate` | function | `(ref_date: 'DateScalar \| DateArray', start_date: 'DateScalar \| DateArray', end_date: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Accumulated rate over ``[start_date, end_date]`` as seen from ``ref_date``. |
| `SofrCurve.get_discount_factor` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Discount factor ``DF(ref_date, date) = N(ref_date) / N(date)``, the numéraire ratio. |
| `SofrCurve.get_forward_rate` | function | `(ref_date: 'DateScalar \| DateArray', start: 'DateScalar \| DateArray', end: 'DateScalar \| DateArray', compounding: 'CompoundingType') -> 'float \| Any'` | Forward rate between ``start`` and ``end`` as seen from ``ref_date``. |
| `SofrCurve.get_overnight_rate` | function | `(ref_date: 'DateScalar \| DateArray') -> 'float \| Any'` | Realized one-business-day rate at ``ref_date`` (realized-only; ADR-0100 §7). |
| `SofrCurve.get_rate` | function | `(ref_date: 'DateScalar \| DateArray', date: 'DateScalar \| DateArray', *, compounding: 'CompoundingType', on_undefined: "Literal['raise', 'nan', 'zero']") -> 'float \| Any'` | Term-structure zero rate at maturity ``date`` as seen from ``ref_date``. |
| `SofrCurve.vertices` | function | `(ref_date: 'date') -> 'list[date]'` | Return sorted vertex maturity dates for the given ref_date. |

## `treasuryutils.financialtools.instruments`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AmortizationType` | enum | `BULLET='BULLET', SAC='SAC', PRICE='PRICE', CUSTOM='CUSTOM'` | Principal repayment pattern for an instrument leg. |
| `CapFloorFeature` | class | `(*, type: Literal['cap', 'floor', 'collar'], strike: decimal.Decimal, is_genuine_market_protection: bool, modifies_time_value: bool) -> None` | Capped/floored variable-rate feature (B4.1.13 Instrument C, B4.1.15). |
| `CashFlowSchedule` | class | `(*, schedule_id: str, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, terms_id: str, terms_version: int, cashflows: treasuryutils.financialtools.instruments.models.DataFrameLike) -> None` | Versioned expected cash-flow schedule. |
| `CLIFeature` | class | `(*, tranche_seniority: typing.Annotated[int, Ge(ge=0)], underlying_pool_passes: bool, credit_risk_proportional: bool) -> None` | Contractually linked instrument tranche (B4.1.20-B4.1.26). |
| `ContingentFeature` | class | `(*, relates_to_basic_lending_risk: bool, max_cumulative_cf_deviation_bps: decimal.Decimal, fair_value_at_initial_recognition: decimal.Decimal) -> None` | Contingent cash-flow feature (B4.1.10, B4.1.10A as of 2026). |
| `ContractualFeatures` | class | `(*, instrument_currency: treasuryutils.financialtools.domain.identifiers.Currency, inflation_index_currency: treasuryutils.financialtools.domain.identifiers.Currency \| None, cap_floor: treasuryutils.financialtools.instruments.models.CapFloorFeature \| None, conversion: treasuryutils.financialtools.instruments.models.ConversionFeature \| None, contingent: tuple[treasuryutils.financialtools.instruments.models.ContingentFeature, ...], non_recourse: treasuryutils.financialtools.instruments.models.NonRecourseFeature \| None, contractually_linked: treasuryutils.financialtools.instruments.models.CLIFeature \| None, prepayment: treasuryutils.financialtools.instruments.models.PrepaymentFeature \| None, extension: treasuryutils.financialtools.instruments.models.ExtensionFeature \| None, leverage: treasuryutils.financialtools.instruments.models.LeverageFeature \| None, modified_tvm: treasuryutils.financialtools.instruments.models.ModifiedTVMFeature \| None, references_third_party_credit: bool) -> None` | Aggregate of contractual features relevant to SPPI evaluation. |
| `ConversionFeature` | class | `(*, settlement: Literal['fixed_shares', 'variable_shares_par_equivalent', 'cash_at_holder_choice'], issuer_shares_quoted: bool, is_genuine: bool) -> None` | Convertible-bond conversion feature (B4.1.7, B4.1.14 Instrument F). |
| `decode_instrument` | function | `(source: 'str \| Path \| dict[str, Any]', *, id_generator: 'IdGenerator \| None', seen_names: 'dict[str, int] \| None', generate_schedule: 'bool', calendar: 'object') -> 'DecodedInstrument'` | Decode a human-friendly YAML into the full graph of Pydantic models. |
| `decode_instruments` | function | `(sources: 'list[str \| Path \| dict[str, Any]]', *, id_generator: 'IdGenerator \| None', generate_schedule: 'bool', calendar: 'object') -> 'list[DecodedInstrument]'` | Decode multiple YAML definitions, sharing a single ID generator. |
| `DecodedInstrument` | class | `(instrument: 'Instrument', terms: 'InstrumentTerms', schedule: 'CashFlowSchedule \| None', position: 'Position \| None', book_classification: 'BookClassification \| None', accounting_designation: 'AccountingDesignation \| None', measurement_config: 'MeasurementConfig \| None', ecl_parameters: 'ECLParameters \| None') -> None` | All domain objects decoded from a single YAML instrument definition. |
| `ExtensionFeature` | class | `(*, extends_at_borrower_option: bool, cf_during_extension_remain_basic: bool) -> None` | Term-extension option (B4.1.11(c)). |
| `generate_schedule` | function | `(terms: 'InstrumentTerms', *, calendar: 'object', schedule_version: 'int \| None') -> 'CashFlowSchedule'` | Generate a versioned authored cash-flow schedule from contract terms. |
| `generate_schedule_df` | function | `(terms: 'InstrumentTerms', *, calendar: 'object') -> 'Any'` | Generate a validated cashflow DataFrame directly from contract terms. |
| `generate_schedules` | function | `(terms_list: 'Sequence[InstrumentTerms]', *, calendar: 'object') -> 'Any'` | Generate validated cashflow DataFrame for multiple instruments. |
| `Instrument` | class | `(*, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, currency: treasuryutils.financialtools.domain.identifiers.Currency, trade_date: datetime.date, issuer: str \| None, isin: str \| None, name: str \| None, status: treasuryutils.financialtools.domain.identifiers.InstrumentStatus, external_id: str \| None, external_source: str \| None, contractual_features: treasuryutils.financialtools.instruments.models.ContractualFeatures \| None) -> None` | Static instrument identity. |
| `InstrumentTerms` | class | `(*, terms_id: str, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, effective_date: datetime.date, maturity_date: datetime.date, notional: decimal.Decimal, legs: typing.Annotated[tuple[treasuryutils.financialtools.instruments.models.LegDefinition, ...], MinLen(min_length=1)]) -> None` | Versioned contractual terms for an instrument. |
| `LegDefinition` | class | `(*, leg_id: str, direction: Literal[-1, 1], currency: treasuryutils.financialtools.domain.identifiers.Currency, notional: typing.Annotated[decimal.Decimal, Gt(gt=0)], leg_type: treasuryutils.financialtools.domain.identifiers.RateType, day_count: treasuryutils.calendartools.day_count.conventions.DayCountConvention, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType, spread_method: treasuryutils.financialtools.domain.identifiers.SpreadMethod, payment_frequency: treasuryutils.financialtools.instruments.models.PaymentFrequency, business_day_conv: Union[Literal['following', 'preceding', 'modified_following', 'modified_preceding'], str], amortization_type: treasuryutils.financialtools.instruments.models.AmortizationType, fixed_rate: decimal.Decimal \| None, index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, index_perc: decimal.Decimal, spread: decimal.Decimal, name: str \| None, fixing_convention: treasuryutils.financialtools.domain.identifiers.FixingConvention, fixing_lag: typing.Annotated[int, Ge(ge=0)], payment_delay: typing.Annotated[int, Ge(ge=0)]) -> None` | Rules for generating a single leg cash-flow schedule. |
| `LeverageFeature` | class | `(*, multiplier: decimal.Decimal) -> None` | Contractual leverage on the variable component (B4.1.9, B4.1.18). |
| `ModifiedTVMFeature` | class | `(*, reset_period_months: typing.Annotated[int, Ge(ge=0)], tenor_months: typing.Annotated[int, Ge(ge=0)], benchmark_cf_deviation_bps: decimal.Decimal) -> None` | Modified time value of money (B4.1.9B-B4.1.9E). |
| `NonRecourseFeature` | class | `(*, underlying_asset_pool: tuple[str, ...], has_topup_right: bool, look_through_passes: bool) -> None` | Non-recourse loan with contractual look-through (B4.1.16, B4.1.16A). |
| `PaymentFrequency` | enum | `DAILY='DAILY', MONTHLY='MONTHLY', QUARTERLY='QUARTERLY', SEMIANNUAL='SEMIANNUAL', ANNUAL='ANNUAL', AT_MATURITY='AT_MATURITY'` | Coupon or amortization payment frequency for an instrument leg. |
| `PrepaymentFeature` | class | `(*, at_par: bool, compensation_reasonable: bool, is_make_whole: bool) -> None` | Prepayment at par or with reasonable compensation (B4.1.11(b), B4.1.12). |
| `resolve_as_of` | function | `(versions: 'Sequence[T]', *, as_of: 'date') -> 'T'` | Resolve the unique version active on a reference date. |
| `Versioned` | class | `(*args, **kwargs)` | Protocol for entities with SCD-2 style validity windows. |

## `treasuryutils.financialtools.instruments.decoder`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `decode_instrument` | function | `(source: 'str \| Path \| dict[str, Any]', *, id_generator: 'IdGenerator \| None', seen_names: 'dict[str, int] \| None', generate_schedule: 'bool', calendar: 'object') -> 'DecodedInstrument'` | Decode a human-friendly YAML into the full graph of Pydantic models. |
| `decode_instruments` | function | `(sources: 'list[str \| Path \| dict[str, Any]]', *, id_generator: 'IdGenerator \| None', generate_schedule: 'bool', calendar: 'object') -> 'list[DecodedInstrument]'` | Decode multiple YAML definitions, sharing a single ID generator. |
| `DecodedInstrument` | class | `(instrument: 'Instrument', terms: 'InstrumentTerms', schedule: 'CashFlowSchedule \| None', position: 'Position \| None', book_classification: 'BookClassification \| None', accounting_designation: 'AccountingDesignation \| None', measurement_config: 'MeasurementConfig \| None', ecl_parameters: 'ECLParameters \| None') -> None` | All domain objects decoded from a single YAML instrument definition. |

## `treasuryutils.financialtools.instruments.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AmortizationType` | enum | `BULLET='BULLET', SAC='SAC', PRICE='PRICE', CUSTOM='CUSTOM'` | Principal repayment pattern for an instrument leg. |
| `CapFloorFeature` | class | `(*, type: Literal['cap', 'floor', 'collar'], strike: decimal.Decimal, is_genuine_market_protection: bool, modifies_time_value: bool) -> None` | Capped/floored variable-rate feature (B4.1.13 Instrument C, B4.1.15). |
| `CashFlowSchedule` | class | `(*, schedule_id: str, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, terms_id: str, terms_version: int, cashflows: treasuryutils.financialtools.instruments.models.DataFrameLike) -> None` | Versioned expected cash-flow schedule. |
| `CLIFeature` | class | `(*, tranche_seniority: typing.Annotated[int, Ge(ge=0)], underlying_pool_passes: bool, credit_risk_proportional: bool) -> None` | Contractually linked instrument tranche (B4.1.20-B4.1.26). |
| `ContingentFeature` | class | `(*, relates_to_basic_lending_risk: bool, max_cumulative_cf_deviation_bps: decimal.Decimal, fair_value_at_initial_recognition: decimal.Decimal) -> None` | Contingent cash-flow feature (B4.1.10, B4.1.10A as of 2026). |
| `ContractualFeatures` | class | `(*, instrument_currency: treasuryutils.financialtools.domain.identifiers.Currency, inflation_index_currency: treasuryutils.financialtools.domain.identifiers.Currency \| None, cap_floor: treasuryutils.financialtools.instruments.models.CapFloorFeature \| None, conversion: treasuryutils.financialtools.instruments.models.ConversionFeature \| None, contingent: tuple[treasuryutils.financialtools.instruments.models.ContingentFeature, ...], non_recourse: treasuryutils.financialtools.instruments.models.NonRecourseFeature \| None, contractually_linked: treasuryutils.financialtools.instruments.models.CLIFeature \| None, prepayment: treasuryutils.financialtools.instruments.models.PrepaymentFeature \| None, extension: treasuryutils.financialtools.instruments.models.ExtensionFeature \| None, leverage: treasuryutils.financialtools.instruments.models.LeverageFeature \| None, modified_tvm: treasuryutils.financialtools.instruments.models.ModifiedTVMFeature \| None, references_third_party_credit: bool) -> None` | Aggregate of contractual features relevant to SPPI evaluation. |
| `ConversionFeature` | class | `(*, settlement: Literal['fixed_shares', 'variable_shares_par_equivalent', 'cash_at_holder_choice'], issuer_shares_quoted: bool, is_genuine: bool) -> None` | Convertible-bond conversion feature (B4.1.7, B4.1.14 Instrument F). |
| `DataFrameLike` | class | `(*args, **kwargs)` | Minimal DataFrame interface required by CashFlowSchedule. |
| `ExtensionFeature` | class | `(*, extends_at_borrower_option: bool, cf_during_extension_remain_basic: bool) -> None` | Term-extension option (B4.1.11(c)). |
| `Instrument` | class | `(*, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, currency: treasuryutils.financialtools.domain.identifiers.Currency, trade_date: datetime.date, issuer: str \| None, isin: str \| None, name: str \| None, status: treasuryutils.financialtools.domain.identifiers.InstrumentStatus, external_id: str \| None, external_source: str \| None, contractual_features: treasuryutils.financialtools.instruments.models.ContractualFeatures \| None) -> None` | Static instrument identity. |
| `InstrumentTerms` | class | `(*, terms_id: str, instrument_id: str, instrument_type: treasuryutils.financialtools.domain.identifiers.InstrumentType, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: str, effective_date: datetime.date, maturity_date: datetime.date, notional: decimal.Decimal, legs: typing.Annotated[tuple[treasuryutils.financialtools.instruments.models.LegDefinition, ...], MinLen(min_length=1)]) -> None` | Versioned contractual terms for an instrument. |
| `LegDefinition` | class | `(*, leg_id: str, direction: Literal[-1, 1], currency: treasuryutils.financialtools.domain.identifiers.Currency, notional: typing.Annotated[decimal.Decimal, Gt(gt=0)], leg_type: treasuryutils.financialtools.domain.identifiers.RateType, day_count: treasuryutils.calendartools.day_count.conventions.DayCountConvention, compounding: treasuryutils.financialtools.domain.identifiers.CompoundingType, spread_method: treasuryutils.financialtools.domain.identifiers.SpreadMethod, payment_frequency: treasuryutils.financialtools.instruments.models.PaymentFrequency, business_day_conv: Union[Literal['following', 'preceding', 'modified_following', 'modified_preceding'], str], amortization_type: treasuryutils.financialtools.instruments.models.AmortizationType, fixed_rate: decimal.Decimal \| None, index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, index_perc: decimal.Decimal, spread: decimal.Decimal, name: str \| None, fixing_convention: treasuryutils.financialtools.domain.identifiers.FixingConvention, fixing_lag: typing.Annotated[int, Ge(ge=0)], payment_delay: typing.Annotated[int, Ge(ge=0)]) -> None` | Rules for generating a single leg cash-flow schedule. |
| `LeverageFeature` | class | `(*, multiplier: decimal.Decimal) -> None` | Contractual leverage on the variable component (B4.1.9, B4.1.18). |
| `ModifiedTVMFeature` | class | `(*, reset_period_months: typing.Annotated[int, Ge(ge=0)], tenor_months: typing.Annotated[int, Ge(ge=0)], benchmark_cf_deviation_bps: decimal.Decimal) -> None` | Modified time value of money (B4.1.9B-B4.1.9E). |
| `NonRecourseFeature` | class | `(*, underlying_asset_pool: tuple[str, ...], has_topup_right: bool, look_through_passes: bool) -> None` | Non-recourse loan with contractual look-through (B4.1.16, B4.1.16A). |
| `PaymentFrequency` | enum | `DAILY='DAILY', MONTHLY='MONTHLY', QUARTERLY='QUARTERLY', SEMIANNUAL='SEMIANNUAL', ANNUAL='ANNUAL', AT_MATURITY='AT_MATURITY'` | Coupon or amortization payment frequency for an instrument leg. |
| `PrepaymentFeature` | class | `(*, at_par: bool, compensation_reasonable: bool, is_make_whole: bool) -> None` | Prepayment at par or with reasonable compensation (B4.1.11(b), B4.1.12). |

## `treasuryutils.financialtools.instruments.schedule`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `generate_schedule` | function | `(terms: 'InstrumentTerms', *, calendar: 'object', schedule_version: 'int \| None') -> 'CashFlowSchedule'` | Generate a versioned authored cash-flow schedule from contract terms. |
| `generate_schedule_df` | function | `(terms: 'InstrumentTerms', *, calendar: 'object') -> 'Any'` | Generate a validated cashflow DataFrame directly from contract terms. |
| `generate_schedules` | function | `(terms_list: 'Sequence[InstrumentTerms]', *, calendar: 'object') -> 'Any'` | Generate validated cashflow DataFrame for multiple instruments. |

## `treasuryutils.financialtools.instruments.versioning`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `resolve_as_of` | function | `(versions: 'Sequence[T]', *, as_of: 'date') -> 'T'` | Resolve the unique version active on a reference date. |
| `Versioned` | class | `(*args, **kwargs)` | Protocol for entities with SCD-2 style validity windows. |

## `treasuryutils.financialtools.market_data`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CurveConvention` | class | `(curve_id: 'str', day_count: 'str', quote_compounding: 'str', default_interpolation: 'str', currency: 'str \| None') -> None` | Default day-count and compounding conventions for a curve. |
| `CurveDatasetSpec` | class | `(dataset_name: 'str', ref_date_col: 'str', maturity_date_col: 'str', x_expr: 'pl.Expr', y_col: 'str') -> None` | Mapping from a raw dataset to canonical curve panel fields. |
| `CurveDatasetSpec.x_root_columns` | function | `() -> 'tuple[str, ...]'` | Return source columns referenced by x_expr (stable order, deduplicated). |
| `CurveNodePanel` | class | `(df: 'pl.DataFrame') -> None` | Projected curve nodes across many ref_dates (panel data). |
| `DatatoolsMarketDataSource` | class | `(*, reader: '_DatasetReader \| None') -> 'None'` | MarketDataSource backed by DataTools materialized datasets. |
| `DatatoolsMarketDataSource.clear_cache` | function | `() -> 'None'` | Clear all cached curve panels and index series. |
| `DatatoolsMarketDataSource.get_all_conventions` | function | `() -> 'pl.DataFrame'` | Return all known conventions as a canonical DataFrame. |
| `DatatoolsMarketDataSource.get_curve_convention` | function | `(curve_id: 'str') -> 'CurveConvention \| None'` | Return the convention for *curve_id*, or ``None`` if unknown. |
| `DatatoolsMarketDataSource.get_curve_node_panel` | function | `(curve_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'CurveNodePanel'` | Return normalized curve nodes for *curve_id*. |
| `DatatoolsMarketDataSource.get_index_level_series` | function | `(index_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'IndexLevelSeries'` | Return normalized index level time series for *index_id*. |
| `IndexDatasetSpec` | class | `(dataset_name: 'str', ref_date_col: 'str', level_col: 'str') -> None` | Mapping from a raw dataset to canonical index level fields. |
| `IndexLevelSeries` | class | `(df: 'pl.DataFrame') -> None` | Index levels over time (time series). |
| `InMemoryMarketDataSource` | class | `(*, datasets: 'dict[str, pl.DataFrame]', curve_specs: 'dict[str, CurveDatasetSpec]', index_specs: 'dict[str, IndexDatasetSpec]', conventions: 'dict[str, CurveConvention] \| None') -> 'None'` | Pure in-memory MarketDataSource for testing and local experimentation. |
| `InMemoryMarketDataSource.clear_cache` | function | `() -> 'None'` | Clear all cached curve panels and index series. |
| `InMemoryMarketDataSource.get_all_conventions` | function | `() -> 'pl.DataFrame'` | Return all known conventions as a canonical DataFrame. |
| `InMemoryMarketDataSource.get_curve_convention` | function | `(curve_id: 'str') -> 'CurveConvention \| None'` | Return the convention for *curve_id*, or ``None`` if unknown. |
| `InMemoryMarketDataSource.get_curve_node_panel` | function | `(curve_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'CurveNodePanel'` | Return normalized curve nodes for *curve_id*. |
| `InMemoryMarketDataSource.get_index_level_series` | function | `(index_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'IndexLevelSeries'` | Return normalized index level time series for *index_id*. |
| `MarketDataBackendError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an underlying backend read fails. |
| `MarketDataContractError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an input/output contract is violated. |
| `MarketDataCoverageError` | class | `(dataset_name: 'str', *, requested: 'tuple[date, date]', covered: 'tuple[date, date] \| None', code: 'str') -> 'None'` | Raised when a ``covers=(lo, hi)`` read cannot be satisfied for a dataset. |
| `MarketDataError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base class for market-data related errors. |
| `MarketDataNotFoundError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when a requested market-data identifier does not exist. |
| `MarketDataSource` | class | `(*args, **kwargs)` | Read-only market data boundary used by FinancialTools curves. |
| `MarketDataSource.clear_cache` | function | `() -> 'None'` | Clear any internal caches. |
| `MarketDataSource.get_all_conventions` | function | `() -> 'pl.DataFrame'` | Return all known conventions as a canonical DataFrame. |
| `MarketDataSource.get_curve_convention` | function | `(curve_id: 'str') -> 'CurveConvention \| None'` | Return the convention for *curve_id*, or ``None`` if unknown. |
| `MarketDataSource.get_curve_node_panel` | function | `(curve_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'CurveNodePanel'` | Return normalized curve nodes for *curve_id*. |
| `MarketDataSource.get_index_level_series` | function | `(index_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'IndexLevelSeries'` | Return normalized index level time series for *index_id*. |
| `MarketDataValidationError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when canonical invariant validation fails. |

## `treasuryutils.financialtools.market_data.adapters`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CacheControl` | class | `(*args, **kwargs)` | Optional cache lifecycle control for stateful adapters. |
| `CacheControl.clear_cache` | function | `() -> 'None'` | Invalidate all cached state held by the adapter. |
| `ConventionProvider` | class | `(*args, **kwargs)` | Protocol for adapters that can return curve conventions. |
| `ConventionProvider.get_all_conventions` | function | `() -> 'pl.DataFrame'` | Return all known conventions as a canonical DataFrame. |
| `ConventionProvider.get_curve_convention` | function | `(curve_id: 'str') -> 'CurveConvention \| None'` | Return the convention for *curve_id*, or ``None`` if unknown. |
| `RawFrameReader` | class | `(*args, **kwargs)` | Protocol for adapters that can read raw frames by dataset name. |
| `RawFrameReader.read` | function | `(*, dataset_name: 'str', columns: 'tuple[str, ...] \| None') -> 'pl.DataFrame'` | Return a DataFrame for the given dataset, optionally projected to *columns*. |

## `treasuryutils.financialtools.market_data.adapters.datatools`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DatatoolsDatasetAdapter` | class | `(*, memory_map: 'bool') -> 'None'` | Raw-frame adapter backed by DataTools DatasetManager handles. |
| `DatatoolsDatasetAdapter.clear_cache` | function | `() -> 'None'` | Discard all cached DatasetManager instances. |
| `DatatoolsDatasetAdapter.read` | function | `(*, dataset_name: 'str', columns: 'tuple[str, ...] \| None', covers: 'tuple[date, date] \| None') -> 'pl.DataFrame'` | Read a dataset from the DataTools cache, raising on backend failures. |

## `treasuryutils.financialtools.market_data.adapters.in_memory`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `InMemoryDatasetAdapter` | class | `(*, datasets: 'Mapping[str, pl.DataFrame]', conventions: 'Mapping[str, CurveConvention]') -> 'None'` | Raw-frame adapter backed by in-memory DataFrame dictionaries. |
| `InMemoryDatasetAdapter.get_all_conventions` | function | `() -> 'pl.DataFrame'` | Return all stored conventions as a canonical DataFrame. |
| `InMemoryDatasetAdapter.get_curve_convention` | function | `(curve_id: 'str') -> 'CurveConvention \| None'` | Return the convention for *curve_id*, or ``None`` if unknown. |
| `InMemoryDatasetAdapter.read` | function | `(*, dataset_name: 'str', columns: 'tuple[str, ...] \| None') -> 'pl.DataFrame'` | Return a DataFrame from the in-memory store, raising if missing. |

## `treasuryutils.financialtools.market_data.errors`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `MarketDataBackendError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an underlying backend read fails. |
| `MarketDataContractError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when an input/output contract is violated. |
| `MarketDataCoverageError` | class | `(dataset_name: 'str', *, requested: 'tuple[date, date]', covered: 'tuple[date, date] \| None', code: 'str') -> 'None'` | Raised when a ``covers=(lo, hi)`` read cannot be satisfied for a dataset. |
| `MarketDataError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base class for market-data related errors. |
| `MarketDataNotFoundError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when a requested market-data identifier does not exist. |
| `MarketDataValidationError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when canonical invariant validation fails. |

## `treasuryutils.financialtools.market_data.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CurveConvention` | class | `(curve_id: 'str', day_count: 'str', quote_compounding: 'str', default_interpolation: 'str', currency: 'str \| None') -> None` | Default day-count and compounding conventions for a curve. |
| `CurveNodePanel` | class | `(df: 'pl.DataFrame') -> None` | Projected curve nodes across many ref_dates (panel data). |
| `IndexLevelSeries` | class | `(df: 'pl.DataFrame') -> None` | Index levels over time (time series). |

## `treasuryutils.financialtools.market_data.normalizers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `conventions_to_frame` | function | `(conventions: 'Iterable[CurveConvention]') -> 'pl.DataFrame'` | Build a canonical conventions frame from convention models. |
| `normalize_conventions_frame` | function | `(raw: 'pl.DataFrame') -> 'pl.DataFrame'` | Validate and canonicalize conventions dataframe contract. |
| `normalize_curve_node_panel` | function | `(*, curve_id: 'str', raw: 'pl.DataFrame', spec: 'CurveDatasetSpec') -> 'CurveNodePanel'` | Normalize raw curve rows into canonical CurveNodePanel shape. |
| `normalize_index_level_series` | function | `(*, index_id: 'str', raw: 'pl.DataFrame', spec: 'IndexDatasetSpec') -> 'IndexLevelSeries'` | Normalize raw index rows into canonical IndexLevelSeries shape. |

## `treasuryutils.financialtools.market_data.protocol`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `MarketDataSource` | class | `(*args, **kwargs)` | Read-only market data boundary used by FinancialTools curves. |
| `MarketDataSource.clear_cache` | function | `() -> 'None'` | Clear any internal caches. |
| `MarketDataSource.get_all_conventions` | function | `() -> 'pl.DataFrame'` | Return all known conventions as a canonical DataFrame. |
| `MarketDataSource.get_curve_convention` | function | `(curve_id: 'str') -> 'CurveConvention \| None'` | Return the convention for *curve_id*, or ``None`` if unknown. |
| `MarketDataSource.get_curve_node_panel` | function | `(curve_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'CurveNodePanel'` | Return normalized curve nodes for *curve_id*. |
| `MarketDataSource.get_index_level_series` | function | `(index_id: 'str', *, covers: 'tuple[date, date] \| None') -> 'IndexLevelSeries'` | Return normalized index level time series for *index_id*. |

## `treasuryutils.financialtools.market_data.specs`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CurveDatasetSpec` | class | `(dataset_name: 'str', ref_date_col: 'str', maturity_date_col: 'str', x_expr: 'pl.Expr', y_col: 'str') -> None` | Mapping from a raw dataset to canonical curve panel fields. |
| `CurveDatasetSpec.x_root_columns` | function | `() -> 'tuple[str, ...]'` | Return source columns referenced by x_expr (stable order, deduplicated). |
| `IndexDatasetSpec` | class | `(dataset_name: 'str', ref_date_col: 'str', level_col: 'str') -> None` | Mapping from a raw dataset to canonical index level fields. |

## `treasuryutils.financialtools.positions`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Agreement` | class | `(*, agreement_id: typing.Annotated[str, MinLen(min_length=1)], agreement_type: treasuryutils.financialtools.domain.identifiers.AgreementType, entity_id: typing.Annotated[str, MinLen(min_length=1)], counterparty_entity_id: typing.Annotated[str, MinLen(min_length=1)], effective_date: datetime.date, maturity_date: datetime.date \| None, notional_limit: typing.Annotated[decimal.Decimal, Gt(gt=0)], currency: treasuryutils.financialtools.domain.identifiers.Currency, base_index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, base_spread: decimal.Decimal \| None, allowed_instrument_types: tuple[treasuryutils.financialtools.domain.identifiers.InstrumentType, ...] \| None, min_tenor_days: int \| None, max_tenor_days: int \| None, status: treasuryutils.financialtools.domain.identifiers.AgreementStatus) -> None` | Master framework that groups instruments by commercial relationship. |
| `BookClassification` | class | `(*, instrument_id: typing.Annotated[str, MinLen(min_length=1)], book: str, desk: str \| None, strategy: str \| None) -> None` | Managerial/business classification for reporting and grouping. |
| `build_cashflow_projection` | function | `(priced_cashflows: 'Any', positions_df: 'Any', *, fx_rates: 'dict[str, float] \| None', base_currency: 'str', instrument_col: 'str', validate: 'bool') -> 'Any'` | Build FX-aware cashflow projection from priced cashflows. |
| `build_unified_position` | function | `(position_values: 'Any', pnl_attribution: 'Any \| None', risk_metrics: 'Any \| None', period_settlements: 'Any \| None', leg_decomposition: 'Any \| None', period_results: 'Any \| None', *, metadata: 'Any \| None', ref_date_prev: 'Any', validate: 'bool') -> 'Any'` | Assemble unified position from pre-computed pipeline outputs. |
| `compute_portfolio_risk` | function | `(key_rate_dv01: 'Any', rate_history: 'np.ndarray', *, portfolio_id: 'str', ref_date: 'date', confidence_level: 'float', ewma_decay: 'float', observation_window: 'int', base_currency: 'str', fx_rates: 'Mapping[str, float] \| None') -> 'dict[str, Any]'` | Compute parametric VaR and DV01 aggregates for a portfolio. |
| `compute_portfolio_risk_from_df` | function | `(key_rate_dv01_df: 'Any', rate_change_df: 'Any', *, portfolio_id: 'str', ref_date: 'date', confidence_level: 'float', ewma_decay: 'float', observation_window: 'int', base_currency: 'str', fx_rates: 'Mapping[str, float] \| None', validate: 'bool') -> 'Any'` | Compute portfolio VaR from DataFrames. |
| `EntityGroup` | class | `(*, group_id: str, parent_entity_id: str, child_entity_id: str, ownership_pct: typing.Annotated[decimal.Decimal, Gt(gt=0), Le(le=1)], consolidation_method: treasuryutils.financialtools.domain.identifiers.ConsolidationMethod, effective_date: datetime.date) -> None` | Ownership relationship between entities for consolidation. |
| `LegalEntity` | class | `(*, entity_id: typing.Annotated[str, MinLen(min_length=1)], entity_name: str, entity_type: treasuryutils.financialtools.domain.identifiers.EntityType, country: str, functional_currency: treasuryutils.financialtools.domain.identifiers.Currency, tax_id: str \| None) -> None` | A legal entity that can hold positions. |
| `Portfolio` | class | `(*, portfolio_id: typing.Annotated[str, MinLen(min_length=1)], portfolio_name: str, portfolio_type: treasuryutils.financialtools.domain.identifiers.PortfolioType, business_unit: str \| None) -> None` | Logical grouping of positions by business purpose. |
| `Position` | class | `(*, position_id: typing.Annotated[str, MinLen(min_length=1)], instrument_id: typing.Annotated[str, MinLen(min_length=1)], portfolio_id: typing.Annotated[str, MinLen(min_length=1)], entity_id: typing.Annotated[str, MinLen(min_length=1)], counterparty_entity_id: str \| None, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: treasuryutils.financialtools.domain.identifiers.PositionReason, settlement_date: datetime.date, acquisition_price: typing.Annotated[decimal.Decimal, Gt(gt=0)], acquisition_cost: decimal.Decimal, transaction_costs: decimal.Decimal, quantity: typing.Annotated[decimal.Decimal, Ge(ge=0)], status: treasuryutils.financialtools.domain.identifiers.PositionStatus) -> None` | Ownership of an instrument — SCD-2 versioned. |
| `scale_attribution_by_position` | function | `(attribution_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit P&L attribution by position quantity. |
| `scale_by_position` | function | `(pricing: 'Any', positions: 'Any', *, quantity_column: 'str', instrument_id_column: 'str', value_columns: 'list[str] \| None', validate: 'bool') -> 'Any'` | Scale per-unit pricing results by position quantity. |
| `scale_key_rate_risk_by_position` | function | `(key_rate_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit key-rate DV01 by position quantity. |
| `scale_risk_by_position` | function | `(risk_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit risk metrics by position quantity. |
| `summarize_leg_values` | function | `(summary: 'Any', *, base_currency: 'str', fx_rates: 'dict[str, float] \| None', fx_rate: 'float \| None') -> 'Any'` | Decompose leg-level pricing into BRL vs foreign currency components. |

## `treasuryutils.financialtools.positions.cashflow_projection`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_cashflow_projection` | function | `(priced_cashflows: 'Any', positions_df: 'Any', *, fx_rates: 'dict[str, float] \| None', base_currency: 'str', instrument_col: 'str', validate: 'bool') -> 'Any'` | Build FX-aware cashflow projection from priced cashflows. |

## `treasuryutils.financialtools.positions.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Agreement` | class | `(*, agreement_id: typing.Annotated[str, MinLen(min_length=1)], agreement_type: treasuryutils.financialtools.domain.identifiers.AgreementType, entity_id: typing.Annotated[str, MinLen(min_length=1)], counterparty_entity_id: typing.Annotated[str, MinLen(min_length=1)], effective_date: datetime.date, maturity_date: datetime.date \| None, notional_limit: typing.Annotated[decimal.Decimal, Gt(gt=0)], currency: treasuryutils.financialtools.domain.identifiers.Currency, base_index: treasuryutils.financialtools.domain.identifiers.MarketIndex \| None, base_spread: decimal.Decimal \| None, allowed_instrument_types: tuple[treasuryutils.financialtools.domain.identifiers.InstrumentType, ...] \| None, min_tenor_days: int \| None, max_tenor_days: int \| None, status: treasuryutils.financialtools.domain.identifiers.AgreementStatus) -> None` | Master framework that groups instruments by commercial relationship. |
| `BookClassification` | class | `(*, instrument_id: typing.Annotated[str, MinLen(min_length=1)], book: str, desk: str \| None, strategy: str \| None) -> None` | Managerial/business classification for reporting and grouping. |
| `EntityGroup` | class | `(*, group_id: str, parent_entity_id: str, child_entity_id: str, ownership_pct: typing.Annotated[decimal.Decimal, Gt(gt=0), Le(le=1)], consolidation_method: treasuryutils.financialtools.domain.identifiers.ConsolidationMethod, effective_date: datetime.date) -> None` | Ownership relationship between entities for consolidation. |
| `LegalEntity` | class | `(*, entity_id: typing.Annotated[str, MinLen(min_length=1)], entity_name: str, entity_type: treasuryutils.financialtools.domain.identifiers.EntityType, country: str, functional_currency: treasuryutils.financialtools.domain.identifiers.Currency, tax_id: str \| None) -> None` | A legal entity that can hold positions. |
| `Portfolio` | class | `(*, portfolio_id: typing.Annotated[str, MinLen(min_length=1)], portfolio_name: str, portfolio_type: treasuryutils.financialtools.domain.identifiers.PortfolioType, business_unit: str \| None) -> None` | Logical grouping of positions by business purpose. |
| `Position` | class | `(*, position_id: typing.Annotated[str, MinLen(min_length=1)], instrument_id: typing.Annotated[str, MinLen(min_length=1)], portfolio_id: typing.Annotated[str, MinLen(min_length=1)], entity_id: typing.Annotated[str, MinLen(min_length=1)], counterparty_entity_id: str \| None, version: int, valid_from: datetime.date, valid_to: datetime.date \| None, reason: treasuryutils.financialtools.domain.identifiers.PositionReason, settlement_date: datetime.date, acquisition_price: typing.Annotated[decimal.Decimal, Gt(gt=0)], acquisition_cost: decimal.Decimal, transaction_costs: decimal.Decimal, quantity: typing.Annotated[decimal.Decimal, Ge(ge=0)], status: treasuryutils.financialtools.domain.identifiers.PositionStatus) -> None` | Ownership of an instrument — SCD-2 versioned. |

## `treasuryutils.financialtools.positions.risk`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_portfolio_risk` | function | `(key_rate_dv01: 'Any', rate_history: 'np.ndarray', *, portfolio_id: 'str', ref_date: 'date', confidence_level: 'float', ewma_decay: 'float', observation_window: 'int', base_currency: 'str', fx_rates: 'Mapping[str, float] \| None') -> 'dict[str, Any]'` | Compute parametric VaR and DV01 aggregates for a portfolio. |
| `compute_portfolio_risk_from_df` | function | `(key_rate_dv01_df: 'Any', rate_change_df: 'Any', *, portfolio_id: 'str', ref_date: 'date', confidence_level: 'float', ewma_decay: 'float', observation_window: 'int', base_currency: 'str', fx_rates: 'Mapping[str, float] \| None', validate: 'bool') -> 'Any'` | Compute portfolio VaR from DataFrames. |

## `treasuryutils.financialtools.positions.scaling`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `scale_attribution_by_position` | function | `(attribution_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit P&L attribution by position quantity. |
| `scale_by_position` | function | `(pricing: 'Any', positions: 'Any', *, quantity_column: 'str', instrument_id_column: 'str', value_columns: 'list[str] \| None', validate: 'bool') -> 'Any'` | Scale per-unit pricing results by position quantity. |
| `scale_key_rate_risk_by_position` | function | `(key_rate_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit key-rate DV01 by position quantity. |
| `scale_risk_by_position` | function | `(risk_df: 'Any', positions_df: 'Any', *, instrument_col: 'str') -> 'Any'` | Scale per-unit risk metrics by position quantity. |

## `treasuryutils.financialtools.positions.unified_position`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_unified_position` | function | `(position_values: 'Any', pnl_attribution: 'Any \| None', risk_metrics: 'Any \| None', period_settlements: 'Any \| None', leg_decomposition: 'Any \| None', period_results: 'Any \| None', *, metadata: 'Any \| None', ref_date_prev: 'Any', validate: 'bool') -> 'Any'` | Assemble unified position from pre-computed pipeline outputs. |
| `summarize_leg_values` | function | `(summary: 'Any', *, base_currency: 'str', fx_rates: 'dict[str, float] \| None', fx_rate: 'float \| None') -> 'Any'` | Decompose leg-level pricing into BRL vs foreign currency components. |

## `treasuryutils.financialtools.pricing`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_key_rate_risk` | function | `(cashflow_df: 'Any', ref_date: 'date', *, discount_curve: 'Any', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', bump_size: 'float', vertices: 'Sequence[date] \| None', validate: 'bool') -> 'Any'` | Compute key-rate DV01 per curve vertex and deal. |
| `compute_pnl_attribution` | function | `(summary_current: 'Any', summary_previous: 'Any', risk_previous: 'Any', *, rate_change: 'float \| Any', overnight_rate: 'float', overnight_rate_previous: 'float', ref_date: 'date', dollar_convexity: 'float \| Any', is_new_deal_mask: 'Any \| None', fx_rate: 'float \| Any', fx_rate_previous: 'float \| Any', present_value_ccy: 'float \| Any', accrued_interest_ccy: 'float \| Any', bump_size: 'float', convexity: 'float \| Any', validate: 'bool') -> 'Any'` | Decompose daily P&L into carry, rate, convexity, FX, and residual components. |
| `compute_risk_metrics` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', bump_size: 'float', bump_projection: 'bool', validate: 'bool') -> 'Any'` | Compute duration and DV01 via bump-and-revalue per (deal_id, ref_date). |
| `extract_period_settlements` | function | `(priced_cashflows: 'Any', ref_date: 'date', ref_date_prev: 'date') -> 'Any'` | Extract settled cashflows in the period (ref_date_prev, ref_date]. |
| `price_cashflows` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', validate: 'bool') -> 'Any'` | Compute priced cashflows — one row per (ref_date, period). |
| `price_cashflows_scd` | function | `(schedule_versions: 'Sequence[tuple[Any, date, date \| None]]', ref_dates: 'Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object') -> 'Any'` | Price cashflows across SCD schedule versions. |
| `price_cashflows_summary` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', validate: 'bool') -> 'Any'` | Aggregate priced cashflows into a leg-level summary. |

## `treasuryutils.financialtools.pricing.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `compute_key_rate_risk` | function | `(cashflow_df: 'Any', ref_date: 'date', *, discount_curve: 'Any', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', bump_size: 'float', vertices: 'Sequence[date] \| None', validate: 'bool') -> 'Any'` | Compute key-rate DV01 per curve vertex and deal. |
| `compute_pnl_attribution` | function | `(summary_current: 'Any', summary_previous: 'Any', risk_previous: 'Any', *, rate_change: 'float \| Any', overnight_rate: 'float', overnight_rate_previous: 'float', ref_date: 'date', dollar_convexity: 'float \| Any', is_new_deal_mask: 'Any \| None', fx_rate: 'float \| Any', fx_rate_previous: 'float \| Any', present_value_ccy: 'float \| Any', accrued_interest_ccy: 'float \| Any', bump_size: 'float', convexity: 'float \| Any', validate: 'bool') -> 'Any'` | Decompose daily P&L into carry, rate, convexity, FX, and residual components. |
| `compute_risk_metrics` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', bump_size: 'float', bump_projection: 'bool', validate: 'bool') -> 'Any'` | Compute duration and DV01 via bump-and-revalue per (deal_id, ref_date). |
| `extract_period_settlements` | function | `(priced_cashflows: 'Any', ref_date: 'date', ref_date_prev: 'date') -> 'Any'` | Extract settled cashflows in the period (ref_date_prev, ref_date]. |
| `price_cashflows` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', validate: 'bool') -> 'Any'` | Compute priced cashflows — one row per (ref_date, period). |
| `price_cashflows_scd` | function | `(schedule_versions: 'Sequence[tuple[Any, date, date \| None]]', ref_dates: 'Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object') -> 'Any'` | Price cashflows across SCD schedule versions. |
| `price_cashflows_summary` | function | `(cashflow_df: 'Any', ref_date: 'date \| Any', *, discount_curve: 'InterestRateCurve', projection_curves: 'Mapping[str, InterestRateCurve] \| None', calendar: 'object', validate: 'bool') -> 'Any'` | Aggregate priced cashflows into a leg-level summary. |

## `treasuryutils.financialtools.pricing.formulas`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `convexity_from_dv01` | function | `(dirty_value_up: 'Any', dirty_value_base: 'Any', dirty_value_down: 'Any', bump_size: 'float') -> 'BackendResult'` | Compute effective modified convexity via central finite difference. |
| `duration_weight` | function | `(time_to_payment: 'Any', pv_cashflow: 'Any') -> 'BackendResult'` | Compute the Macaulay-duration weighted present value term. |
| `effective_dollar_convexity` | function | `(dirty_value_up: 'Any', dirty_value_base: 'Any', dirty_value_down: 'Any', bump_size: 'float') -> 'BackendResult'` | Compute effective dollar convexity via central finite difference. |
| `effective_dollar_convexity_from_modified` | function | `(modified_convexity: 'Any', pv_base: 'Any') -> 'BackendResult'` | Convert modified convexity (years²) to dollar convexity (currency). |
| `effective_modified_convexity` | function | `(dirty_value_up: 'Any', dirty_value_base: 'Any', dirty_value_down: 'Any', bump_size: 'float') -> 'BackendResult'` | Compute effective modified convexity via central finite difference. |
| `fixed_accumulation_factor` | function | `(rate_value: 'Any', year_frac: 'Any', compounding: 'CompoundingType') -> 'BackendResult'` | Compute fixed-leg accumulation factor. |
| `float_accumulation_factor` | function | `(index_growth: 'Any', spread: 'Any', year_frac: 'Any', compounding: 'CompoundingType \| Any', spread_method: 'SpreadMethod \| Any') -> 'BackendResult'` | Compute floating-leg accumulation factor. |
| `float_index_growth` | function | `(df_at_start: 'Any', df_at_end: 'Any', index_perc: 'Any') -> 'BackendResult'` | Compute floating-leg index growth factor. |
| `gamma_second_order` | function | `(dollar_convexity: 'Any', rate_change: 'Any') -> 'BackendResult'` | Compute second-order rate-sensitivity P&L in currency units. |
| `modified_duration_from_dv01` | function | `(dv01: 'Any', dirty_value: 'Any', bump_size: 'float') -> 'BackendResult'` | Compute modified duration from bump-and-revalue DV01. |
| `period_cashflow` | function | `(unit_price: 'Any', accum_factor: 'Any', amortization: 'Any') -> 'BackendResult'` | Compute the contractual period cashflow. |
| `pnl_ccy_accrual_in_base` | function | `(accrued_interest_ccy: 'Any', fx_rate: 'Any') -> 'BackendResult'` | Convert foreign-currency accrued interest to base currency. |
| `pnl_fx_revaluation` | function | `(present_value_ccy: 'Any', fx_rate: 'Any', fx_rate_prev: 'Any') -> 'BackendResult'` | Compute P&L from FX rate changes on foreign-currency positions. |
| `pnl_residual` | function | `(pnl_total: 'Any', theta_carry_value: 'Any', theta_funding_value: 'Any', rho: 'Any', gamma: 'Any', spread: 'Any', pnl_fx: 'Any', pnl_ccy_accrual: 'Any') -> 'BackendResult'` | Compute unexplained P&L residual. |
| `present_value` | function | `(direction: 'Any', cashflow: 'Any', discount_factor: 'Any') -> 'BackendResult'` | Compute the discounted present value. |
| `rho_first_order` | function | `(dv01: 'Any', rate_change: 'Any', bump_size: 'float') -> 'BackendResult'` | Compute first-order rate sensitivity P&L. |
| `theta_carry` | function | `(present_value: 'Any', rate: 'Any', day_count_fraction: 'float') -> 'BackendResult'` | Compute daily carry from the fixed/discount rate. |
| `theta_funding` | function | `(present_value: 'Any', overnight_rate: 'Any', day_count_fraction: 'float') -> 'BackendResult'` | Compute daily funding cost from the overnight rate. |

## `treasuryutils.financialtools.pricing.models`

_No public callables discovered._

## `treasuryutils.financialtools.schema`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AmortizedCostModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-period EIR accrual track output. |
| `CashflowProjectionModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the position-scaled cashflow projection output. |
| `EclResultModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-assessment impairment output. |
| `FairValueChangeModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-period FV movements output (FVTPL). |
| `HedgeResultModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-period hedge accounting output. |
| `KeyRateRiskModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-instrument DV01 at each curve vertex output. |
| `OciMovementModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-period OCI for FVOCI output. |
| `PeriodResultModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the consolidated per-position output. |
| `PnlAttributionModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-instrument daily P&L decomposition output. |
| `PortfolioRiskModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the portfolio-level VaR + DV01 aggregate output. |
| `PricedCashFlowModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the priced cashflow (per-period detail) output. |
| `RiskModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-instrument risk metrics output. |
| `ScaledPositionsModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the position-weighted pricing output. |
| `SummaryModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the per-leg summary output. |
| `UnifiedCashFlowModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the 'Unified Cash Flow' structure. |
| `UnifiedCashFlowModel.from_raw` | method | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Sanitize raw input and validate against the strict schema. |
| `UnifiedPositionModel` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Validates the single normalized unified position table output. |
| `validate_amortized_cost` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate an amortized cost DataFrame against AMORTIZED_COST_SCHEMA. |
| `validate_cashflow_projection` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a cashflow projection DataFrame against CASHFLOW_PROJECTION_SCHEMA. |
| `validate_ecl_result` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate an ECL result DataFrame against ECL_RESULT_SCHEMA. |
| `validate_fair_value_change` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a fair value change DataFrame against FAIR_VALUE_CHANGE_SCHEMA. |
| `validate_flows` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Sanitize and validate a raw cashflow DataFrame. |
| `validate_hedge_result` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a hedge result DataFrame against HEDGE_RESULT_SCHEMA. |
| `validate_key_rate_risk` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a key-rate risk DataFrame against KEY_RATE_RISK_SCHEMA. |
| `validate_oci_movement` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate an OCI movement DataFrame against OCI_MOVEMENT_SCHEMA. |
| `validate_period_result` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a period result DataFrame against PERIOD_RESULT_SCHEMA. |
| `validate_pnl_attribution` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a P&L attribution DataFrame against PNL_ATTRIBUTION_SCHEMA. |
| `validate_portfolio_risk` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a portfolio risk DataFrame against PORTFOLIO_RISK_SCHEMA. |
| `validate_priced_cashflow` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a priced cashflow DataFrame against PRICED_CASHFLOW_SCHEMA. |
| `validate_risk` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a risk DataFrame against RISK_SCHEMA. |
| `validate_scaled_positions` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a scaled positions DataFrame against SCALED_POSITIONS_SCHEMA. |
| `validate_summary` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a summary DataFrame against SUMMARY_SCHEMA. |
| `validate_unified_position` | function | `(df: polars.dataframe.frame.DataFrame, *, validate: bool) -> polars.dataframe.frame.DataFrame` | Validate a unified position DataFrame against UNIFIED_POSITION_SCHEMA. |

## `treasuryutils.financialtools.schema_definition`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BusinessRuleDef` | class | `(name: 'str', description: 'str') -> None` | Backend-agnostic cross-column constraint definition. |
| `CashFlowSchemaDef` | class | `(columns: 'tuple[ColumnDef, ...]', business_rules: 'tuple[BusinessRuleDef, ...]', strict: 'bool', coerce: 'bool') -> None` | Backend-agnostic schema definition used by all financial output schemas. · alias of `SchemaDef` (import: `from treasuryutils.financialtools.schema_definition import SchemaDef`) |
| `CashFlowSchemaDef.extend` | function | `(extra_columns: 'tuple[ColumnDef, ...] \| ColumnDef', *, business_rules: 'tuple[BusinessRuleDef, ...] \| None', strict: 'bool \| None', coerce: 'bool \| None') -> 'SchemaDef'` | Create a new schema by appending columns to this one. |
| `ColumnDef` | class | `(name: 'str', dtype: 'str', description: 'str', nullable: 'bool', default: 'Any', allowed_values: 'AllowedValues', ge: 'float \| int \| None', gt: 'float \| int \| None', le: 'float \| int \| None', lt: 'float \| int \| None', str_length: 'int \| None') -> None` | Backend-agnostic column definition. |
| `resolve_allowed_values` | function | `(allowed_values: 'AllowedValues') -> 'tuple[str, ...] \| None'` | Resolve concrete allowlists and symbolic allowlist references. |
| `SchemaDef` | class | `(columns: 'tuple[ColumnDef, ...]', business_rules: 'tuple[BusinessRuleDef, ...]', strict: 'bool', coerce: 'bool') -> None` | Backend-agnostic schema definition used by all financial output schemas. |
| `SchemaDef.extend` | function | `(extra_columns: 'tuple[ColumnDef, ...] \| ColumnDef', *, business_rules: 'tuple[BusinessRuleDef, ...] \| None', strict: 'bool \| None', coerce: 'bool \| None') -> 'SchemaDef'` | Create a new schema by appending columns to this one. |

## Type Aliases

Type-alias names used in the signatures above, resolved from the treasuryutils source (some are defined under `TYPE_CHECKING`).

| Alias | Definition |
| --- | --- |
| `AllowListSentinel` | `Literal['VALID_DAY_COUNTS']` |
| `AllowedValues` | `tuple[str, ...] \| AllowListSentinel \| None` |
| `DateArray` | `DateSequence \| NumpyDateArray \| PandasDateSeries \| PolarsDateSeries` |
| `DateScalar` | `date \| datetime \| str \| int \| float \| datetime64 \| Timestamp` |
| `DateSequence` | `list[Any] \| tuple[Any, ...]` |
| `NumpyDateArray` | `ndarray` |
| `PandasDateSeries` | `Series \| Index` |
| `PolarsDateSeries` | `PlSeries` |
