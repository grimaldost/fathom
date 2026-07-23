# CalendarTools API Reference (generated)

- treasuryutils_version: `1.8.0`
- generated_at_utc: `2026-07-10T16:08:46.035900+00:00`
- install_extras: `treasuryutils[calendartools]`

## Capability status

- Calendar ops are backend-DISPATCHED over numpy + polars via `dispatch_calendar_op` (calendartools/dispatch.py + primitives.py). This is NOT a polars-only surface.
- The vectorized expression currency is `pl.Expr` (polars), NOT `nw.Expr`: calendartools ops therefore do NOT compose inside `treasuryutils.compute.expr` (deferred, ADR-0107 §4).
- A `pl.DataFrame` / `pl.LazyFrame` input is rejected structurally; the Spark backend is deferred and raises a structured error (ADR-0039 / ADR-0043).

## `treasuryutils.calendartools`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `add_workdays` | function | `(date_input: 'DateInput', days: 'int \| Any', *, calendar: 'CalendarLike', non_workday_err: "Literal['coerce', 'strict']", **kwargs: 'Any') -> 'Any'` | Add *days* workdays to *date_input*. |
| `backward_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Roll non-workdays backward to the most recent workday. |
| `beginning_of_month` | function | `(date_input: 'DateInput') -> 'Any'` | Return the first day of the month for each date. |
| `Calendar` | class | `(data: 'pl.DataFrame', name: 'str') -> 'None'` | Validated, immutable container for business-calendar data. |
| `DayCountConvention` | enum | `ACT_360='act_360', ACT_365='act_365', THIRTY_360_BOND_BASIS='thirty_360_bond_basis', THIRTYE_360='thirtye_360', BUS_252='bus_252'` | Supported day-count conventions with flexible string parsing via ``_missing_``. |
| `end_of_month` | function | `(date_input: 'DateInput') -> 'Any'` | Return the last day of the month for each date. |
| `forward_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Roll non-workdays forward to the nearest following workday. |
| `get_calendar` | function | `(calendar_reference: 'str \| Calendar', *, allow_update: 'bool \| None', registry: 'CalendarRegistry \| None') -> 'Calendar'` | Resolve and return a validated ``Calendar`` instance. |
| `get_day` | function | `(date_input: 'DateInput') -> 'Any'` | Extract the day-of-month component (1--31) from date(s). |
| `get_month` | function | `(date_input: 'DateInput') -> 'Any'` | Extract the month component (1--12) from date(s). |
| `get_year` | function | `(date_input: 'DateInput') -> 'Any'` | Extract the year component from date(s). |
| `is_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Check whether date(s) fall on workdays. |
| `last_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Return the workday strictly before each date. |
| `net_calendardays` | function | `(start_date: 'DateInput', end_date: 'DateInput', **kwargs: 'Any') -> 'Any'` | Compute the number of calendar days between two dates. |
| `net_workdays` | function | `(start_date: 'DateInput', end_date: 'DateInput', *, calendar: 'CalendarLike', non_workday_err: "Literal['coerce', 'strict']") -> 'Any'` | Compute the number of workdays between two dates. |
| `next_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Return the workday strictly after each date. |
| `normalize_day_count` | function | `(value: 'str') -> 'str \| None'` | Normalize a raw day-count string to its canonical lowercase form. |
| `reset_default_registry` | function | `() -> 'None'` | Replace the module-level default registry with a fresh instance. |
| `roll_date` | function | `(date_input: 'DateInput', convention: 'RollingConvention', *, calendar: 'CalendarLike') -> 'Any'` | Apply a business-day rolling convention to *date_input*. |
| `RollingConvention` | callable | `(*args, **kwargs)` |  |
| `to_date` | function | `(date_input: 'DateInput') -> 'Any'` | Convert input to normalized ``datetime64[ns]`` representation. |
| `to_pydate` | function | `(value: 'DateScalar') -> 'date'` | Convert a scalar calendar result to a ``datetime.date``. |
| `wdate_range` | function | `(start_date: 'DateScalar', end_date: 'DateScalar', *, backend: "Literal['numpy', 'polars']", calendar: 'CalendarLike') -> 'Any'` | Generate workdays between *start_date* and *end_date* (inclusive). |
| `where` | function | `(condition: 'Any', x: 'Any', y: 'Any') -> 'Any'` | Return *x* where *condition* is true, *y* otherwise (element-wise). |
| `workday_num` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Return the cumulative workday index for date(s). |
| `year_fraction` | function | `(start: 'Any', end: 'Any', convention: 'Any', *, calendar: 'Any \| None', only: 'Sequence[DayCount] \| None', termination_date: 'Any \| None', **kw: 'Any') -> 'Any'` | Compute year fraction between *start* and *end* using a day-count convention. |

## `treasuryutils.calendartools.backends`

_No public callables discovered._

## `treasuryutils.calendartools.backends.numpy_backend`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `execute_op` | function | `(data_container: 'Any', calendar_table: 'Any', op: 'str', **kwargs: 'Any') -> 'Any'` | Execute a calendar operation. |
| `wdate_range` | function | `(start_date: 'Any', end_date: 'Any', calendar_table: 'Any') -> 'Any'` | Generate workdays in a date range (inclusive). |

## `treasuryutils.calendartools.backends.polars_backend`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `execute_op` | function | `(data_container: 'Any', calendar_table: 'Any', op: 'str', **kwargs: 'Any') -> 'Any'` | Execute a calendar operation. |
| `wdate_range` | function | `(start_date: 'Any', end_date: 'Any', calendar_table: 'Any') -> 'pl.Series'` | Generate workdays in a date range (inclusive). |

## `treasuryutils.calendartools.day_count`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DayCountConvention` | enum | `ACT_360='act_360', ACT_365='act_365', THIRTY_360_BOND_BASIS='thirty_360_bond_basis', THIRTYE_360='thirtye_360', BUS_252='bus_252'` | Supported day-count conventions with flexible string parsing via ``_missing_``. |
| `normalize_day_count` | function | `(value: 'str') -> 'str \| None'` | Normalize a raw day-count string to its canonical lowercase form. |
| `year_fraction` | function | `(start: 'Any', end: 'Any', convention: 'Any', *, calendar: 'Any \| None', only: 'Sequence[DayCount] \| None', termination_date: 'Any \| None', **kw: 'Any') -> 'Any'` | Compute year fraction between *start* and *end* using a day-count convention. |

