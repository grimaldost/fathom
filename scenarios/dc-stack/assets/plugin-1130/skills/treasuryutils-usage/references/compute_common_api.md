# Compute & Common API Reference (generated)

- treasuryutils_version: `1.8.0`
- generated_at_utc: `2026-07-10T16:08:46.035900+00:00`
- install_extras: `treasuryutils (core)`

## Capability status

- Backend-agnostic FRAME ops (the `df_*` dataframe algebra, `asof_join`, `weighted_average`) run on pandas or polars through the narwhals seam (ADR-0040); narwhals wraps frames/series, so a numpy `ndarray` is NOT a frame backend and raises `BackendNotSupportedError` (registry.py `_NARWHALS_CAPABLE_BACKENDS`, where NUMPY is deliberately excluded). The element-wise `umath` primitives (`exp` / `log` / `where` / `safe_divide` / …) DO accept numpy scalars/arrays; the frame algebra above does not.
- SPARK backend symbols are UNWIRED / deferred: single-node is the ratified scope (ADR-0099), no fully-narwhals op registers Spark, and a Spark frame raises `BackendNotSupportedError` at runtime (compute/registry.py + umath.py). Wiring Spark is an explicit `register(..., Backend.SPARK, ...)` code change.
- The curated backend-agnostic `nw.Expr` surface is `treasuryutils.compute.expr` (`col` / `lit` / `when`, ADR-0106), deliberately kept OUTSIDE `compute.__all__`.

## `treasuryutils.common`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `clean_whitespace` | function | `(text: 'str \| Any') -> 'str \| Any'` | Normalize whitespace (e.g., '  A   B  ' -> 'A B'). |
| `normalize_text` | function | `(text: 'str \| Any') -> 'str \| Any'` | Remove accents (e.g., 'São Paulo' -> 'Sao Paulo'). · alias of `strip_accents` (import: `from treasuryutils.common import strip_accents`) |
| `SmartIdentifier` | enum | `` | StrEnum subclass with case-insensitive instantiation. |
| `strip_accents` | function | `(text: 'str \| Any') -> 'str \| Any'` | Remove accents (e.g., 'São Paulo' -> 'Sao Paulo'). |
| `to_camel_case` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to camelCase (e.g., 'snake_case' -> 'snakeCase'). |
| `to_kebab_case` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to kebab-case (e.g., 'CamelCase' -> 'camel-case'). |
| `to_slug` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to kebab-case (e.g., 'CamelCase' -> 'camel-case'). · alias of `to_kebab_case` (import: `from treasuryutils.common import to_kebab_case`) |
| `to_snake_case` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to snake_case (e.g., 'CamelCase' -> 'camel_case'). |

## `treasuryutils.common.identifiers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `SmartIdentifier` | enum | `` | StrEnum subclass with case-insensitive instantiation. |

## `treasuryutils.common.strings`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `clean_whitespace` | function | `(text: 'str \| Any') -> 'str \| Any'` | Normalize whitespace (e.g., '  A   B  ' -> 'A B'). |
| `normalize_text` | function | `(text: 'str \| Any') -> 'str \| Any'` | Remove accents (e.g., 'São Paulo' -> 'Sao Paulo'). · alias of `strip_accents` (import: `from treasuryutils.common import strip_accents`) |
| `strip_accents` | function | `(text: 'str \| Any') -> 'str \| Any'` | Remove accents (e.g., 'São Paulo' -> 'Sao Paulo'). |
| `to_camel_case` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to camelCase (e.g., 'snake_case' -> 'snakeCase'). |
| `to_kebab_case` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to kebab-case (e.g., 'CamelCase' -> 'camel-case'). |
| `to_slug` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to kebab-case (e.g., 'CamelCase' -> 'camel-case'). · alias of `to_kebab_case` (import: `from treasuryutils.common import to_kebab_case`) |
| `to_snake_case` | function | `(text: 'str \| Any') -> 'str \| Any'` | Convert to snake_case (e.g., 'CamelCase' -> 'camel_case'). |

## `treasuryutils.compute`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `asof_aggregate` | function | `(data: 'Any', *, window: 'WindowSpec', group_cols: 'str \| Sequence[str]', measures: 'Sequence[Measure]') -> 'Any'` | Compute as-of (point-in-time) aggregations over half-open validity intervals. |
| `asof_join` | function | `(left: 'Any', right: 'Any', *, left_on: 'str', right_on: 'str', by: 'str \| Sequence[str] \| None', strategy: 'str', suffix: 'str') -> 'Any'` | Attach each *left* row's as-of match from *right*, keyed by *by*. |
| `CountAgg` | class | `(output_col: 'str') -> None` | Count rows per group and write the result to ``output_col``. |
| `cumulative_product` | function | `(data: 'Any', *, value: 'str', order_by: 'str', partition_by: 'str \| Sequence[str] \| None', out: 'str') -> 'Any'` | Append the ordered cumulative product of a value column. |
| `df_cast_date_to_datetime` | function | `(df: 'Any', column: 'str', *, output_column: 'str \| None') -> 'Any'` | Cast a Date column to Datetime, optionally writing to *output_column*. |
| `df_col_is_null` | function | `(column: 'Any') -> 'Any'` | Return a boolean mask where *column* values are null/NaT/None. |
| `df_concat` | function | `(frames: 'Iterable[Any]', *, how: 'str') -> 'Any'` | Concatenate a sequence of dispatched DataFrames. |
| `df_create` | function | `(data: 'dict[str, Any]') -> 'Any'` | Create a DataFrame from a dict of column name to list/array values. |
| `df_cross_join` | function | `(left: 'Any', right: 'Any') -> 'Any'` | Compute the cartesian product of two dispatched DataFrames. |
| `df_cross_sectional_agg` | function | `(df: 'Any', keys: 'list[str]', specs: 'Sequence[CrossSectionalSpec]') -> 'Any'` | Compute per-row cross-sectional statistics within groups, preserving all rows. |
| `df_filter` | function | `(df: 'Any', mask: 'Any') -> 'Any'` | Filter a dispatched DataFrame using a backend-native boolean mask. |
| `df_filter_date_eq` | function | `(df: 'Any', column: 'str', value: 'date') -> 'Any'` | Filter rows where a date *column* equals *value*. |
| `df_filter_isin` | function | `(df: 'Any', column: 'str', values: 'Iterable[Any]', *, negate: 'bool') -> 'Any'` | Filter rows where *column* value is (or, with ``negate``, is not) in *values*. |
| `df_get_column` | function | `(df: 'Any', name: 'str') -> 'Any'` | Extract a single column from a dispatched DataFrame. |
| `df_group_by_agg` | function | `(df: 'Any', keys: 'list[str]', agg_specs: 'Sequence[AggSpec]') -> 'Any'` | Group a dispatched DataFrame and apply aggregation specifications. |
| `df_height` | function | `(df: 'Any') -> 'int'` | Return the number of rows in a dispatched DataFrame. |
| `df_is_empty` | function | `(df: 'Any') -> 'bool'` | Return whether a dispatched DataFrame has zero rows. |
| `df_join` | function | `(left: 'Any', right: 'Any', *, on: 'str \| list[str]', how: 'str', coalesce: 'bool') -> 'Any'` | Join two dispatched DataFrames on shared key columns. |
| `df_partition_by` | function | `(df: 'Any', keys: 'list[str]', *, maintain_order: 'bool') -> 'list[Any]'` | Split a dispatched DataFrame into groups. |
| `df_rename` | function | `(df: 'Any', mapping: 'dict[str, str]') -> 'Any'` | Rename columns in a dispatched DataFrame. |
| `df_select` | function | `(df: 'Any', columns: 'list[str]') -> 'Any'` | Select a subset of columns from a dispatched DataFrame. |
| `df_sort` | function | `(df: 'Any', by: 'str \| list[str]', *, descending: 'bool') -> 'Any'` | Sort a dispatched DataFrame by one or more columns. |
| `df_unique` | function | `(df: 'Any', columns: 'list[str]') -> 'Any'` | Return rows with unique values in the specified columns. |
| `df_with_columns` | function | `(df: 'Any', new_columns: 'dict[str, Any]') -> 'Any'` | Attach one or more computed columns to a dispatched DataFrame. |
| `FirstAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Take the first value in ``source_col`` and write it to ``output_col``. |
| `LastAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Take the last value in ``source_col`` and write it to ``output_col``. |
| `PercentileRankAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Within-group percentile rank in (0, 1]; average-method ties, nulls rank null. |
| `RankAgg` | class | `(source_col: 'str', ascending: 'bool', output_col: 'str') -> None` | Within-group 1-based ordinal rank; ties broken by row order, nulls rank null. |
| `SumAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Sum values in ``source_col`` and write the result to ``output_col``. |
| `SumMeasure` | class | `(value_col: 'str', out: 'str') -> None` | Specify a simple additive measure for as-of aggregation. |
| `weighted_average` | function | `(data: 'Any', *, group_cols: 'str \| Sequence[str]', specs: 'SpecsLike') -> 'Any'` | Compute grouped weighted averages for one or more value columns. |
| `WeightedAverageSpec` | class | `(value_col: 'str', weight_cols: 'Sequence[str]', out: 'str', fill_value: 'float') -> None` | Specify one weighted-average output. |
| `WeightedAvgMeasure` | class | `(value_col: 'str', weight_cols: 'Sequence[str]', out: 'str', fill_value: 'float') -> None` | Specify a weighted-average measure: ``sum(value * weight) / sum(weight)``. |
| `WindowSpec` | class | `(position_date: 'PositionDateLike', start_col: 'str', end_col: 'str') -> None` | Define the interval window columns and the as-of date. |
| `ZScoreAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Within-group z-score (x - mean) / population std (ddof=0); 0.0 when std is 0. |

## `treasuryutils.compute.asof`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `asof_aggregate` | function | `(data: 'Any', *, window: 'WindowSpec', group_cols: 'str \| Sequence[str]', measures: 'Sequence[Measure]') -> 'Any'` | Compute as-of (point-in-time) aggregations over half-open validity intervals. |
| `asof_join` | function | `(left: 'Any', right: 'Any', *, left_on: 'str', right_on: 'str', by: 'str \| Sequence[str] \| None', strategy: 'str', suffix: 'str') -> 'Any'` | Attach each *left* row's as-of match from *right*, keyed by *by*. |
| `SumMeasure` | class | `(value_col: 'str', out: 'str') -> None` | Specify a simple additive measure for as-of aggregation. |
| `WeightedAvgMeasure` | class | `(value_col: 'str', weight_cols: 'Sequence[str]', out: 'str', fill_value: 'float') -> None` | Specify a weighted-average measure: ``sum(value * weight) / sum(weight)``. |
| `WindowSpec` | class | `(position_date: 'PositionDateLike', start_col: 'str', end_col: 'str') -> None` | Define the interval window columns and the as-of date. |

## `treasuryutils.compute.cumulative_product`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `cumulative_product` | function | `(data: 'Any', *, value: 'str', order_by: 'str', partition_by: 'str \| Sequence[str] \| None', out: 'str') -> 'Any'` | Append the ordered cumulative product of a value column. |

## `treasuryutils.compute.dataframe_ops`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CountAgg` | class | `(output_col: 'str') -> None` | Count rows per group and write the result to ``output_col``. |
| `df_cast_date_to_datetime` | function | `(df: 'Any', column: 'str', *, output_column: 'str \| None') -> 'Any'` | Cast a Date column to Datetime, optionally writing to *output_column*. |
| `df_col_is_null` | function | `(column: 'Any') -> 'Any'` | Return a boolean mask where *column* values are null/NaT/None. |
| `df_concat` | function | `(frames: 'Iterable[Any]', *, how: 'str') -> 'Any'` | Concatenate a sequence of dispatched DataFrames. |
| `df_create` | function | `(data: 'dict[str, Any]') -> 'Any'` | Create a DataFrame from a dict of column name to list/array values. |
| `df_cross_join` | function | `(left: 'Any', right: 'Any') -> 'Any'` | Compute the cartesian product of two dispatched DataFrames. |
| `df_cross_sectional_agg` | function | `(df: 'Any', keys: 'list[str]', specs: 'Sequence[CrossSectionalSpec]') -> 'Any'` | Compute per-row cross-sectional statistics within groups, preserving all rows. |
| `df_filter` | function | `(df: 'Any', mask: 'Any') -> 'Any'` | Filter a dispatched DataFrame using a backend-native boolean mask. |
| `df_filter_date_eq` | function | `(df: 'Any', column: 'str', value: 'date') -> 'Any'` | Filter rows where a date *column* equals *value*. |
| `df_filter_isin` | function | `(df: 'Any', column: 'str', values: 'Iterable[Any]', *, negate: 'bool') -> 'Any'` | Filter rows where *column* value is (or, with ``negate``, is not) in *values*. |
| `df_get_column` | function | `(df: 'Any', name: 'str') -> 'Any'` | Extract a single column from a dispatched DataFrame. |
| `df_group_by_agg` | function | `(df: 'Any', keys: 'list[str]', agg_specs: 'Sequence[AggSpec]') -> 'Any'` | Group a dispatched DataFrame and apply aggregation specifications. |
| `df_height` | function | `(df: 'Any') -> 'int'` | Return the number of rows in a dispatched DataFrame. |
| `df_is_empty` | function | `(df: 'Any') -> 'bool'` | Return whether a dispatched DataFrame has zero rows. |
| `df_join` | function | `(left: 'Any', right: 'Any', *, on: 'str \| list[str]', how: 'str', coalesce: 'bool') -> 'Any'` | Join two dispatched DataFrames on shared key columns. |
| `df_partition_by` | function | `(df: 'Any', keys: 'list[str]', *, maintain_order: 'bool') -> 'list[Any]'` | Split a dispatched DataFrame into groups. |
| `df_rename` | function | `(df: 'Any', mapping: 'dict[str, str]') -> 'Any'` | Rename columns in a dispatched DataFrame. |
| `df_select` | function | `(df: 'Any', columns: 'list[str]') -> 'Any'` | Select a subset of columns from a dispatched DataFrame. |
| `df_sort` | function | `(df: 'Any', by: 'str \| list[str]', *, descending: 'bool') -> 'Any'` | Sort a dispatched DataFrame by one or more columns. |
| `df_unique` | function | `(df: 'Any', columns: 'list[str]') -> 'Any'` | Return rows with unique values in the specified columns. |
| `df_with_columns` | function | `(df: 'Any', new_columns: 'dict[str, Any]') -> 'Any'` | Attach one or more computed columns to a dispatched DataFrame. |
| `FirstAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Take the first value in ``source_col`` and write it to ``output_col``. |
| `LastAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Take the last value in ``source_col`` and write it to ``output_col``. |
| `PercentileRankAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Within-group percentile rank in (0, 1]; average-method ties, nulls rank null. |
| `RankAgg` | class | `(source_col: 'str', ascending: 'bool', output_col: 'str') -> None` | Within-group 1-based ordinal rank; ties broken by row order, nulls rank null. |
| `SumAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Sum values in ``source_col`` and write the result to ``output_col``. |
| `ZScoreAgg` | class | `(source_col: 'str', output_col: 'str') -> None` | Within-group z-score (x - mean) / population std (ddof=0); 0.0 when std is 0. |