## `treasuryutils.calendartools.day_count.calculators`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `year_fraction` | function | `(start: 'Any', end: 'Any', convention: 'Any', *, calendar: 'Any \| None', only: 'Sequence[DayCount] \| None', termination_date: 'Any \| None', **kw: 'Any') -> 'Any'` | Compute year fraction between *start* and *end* using a day-count convention. |

## `treasuryutils.calendartools.day_count.conventions`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DayCountConvention` | enum | `ACT_360='act_360', ACT_365='act_365', THIRTY_360_BOND_BASIS='thirty_360_bond_basis', THIRTYE_360='thirtye_360', BUS_252='bus_252'` | Supported day-count conventions with flexible string parsing via ``_missing_``. |
| `normalize_day_count` | function | `(value: 'str') -> 'str \| None'` | Normalize a raw day-count string to its canonical lowercase form. |

## `treasuryutils.calendartools.definitions`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Calendar` | class | `(data: 'pl.DataFrame', name: 'str') -> 'None'` | Validated, immutable container for business-calendar data. |
| `CalendarRegistry` | class | `(source: 'CalendarSource \| None') -> 'None'` | Registry that manages lazy-loading of Calendar objects. |
| `CalendarRegistry.get` | function | `(dataset_name: 'str', *, allow_update: 'bool \| None') -> 'Calendar'` | Get a validated calendar by dataset identifier. |
| `CalendarRegistry.refresh` | function | `(dataset_name: 'str \| None') -> 'None'` | Evict cached calendars to force a reload on next access. |
| `CalendarSchema` | class | `(*args, **kwargs) -> pandera.typing.common.DataFrameBase[typing.Self]` | Pandera schema defining the required columns for a valid business calendar. |
| `get_calendar` | function | `(calendar_reference: 'str \| Calendar', *, allow_update: 'bool \| None', registry: 'CalendarRegistry \| None') -> 'Calendar'` | Resolve and return a validated ``Calendar`` instance. |
| `get_calendar_numpy_bundle` | function | `(calendar_reference: 'str \| Calendar', *, allow_update: 'bool \| None') -> 'NumpyCalendarBundle'` | NumPy backend bundle accessor. |
| `get_calendar_polars_bundle` | function | `(calendar_reference: 'str \| Calendar', *, allow_update: 'bool \| None') -> 'PolarsCalendarBundle'` | Polars backend bundle accessor. |
| `NumpyCalendarBundle` | class | `(min_day_int: 'int', max_day_int: 'int', is_workday: 'np.ndarray', workday_num: 'np.ndarray', next_workday_day: 'np.ndarray', last_workday_day: 'np.ndarray', next_workday_num: 'np.ndarray', last_workday_num: 'np.ndarray', workday_num_to_day: 'np.ndarray') -> None` | Dense array-based lookup for O(1) calendar queries in the NumPy backend. |
| `PolarsCalendarBundle` | class | `(date: 'pl.Series', is_workday: 'pl.Series', next_workday: 'pl.Series', last_workday: 'pl.Series', workday_num: 'pl.Series', last_workday_num: 'pl.Series', next_workday_num: 'pl.Series', workday_num_workdays: 'pl.Series', date_workdays: 'pl.Series', non_workday_date: 'pl.Series', non_workday_next_workday: 'pl.Series', non_workday_last_workday: 'pl.Series', non_workday_next_workday_num: 'pl.Series', non_workday_last_workday_num: 'pl.Series') -> None` | Pre-extracted Polars Series for O(n) map-based calendar lookups. |
| `reset_default_registry` | function | `() -> 'None'` | Replace the module-level default registry with a fresh instance. |