## `treasuryutils.compute.expr`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `col` | function | `(name: 'str') -> 'nw.Expr'` | Reference column *name* as a Narwhals expression. |
| `lit` | function | `(value: 'Any') -> 'nw.Expr'` | Wrap *value* as a Narwhals literal expression. |
| `when` | function | `(condition: 'nw.Expr') -> 'Any'` | Start a conditional expression on *condition*. |

## `treasuryutils.compute.interpolators`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `apply_curve` | function | `(df: Any, target_col: str, curve_data: Any, output_col: str, by: str \| list[str] \| None) -> Any` | Apply a static or bulk interpolation curve to a DataFrame. |
| `CubicSplineInterpolator` | class | `()` | Natural Cubic Spline on Rates. |
| `CubicSplineInterpolator.interpolate` | function | `(x_target: Any, x_nodes: Any, y_nodes: Any) -> Any` | Interpolate using a natural cubic spline with clamped extrapolation. |
| `FlatForwardInterpolator` | class | `()` | Interpolates linearly on Accumulated Log Return (Log Discount Factors). |
| `FlatForwardInterpolator.interpolate` | function | `(x_target: Any, x_nodes: Any, y_nodes: Any) -> Any` | Interpolate linearly on accumulated log-return space. |
| `get_interpolator` | function | `(method: treasuryutils.compute.interpolators.InterpolationMethod \| str) -> treasuryutils.compute.interpolators.InterpolatorStrategy` | Return the interpolation strategy for the given method. |
| `InterpolationMethod` | enum | `LINEAR='linear', FLAT_FORWARD='flat_forward', CUBIC_SPLINE='cubic_spline'` | Supported interpolation methods. |
| `InterpolatorStrategy` | class | `(*args, **kwargs)` | Protocol for defining how to interpolate between nodes. |
| `InterpolatorStrategy.interpolate` | function | `(x_target: Any, x_nodes: Any, y_nodes: Any) -> Any` | Interpolate rate values at the given target positions. |
| `LinearInterpolator` | class | `()` | Standard Linear Interpolation on Rates. |
| `LinearInterpolator.interpolate` | function | `(x_target: Any, x_nodes: Any, y_nodes: Any) -> Any` | Interpolate linearly on the rate axis. |