## `treasuryutils.calendartools.dispatch`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CalendarOpHandler` | class | `(*args, **kwargs)` | Common callable interface for backend operation handlers. |
| `execute_range_op` | function | `(backend: Literal['numpy', 'polars'], start_date: Any, end_date: Any, calendar_table: Any) -> Any` | Route ``wdate_range`` calls to the named backend. |
| `validate_ops_registry` | function | `(registry: collections.abc.Mapping[str, treasuryutils.calendartools.dispatch.CalendarOpHandler], *, backend_name: str, allow_incomplete: bool) -> None` | Validate that *registry* covers every ``CalendarOp`` literal. |

## `treasuryutils.calendartools.functions`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `net_workdays` | function | `(start_date: 'DateInput', end_date: 'DateInput', *, calendar: 'CalendarLike', non_workday_err: "Literal['coerce', 'strict']") -> 'Any'` | Compute the number of workdays between two dates. |

## `treasuryutils.calendartools.primitives`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `add_workdays` | function | `(date_input: 'DateInput', days: 'int \| Any', *, calendar: 'CalendarLike', non_workday_err: "Literal['coerce', 'strict']", **kwargs: 'Any') -> 'Any'` | Add *days* workdays to *date_input*. |
| `backward_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Roll non-workdays backward to the most recent workday. |
| `beginning_of_month` | function | `(date_input: 'DateInput') -> 'Any'` | Return the first day of the month for each date. |
| `end_of_month` | function | `(date_input: 'DateInput') -> 'Any'` | Return the last day of the month for each date. |
| `forward_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Roll non-workdays forward to the nearest following workday. |
| `get_day` | function | `(date_input: 'DateInput') -> 'Any'` | Extract the day-of-month component (1--31) from date(s). |
| `get_month` | function | `(date_input: 'DateInput') -> 'Any'` | Extract the month component (1--12) from date(s). |
| `get_year` | function | `(date_input: 'DateInput') -> 'Any'` | Extract the year component from date(s). |
| `is_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Check whether date(s) fall on workdays. |
| `last_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Return the workday strictly before each date. |
| `net_calendardays` | function | `(start_date: 'DateInput', end_date: 'DateInput', **kwargs: 'Any') -> 'Any'` | Compute the number of calendar days between two dates. |
| `next_workday` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Return the workday strictly after each date. |
| `roll_date` | function | `(date_input: 'DateInput', convention: 'RollingConvention', *, calendar: 'CalendarLike') -> 'Any'` | Apply a business-day rolling convention to *date_input*. |
| `to_date` | function | `(date_input: 'DateInput') -> 'Any'` | Convert input to normalized ``datetime64[ns]`` representation. |
| `to_pydate` | function | `(value: 'DateScalar') -> 'date'` | Convert a scalar calendar result to a ``datetime.date``. |
| `wdate_range` | function | `(start_date: 'DateScalar', end_date: 'DateScalar', *, backend: "Literal['numpy', 'polars']", calendar: 'CalendarLike') -> 'Any'` | Generate workdays between *start_date* and *end_date* (inclusive). |
| `where` | function | `(condition: 'Any', x: 'Any', y: 'Any') -> 'Any'` | Return *x* where *condition* is true, *y* otherwise (element-wise). |
| `workday_num` | function | `(date_input: 'DateInput', *, calendar: 'CalendarLike') -> 'Any'` | Return the cumulative workday index for date(s). |

## Type Aliases

Type-alias names used in the signatures above, resolved from the treasuryutils source (some are defined under `TYPE_CHECKING`).

| Alias | Definition |
| --- | --- |
| `CalendarLike` | `Calendar \| str \| None \| PlDataFrame` |
| `DateExpr` | `PlExpr` |
| `DateInput` | `DateScalar \| DateSequence \| DateExpr \| PolarsDateSeries \| NumpyDateArray \| PandasDateSeries` |
| `DateScalar` | `date \| datetime \| str \| int \| float \| datetime64 \| Timestamp` |
| `DateSequence` | `list[Any] \| tuple[Any, ...]` |
| `NumpyDateArray` | `ndarray` |
| `PandasDateSeries` | `Series \| Index` |
| `PolarsDateSeries` | `PlSeries` |