## `treasuryutils.compute.op_registry`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_op_dispatcher` | function | `(default_impl: 'Callable[..., Any]', *, context_name: 'str', context_where: 'str', polars_impl: 'Callable[..., Any] \| None', spark_impl: 'Callable[..., Any] \| None', polars_types: 'tuple[str, ...] \| None', spark_types: 'tuple[str, ...] \| None') -> 'Any'` | Build a singledispatch op-dispatcher with a DataFrame-rejection default. |
| `validate_ops_registry` | function | `(registry: 'Mapping[str, Any]', op_literal: 'Any', *, backend_name: 'str', allow_incomplete: 'bool') -> 'None'` | Validate that *registry* covers every value enumerated by *op_literal*. |

## `treasuryutils.compute.registry`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Backend` | enum | `NUMPY='numpy', PANDAS='pandas', POLARS='polars', SPARK='spark'` | The compute backends the registry can dispatch to. |
| `BackendNotSupportedError` | class | `(...)` | Raised when an operation has no implementation for an otherwise-installed backend. |
| `BackendSpec` | class | `(backend: treasuryutils.compute.registry.Backend, module: str, type_paths: tuple[tuple[str, str], ...]) -> None` | Immutable description of one compute backend. |
| `BackendSpec.available` | function | `() -> bool` | Return whether the backend's module can be imported. |
| `BackendSpec.types` | function | `() -> tuple[type, ...]` | Resolve and return the backend's container classes. |
| `BackendUnavailableError` | class | `(...)` | Raised when the backend for an input type is not installed. |
| `create_dispatcher` | function | `(default_impl: collections.abc.Callable[..., typing.Any]) -> Any` | Create a singledispatch function with the given default implementation. |
| `Dispatcher` | class | `(*args, **kwargs)` | Structural type for the singledispatch callables compute passes around. |
| `Dispatcher.register` | function | `(cls: type, impl: collections.abc.Callable[..., typing.Any], /) -> collections.abc.Callable[..., typing.Any]` | Attach ``impl`` as the implementation for ``cls``. |
| `narwhals_supported_backends` | function | `() -> frozenset[treasuryutils.compute.registry.Backend]` | Derive the frame backends a fully Narwhals-expressed op supports. |
| `register` | function | `(dispatcher: treasuryutils.compute.registry.Dispatcher, backend: treasuryutils.compute.registry.Backend, impl: collections.abc.Callable[..., typing.Any], *, types: tuple[str, ...] \| None) -> None` | Register a backend implementation on a dispatcher. |
| `register_polars` | function | `(dispatcher: treasuryutils.compute.registry.Dispatcher, impl_func: collections.abc.Callable[..., typing.Any], *, types: tuple[str, ...] \| None) -> None` | Safely register a Polars implementation to the dispatcher. |
| `register_spark` | function | `(dispatcher: treasuryutils.compute.registry.Dispatcher, impl_func: collections.abc.Callable[..., typing.Any], *, types: tuple[str, ...] \| None) -> None` | Safely register a Spark implementation to the dispatcher. |
| `resolve_backend` | function | `(*args: Any) -> treasuryutils.compute.registry.Backend` | Determine the winning backend from the runtime types of the arguments. |
| `supported_backends` | function | `(dispatcher: treasuryutils.compute.registry.Dispatcher) -> frozenset[treasuryutils.compute.registry.Backend]` | Derive which backends a dispatcher supports from its registry. |

## `treasuryutils.compute.umath`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `exp` | function | `(val: ~InputT) -> ~InputT` | Compute element-wise natural exponential. |
| `interp` | function | `(x: Any, xp: Union[numpy._typing._array_like._Buffer, numpy._typing._array_like._SupportsArray[numpy.dtype[Any]], numpy._typing._nested_sequence._NestedSequence[numpy._typing._array_like._SupportsArray[numpy.dtype[Any]]], complex, bytes, str, numpy._typing._nested_sequence._NestedSequence[complex \| bytes \| str]], fp: Union[numpy._typing._array_like._Buffer, numpy._typing._array_like._SupportsArray[numpy.dtype[Any]], numpy._typing._nested_sequence._NestedSequence[numpy._typing._array_like._SupportsArray[numpy.dtype[Any]]], complex, bytes, str, numpy._typing._nested_sequence._NestedSequence[complex \| bytes \| str]]) -> Any` | Perform linear interpolation, dispatched across NumPy and Polars. |
| `interpolate_bulk` | function | `(targets: Any, curves: Any, on: str, by: str \| list[str], curve_value_col: str, target_col: str \| None) -> Any` | Perform vectorized bulk interpolation across grouped curve data. |
| `is_column_like` | function | `(value: Any) -> bool` | Return True when *value* is a vectorized column rather than a scalar. |
| `log` | function | `(val: ~InputT) -> ~InputT` | Compute element-wise natural logarithm. |
| `power` | function | `(base: ~InputT, exponent: Any) -> ~InputT` | Compute element-wise exponentiation. |
| `safe_divide` | function | `(numerator: Any, denominator: Any, fill_value: float) -> Any` | Divide numerator by denominator, replacing zero/inf/NaN with *fill_value*. |
| `sqrt` | function | `(val: ~InputT) -> ~InputT` | Compute element-wise square root. |
| `where` | function | `(condition: Any, value_if_true: Any, value_if_false: Any) -> Any` | Select values element-wise based on a boolean condition. |

## `treasuryutils.compute.weighted_average`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `weighted_average` | function | `(data: 'Any', *, group_cols: 'str \| Sequence[str]', specs: 'SpecsLike') -> 'Any'` | Compute grouped weighted averages for one or more value columns. |
| `WeightedAverageSpec` | class | `(value_col: 'str', weight_cols: 'Sequence[str]', out: 'str', fill_value: 'float') -> None` | Specify one weighted-average output. |

## Type Aliases

Type-alias names used in the signatures above, resolved from the treasuryutils source (some are defined under `TYPE_CHECKING`).

| Alias | Definition |
| --- | --- |
| `AggSpec` | `SumAgg \| FirstAgg \| LastAgg \| CountAgg` |
| `CrossSectionalSpec` | `RankAgg \| PercentileRankAgg \| ZScoreAgg` |
| `DateLike` | `date \| datetime \| str` |
| `Measure` | `SumMeasure \| WeightedAvgMeasure` |
| `PositionDateLike` | `DateLike \| Sequence[DateLike] \| np.ndarray` |
| `SpecsLike` | `Sequence[WeightedAverageSpec] \| WeightsByValue` |
| `WeightsByValue` | `Mapping[str, str \| Sequence[str]]` |
