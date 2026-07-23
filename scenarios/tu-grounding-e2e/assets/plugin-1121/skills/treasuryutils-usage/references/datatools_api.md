# DataTools API Reference (generated)

- treasuryutils_version: `1.5.2.dev174+g64f80dc79`
- generated_at_utc: `2026-07-09T20:04:53.120267+00:00`
- install_extras: `treasuryutils[datatools]`

## `treasuryutils.config`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AuthenticatorConfig` | class | `(*, default_profile: str \| None, profiles: dict[str, typing.Annotated[treasuryutils.config.MsalAuthProfile \| treasuryutils.config.GoogleAuthProfile \| treasuryutils.config.BearerAuthProfile \| treasuryutils.config.DatabricksAuthProfile, FieldInfo(annotation=NoneType, required=True, discriminator='type')]]) -> None` | Authenticator subsystem configuration. |
| `CalendarToolsConfig` | class | `(*, allow_update_on_miss: bool, holidays_file_path: pathlib.Path, workdaysnum_file_path: pathlib.Path, calendardaynum_file_path: pathlib.Path, holidays_brazil_file_path: pathlib.Path, holidays_us_file_path: pathlib.Path, holidays_sifma_us_file_path: pathlib.Path) -> None` | CalendarTools subsystem configuration. |
| `DatatoolsConfig` | class | `(*, schema_mode: Literal['strict', 'permissive'], serve_mode: Literal['cache', 'direct', 'auto'], catalog_startup_mode: Literal['strict', 'permissive'], catalog_metadata_path: str, source_bindings_path: str, sink_metadata_path: str, catalog_allow_overwrite_noncanonical: bool, data_cache_dir: str \| None, databricks_default_warehouse_id: str \| None, cache_retention_days: int, cache_max_size_gb: float, cache_emergency_retention_days: int \| None, artifact_lock_timeout_s: int, dlt_naming_convention: str, yaml_substitution: treasuryutils.config.YamlSubstitutionConfig) -> None` | DataTools subsystem configuration. |
| `EnvMemoryConfig` | class | `(*, dir: str \| None, enabled: bool, max_rows: int) -> None` | Environment-facts memory (A5) configuration. |
| `FinancialToolsConfig` | class | `() -> None` | FinancialTools subsystem configuration (placeholder). |
| `ObservabilityConfig` | class | `(*, level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], format: Literal['json', 'console', 'auto'], rich_tracebacks: bool, redact_keys: set[str] \| None, logger_levels: dict[str, str] \| None) -> None` | Logging / observability configuration. |
| `ObservabilityConfig.validate_logger_levels` | method | `(v: 'dict[str, str] \| None') -> 'dict[str, str] \| None'` | Reject unknown level strings early at settings-load time. |
| `TreasuryBaseSettings` | class | `(*, app_name: str, environment: Literal['development', 'staging', 'production'], base_data_path: pathlib.Path, authenticator: treasuryutils.config.AuthenticatorConfig, calendartools: treasuryutils.config.CalendarToolsConfig, datatools: treasuryutils.config.DatatoolsConfig, envmemory: treasuryutils.config.EnvMemoryConfig, financialtools: treasuryutils.config.FinancialToolsConfig, observability: treasuryutils.config.ObservabilityConfig) -> None` | Corporate standard configuration. |
| `TreasuryBaseSettings.resolve_relative_paths` | function | `() -> 'Self'` | Recursively resolve relative ``Path`` fields against ``base_data_path``. |

## `treasuryutils.datatools`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BindingValidationResult` | class | `(dataset_name: 'str', ok: 'bool', connected: 'bool', error: 'str \| None', source_type: 'str \| None', source_detail: 'str \| None', error_type: 'str \| None', error_code: 'str \| None') -> None` | Outcome of validating one ``source_bindings.yaml`` entry. |
| `CacheCorruptionError` | class | `(dataset_name: 'str', message: 'str', *, code: 'str') -> 'None'` | Raised when cache data is corrupt or unreadable. |
| `CacheMissError` | class | `(dataset_name: 'str', cache_path: 'str \| None', *, code: 'str') -> 'None'` | Raised when requested data is not in the cache. |
| `config_status` | function | `(*, catalog: 'DataCatalog \| None') -> 'ConfigStatusReport'` | Build a structured doctor report for the source-binding configuration. |
| `ConfigStatusReport` | class | `(source_bindings_path: 'str', serve_mode: 'str', catalog_metadata_path: 'str', sink_metadata_path: 'str', datasets: 'list[DatasetStatus]', configured_auth_profiles: 'tuple[str, ...]') -> None` | Machine-readable doctor report for the source-binding configuration. |
| `ConfigurationError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when dataset configuration is invalid or missing. |
| `CoverageError` | class | `(dataset: 'str', *, requested: 'tuple[date, date]', covered: 'tuple[date, date] \| None', code: 'str') -> 'None'` | Raised when a cached table exists but does not span the requested range. |
| `DatasetClient` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None', update_on_start: 'bool', full_refresh_on_start: 'bool', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Primary manager for DuckDB-backed persistent storage. |
| `DatasetClient.ensure_fresh` | function | `(*, recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool') -> 'list[str]'` | Ensure this dataset (and optionally its dependencies) are fresh. |
| `DatasetClient.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool \| None', artifact_kind: 'ArtifactKind \| None', force_refresh: 'bool \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', persist_artifacts: 'bool \| None', use_existing_artifacts: 'bool \| None', covers: 'tuple[date, date] \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'pl.DataFrame'` | Get data as a Polars DataFrame. |
| `DatasetClient.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency. |
| `DatasetClient.get_last_updated` | function | `() -> 'str \| None'` | Get the last update timestamp for this dataset. |
| `DatasetClient.handle` | function | `(*, serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'DatasetHandle'` | Return a storage-agnostic dataset handle. |
| `DatasetClient.hard_reset` | function | `() -> 'None'` | Force a complete reset of the dataset pipeline state. |
| `DatasetClient.has_cache` | function | `() -> 'bool'` | Check if cached data exists for this dataset. |
| `DatasetClient.iter_batches` | function | `(*, batch_size: 'int', columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'Iterator[pl.DataFrame]'` | Yield data in batches from the dataset handle. |
| `DatasetClient.prefetch` | function | `() -> 'None'` | Run any pending startup update eagerly. |
| `DatasetClient.query` | function | `(sql: 'str') -> 'pl.DataFrame \| None'` | Execute ad-hoc SQL against a provider that supports SQL. |
| `DatasetClient.update` | function | `(*, full_refresh: 'FullRefreshScope', initial_value: 'str \| None', respect_target_policy: 'bool') -> 'None'` | Sync local persistent storage with the remote source. |
| `DatasetClient.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Execute update without acquiring the global lock. |
| `DatasetHandle` | class | `(dataset_name: 'str', provider: 'SourceProvider', spec: 'ReadSpec', postprocess: 'PostprocessFn \| None', declared_columns: 'frozenset[str] \| None') -> None` | A storage-agnostic handle for reading a dataset. |
| `DatasetHandle.collect` | function | `() -> 'pl.DataFrame'` | Materialize the current ReadSpec as a Polars DataFrame. |
| `DatasetHandle.iter_batches` | function | `(*, batch_size: 'int') -> 'Iterator[pl.DataFrame]'` | Yield data in batches as Polars DataFrames. |
| `DatasetHandle.scan` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', memory_map: 'bool \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'DatasetHandle'` | Return a new handle with an updated ReadSpec (immutable builder). |
| `DatasetManager` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None', update_on_start: 'bool', full_refresh_on_start: 'bool', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Primary manager for DuckDB-backed persistent storage. · alias of `DatasetClient` (import: `from treasuryutils.datatools import DatasetClient`) |
| `DatasetManager.ensure_fresh` | function | `(*, recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool') -> 'list[str]'` | Ensure this dataset (and optionally its dependencies) are fresh. |
| `DatasetManager.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool \| None', artifact_kind: 'ArtifactKind \| None', force_refresh: 'bool \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', persist_artifacts: 'bool \| None', use_existing_artifacts: 'bool \| None', covers: 'tuple[date, date] \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'pl.DataFrame'` | Get data as a Polars DataFrame. |
| `DatasetManager.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency. |
| `DatasetManager.get_last_updated` | function | `() -> 'str \| None'` | Get the last update timestamp for this dataset. |
| `DatasetManager.handle` | function | `(*, serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'DatasetHandle'` | Return a storage-agnostic dataset handle. |
| `DatasetManager.hard_reset` | function | `() -> 'None'` | Force a complete reset of the dataset pipeline state. |
| `DatasetManager.has_cache` | function | `() -> 'bool'` | Check if cached data exists for this dataset. |
| `DatasetManager.iter_batches` | function | `(*, batch_size: 'int', columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'Iterator[pl.DataFrame]'` | Yield data in batches from the dataset handle. |
| `DatasetManager.prefetch` | function | `() -> 'None'` | Run any pending startup update eagerly. |
| `DatasetManager.query` | function | `(sql: 'str') -> 'pl.DataFrame \| None'` | Execute ad-hoc SQL against a provider that supports SQL. |
| `DatasetManager.update` | function | `(*, full_refresh: 'FullRefreshScope', initial_value: 'str \| None', respect_target_policy: 'bool') -> 'None'` | Sync local persistent storage with the remote source. |
| `DatasetManager.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Execute update without acquiring the global lock. |
| `DatasetSinkManager` | class | `(sink_config: 'SinkConfig', *, auth_registry: 'Mapping[str, Any] \| None', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Manages target-aware sync from one dataset to one sink. · alias of `SinkExporter` (import: `from treasuryutils.datatools import SinkExporter`) |
| `DatasetSinkManager.run` | function | `() -> 'SinkResult'` | Execute one dataset → sink sync. |
| `DatasetStatus` | class | `(dataset_name: 'str', is_primitive: 'bool', has_binding: 'bool', proprietary_driver: 'bool', source_type: 'str', auth_profile: 'str \| None', auth_profile_configured: 'bool') -> None` | Per-dataset status line in a :class:`ConfigStatusReport`. |
| `DatasetValidationResult` | class | `(dataset_name: 'str', ok: 'bool', connected: 'bool', error_kind: 'str', error: 'str \| None', unresolved_dependencies: 'tuple[str, ...]', error_type: 'str \| None', error_code: 'str \| None') -> None` | Outcome of validating one candidate dataset config. |
| `DataToolsError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base exception for all DataTools errors. |
| `DependencyCycleError` | class | `(cycle_path: 'list[str]', *, code: 'str') -> 'None'` | Raised when a circular dependency is detected. |
| `DependencyError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when dependency resolution fails. |
| `DependencyNotFoundError` | class | `(dataset_name: 'str', missing_dependency: 'str', *, code: 'str') -> 'None'` | Raised when a declared dependency doesn't exist. |
| `LockTimeoutError` | class | `(resource: 'str', timeout_seconds: 'int', *, code: 'str') -> 'None'` | Raised when acquiring a lock times out. |
| `MultiInputPyBuilder` | class | `(manager_ref: 'DependencyReader \| None') -> 'None'` | Interface for named multi-input Python builders (spec §2, R3). |
| `MultiInputPyBuilder.run` | function | `(*, inputs: 'Mapping[str, DependencyReader]', start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame \| None'` | Execute the builder logic against named upstream inputs. |
| `MultiSinkError` | class | `(dataset_name: 'str', failures: 'list[SinkResult]', *, code: 'str') -> 'None'` | Raised when ``strict_mirrors=True`` and one or more fan-out mirrors failed. |
| `NestedUpdateError` | class | `(dataset_name: 'str', *, code: 'str') -> 'None'` | Raised when an update is triggered while another is already running in-process. |
| `ParquetUpsert` | class | `(dataset_identifier: 'str \| Path', sink_file_path: 'str \| Path', auth_registry: 'Mapping[str, Any] \| None', partition_by: 'list[str] \| None') -> 'None'` | Lightweight manager for serverless Parquet upserts. |
| `ParquetUpsert.run_upsert` | function | `(*, fan_out: 'bool', strict_mirrors: 'bool') -> 'UpsertResult'` | Execute an atomic upsert to the Parquet file, then fan out to mirrors. |
| `Pipeline` | class | `(name: 'str', *, base_path: 'Path \| str \| None', auth_registry: 'Mapping[str, Any] \| None') -> 'None'` | Multi-step ETL orchestration. |
| `Pipeline.add` | function | `(dataset_name: 'str', *, manager_type: "Literal['dataset', 'parquet']", sink_path: 'Path \| str \| None', partition_by: 'list[str] \| None', **manager_kwargs: 'Any') -> 'Pipeline'` | Register a dataset step. Returns ``self`` for chaining. |
| `Pipeline.execute` | function | `(*, full_refresh: 'bool', dry_run: 'bool') -> 'PipelineResult'` | Run the pipeline. |
| `Pipeline.status` | function | `() -> "dict[str, Literal['pending', 'unknown']]"` | Return dataset status. Currently all are ``pending`` or ``unknown``. |
| `PipelineExecutionError` | class | `(dataset_name: 'str', message: 'str', cause: 'Exception \| None', *, fix: 'str \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when a DLT pipeline execution fails. |
| `ReadSpec` | class | `(columns: 'tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'tuple[str, ...] \| None', limit: 'int \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> None` | A storage-agnostic read request. |
| `ReadSpec.is_full_scan` | function | `() -> 'bool'` | Return True when no columns, filter, ordering, limit, or params are applied. |
| `render_config_status` | function | `(report: 'ConfigStatusReport') -> 'str'` | Render a :class:`ConfigStatusReport` as human-readable text. |
| `scaffold_bindings` | function | `(*, path: 'str \| Path \| None', drivers: 'list[str] \| None', overwrite: 'bool', catalog: 'DataCatalog \| None') -> 'str'` | Build a ``source_bindings.yaml`` skeleton for every canonical primitive. |
| `scaffold_dataset` | function | `(*, dataset_name: 'str', source_type: 'str', path: 'str \| Path \| None', overwrite: 'bool') -> 'str'` | Build a commented ``DatasetConfig`` YAML skeleton for one source driver. |
| `SchemaValidationError` | class | `(dataset_name: 'str', message: 'str', failure_cases: 'list[dict[str, Any]] \| None', *, code: 'str') -> 'None'` | Raised when data fails schema validation. |
| `ServeMode` | callable | `(*args, **kwargs)` |  |
| `SinkConfig` | class | `(*, sink_name: str, dataset_name: str, type: str, auth_profile: str \| None, target: dict[str, typing.Any], write_disposition: Literal['merge', 'append', 'replace'], primary_key: str \| list[str] \| None, cursor_column: str \| None, lookback_days: typing.Annotated[int, Ge(ge=0)], config: dict[str, typing.Any], description: str \| None) -> None` | Concrete sync from one dataset to one external target. |
| `SinkExporter` | class | `(sink_config: 'SinkConfig', *, auth_registry: 'Mapping[str, Any] \| None', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Manages target-aware sync from one dataset to one sink. |
| `SinkExporter.run` | function | `() -> 'SinkResult'` | Execute one dataset → sink sync. |
| `SinkResult` | class | `(sink_name: 'str', dataset_name: 'str', status: "Literal['written', 'skipped', 'failed']", write_disposition: 'WriteDisposition', duration_seconds: 'float', rows_written: 'int \| None', rows_extracted: 'int \| None', cursor_min: 'Any \| None', cursor_max: 'Any \| None', error: 'str \| None', error_type: 'str \| None', error_code: 'str \| None') -> None` | Aggregate outcome of a single dataset→sink sync. |
| `SourceAccessError` | class | `(message: 'str', *, dataset_name: 'str', source_type: 'str', code: 'str') -> 'None'` | Raised when a consumer cannot access a dataset's configured source. |
| `SourceExtractionError` | class | `(source_type: 'str', message: 'str', cause: 'Exception \| None', *, code: 'str') -> 'None'` | Raised when data extraction from a source fails. |
| `StatelessParquetManager` | class | `(dataset_identifier: 'str \| Path', sink_file_path: 'str \| Path', auth_registry: 'Mapping[str, Any] \| None', partition_by: 'list[str] \| None') -> 'None'` | Lightweight manager for serverless Parquet upserts. · alias of `ParquetUpsert` (import: `from treasuryutils.datatools import ParquetUpsert`) |
| `StatelessParquetManager.run_upsert` | function | `(*, fan_out: 'bool', strict_mirrors: 'bool') -> 'UpsertResult'` | Execute an atomic upsert to the Parquet file, then fan out to mirrors. |
| `StreamingProvider` | class | `(*args, **kwargs)` | Provider capability: stream data as Arrow RecordBatches instead of a single DataFrame. |
| `StreamingProvider.collect_batches` | function | `(spec: 'ReadSpec', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` |  |
| `UpsertResult` | class | `(canonical: 'SinkResult', mirrors: 'tuple[SinkResult, ...]', watermark: 'WatermarkInfo \| None') -> None` | Outcome of one ``ParquetUpsert.run_upsert`` call. |
| `validate_bindings` | function | `(*, path: 'str \| Path \| None', connect: 'bool', sample_reader: 'Callable[[str], pl.DataFrame] \| None', catalog: 'DataCatalog \| None') -> 'list[BindingValidationResult]'` | Validate a ``source_bindings.yaml`` file, collecting per-dataset results. |
| `validate_dataset` | function | `(source: 'str \| dict[str, Any] \| Path', *, connect: 'bool', sample_reader: 'Callable[[str], pl.DataFrame] \| None', catalog: 'DataCatalog \| None') -> 'list[DatasetValidationResult]'` | Validate candidate dataset config(s), collecting per-dataset results. |
| `WatermarkInfo` | class | `(cursor_column: 'str \| None', cursor_max: 'Any \| None', rows_written: 'int \| None') -> None` | The high-watermark produced by one ``ParquetUpsert.run_upsert`` call. |

## `treasuryutils.datatools.cache`

_No public callables discovered._

## `treasuryutils.datatools.cache.contracts`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactStore` | class | `(*args, **kwargs)` | Optional materialization backend for the read-artifact tier (spec §3.2/§3.3). |
| `ArtifactStore.fingerprint_matches` | function | `(kind: 'str') -> 'bool'` | Return whether the persisted ``kind`` artifact matches the current config fingerprint. |
| `ArtifactStore.get_handle` | function | `(*, memory_map: 'bool') -> 'DatasetHandle'` |  |
| `ArtifactStore.materialize` | function | `(*, kind: 'ArtifactKind', spec: 'ReadSpec', sort_cols: 'str \| list[str] \| tuple[str, ...] \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', force_refresh: 'bool') -> 'DataArtifact'` |  |
| `BuildProvenanceStore` | class | `(*args, **kwargs)` | Cache build-provenance read/write surface (spec D4). |
| `BuildProvenanceStore.build_binding_fingerprint` | function | `(dataset_name: 'str') -> 'str \| None'` | Return the recorded build-binding fingerprint, or ``None`` when UNKNOWN. |
| `BuildProvenanceStore.record_build_binding_fingerprint` | function | `(dataset_name: 'str', fingerprint: 'str', *, table_name: 'str \| None') -> 'None'` | Persist the build-binding ``fingerprint`` for ``dataset_name``. |
| `CacheExporter` | class | `(*args, **kwargs)` | Export the working cache to read-artifact files (Tier-1 → Tier-2). |
| `CacheExporter.export_parquet_hive` | function | `(table_name: 'str', dest_dir: 'Path', *, partition_by: 'list[str] \| None', compression: 'str') -> 'None'` |  |
| `CacheExporter.export_sorted_ipc` | function | `(table_name: 'str', sort_columns: 'str \| list[str] \| tuple[str, ...]', dest_path: 'Path', *, rows_per_batch: 'int') -> 'None'` |  |
| `CacheReadAccess` | class | `(*args, **kwargs)` | Abstract cache bundle that serving's resolver depends on (spec §4.3). |
| `CacheReadAccess.exporter` | function | `() -> 'CacheExporter'` |  |
| `CacheReadAccess.reader` | function | `() -> 'CacheReader'` |  |
| `CacheReader` | class | `(*args, **kwargs)` | Read access to the working cache (Tier-1) — serving's cache provider. |
| `CacheReader.build_select_sql` | function | `(*, table_name: 'str', columns: 'Sequence[str] \| None', where_sql: 'str \| None', order_by: 'Sequence[str] \| None', limit: 'int \| None') -> 'str'` |  |
| `CacheReader.query` | function | `(sql: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame \| None'` |  |
| `CacheReader.query_batches` | function | `(sql: 'str', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches without full materialization. |
| `CacheReader.read_table` | function | `(table_name: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame'` |  |
| `CacheReader.table_exists` | function | `(table_name: 'str') -> 'bool'` |  |
| `CacheWriteTarget` | class | `(*args, **kwargs)` | Where ingest's DLT load writes the working cache (Tier-1) — spec §3.2. |
| `CoverageReader` | class | `(*args, **kwargs)` | Range-coverage read surface for refresh-on-read (design §4.1). |
| `CoverageReader.coverage` | function | `(table_name: 'str', update_key: 'str') -> 'tuple[dt.date, dt.date] \| None'` | Return ``(min, max)`` of the cached ``update_key`` as a date interval. |
| `LakehouseEngine` | class | `(*args, **kwargs)` | Backward-compat composition of the decomposed cache engine protocols. |
| `LakehouseEngine.build_select_sql` | function | `(*, table_name: 'str', columns: 'Sequence[str] \| None', where_sql: 'str \| None', order_by: 'Sequence[str] \| None', limit: 'int \| None') -> 'str'` |  |
| `LakehouseEngine.export_parquet_hive` | function | `(table_name: 'str', dest_dir: 'Path', *, partition_by: 'list[str] \| None', compression: 'str') -> 'None'` |  |
| `LakehouseEngine.export_sorted_ipc` | function | `(table_name: 'str', sort_columns: 'str \| list[str] \| tuple[str, ...]', dest_path: 'Path', *, rows_per_batch: 'int') -> 'None'` |  |
| `LakehouseEngine.query` | function | `(sql: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame \| None'` |  |
| `LakehouseEngine.query_batches` | function | `(sql: 'str', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches without full materialization. |
| `LakehouseEngine.quote_identifier` | function | `(name: 'str') -> 'str'` |  |
| `LakehouseEngine.read_table` | function | `(table_name: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame'` |  |
| `LakehouseEngine.table_exists` | function | `(table_name: 'str') -> 'bool'` |  |
| `LeafProbeReader` | class | `(*args, **kwargs)` | Append-only extent read surface for the leaf state-probe (design §2 D-RUN-B). |
| `LeafProbeReader.append_only_probe` | function | `(table_name: 'str', update_key: 'str') -> 'tuple[str, int] \| None'` | Return ``(stringified max(update_key), rowcount)`` of the cached table. |
| `participates_in_refresh_on_read` | function | `(config: 'DatasetConfig') -> 'bool'` | Static (config-only) half of the refresh-on-read participation guard. |
| `StateStore` | class | `(*args, **kwargs)` | State tracking for the local cache. |
| `StateStore.get_last_updated` | function | `(dataset_name: 'str') -> 'dt.datetime \| None'` | Return the last update timestamp, if present. |
| `StateStore.record_access` | function | `(dataset_name: 'str', *, table_name: 'str \| None') -> 'None'` | Record an access event (best-effort is allowed). |
| `StateStore.record_update` | function | `(dataset_name: 'str', *, table_name: 'str \| None') -> 'None'` | Record that a dataset has been updated. |
| `StateStore.remove_metadata` | function | `(dataset_name: 'str') -> 'None'` | Remove all metadata rows for a dataset. |
| `StateTokenReader` | class | `(*args, **kwargs)` | Recorded-source-tokens read surface for state-based refresh (design §2 D-RUN-D). |
| `StateTokenReader.source_tokens_at_build` | function | `(dataset_name: 'str') -> 'Mapping[str, str] \| None'` | Return the upstream source tokens recorded at the dataset's last build. |
| `StateTokenWriter` | class | `(*args, **kwargs)` | Recorded-source-tokens WRITE surface for state-based refresh (design §2 D-RUN-D). |
| `StateTokenWriter.record_update_with_source_tokens` | function | `(dataset_name: 'str', source_tokens: 'Mapping[str, str]', *, table_name: 'str \| None', build_binding_fingerprint: 'str \| None') -> 'None'` | Atomically record ``last_updated`` AND ``source_tokens_at_build`` (one upsert). |
| `to_iso` | function | `(value: 'dt.datetime \| None') -> 'str \| None'` | Convert a datetime to an ISO string, preserving timezone/naivety. |

## `treasuryutils.datatools.cache.duckdb`

_No public callables discovered._

## `treasuryutils.datatools.cache.duckdb.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DuckdbEngine` | class | `(db_path: 'Path') -> 'None'` | DuckDB query/export adapter for the local cache. |
| `DuckdbEngine.append_only_probe` | function | `(table_name: 'str', update_key: 'str') -> 'tuple[str, int] \| None'` | Return the cached leaf table's ``(stringified max(update_key), rowcount)``. |
| `DuckdbEngine.build_select_sql` | function | `(*, table_name: 'str', columns: 'Sequence[str] \| None', where_sql: 'str \| None', order_by: 'Sequence[str] \| None', limit: 'int \| None') -> 'str'` | Build a SELECT statement for DuckDB with defensive identifier quoting. |
| `DuckdbEngine.coverage` | function | `(table_name: 'str', update_key: 'str') -> 'tuple[datetime.date, datetime.date] \| None'` | Return the cached cursor's ``(min, max)`` as a date interval, or ``None``. |
| `DuckdbEngine.export_parquet_hive` | function | `(table_name: 'str', dest_dir: 'Path', *, partition_by: 'list[str] \| None', compression: 'str') -> 'None'` | Export a table to a hive-partitioned parquet dataset. |
| `DuckdbEngine.export_sorted_ipc` | function | `(table_name: 'str', sort_columns: 'str \| list[str] \| tuple[str, ...]', dest_path: 'Path', *, rows_per_batch: 'int') -> 'None'` | Export a sorted table to an Arrow IPC file (memory-map friendly). |
| `DuckdbEngine.query` | function | `(sql: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame \| None'` | Execute arbitrary SQL and return results as a Polars DataFrame, or None for DDL/DML. |
| `DuckdbEngine.query_batches` | function | `(sql: 'str', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches without full materialization. |
| `DuckdbEngine.quote_identifier` | function | `(name: 'str') -> 'str'` | Quote an identifier for DuckDB SQL. |
| `DuckdbEngine.read_sorted` | function | `(table_name: 'str', sort_columns: 'str \| list[str] \| tuple[str, ...]', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame'` | Read a table sorted by *sort_columns*, applying schema enforcement if provided. |
| `DuckdbEngine.read_table` | function | `(table_name: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame'` | Load an entire table into a Polars DataFrame, applying schema enforcement if provided. |
| `DuckdbEngine.table_exists` | function | `(table_name: 'str') -> 'bool'` | Return True if *table_name* exists in the ``data`` or ``main`` schema. |
| `DuckdbWriteTarget` | class | `(db_path: 'Path', table_name: 'str') -> None` | Concrete :class:`~treasuryutils.datatools.cache.contracts.CacheWriteTarget`. |

## `treasuryutils.datatools.cache.duckdb.internal_tables`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ensure_internal_tables` | function | `(conn: 'DuckDBPyConnection') -> 'None'` | Create internal metadata tables if they do not exist (with best-effort migrations). |
| `get_build_binding_fingerprint` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str') -> 'str \| None'` | Return the recorded ``build_binding_fingerprint``, or ``None`` when UNKNOWN. |
| `get_last_updated` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str') -> 'datetime.datetime \| None'` | Return last update timestamp for dataset, if present. |
| `get_source_tokens_at_build` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str') -> 'dict[str, str] \| None'` | Return the recorded ``source_tokens_at_build`` mapping, or ``None`` when UNKNOWN. |
| `get_stale_datasets` | function | `(conn: 'DuckDBPyConnection', cutoff: 'datetime.datetime') -> 'list[tuple[str, str \| None]]'` | Return datasets that have not been accessed since cutoff. |
| `log_access` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', cache_table_name: 'str \| None') -> 'None'` | Record access time for LRU maintenance. |
| `record_build_provenance` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', build_binding_fingerprint: 'str', cache_table_name: 'str \| None') -> 'None'` | Record the build-binding fingerprint for a dataset (cache provenance, spec D4). |
| `record_update` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', cache_table_name: 'str \| None', build_binding_fingerprint: 'str \| None') -> 'None'` | Record update time for staleness checks (and, optionally, build-provenance). |
| `record_update_with_source_tokens` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', source_tokens: 'Mapping[str, str]', cache_table_name: 'str \| None', build_binding_fingerprint: 'str \| None') -> 'None'` | Atomically record ``last_updated``, ``source_tokens_at_build`` (+ provenance). |
| `remove_dataset_metadata` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str') -> 'None'` | Remove internal metadata for dataset. |

## `treasuryutils.datatools.cache.duckdb.maintenance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DuckdbMaintenance` | class | `(db_path: 'Path') -> 'None'` | DuckDB file maintenance operations (prune/vacuum/drop). |
| `DuckdbMaintenance.drop_dataset` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', *, table_name: 'str \| None') -> 'bool'` | Drop the dataset table and associated metadata. |
| `DuckdbMaintenance.prune_by_age` | function | `(*, days_unused: 'int') -> 'list[str]'` | Drop datasets that have not been accessed in `days_unused`. |
| `DuckdbMaintenance.prune_to_size` | function | `(*, min_safe_days: 'int') -> 'list[str]'` | Drop least-recently-accessed datasets until safety buffer is reached. |
| `DuckdbMaintenance.vacuum` | function | `(*, checkpoint: 'bool') -> 'None'` | Run VACUUM (and optionally CHECKPOINT) to reclaim disk space. |

## `treasuryutils.datatools.cache.duckdb.state`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DuckdbStateStore` | class | `(db_path: 'Path') -> 'None'` | DuckDB-backed state store for cache access + update tracking. |
| `DuckdbStateStore.build_binding_fingerprint` | function | `(dataset_name: 'str') -> 'str \| None'` | Return the recorded build-binding fingerprint, or ``None`` when UNKNOWN. |
| `DuckdbStateStore.get_last_updated` | function | `(dataset_name: 'str') -> 'dt.datetime \| None'` | Return last updated timestamp, if present. |
| `DuckdbStateStore.record_access` | function | `(dataset_name: 'str', *, table_name: 'str \| None') -> 'None'` | Best-effort access logging for the ``_access_log`` metadata table. |
| `DuckdbStateStore.record_build_binding_fingerprint` | function | `(dataset_name: 'str', fingerprint: 'str', *, table_name: 'str \| None') -> 'None'` | Persist the build-binding ``fingerprint`` for ``dataset_name``. |
| `DuckdbStateStore.record_update` | function | `(dataset_name: 'str', *, table_name: 'str \| None') -> 'None'` | Persist a last_updated timestamp. |
| `DuckdbStateStore.record_update_with_source_tokens` | function | `(dataset_name: 'str', source_tokens: 'Mapping[str, str]', *, table_name: 'str \| None', build_binding_fingerprint: 'str \| None') -> 'None'` | Atomically persist ``last_updated`` AND ``source_tokens_at_build`` in one upsert. |
| `DuckdbStateStore.remove_metadata` | function | `(dataset_name: 'str') -> 'None'` | Remove all metadata rows for a dataset. |
| `DuckdbStateStore.source_tokens_at_build` | function | `(dataset_name: 'str') -> 'Mapping[str, str] \| None'` | Return the upstream source tokens recorded at the dataset's last build. |

## `treasuryutils.datatools.cache.local`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `create_default_cache` | function | `(root: 'Path') -> 'LocalCache'` | Create the default local cache instance for a given root. |
| `create_default_lakehouse` | function | `(root: 'Path') -> 'LocalCache'` | Create the default local cache instance for a given root. · alias of `create_default_cache` (import: `from treasuryutils.datatools.cache.local import create_default_cache`) |
| `LocalCache` | class | `(root: 'Path', db_path: 'Path') -> None` | Concrete local cache wiring (was ``LocalLakehouse`` — spec §1.6, ADR-0013). |
| `LocalCache.exporter` | function | `() -> 'CacheExporter'` | Hand serving the narrow export view (Tier-1 → Tier-2; spec §3.2/§3.4). |
| `LocalCache.reader` | function | `() -> 'CacheReader'` | Hand serving the narrow read view of the working cache (spec §3.2/§3.4). |
| `LocalCache.write_target` | function | `(table_name: 'str') -> 'CacheWriteTarget'` | Return the ``(db_path, table_name)`` write descriptor for ingest's DLT load. |
| `LocalLakehouse` | class | `(root: 'Path', db_path: 'Path') -> None` | Concrete local cache wiring (was ``LocalLakehouse`` — spec §1.6, ADR-0013). · alias of `LocalCache` (import: `from treasuryutils.datatools.cache.local import LocalCache`) |
| `LocalLakehouse.exporter` | function | `() -> 'CacheExporter'` | Hand serving the narrow export view (Tier-1 → Tier-2; spec §3.2/§3.4). |
| `LocalLakehouse.reader` | function | `() -> 'CacheReader'` | Hand serving the narrow read view of the working cache (spec §3.2/§3.4). |
| `LocalLakehouse.write_target` | function | `(table_name: 'str') -> 'CacheWriteTarget'` | Return the ``(db_path, table_name)`` write descriptor for ingest's DLT load. |

## `treasuryutils.datatools.cache.maintenance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `LakehouseMaintainer` | class | `(root: 'Path') -> None` | Coordinates cache maintenance across runtime artifacts and engine storage. |
| `LakehouseMaintainer.get_file_size_gb` | function | `() -> 'float'` | Returns total size of the cache directory in GB. |
| `LakehouseMaintainer.prune_all` | function | `(*, force_vacuum: 'bool', timeout_seconds: 'int') -> 'None'` | Run maintenance across runtime artifacts and the DuckDB engine file. |

## `treasuryutils.datatools.cache.paths`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `arrow_mmap_dir` | function | `(root: 'Path') -> 'Path'` | Return the Arrow IPC memory-map directory under *root*. |
| `arrow_mmap_path` | function | `(root: 'Path', dataset_name: 'str') -> 'Path'` | Return the Arrow IPC file path for *dataset_name* under *root*. |
| `artifact_fingerprint_path` | function | `(root: 'Path', dataset_name: 'str', kind: 'str') -> 'Path'` | Return the per-artifact sidecar fingerprint path for *dataset_name* and *kind*. |
| `artifact_lock_path` | function | `(root: 'Path', dataset_name: 'str', artifact_kind: 'str') -> 'Path'` | Return the per-artifact file-lock path for *dataset_name* and *artifact_kind*. |
| `artifacts_dir` | function | `(root: 'Path') -> 'Path'` | Return the artifacts sub-directory under *root*. |
| `duckdb_db_path` | function | `(root: 'Path') -> 'Path'` | Return the canonical DuckDB file path for a given cache *root*. |
| `duckdb_engine_dir` | function | `(root: 'Path') -> 'Path'` | Return the DuckDB engine sub-directory under *root*. |
| `duckdb_update_lock_path` | function | `(root: 'Path') -> 'Path'` | Return the DuckDB single-writer update lock file path. |
| `engines_dir` | function | `(root: 'Path') -> 'Path'` | Return the engines sub-directory under *root*. |
| `ensure_layout` | function | `(root: 'Path') -> 'None'` | Ensure the cache directory layout exists. |
| `locks_dir` | function | `(root: 'Path') -> 'Path'` | Return the file-lock directory under *root*. |
| `parquet_hive_dir` | function | `(root: 'Path') -> 'Path'` | Return the hive-partitioned Parquet root directory under *root*. |
| `parquet_hive_path` | function | `(root: 'Path', dataset_name: 'str') -> 'Path'` | Return the hive-partitioned Parquet directory for *dataset_name* under *root*. |
| `resolve_root` | function | `(provided_path: 'str \| Path \| None') -> 'Path'` | Resolve the cache root directory. |

## `treasuryutils.datatools.cache.tiers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArrowMmapArtifact` | class | `(dataset_name: 'str', path: 'Path', kind: 'str') -> None` | Continuous Arrow IPC file suitable for memory-mapped reads. |
| `ArrowMmapArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Read the Arrow IPC file into a Polars DataFrame. |
| `InMemoryArtifact` | class | `(dataset_name: 'str', df: 'pl.DataFrame', postprocess: 'PostprocessFn \| None', kind: 'str', location: 'Path \| None') -> None` | In-memory artifact wrapping a DataFrame. |
| `InMemoryArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Apply postprocess (if any) and return the in-memory DataFrame. |
| `ParquetHiveArtifact` | class | `(dataset_name: 'str', path: 'Path', postprocess: 'PostprocessFn \| None', kind: 'str') -> None` | Hive-partitioned parquet dataset directory. |
| `ParquetHiveArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Collect a full scan of the parquet dataset. |
| `ParquetHiveArtifact.collect_spec` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Collect a ReadSpec using Polars lazy operations / SQL when possible. |
| `UniversalArtifactStore` | class | `(dataset_name: 'str', provider: 'SourceProvider', root: 'Path', postprocess: 'PostprocessFn \| None', lock_backend: 'LockBackend \| None', artifact_lock_timeout_s: 'int', config_fingerprint: 'str \| None', declared_columns: 'frozenset[str] \| None') -> None` | Materialize Arrow IPC and hive-parquet artifacts for a dataset. |
| `UniversalArtifactStore.fingerprint_matches` | function | `(kind: 'str') -> 'bool'` | Return True when the stored sidecar fingerprint matches ``self.config_fingerprint``. |
| `UniversalArtifactStore.get_handle` | function | `(*, memory_map: 'bool') -> 'DatasetHandle'` | Return a DatasetHandle backed by this store's provider and postprocess. |
| `UniversalArtifactStore.materialize` | function | `(*, kind: 'ArtifactKind', spec: 'ReadSpec', sort_cols: 'str \| list[str] \| tuple[str, ...] \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', force_refresh: 'bool') -> 'DataArtifact'` | Materialize a dataset artifact of the requested kind, using a lock to prevent races. |

## `treasuryutils.datatools.cache.tiers.artifacts`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArrowMmapArtifact` | class | `(dataset_name: 'str', path: 'Path', kind: 'str') -> None` | Continuous Arrow IPC file suitable for memory-mapped reads. |
| `ArrowMmapArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Read the Arrow IPC file into a Polars DataFrame. |
| `InMemoryArtifact` | class | `(dataset_name: 'str', df: 'pl.DataFrame', postprocess: 'PostprocessFn \| None', kind: 'str', location: 'Path \| None') -> None` | In-memory artifact wrapping a DataFrame. |
| `InMemoryArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Apply postprocess (if any) and return the in-memory DataFrame. |
| `ParquetHiveArtifact` | class | `(dataset_name: 'str', path: 'Path', postprocess: 'PostprocessFn \| None', kind: 'str') -> None` | Hive-partitioned parquet dataset directory. |
| `ParquetHiveArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Collect a full scan of the parquet dataset. |
| `ParquetHiveArtifact.collect_spec` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Collect a ReadSpec using Polars lazy operations / SQL when possible. |

## `treasuryutils.datatools.cache.tiers.maintenance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `delete_dataset_artifacts` | function | `(*, root: 'Path', dataset_name: 'str') -> 'None'` | Best-effort removal of all artifacts for a dataset. |
| `prune_runtime_artifacts` | function | `(*, root: 'Path', days_unused: 'int') -> 'None'` | Delete runtime artifacts that have not been accessed in `days_unused` days. |

## `treasuryutils.datatools.cache.tiers.store`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `UniversalArtifactStore` | class | `(dataset_name: 'str', provider: 'SourceProvider', root: 'Path', postprocess: 'PostprocessFn \| None', lock_backend: 'LockBackend \| None', artifact_lock_timeout_s: 'int', config_fingerprint: 'str \| None', declared_columns: 'frozenset[str] \| None') -> None` | Materialize Arrow IPC and hive-parquet artifacts for a dataset. |
| `UniversalArtifactStore.fingerprint_matches` | function | `(kind: 'str') -> 'bool'` | Return True when the stored sidecar fingerprint matches ``self.config_fingerprint``. |
| `UniversalArtifactStore.get_handle` | function | `(*, memory_map: 'bool') -> 'DatasetHandle'` | Return a DatasetHandle backed by this store's provider and postprocess. |
| `UniversalArtifactStore.materialize` | function | `(*, kind: 'ArtifactKind', spec: 'ReadSpec', sort_cols: 'str \| list[str] \| tuple[str, ...] \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', force_refresh: 'bool') -> 'DataArtifact'` | Materialize a dataset artifact of the requested kind, using a lock to prevent races. |

## `treasuryutils.datatools.catalog`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactKind` | callable | `(*args, **kwargs)` |  |
| `config_fingerprint` | function | `(config: 'DatasetConfig', schema_mode: 'SchemaMode', binding: 'SourceBinding \| None') -> 'str'` | Return a short, stable hex hash for (config, schema_mode, binding). |
| `DataCatalog` | class | `() -> 'None'` | Central registry for all dataset definitions. |
| `DataCatalog.bind_source` | function | `(dataset_name: 'str', *, source: '_SourceArg \| None', provider: '_ProviderArg \| None', auth_profile: 'str \| None') -> 'None'` | Programmatically rebind a primitive dataset's physical source. |
| `DataCatalog.get_config` | function | `(dataset_name: 'str \| None') -> 'dict[str, Any] \| dict[str, dict[str, Any]]'` | Retrieve the configuration for a specific dataset or the entire catalog. |
| `DataCatalog.get_sink` | function | `(sink_name: 'str') -> 'SinkConfig'` | Return the SinkConfig for a registered sink_name. |
| `DataCatalog.list_sinks` | function | `() -> 'list[str]'` | Return all loaded sink names, sorted alphabetically. |
| `DataCatalog.load_from_file` | function | `(path: 'str \| Path \| list[str \| Path] \| tuple[str \| Path, ...]', *, _canonical: 'bool') -> 'str \| list[str]'` | Load and register dataset definitions from metadata paths. |
| `DataCatalog.register` | function | `(config: 'dict[str, Any] \| DatasetConfig', source: 'str', *, _canonical: 'bool') -> 'None'` | Dynamically register a dataset configuration. |
| `DataCatalog.register_sink` | function | `(config: 'SinkConfig \| dict[str, Any]') -> 'None'` | Programmatically register a sink configuration into the catalog. |
| `DataCatalog.sinks_for_dataset` | function | `(dataset_name: 'str') -> 'list[SinkConfig]'` | Return all sinks whose dataset_name matches. |
| `DatasetConfig` | class | `(*, dataset_name: str, cache_table_name: str \| None, description: str \| None, depends_on: list[str], refresh_policy: treasuryutils.datatools.config.models.RefreshPolicy \| None, write_disposition: Literal['merge', 'replace', 'append'], primary_key: str \| list[str] \| None, update_key: str \| None, columns: dict[str, typing.Any], schema_mode: Optional[Literal['strict', 'permissive']], serve_mode: Optional[Literal['cache', 'direct', 'auto']], serving: treasuryutils.datatools.config.models.ServingConfig \| None, provider: treasuryutils.datatools.config.models.ProviderConfig \| None, source: treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig], contract_version: str, migrations: dict[str, typing.Any] \| None, materialize: Literal['materialized', 'virtual'], annex: treasuryutils.datatools.config.models.AnnexModel \| None) -> None` | Strict data contract for a dataset (validated from YAML). |
| `ProviderConfig` | class | `(*, type: Literal['auto', 'lakehouse', 'file', 'bigquery', 'databricks', 'python', 'dataset'], query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any]) -> None` | Serving provider configuration (read path only). |
| `RefreshMode` | callable | `(*args, **kwargs)` |  |
| `RefreshPolicy` | class | `(*, mode: Literal['if_missing', 'if_stale', 'always', 'never'], max_age_seconds: typing.Annotated[int \| None, Ge(ge=0)], stale_if_dependency_newer: bool) -> None` | Controls when a dataset should be refreshed automatically. |
| `resolve_schema_mode` | function | `(meta: 'dict[str, Any]') -> 'SchemaMode'` | Resolve the effective schema mode for a dataset. |
| `SchemaMode` | callable | `(*args, **kwargs)` |  |
| `ServingConfig` | class | `(*, artifact_kind: Literal['auto', 'in_memory', 'arrow_mmap', 'parquet_hive'], memory_map: bool, force_refresh: bool, persist_artifacts: bool \| None, use_existing_artifacts: bool \| None, partition_by: list[str]) -> None` | Optional serving materialization configuration. |
| `SinkConfig` | class | `(*, sink_name: str, dataset_name: str, type: str, auth_profile: str \| None, target: dict[str, typing.Any], write_disposition: Literal['merge', 'append', 'replace'], primary_key: str \| list[str] \| None, cursor_column: str \| None, lookback_days: typing.Annotated[int, Ge(ge=0)], config: dict[str, typing.Any], description: str \| None) -> None` | Concrete sync from one dataset to one external target. |
| `SourceConfig` | class | `(*, type: str, query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any], kind: str \| None, requires: list[str], inputs: dict[str, str] \| None, refresh_on_build: bool) -> None` | Defines the extraction strategy for a dataset. |
| `SourceConfig.validate_driver_config` | function | `() -> 'SourceConfig'` | Delegate driver-specific validation to the registered validator. |
| `SourceType` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.catalog.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactKind` | callable | `(*args, **kwargs)` |  |
| `DatasetConfig` | class | `(*, dataset_name: str, cache_table_name: str \| None, description: str \| None, depends_on: list[str], refresh_policy: treasuryutils.datatools.config.models.RefreshPolicy \| None, write_disposition: Literal['merge', 'replace', 'append'], primary_key: str \| list[str] \| None, update_key: str \| None, columns: dict[str, typing.Any], schema_mode: Optional[Literal['strict', 'permissive']], serve_mode: Optional[Literal['cache', 'direct', 'auto']], serving: treasuryutils.datatools.config.models.ServingConfig \| None, provider: treasuryutils.datatools.config.models.ProviderConfig \| None, source: treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig], contract_version: str, migrations: dict[str, typing.Any] \| None, materialize: Literal['materialized', 'virtual'], annex: treasuryutils.datatools.config.models.AnnexModel \| None) -> None` | Strict data contract for a dataset (validated from YAML). |
| `ProviderConfig` | class | `(*, type: Literal['auto', 'lakehouse', 'file', 'bigquery', 'databricks', 'python', 'dataset'], query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any]) -> None` | Serving provider configuration (read path only). |
| `RefreshMode` | callable | `(*args, **kwargs)` |  |
| `RefreshPolicy` | class | `(*, mode: Literal['if_missing', 'if_stale', 'always', 'never'], max_age_seconds: typing.Annotated[int \| None, Ge(ge=0)], stale_if_dependency_newer: bool) -> None` | Controls when a dataset should be refreshed automatically. |
| `ServingConfig` | class | `(*, artifact_kind: Literal['auto', 'in_memory', 'arrow_mmap', 'parquet_hive'], memory_map: bool, force_refresh: bool, persist_artifacts: bool \| None, use_existing_artifacts: bool \| None, partition_by: list[str]) -> None` | Optional serving materialization configuration. |
| `SinkConfig` | class | `(*, sink_name: str, dataset_name: str, type: str, auth_profile: str \| None, target: dict[str, typing.Any], write_disposition: Literal['merge', 'append', 'replace'], primary_key: str \| list[str] \| None, cursor_column: str \| None, lookback_days: typing.Annotated[int, Ge(ge=0)], config: dict[str, typing.Any], description: str \| None) -> None` | Concrete sync from one dataset to one external target. |
| `SourceBinding` | class | `(*, source: treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig] \| None, provider: treasuryutils.datatools.config.models.ProviderConfig \| None, auth_profile: str \| None) -> None` | Consumer override of a primitive dataset's physical source binding. |
| `SourceBindingsFile` | class | `(*, version: int, bindings: dict[str, treasuryutils.datatools.config.models.SourceBinding]) -> None` | A ``source_bindings.yaml`` document: ``dataset_name`` → :class:`SourceBinding`. |
| `SourceConfig` | class | `(*, type: str, query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any], kind: str \| None, requires: list[str], inputs: dict[str, str] \| None, refresh_on_build: bool) -> None` | Defines the extraction strategy for a dataset. |
| `SourceConfig.validate_driver_config` | function | `() -> 'SourceConfig'` | Delegate driver-specific validation to the registered validator. |
| `SourceType` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.catalog.registry`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DataCatalog` | class | `() -> 'None'` | Central registry for all dataset definitions. |
| `DataCatalog.bind_source` | function | `(dataset_name: 'str', *, source: '_SourceArg \| None', provider: '_ProviderArg \| None', auth_profile: 'str \| None') -> 'None'` | Programmatically rebind a primitive dataset's physical source. |
| `DataCatalog.get_config` | function | `(dataset_name: 'str \| None') -> 'dict[str, Any] \| dict[str, dict[str, Any]]'` | Retrieve the configuration for a specific dataset or the entire catalog. |
| `DataCatalog.get_sink` | function | `(sink_name: 'str') -> 'SinkConfig'` | Return the SinkConfig for a registered sink_name. |
| `DataCatalog.list_sinks` | function | `() -> 'list[str]'` | Return all loaded sink names, sorted alphabetically. |
| `DataCatalog.load_from_file` | function | `(path: 'str \| Path \| list[str \| Path] \| tuple[str \| Path, ...]', *, _canonical: 'bool') -> 'str \| list[str]'` | Load and register dataset definitions from metadata paths. |
| `DataCatalog.register` | function | `(config: 'dict[str, Any] \| DatasetConfig', source: 'str', *, _canonical: 'bool') -> 'None'` | Dynamically register a dataset configuration. |
| `DataCatalog.register_sink` | function | `(config: 'SinkConfig \| dict[str, Any]') -> 'None'` | Programmatically register a sink configuration into the catalog. |
| `DataCatalog.sinks_for_dataset` | function | `(dataset_name: 'str') -> 'list[SinkConfig]'` | Return all sinks whose dataset_name matches. |

## `treasuryutils.datatools.catalog.validation`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `resolve_schema_mode` | function | `(meta: 'dict[str, Any]') -> 'SchemaMode'` | Resolve the effective schema mode for a dataset. |
| `SchemaMode` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.config`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactKind` | callable | `(*args, **kwargs)` |  |
| `config_fingerprint` | function | `(config: 'DatasetConfig', schema_mode: 'SchemaMode', binding: 'SourceBinding \| None') -> 'str'` | Return a short, stable hex hash for (config, schema_mode, binding). |
| `DataCatalog` | class | `() -> 'None'` | Central registry for all dataset definitions. |
| `DataCatalog.bind_source` | function | `(dataset_name: 'str', *, source: '_SourceArg \| None', provider: '_ProviderArg \| None', auth_profile: 'str \| None') -> 'None'` | Programmatically rebind a primitive dataset's physical source. |
| `DataCatalog.get_config` | function | `(dataset_name: 'str \| None') -> 'dict[str, Any] \| dict[str, dict[str, Any]]'` | Retrieve the configuration for a specific dataset or the entire catalog. |
| `DataCatalog.get_sink` | function | `(sink_name: 'str') -> 'SinkConfig'` | Return the SinkConfig for a registered sink_name. |
| `DataCatalog.list_sinks` | function | `() -> 'list[str]'` | Return all loaded sink names, sorted alphabetically. |
| `DataCatalog.load_from_file` | function | `(path: 'str \| Path \| list[str \| Path] \| tuple[str \| Path, ...]', *, _canonical: 'bool') -> 'str \| list[str]'` | Load and register dataset definitions from metadata paths. |
| `DataCatalog.register` | function | `(config: 'dict[str, Any] \| DatasetConfig', source: 'str', *, _canonical: 'bool') -> 'None'` | Dynamically register a dataset configuration. |
| `DataCatalog.register_sink` | function | `(config: 'SinkConfig \| dict[str, Any]') -> 'None'` | Programmatically register a sink configuration into the catalog. |
| `DataCatalog.sinks_for_dataset` | function | `(dataset_name: 'str') -> 'list[SinkConfig]'` | Return all sinks whose dataset_name matches. |
| `DatasetConfig` | class | `(*, dataset_name: str, cache_table_name: str \| None, description: str \| None, depends_on: list[str], refresh_policy: treasuryutils.datatools.config.models.RefreshPolicy \| None, write_disposition: Literal['merge', 'replace', 'append'], primary_key: str \| list[str] \| None, update_key: str \| None, columns: dict[str, typing.Any], schema_mode: Optional[Literal['strict', 'permissive']], serve_mode: Optional[Literal['cache', 'direct', 'auto']], serving: treasuryutils.datatools.config.models.ServingConfig \| None, provider: treasuryutils.datatools.config.models.ProviderConfig \| None, source: treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig], contract_version: str, migrations: dict[str, typing.Any] \| None, materialize: Literal['materialized', 'virtual'], annex: treasuryutils.datatools.config.models.AnnexModel \| None) -> None` | Strict data contract for a dataset (validated from YAML). |
| `ProviderConfig` | class | `(*, type: Literal['auto', 'lakehouse', 'file', 'bigquery', 'databricks', 'python', 'dataset'], query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any]) -> None` | Serving provider configuration (read path only). |
| `RefreshMode` | callable | `(*args, **kwargs)` |  |
| `RefreshPolicy` | class | `(*, mode: Literal['if_missing', 'if_stale', 'always', 'never'], max_age_seconds: typing.Annotated[int \| None, Ge(ge=0)], stale_if_dependency_newer: bool) -> None` | Controls when a dataset should be refreshed automatically. |
| `resolve_schema_mode` | function | `(meta: 'dict[str, Any]') -> 'SchemaMode'` | Resolve the effective schema mode for a dataset. |
| `SchemaMode` | callable | `(*args, **kwargs)` |  |
| `ServingConfig` | class | `(*, artifact_kind: Literal['auto', 'in_memory', 'arrow_mmap', 'parquet_hive'], memory_map: bool, force_refresh: bool, persist_artifacts: bool \| None, use_existing_artifacts: bool \| None, partition_by: list[str]) -> None` | Optional serving materialization configuration. |
| `SinkConfig` | class | `(*, sink_name: str, dataset_name: str, type: str, auth_profile: str \| None, target: dict[str, typing.Any], write_disposition: Literal['merge', 'append', 'replace'], primary_key: str \| list[str] \| None, cursor_column: str \| None, lookback_days: typing.Annotated[int, Ge(ge=0)], config: dict[str, typing.Any], description: str \| None) -> None` | Concrete sync from one dataset to one external target. |
| `SourceConfig` | class | `(*, type: str, query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any], kind: str \| None, requires: list[str], inputs: dict[str, str] \| None, refresh_on_build: bool) -> None` | Defines the extraction strategy for a dataset. |
| `SourceConfig.validate_driver_config` | function | `() -> 'SourceConfig'` | Delegate driver-specific validation to the registered validator. |
| `SourceType` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.config.models`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AnnexModel` | class | `(*, description: str \| None, owner: str \| None, domain: str \| None, sla: str \| None, lineage: dict[str, typing.Any] \| None) -> None` | Typed annex of non-contract metadata (spec D-W1-C / D-W1-E / D-W1-G). |
| `ColumnSpec` | class | `(*, data_type: str, nullable: bool, description: str \| None, tags: list[str], checks: list[str]) -> None` | Typed contract for a single column definition (spec D-W1-A). |
| `DatasetConfig` | class | `(*, dataset_name: str, cache_table_name: str \| None, description: str \| None, depends_on: list[str], refresh_policy: treasuryutils.datatools.config.models.RefreshPolicy \| None, write_disposition: Literal['merge', 'replace', 'append'], primary_key: str \| list[str] \| None, update_key: str \| None, columns: dict[str, typing.Any], schema_mode: Optional[Literal['strict', 'permissive']], serve_mode: Optional[Literal['cache', 'direct', 'auto']], serving: treasuryutils.datatools.config.models.ServingConfig \| None, provider: treasuryutils.datatools.config.models.ProviderConfig \| None, source: treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig], contract_version: str, migrations: dict[str, typing.Any] \| None, materialize: Literal['materialized', 'virtual'], annex: treasuryutils.datatools.config.models.AnnexModel \| None) -> None` | Strict data contract for a dataset (validated from YAML). |
| `ProviderConfig` | class | `(*, type: Literal['auto', 'lakehouse', 'file', 'bigquery', 'databricks', 'python', 'dataset'], query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any]) -> None` | Serving provider configuration (read path only). |
| `RefreshPolicy` | class | `(*, mode: Literal['if_missing', 'if_stale', 'always', 'never'], max_age_seconds: typing.Annotated[int \| None, Ge(ge=0)], stale_if_dependency_newer: bool) -> None` | Controls when a dataset should be refreshed automatically. |
| `ServingConfig` | class | `(*, artifact_kind: Literal['auto', 'in_memory', 'arrow_mmap', 'parquet_hive'], memory_map: bool, force_refresh: bool, persist_artifacts: bool \| None, use_existing_artifacts: bool \| None, partition_by: list[str]) -> None` | Optional serving materialization configuration. |
| `SinkConfig` | class | `(*, sink_name: str, dataset_name: str, type: str, auth_profile: str \| None, target: dict[str, typing.Any], write_disposition: Literal['merge', 'append', 'replace'], primary_key: str \| list[str] \| None, cursor_column: str \| None, lookback_days: typing.Annotated[int, Ge(ge=0)], config: dict[str, typing.Any], description: str \| None) -> None` | Concrete sync from one dataset to one external target. |
| `SourceBinding` | class | `(*, source: treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig] \| None, provider: treasuryutils.datatools.config.models.ProviderConfig \| None, auth_profile: str \| None) -> None` | Consumer override of a primitive dataset's physical source binding. |
| `SourceBindingsFile` | class | `(*, version: int, bindings: dict[str, treasuryutils.datatools.config.models.SourceBinding]) -> None` | A ``source_bindings.yaml`` document: ``dataset_name`` → :class:`SourceBinding`. |
| `SourceConfig` | class | `(*, type: str, query: str \| None, auth_profile: str \| None, config: dict[str, typing.Any], kind: str \| None, requires: list[str], inputs: dict[str, str] \| None, refresh_on_build: bool) -> None` | Defines the extraction strategy for a dataset. |
| `SourceConfig.validate_driver_config` | function | `() -> 'SourceConfig'` | Delegate driver-specific validation to the registered validator. |

## `treasuryutils.datatools.config.registry`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DataCatalog` | class | `() -> 'None'` | Central registry for all dataset definitions. |
| `DataCatalog.bind_source` | function | `(dataset_name: 'str', *, source: '_SourceArg \| None', provider: '_ProviderArg \| None', auth_profile: 'str \| None') -> 'None'` | Programmatically rebind a primitive dataset's physical source. |
| `DataCatalog.get_config` | function | `(dataset_name: 'str \| None') -> 'dict[str, Any] \| dict[str, dict[str, Any]]'` | Retrieve the configuration for a specific dataset or the entire catalog. |
| `DataCatalog.get_sink` | function | `(sink_name: 'str') -> 'SinkConfig'` | Return the SinkConfig for a registered sink_name. |
| `DataCatalog.list_sinks` | function | `() -> 'list[str]'` | Return all loaded sink names, sorted alphabetically. |
| `DataCatalog.load_from_file` | function | `(path: 'str \| Path \| list[str \| Path] \| tuple[str \| Path, ...]', *, _canonical: 'bool') -> 'str \| list[str]'` | Load and register dataset definitions from metadata paths. |
| `DataCatalog.register` | function | `(config: 'dict[str, Any] \| DatasetConfig', source: 'str', *, _canonical: 'bool') -> 'None'` | Dynamically register a dataset configuration. |
| `DataCatalog.register_sink` | function | `(config: 'SinkConfig \| dict[str, Any]') -> 'None'` | Programmatically register a sink configuration into the catalog. |
| `DataCatalog.sinks_for_dataset` | function | `(dataset_name: 'str') -> 'list[SinkConfig]'` | Return all sinks whose dataset_name matches. |

## `treasuryutils.datatools.config.validation`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `resolve_schema_mode` | function | `(meta: 'dict[str, Any]') -> 'SchemaMode'` | Resolve the effective schema mode for a dataset. |

## `treasuryutils.datatools.connectors`

_No public callables discovered._

## `treasuryutils.datatools.contracts`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactKind` | callable | `(*args, **kwargs)` |  |
| `CacheMissError` | class | `(dataset_name: 'str', cache_path: 'str \| None', *, code: 'str') -> 'None'` | Raised when requested data is not in the cache. |
| `DatasetUpdater` | class | `(*args, **kwargs)` | The narrow capability the update coordinator needs: run a dataset's ingestion. |
| `DatasetUpdater.get_last_updated` | function | `() -> 'str \| None'` | Return the ISO-8601 timestamp of the last update, or None if never updated. |
| `DatasetUpdater.has_cache` | function | `() -> 'bool'` | Return True when the dataset is already materialized in the cache. |
| `DatasetUpdater.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Run the dataset's ingestion without acquiring the lock (caller holds it). |
| `DependencyReader` | class | `(*args, **kwargs)` | The narrow capability a Python builder needs: read other datasets. |
| `DependencyReader.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', covers: 'tuple[date, date] \| None') -> 'pl.DataFrame'` | Read the dataset as a Polars DataFrame (optionally narrowed). |
| `DependencyReader.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency (same storage root). |
| `DriverRegistry` | class | `(*args, **kwargs)` | The narrow capability the config layer needs: resolve a driver's validator. |
| `DriverRegistry.get_sink_validator` | function | `(type_key: 'str') -> 'Callable[[dict[str, Any], dict[str, Any]], None]'` | Return the ``(target, config)`` validator for sink ``type_key``. |
| `DriverRegistry.get_source_validator` | function | `(src_type: 'str') -> 'Callable[[dict[str, Any], str \| None], None]'` | Return the ``(config, query)`` validator for source ``src_type``. |
| `DriverRegistry.is_sink_driver_registered` | function | `(type_key: 'str') -> 'bool'` | Return True when a sink driver is registered for ``type_key``. |
| `DriverRegistry.is_source_driver_registered` | function | `(src_type: 'str') -> 'bool'` | Return True when a source driver is registered for ``src_type``. |
| `LockBackend` | class | `(*args, **kwargs)` | Abstract distributed lock (spec §4.5, §10.2 #5). |
| `LockBackend.acquire` | function | `(resource_id: 'str', *, timeout_s: 'int') -> 'Iterator[None]'` | Acquire an exclusive lock on resource_id, releasing it on context exit. |
| `MultiInputPyBuilder` | class | `(manager_ref: 'DependencyReader \| None') -> 'None'` | Interface for named multi-input Python builders (spec §2, R3). |
| `MultiInputPyBuilder.run` | function | `(*, inputs: 'Mapping[str, DependencyReader]', start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame \| None'` | Execute the builder logic against named upstream inputs. |
| `PyBuilderProtocol` | class | `(manager_ref: 'DependencyReader \| None') -> 'None'` | Interface for Python-based data builders. |
| `PyBuilderProtocol.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame \| None'` | Execute the builder logic. |
| `SchemaMode` | callable | `(*args, **kwargs)` |  |
| `ServeMode` | callable | `(*args, **kwargs)` |  |
| `WriteDisposition` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.contracts.protocols`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DatasetUpdater` | class | `(*args, **kwargs)` | The narrow capability the update coordinator needs: run a dataset's ingestion. |
| `DatasetUpdater.get_last_updated` | function | `() -> 'str \| None'` | Return the ISO-8601 timestamp of the last update, or None if never updated. |
| `DatasetUpdater.has_cache` | function | `() -> 'bool'` | Return True when the dataset is already materialized in the cache. |
| `DatasetUpdater.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Run the dataset's ingestion without acquiring the lock (caller holds it). |
| `DependencyReader` | class | `(*args, **kwargs)` | The narrow capability a Python builder needs: read other datasets. |
| `DependencyReader.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', covers: 'tuple[date, date] \| None') -> 'pl.DataFrame'` | Read the dataset as a Polars DataFrame (optionally narrowed). |
| `DependencyReader.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency (same storage root). |
| `DriverRegistry` | class | `(*args, **kwargs)` | The narrow capability the config layer needs: resolve a driver's validator. |
| `DriverRegistry.get_sink_validator` | function | `(type_key: 'str') -> 'Callable[[dict[str, Any], dict[str, Any]], None]'` | Return the ``(target, config)`` validator for sink ``type_key``. |
| `DriverRegistry.get_source_validator` | function | `(src_type: 'str') -> 'Callable[[dict[str, Any], str \| None], None]'` | Return the ``(config, query)`` validator for source ``src_type``. |
| `DriverRegistry.is_sink_driver_registered` | function | `(type_key: 'str') -> 'bool'` | Return True when a sink driver is registered for ``type_key``. |
| `DriverRegistry.is_source_driver_registered` | function | `(src_type: 'str') -> 'bool'` | Return True when a source driver is registered for ``src_type``. |
| `LockBackend` | class | `(*args, **kwargs)` | Abstract distributed lock (spec §4.5, §10.2 #5). |
| `LockBackend.acquire` | function | `(resource_id: 'str', *, timeout_s: 'int') -> 'Iterator[None]'` | Acquire an exclusive lock on resource_id, releasing it on context exit. |
| `MultiInputPyBuilder` | class | `(manager_ref: 'DependencyReader \| None') -> 'None'` | Interface for named multi-input Python builders (spec §2, R3). |
| `MultiInputPyBuilder.run` | function | `(*, inputs: 'Mapping[str, DependencyReader]', start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame \| None'` | Execute the builder logic against named upstream inputs. |
| `PyBuilderProtocol` | class | `(manager_ref: 'DependencyReader \| None') -> 'None'` | Interface for Python-based data builders. |
| `PyBuilderProtocol.run` | function | `(start_date: 'Any \| None', end_date: 'Any \| None') -> 'pl.DataFrame \| None'` | Execute the builder logic. |

## `treasuryutils.datatools.contracts.registry`

_No public callables discovered._

## `treasuryutils.datatools.contracts.vocab`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactKind` | callable | `(*args, **kwargs)` |  |
| `SchemaMode` | callable | `(*args, **kwargs)` |  |
| `ServeMode` | callable | `(*args, **kwargs)` |  |
| `WriteDisposition` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.exceptions`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CacheCorruptionError` | class | `(dataset_name: 'str', message: 'str', *, code: 'str') -> 'None'` | Raised when cache data is corrupt or unreadable. |
| `CacheError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base class for cache-related errors. |
| `CacheMissError` | class | `(dataset_name: 'str', cache_path: 'str \| None', *, code: 'str') -> 'None'` | Raised when requested data is not in the cache. |
| `CacheProvenanceError` | class | `(dataset_name: 'str', *, cached_binding_fingerprint: 'str \| None', active_binding_fingerprint: 'str', code: 'str') -> 'None'` | Raised when a cache was built from a DIFFERENT source binding than the active one. |
| `ConfigurationError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when dataset configuration is invalid or missing. |
| `CoverageError` | class | `(dataset: 'str', *, requested: 'tuple[date, date]', covered: 'tuple[date, date] \| None', code: 'str') -> 'None'` | Raised when a cached table exists but does not span the requested range. |
| `DataToolsError` | class | `(*args: 'object', code: 'str') -> 'None'` | Base exception for all DataTools errors. |
| `DependencyCycleError` | class | `(cycle_path: 'list[str]', *, code: 'str') -> 'None'` | Raised when a circular dependency is detected. |
| `DependencyError` | class | `(*args: 'object', code: 'str') -> 'None'` | Raised when dependency resolution fails. |
| `DependencyNotFoundError` | class | `(dataset_name: 'str', missing_dependency: 'str', *, code: 'str') -> 'None'` | Raised when a declared dependency doesn't exist. |
| `LockTimeoutError` | class | `(resource: 'str', timeout_seconds: 'int', *, code: 'str') -> 'None'` | Raised when acquiring a lock times out. |
| `MultiSinkError` | class | `(dataset_name: 'str', failures: 'list[SinkResult]', *, code: 'str') -> 'None'` | Raised when ``strict_mirrors=True`` and one or more fan-out mirrors failed. |
| `NestedUpdateError` | class | `(dataset_name: 'str', *, code: 'str') -> 'None'` | Raised when an update is triggered while another is already running in-process. |
| `PipelineExecutionError` | class | `(dataset_name: 'str', message: 'str', cause: 'Exception \| None', *, fix: 'str \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when a DLT pipeline execution fails. |
| `SchemaValidationError` | class | `(dataset_name: 'str', message: 'str', failure_cases: 'list[dict[str, Any]] \| None', *, code: 'str') -> 'None'` | Raised when data fails schema validation. |
| `SourceAccessError` | class | `(message: 'str', *, dataset_name: 'str', source_type: 'str', code: 'str') -> 'None'` | Raised when a consumer cannot access a dataset's configured source. |
| `SourceExtractionError` | class | `(source_type: 'str', message: 'str', cause: 'Exception \| None', *, code: 'str') -> 'None'` | Raised when data extraction from a source fails. |

## `treasuryutils.datatools.execution`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DatasetRunner` | class | `(*, config: 'EngineConfig \| None') -> 'None'` | The single execution engine: runs datasets through DLT. |
| `DatasetRunner.hard_reset` | function | `(req: 'ExecutionRequest') -> 'None'` | Reset the pipeline state and clean up artifacts. |
| `DatasetRunner.run` | function | `(req: 'ExecutionRequest') -> 'ExecutionResult'` | Execute the pipeline for the given request. |
| `default_engine_factory` | function | `() -> 'ExecutionEngine'` | Create the default execution engine (DLT-backed). |
| `DestinationSpec` | class | `(*args, **kwargs)` | Marker protocol for destination specifications. |
| `DuckdbDestinationSpec` | class | `(db_path: 'Path') -> None` | Specification for DuckDB destination. |
| `ExecutionEngine` | class | `(*args, **kwargs)` | Pluggable execution engine interface. |
| `ExecutionEngine.hard_reset` | function | `(req: 'ExecutionRequest') -> 'None'` | Reset the pipeline state and clean up artifacts. |
| `ExecutionEngine.run` | function | `(req: 'ExecutionRequest') -> 'ExecutionResult'` | Execute the pipeline for the given request. |
| `ExecutionRequest` | class | `(dataset_name: 'str', cache_table_name: 'str', meta: 'dict[str, Any]', auth_registry: 'Mapping[str, Any]', destination: 'DestinationSpec', pipeline_name: 'str \| None', dataset_schema: 'str', full_refresh: 'bool', initial_value: 'str \| None', write_disposition: 'str \| None', allow_batching: 'bool', manager_ref: 'DependencyReader \| None', write_target: 'CacheWriteTarget \| None', drop_pipeline_on_start: 'bool', drop_pipeline_on_finish: 'bool', cleanup_paths: 'Sequence[Path]') -> None` | Immutable specification for a dataset pipeline execution. |
| `ExecutionResult` | class | `(dataset_name: 'str', cache_table_name: 'str', artifacts: 'dict[str, Path]', duration_seconds: 'float \| None', source_type: 'str \| None', error_message: 'str \| None') -> None` | Result of a dataset pipeline execution. |
| `ParquetUpsertDestinationSpec` | class | `(sink_path: 'Path', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', batch_size: 'int', schema_config: 'dict[str, Any] \| None', partition_by: 'list[str] \| None') -> None` | Specification for stateless Parquet upsert destination. |

## `treasuryutils.datatools.export`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `export_lineage` | function | `(env: 'str', output_path: 'Path', *, catalog: 'DataCatalog \| None') -> 'Path'` | Emit V1 DataHub lineage YAML from the bound catalog to *output_path*. |

## `treasuryutils.datatools.facade`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AbstractDataManager` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None') -> 'None'` | Abstract base class for dataset managers. |
| `DatasetClient` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None', update_on_start: 'bool', full_refresh_on_start: 'bool', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Primary manager for DuckDB-backed persistent storage. |
| `DatasetClient.ensure_fresh` | function | `(*, recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool') -> 'list[str]'` | Ensure this dataset (and optionally its dependencies) are fresh. |
| `DatasetClient.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool \| None', artifact_kind: 'ArtifactKind \| None', force_refresh: 'bool \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', persist_artifacts: 'bool \| None', use_existing_artifacts: 'bool \| None', covers: 'tuple[date, date] \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'pl.DataFrame'` | Get data as a Polars DataFrame. |
| `DatasetClient.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency. |
| `DatasetClient.get_last_updated` | function | `() -> 'str \| None'` | Get the last update timestamp for this dataset. |
| `DatasetClient.handle` | function | `(*, serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'DatasetHandle'` | Return a storage-agnostic dataset handle. |
| `DatasetClient.hard_reset` | function | `() -> 'None'` | Force a complete reset of the dataset pipeline state. |
| `DatasetClient.has_cache` | function | `() -> 'bool'` | Check if cached data exists for this dataset. |
| `DatasetClient.iter_batches` | function | `(*, batch_size: 'int', columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'Iterator[pl.DataFrame]'` | Yield data in batches from the dataset handle. |
| `DatasetClient.prefetch` | function | `() -> 'None'` | Run any pending startup update eagerly. |
| `DatasetClient.query` | function | `(sql: 'str') -> 'pl.DataFrame \| None'` | Execute ad-hoc SQL against a provider that supports SQL. |
| `DatasetClient.update` | function | `(*, full_refresh: 'FullRefreshScope', initial_value: 'str \| None', respect_target_policy: 'bool') -> 'None'` | Sync local persistent storage with the remote source. |
| `DatasetClient.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Execute update without acquiring the global lock. |
| `ParquetUpsert` | class | `(dataset_identifier: 'str \| Path', sink_file_path: 'str \| Path', auth_registry: 'Mapping[str, Any] \| None', partition_by: 'list[str] \| None') -> 'None'` | Lightweight manager for serverless Parquet upserts. |
| `ParquetUpsert.run_upsert` | function | `(*, fan_out: 'bool', strict_mirrors: 'bool') -> 'UpsertResult'` | Execute an atomic upsert to the Parquet file, then fan out to mirrors. |
| `SinkExporter` | class | `(sink_config: 'SinkConfig', *, auth_registry: 'Mapping[str, Any] \| None', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Manages target-aware sync from one dataset to one sink. |
| `SinkExporter.run` | function | `() -> 'SinkResult'` | Execute one dataset → sink sync. |
| `UpsertResult` | class | `(canonical: 'SinkResult', mirrors: 'tuple[SinkResult, ...]', watermark: 'WatermarkInfo \| None') -> None` | Outcome of one ``ParquetUpsert.run_upsert`` call. |
| `WatermarkInfo` | class | `(cursor_column: 'str \| None', cursor_max: 'Any \| None', rows_written: 'int \| None') -> None` | The high-watermark produced by one ``ParquetUpsert.run_upsert`` call. |

## `treasuryutils.datatools.facade.pipeline`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Pipeline` | class | `(name: 'str', *, base_path: 'Path \| str \| None', auth_registry: 'Mapping[str, Any] \| None') -> 'None'` | Multi-step ETL orchestration. |
| `Pipeline.add` | function | `(dataset_name: 'str', *, manager_type: "Literal['dataset', 'parquet']", sink_path: 'Path \| str \| None', partition_by: 'list[str] \| None', **manager_kwargs: 'Any') -> 'Pipeline'` | Register a dataset step. Returns ``self`` for chaining. |
| `Pipeline.execute` | function | `(*, full_refresh: 'bool', dry_run: 'bool') -> 'PipelineResult'` | Run the pipeline. |
| `Pipeline.status` | function | `() -> "dict[str, Literal['pending', 'unknown']]"` | Return dataset status. Currently all are ``pending`` or ``unknown``. |
| `PipelineResult` | class | `(name: 'str', steps: 'tuple[StepResult, ...]', total_duration_seconds: 'float') -> None` | Aggregate outcome of a full pipeline execution. |
| `StepResult` | class | `(dataset_name: 'str', status: "Literal['updated', 'skipped', 'failed']", duration_seconds: 'float', error: 'str \| None', error_type: 'str \| None', error_code: 'str \| None', sinks: 'tuple[SinkResult, ...]') -> None` | Outcome of a single pipeline step (dataset update + its sinks). |

## `treasuryutils.datatools.ingest`

_No public callables discovered._

## `treasuryutils.datatools.ingest.connectors`

_No public callables discovered._

## `treasuryutils.datatools.ingest.coordination`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_update_plan` | function | `(*, configs: 'Mapping[str, Mapping[str, Any]]', target: 'str', include_target: 'bool') -> 'UpdatePlan'` | Build a topological update order for `target` based on `depends_on`. |
| `DatasetManagerLike` | class | `(*args, **kwargs)` | The narrow capability the update coordinator needs: run a dataset's ingestion. · alias of `DatasetUpdater` (import: `from treasuryutils.datatools.contracts import DatasetUpdater`) |
| `DatasetManagerLike.get_last_updated` | function | `() -> 'str \| None'` | Return the ISO-8601 timestamp of the last update, or None if never updated. |
| `DatasetManagerLike.has_cache` | function | `() -> 'bool'` | Return True when the dataset is already materialized in the cache. |
| `DatasetManagerLike.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Run the dataset's ingestion without acquiring the lock (caller holds it). |
| `DuckdbUpdateLock` | class | `(root: 'Path', lock_backend: 'LockBackend \| None') -> None` | The global, cross-process DuckDB write lock for a cache root. |
| `DuckdbUpdateLock.acquire` | function | `(*, timeout_seconds: 'int') -> 'Iterator[None]'` | Acquire the update lock via backend or local file lock. |
| `DuckdbUpdateLock.file_lock` | function | `() -> 'BaseFileLock'` | Create a file lock instance. |
| `UpdateCoordinator` | class | `(*, lock_backend: 'LockBackend \| None') -> 'None'` | Coordinates safe updates for DataTools. |
| `UpdateCoordinator.ensure_fresh` | function | `(*, root: 'Path', dataset: 'str', configs: 'Mapping[str, Mapping[str, Any]]', manager_factory: 'Callable[[str], DatasetUpdater]', recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool', timeout_seconds: 'int') -> 'list[str]'` | Ensure a dataset and its dependencies are fresh. |
| `UpdateCoordinator.run_duckdb_update` | function | `(*, root: 'Path', dataset: 'str', fn: 'Callable[[], T]', timeout_seconds: 'int') -> 'T'` | Execute an update function with proper locking and nesting guards. |
| `UpdatePlan` | class | `(order: 'tuple[str, ...]') -> None` | Represents an ordered update plan. |

## `treasuryutils.datatools.ingest.execution`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DatasetRunner` | class | `(*, config: 'EngineConfig \| None') -> 'None'` | The single execution engine: runs datasets through DLT. |
| `DatasetRunner.hard_reset` | function | `(req: 'ExecutionRequest') -> 'None'` | Reset the pipeline state and clean up artifacts. |
| `DatasetRunner.run` | function | `(req: 'ExecutionRequest') -> 'ExecutionResult'` | Execute the pipeline for the given request. |
| `default_engine_factory` | function | `() -> 'ExecutionEngine'` | Create the default execution engine (DLT-backed). |
| `DestinationSpec` | class | `(*args, **kwargs)` | Marker protocol for destination specifications. |
| `DuckdbDestinationSpec` | class | `(db_path: 'Path') -> None` | Specification for DuckDB destination. |
| `ExecutionEngine` | class | `(*args, **kwargs)` | Pluggable execution engine interface. |
| `ExecutionEngine.hard_reset` | function | `(req: 'ExecutionRequest') -> 'None'` | Reset the pipeline state and clean up artifacts. |
| `ExecutionEngine.run` | function | `(req: 'ExecutionRequest') -> 'ExecutionResult'` | Execute the pipeline for the given request. |
| `ExecutionRequest` | class | `(dataset_name: 'str', cache_table_name: 'str', meta: 'dict[str, Any]', auth_registry: 'Mapping[str, Any]', destination: 'DestinationSpec', pipeline_name: 'str \| None', dataset_schema: 'str', full_refresh: 'bool', initial_value: 'str \| None', write_disposition: 'str \| None', allow_batching: 'bool', manager_ref: 'DependencyReader \| None', write_target: 'CacheWriteTarget \| None', drop_pipeline_on_start: 'bool', drop_pipeline_on_finish: 'bool', cleanup_paths: 'Sequence[Path]') -> None` | Immutable specification for a dataset pipeline execution. |
| `ExecutionResult` | class | `(dataset_name: 'str', cache_table_name: 'str', artifacts: 'dict[str, Path]', duration_seconds: 'float \| None', source_type: 'str \| None', error_message: 'str \| None') -> None` | Result of a dataset pipeline execution. |
| `ParquetUpsertDestinationSpec` | class | `(sink_path: 'Path', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', batch_size: 'int', schema_config: 'dict[str, Any] \| None', partition_by: 'list[str] \| None') -> None` | Specification for stateless Parquet upsert destination. |

## `treasuryutils.datatools.ingest.sources`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `configure_dlt_for_pipeline` | function | `(*, duplicate_cursor_warning_threshold: 'int', dlt_naming_convention: 'str') -> 'None'` | Apply treasuryutils-specific DLT runtime tweaks. |
| `create_source` | function | `(_dataset_name: 'str \| None', meta_config: 'dict[str, Any] \| None', source_config: 'dict[str, Any] \| None', overrides: 'dict[str, Any] \| None', auth_registry: 'Mapping[str, Any] \| None', *, allow_batching: 'bool', manager_ref: 'DependencyReader \| None', write_target: 'CacheWriteTarget \| None', table_name: 'str \| None', dataset_name: 'str \| None') -> 'Any'` | Factory: Creates a DLT resource based on source configuration. |
| `get_source_driver` | function | `(src_type: 'str') -> 'SourceFactory'` | Look up a registered source factory, raising on miss. |
| `is_source_driver_registered` | function | `(src_type: 'str') -> 'bool'` | Check whether a source type has been registered. |
| `load_resource_class` | function | `(class_path: 'str') -> 'Any'` | Dynamically import and return a class from a string path. |
| `register_source_driver` | function | `(src_type: 'str', factory: 'SourceFactory', *, validate_config: 'SourceConfigValidator') -> 'None'` | Register a source-driver factory + its config validator. |
| `SourceContext` | class | `(table_name: 'str', dataset_name: 'str', src_conf: 'dict[str, Any]', meta_config: 'dict[str, Any]', query: 'str \| None', authenticator: 'TokenProvider \| WorkspaceClientProvider \| None', allow_batching: 'bool', manager_ref: 'DependencyReader \| None', write_target: 'CacheWriteTarget \| None', requires: 'tuple[str, ...]') -> None` | Normalised creation context supplied to every source driver factory. |

## `treasuryutils.datatools.lakehouse`

_No public callables discovered._

## `treasuryutils.datatools.lakehouse.duckdb`

_No public callables discovered._

## `treasuryutils.datatools.lakehouse.duckdb.engine`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DuckdbEngine` | class | `(db_path: 'Path') -> 'None'` | DuckDB query/export adapter for the local cache. |
| `DuckdbEngine.append_only_probe` | function | `(table_name: 'str', update_key: 'str') -> 'tuple[str, int] \| None'` | Return the cached leaf table's ``(stringified max(update_key), rowcount)``. |
| `DuckdbEngine.build_select_sql` | function | `(*, table_name: 'str', columns: 'Sequence[str] \| None', where_sql: 'str \| None', order_by: 'Sequence[str] \| None', limit: 'int \| None') -> 'str'` | Build a SELECT statement for DuckDB with defensive identifier quoting. |
| `DuckdbEngine.coverage` | function | `(table_name: 'str', update_key: 'str') -> 'tuple[datetime.date, datetime.date] \| None'` | Return the cached cursor's ``(min, max)`` as a date interval, or ``None``. |
| `DuckdbEngine.export_parquet_hive` | function | `(table_name: 'str', dest_dir: 'Path', *, partition_by: 'list[str] \| None', compression: 'str') -> 'None'` | Export a table to a hive-partitioned parquet dataset. |
| `DuckdbEngine.export_sorted_ipc` | function | `(table_name: 'str', sort_columns: 'str \| list[str] \| tuple[str, ...]', dest_path: 'Path', *, rows_per_batch: 'int') -> 'None'` | Export a sorted table to an Arrow IPC file (memory-map friendly). |
| `DuckdbEngine.query` | function | `(sql: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame \| None'` | Execute arbitrary SQL and return results as a Polars DataFrame, or None for DDL/DML. |
| `DuckdbEngine.query_batches` | function | `(sql: 'str', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches without full materialization. |
| `DuckdbEngine.quote_identifier` | function | `(name: 'str') -> 'str'` | Quote an identifier for DuckDB SQL. |
| `DuckdbEngine.read_sorted` | function | `(table_name: 'str', sort_columns: 'str \| list[str] \| tuple[str, ...]', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame'` | Read a table sorted by *sort_columns*, applying schema enforcement if provided. |
| `DuckdbEngine.read_table` | function | `(table_name: 'str', *, schema: 'SchemaEnforcer \| None') -> 'pl.DataFrame'` | Load an entire table into a Polars DataFrame, applying schema enforcement if provided. |
| `DuckdbEngine.table_exists` | function | `(table_name: 'str') -> 'bool'` | Return True if *table_name* exists in the ``data`` or ``main`` schema. |

## `treasuryutils.datatools.lakehouse.duckdb.internal_tables`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ensure_internal_tables` | function | `(conn: 'DuckDBPyConnection') -> 'None'` | Create internal metadata tables if they do not exist (with best-effort migrations). |
| `get_last_updated` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str') -> 'datetime.datetime \| None'` | Return last update timestamp for dataset, if present. |
| `get_stale_datasets` | function | `(conn: 'DuckDBPyConnection', cutoff: 'datetime.datetime') -> 'list[tuple[str, str \| None]]'` | Return datasets that have not been accessed since cutoff. |
| `log_access` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', cache_table_name: 'str \| None') -> 'None'` | Record access time for LRU maintenance. |
| `record_update` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', cache_table_name: 'str \| None', build_binding_fingerprint: 'str \| None') -> 'None'` | Record update time for staleness checks (and, optionally, build-provenance). |
| `remove_dataset_metadata` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str') -> 'None'` | Remove internal metadata for dataset. |

## `treasuryutils.datatools.lakehouse.duckdb.maintenance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DuckdbMaintenance` | class | `(db_path: 'Path') -> 'None'` | DuckDB file maintenance operations (prune/vacuum/drop). |
| `DuckdbMaintenance.drop_dataset` | function | `(conn: 'DuckDBPyConnection', dataset_name: 'str', *, table_name: 'str \| None') -> 'bool'` | Drop the dataset table and associated metadata. |
| `DuckdbMaintenance.prune_by_age` | function | `(*, days_unused: 'int') -> 'list[str]'` | Drop datasets that have not been accessed in `days_unused`. |
| `DuckdbMaintenance.prune_to_size` | function | `(*, min_safe_days: 'int') -> 'list[str]'` | Drop least-recently-accessed datasets until safety buffer is reached. |
| `DuckdbMaintenance.vacuum` | function | `(*, checkpoint: 'bool') -> 'None'` | Run VACUUM (and optionally CHECKPOINT) to reclaim disk space. |

## `treasuryutils.datatools.lakehouse.duckdb.state`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DuckdbStateStore` | class | `(db_path: 'Path') -> 'None'` | DuckDB-backed state store for cache access + update tracking. |
| `DuckdbStateStore.build_binding_fingerprint` | function | `(dataset_name: 'str') -> 'str \| None'` | Return the recorded build-binding fingerprint, or ``None`` when UNKNOWN. |
| `DuckdbStateStore.get_last_updated` | function | `(dataset_name: 'str') -> 'dt.datetime \| None'` | Return last updated timestamp, if present. |
| `DuckdbStateStore.record_access` | function | `(dataset_name: 'str', *, table_name: 'str \| None') -> 'None'` | Best-effort access logging for the ``_access_log`` metadata table. |
| `DuckdbStateStore.record_build_binding_fingerprint` | function | `(dataset_name: 'str', fingerprint: 'str', *, table_name: 'str \| None') -> 'None'` | Persist the build-binding ``fingerprint`` for ``dataset_name``. |
| `DuckdbStateStore.record_update` | function | `(dataset_name: 'str', *, table_name: 'str \| None') -> 'None'` | Persist a last_updated timestamp. |
| `DuckdbStateStore.record_update_with_source_tokens` | function | `(dataset_name: 'str', source_tokens: 'Mapping[str, str]', *, table_name: 'str \| None', build_binding_fingerprint: 'str \| None') -> 'None'` | Atomically persist ``last_updated`` AND ``source_tokens_at_build`` in one upsert. |
| `DuckdbStateStore.remove_metadata` | function | `(dataset_name: 'str') -> 'None'` | Remove all metadata rows for a dataset. |
| `DuckdbStateStore.source_tokens_at_build` | function | `(dataset_name: 'str') -> 'Mapping[str, str] \| None'` | Return the upstream source tokens recorded at the dataset's last build. |

## `treasuryutils.datatools.lakehouse.local`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `create_default_lakehouse` | function | `(root: 'Path') -> 'LocalCache'` | Create the default local cache instance for a given root. · alias of `create_default_cache` (import: `from treasuryutils.datatools.cache.local import create_default_cache`) |
| `LocalLakehouse` | class | `(root: 'Path', db_path: 'Path') -> None` | Concrete local cache wiring (was ``LocalLakehouse`` — spec §1.6, ADR-0013). · alias of `LocalCache` (import: `from treasuryutils.datatools.cache.local import LocalCache`) |
| `LocalLakehouse.exporter` | function | `() -> 'CacheExporter'` | Hand serving the narrow export view (Tier-1 → Tier-2; spec §3.2/§3.4). |
| `LocalLakehouse.reader` | function | `() -> 'CacheReader'` | Hand serving the narrow read view of the working cache (spec §3.2/§3.4). |
| `LocalLakehouse.write_target` | function | `(table_name: 'str') -> 'CacheWriteTarget'` | Return the ``(db_path, table_name)`` write descriptor for ingest's DLT load. |

## `treasuryutils.datatools.lakehouse.maintenance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `LakehouseMaintainer` | class | `(root: 'Path') -> None` | Coordinates cache maintenance across runtime artifacts and engine storage. |
| `LakehouseMaintainer.get_file_size_gb` | function | `() -> 'float'` | Returns total size of the cache directory in GB. |
| `LakehouseMaintainer.prune_all` | function | `(*, force_vacuum: 'bool', timeout_seconds: 'int') -> 'None'` | Run maintenance across runtime artifacts and the DuckDB engine file. |

## `treasuryutils.datatools.lakehouse.paths`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `arrow_mmap_dir` | function | `(root: 'Path') -> 'Path'` | Return the Arrow IPC memory-map directory under *root*. |
| `arrow_mmap_path` | function | `(root: 'Path', dataset_name: 'str') -> 'Path'` | Return the Arrow IPC file path for *dataset_name* under *root*. |
| `artifact_lock_path` | function | `(root: 'Path', dataset_name: 'str', artifact_kind: 'str') -> 'Path'` | Return the per-artifact file-lock path for *dataset_name* and *artifact_kind*. |
| `artifacts_dir` | function | `(root: 'Path') -> 'Path'` | Return the artifacts sub-directory under *root*. |
| `duckdb_db_path` | function | `(root: 'Path') -> 'Path'` | Return the canonical DuckDB file path for a given cache *root*. |
| `duckdb_engine_dir` | function | `(root: 'Path') -> 'Path'` | Return the DuckDB engine sub-directory under *root*. |
| `duckdb_update_lock_path` | function | `(root: 'Path') -> 'Path'` | Return the DuckDB single-writer update lock file path. |
| `engines_dir` | function | `(root: 'Path') -> 'Path'` | Return the engines sub-directory under *root*. |
| `ensure_layout` | function | `(root: 'Path') -> 'None'` | Ensure the cache directory layout exists. |
| `locks_dir` | function | `(root: 'Path') -> 'Path'` | Return the file-lock directory under *root*. |
| `parquet_hive_dir` | function | `(root: 'Path') -> 'Path'` | Return the hive-partitioned Parquet root directory under *root*. |
| `parquet_hive_path` | function | `(root: 'Path', dataset_name: 'str') -> 'Path'` | Return the hive-partitioned Parquet directory for *dataset_name* under *root*. |
| `resolve_root` | function | `(provided_path: 'str \| Path \| None') -> 'Path'` | Resolve the cache root directory. |

## `treasuryutils.datatools.manager`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AbstractDataManager` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None') -> 'None'` | Abstract base class for dataset managers. |
| `DatasetClient` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None', update_on_start: 'bool', full_refresh_on_start: 'bool', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Primary manager for DuckDB-backed persistent storage. |
| `DatasetClient.ensure_fresh` | function | `(*, recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool') -> 'list[str]'` | Ensure this dataset (and optionally its dependencies) are fresh. |
| `DatasetClient.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool \| None', artifact_kind: 'ArtifactKind \| None', force_refresh: 'bool \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', persist_artifacts: 'bool \| None', use_existing_artifacts: 'bool \| None', covers: 'tuple[date, date] \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'pl.DataFrame'` | Get data as a Polars DataFrame. |
| `DatasetClient.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency. |
| `DatasetClient.get_last_updated` | function | `() -> 'str \| None'` | Get the last update timestamp for this dataset. |
| `DatasetClient.handle` | function | `(*, serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'DatasetHandle'` | Return a storage-agnostic dataset handle. |
| `DatasetClient.hard_reset` | function | `() -> 'None'` | Force a complete reset of the dataset pipeline state. |
| `DatasetClient.has_cache` | function | `() -> 'bool'` | Check if cached data exists for this dataset. |
| `DatasetClient.iter_batches` | function | `(*, batch_size: 'int', columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'Iterator[pl.DataFrame]'` | Yield data in batches from the dataset handle. |
| `DatasetClient.prefetch` | function | `() -> 'None'` | Run any pending startup update eagerly. |
| `DatasetClient.query` | function | `(sql: 'str') -> 'pl.DataFrame \| None'` | Execute ad-hoc SQL against a provider that supports SQL. |
| `DatasetClient.update` | function | `(*, full_refresh: 'FullRefreshScope', initial_value: 'str \| None', respect_target_policy: 'bool') -> 'None'` | Sync local persistent storage with the remote source. |
| `DatasetClient.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Execute update without acquiring the global lock. |
| `DatasetManager` | class | `(dataset_identifier: 'str \| Path', *, auth_registry: 'Mapping[str, Any] \| None', update_on_start: 'bool', full_refresh_on_start: 'bool', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Primary manager for DuckDB-backed persistent storage. · alias of `DatasetClient` (import: `from treasuryutils.datatools import DatasetClient`) |
| `DatasetManager.ensure_fresh` | function | `(*, recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool') -> 'list[str]'` | Ensure this dataset (and optionally its dependencies) are fresh. |
| `DatasetManager.get` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool \| None', artifact_kind: 'ArtifactKind \| None', force_refresh: 'bool \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', persist_artifacts: 'bool \| None', use_existing_artifacts: 'bool \| None', covers: 'tuple[date, date] \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'pl.DataFrame'` | Get data as a Polars DataFrame. |
| `DatasetManager.get_dependency` | function | `(dataset_name: 'str') -> 'DependencyReader'` | Resolve another dataset as a dependency. |
| `DatasetManager.get_last_updated` | function | `() -> 'str \| None'` | Get the last update timestamp for this dataset. |
| `DatasetManager.handle` | function | `(*, serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'DatasetHandle'` | Return a storage-agnostic dataset handle. |
| `DatasetManager.hard_reset` | function | `() -> 'None'` | Force a complete reset of the dataset pipeline state. |
| `DatasetManager.has_cache` | function | `() -> 'bool'` | Check if cached data exists for this dataset. |
| `DatasetManager.iter_batches` | function | `(*, batch_size: 'int', columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', serve_mode: 'ServeMode \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'Iterator[pl.DataFrame]'` | Yield data in batches from the dataset handle. |
| `DatasetManager.prefetch` | function | `() -> 'None'` | Run any pending startup update eagerly. |
| `DatasetManager.query` | function | `(sql: 'str') -> 'pl.DataFrame \| None'` | Execute ad-hoc SQL against a provider that supports SQL. |
| `DatasetManager.update` | function | `(*, full_refresh: 'FullRefreshScope', initial_value: 'str \| None', respect_target_policy: 'bool') -> 'None'` | Sync local persistent storage with the remote source. |
| `DatasetManager.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Execute update without acquiring the global lock. |
| `DatasetSinkManager` | class | `(sink_config: 'SinkConfig', *, auth_registry: 'Mapping[str, Any] \| None', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Manages target-aware sync from one dataset to one sink. · alias of `SinkExporter` (import: `from treasuryutils.datatools import SinkExporter`) |
| `DatasetSinkManager.run` | function | `() -> 'SinkResult'` | Execute one dataset → sink sync. |
| `ParquetUpsert` | class | `(dataset_identifier: 'str \| Path', sink_file_path: 'str \| Path', auth_registry: 'Mapping[str, Any] \| None', partition_by: 'list[str] \| None') -> 'None'` | Lightweight manager for serverless Parquet upserts. |
| `ParquetUpsert.run_upsert` | function | `(*, fan_out: 'bool', strict_mirrors: 'bool') -> 'UpsertResult'` | Execute an atomic upsert to the Parquet file, then fan out to mirrors. |
| `SinkExporter` | class | `(sink_config: 'SinkConfig', *, auth_registry: 'Mapping[str, Any] \| None', base_path: 'str \| Path \| None', serve_mode: 'ServeMode \| None') -> 'None'` | Manages target-aware sync from one dataset to one sink. |
| `SinkExporter.run` | function | `() -> 'SinkResult'` | Execute one dataset → sink sync. |
| `StatelessParquetManager` | class | `(dataset_identifier: 'str \| Path', sink_file_path: 'str \| Path', auth_registry: 'Mapping[str, Any] \| None', partition_by: 'list[str] \| None') -> 'None'` | Lightweight manager for serverless Parquet upserts. · alias of `ParquetUpsert` (import: `from treasuryutils.datatools import ParquetUpsert`) |
| `StatelessParquetManager.run_upsert` | function | `(*, fan_out: 'bool', strict_mirrors: 'bool') -> 'UpsertResult'` | Execute an atomic upsert to the Parquet file, then fan out to mirrors. |

## `treasuryutils.datatools.orchestration`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_update_plan` | function | `(*, configs: 'Mapping[str, Mapping[str, Any]]', target: 'str', include_target: 'bool') -> 'UpdatePlan'` | Build a topological update order for `target` based on `depends_on`. |
| `DatasetManagerLike` | class | `(*args, **kwargs)` | The narrow capability the update coordinator needs: run a dataset's ingestion. · alias of `DatasetUpdater` (import: `from treasuryutils.datatools.contracts import DatasetUpdater`) |
| `DatasetManagerLike.get_last_updated` | function | `() -> 'str \| None'` | Return the ISO-8601 timestamp of the last update, or None if never updated. |
| `DatasetManagerLike.has_cache` | function | `() -> 'bool'` | Return True when the dataset is already materialized in the cache. |
| `DatasetManagerLike.update_unlocked` | function | `(*, full_refresh: 'bool', initial_value: 'str \| None') -> 'None'` | Run the dataset's ingestion without acquiring the lock (caller holds it). |
| `DuckdbUpdateLock` | class | `(root: 'Path', lock_backend: 'LockBackend \| None') -> None` | The global, cross-process DuckDB write lock for a cache root. |
| `DuckdbUpdateLock.acquire` | function | `(*, timeout_seconds: 'int') -> 'Iterator[None]'` | Acquire the update lock via backend or local file lock. |
| `DuckdbUpdateLock.file_lock` | function | `() -> 'BaseFileLock'` | Create a file lock instance. |
| `UpdateCoordinator` | class | `(*, lock_backend: 'LockBackend \| None') -> 'None'` | Coordinates safe updates for DataTools. |
| `UpdateCoordinator.ensure_fresh` | function | `(*, root: 'Path', dataset: 'str', configs: 'Mapping[str, Mapping[str, Any]]', manager_factory: 'Callable[[str], DatasetUpdater]', recursive: 'bool', full_refresh: 'FullRefreshScope', initial_value: 'str \| None', force_target_update: 'bool', respect_target_policy: 'bool', timeout_seconds: 'int') -> 'list[str]'` | Ensure a dataset and its dependencies are fresh. |
| `UpdateCoordinator.run_duckdb_update` | function | `(*, root: 'Path', dataset: 'str', fn: 'Callable[[], T]', timeout_seconds: 'int') -> 'T'` | Execute an update function with proper locking and nesting guards. |
| `UpdatePlan` | class | `(order: 'tuple[str, ...]') -> None` | Represents an ordered update plan. |

## `treasuryutils.datatools.pipeline`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `Pipeline` | class | `(name: 'str', *, base_path: 'Path \| str \| None', auth_registry: 'Mapping[str, Any] \| None') -> 'None'` | Multi-step ETL orchestration. |
| `Pipeline.add` | function | `(dataset_name: 'str', *, manager_type: "Literal['dataset', 'parquet']", sink_path: 'Path \| str \| None', partition_by: 'list[str] \| None', **manager_kwargs: 'Any') -> 'Pipeline'` | Register a dataset step. Returns ``self`` for chaining. |
| `Pipeline.execute` | function | `(*, full_refresh: 'bool', dry_run: 'bool') -> 'PipelineResult'` | Run the pipeline. |
| `Pipeline.status` | function | `() -> "dict[str, Literal['pending', 'unknown']]"` | Return dataset status. Currently all are ``pending`` or ``unknown``. |
| `PipelineResult` | class | `(name: 'str', steps: 'tuple[StepResult, ...]', total_duration_seconds: 'float') -> None` | Aggregate outcome of a full pipeline execution. |
| `SinkResult` | class | `(sink_name: 'str', dataset_name: 'str', status: "Literal['written', 'skipped', 'failed']", write_disposition: 'WriteDisposition', duration_seconds: 'float', rows_written: 'int \| None', rows_extracted: 'int \| None', cursor_min: 'Any \| None', cursor_max: 'Any \| None', error: 'str \| None', error_type: 'str \| None', error_code: 'str \| None') -> None` | Aggregate outcome of a single dataset→sink sync. |
| `StepResult` | class | `(dataset_name: 'str', status: "Literal['updated', 'skipped', 'failed']", duration_seconds: 'float', error: 'str \| None', error_type: 'str \| None', error_code: 'str \| None', sinks: 'tuple[SinkResult, ...]') -> None` | Outcome of a single pipeline step (dataset update + its sinks). |

## `treasuryutils.datatools.schema`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CheckOperator` | enum | `GE='ge', GT='gt', LE='le', LT='lt', EQ='eq', NE='ne', ISIN='isin', NOTIN='notin', STR_MATCHES='str_matches'` | Supported logical operators for YAML semantic checks. |
| `SchemaEnforcer` | class | `(columns_config: 'dict[str, Any]', *, mode: 'SchemaMode', dataset_name: 'str', polyfill_missing: 'bool') -> 'None'` | Compiles YAML contracts into executable Pandera validators. |
| `SchemaEnforcer.apply` | function | `(df: 'pl.DataFrame') -> 'pl.DataFrame'` | Aligns and validates the DataFrame against the contract. |

## `treasuryutils.datatools.serving`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArtifactOrchestrator` | class | `(*, default_mode: 'ServeMode \| None') -> 'None'` | Facade for resolving dataset serving plans and collecting artifacts. |
| `ArtifactOrchestrator.collect` | function | `(*, handle: 'DatasetHandle', plan: 'ResolvedServingPlan', request: 'ArtifactRequest') -> 'pl.DataFrame'` | Artifact-aware data retrieval. |
| `ArtifactOrchestrator.resolve_handle` | function | `(*, manager: 'ManagerLike', serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'DatasetHandle'` | Resolve a DatasetHandle for a manager using the active serving plan. |
| `ArtifactOrchestrator.resolve_plan` | function | `(*, manager: 'ManagerLike', serve_mode: 'ServeMode', memory_map: 'bool') -> 'ResolvedServingPlan'` | Delegate plan resolution to the underlying ProviderResolver. |
| `ArtifactRequest` | class | `(kind: 'ArtifactKind', persist: 'bool', use_existing: 'bool', force_refresh: 'bool', memory_map: 'bool', sort_cols: 'str \| list[str] \| None', partition_by: 'list[str] \| None') -> None` | Resolved artifact retrieval parameters. |
| `DatasetHandle` | class | `(dataset_name: 'str', provider: 'SourceProvider', spec: 'ReadSpec', postprocess: 'PostprocessFn \| None', declared_columns: 'frozenset[str] \| None') -> None` | A storage-agnostic handle for reading a dataset. |
| `DatasetHandle.collect` | function | `() -> 'pl.DataFrame'` | Materialize the current ReadSpec as a Polars DataFrame. |
| `DatasetHandle.iter_batches` | function | `(*, batch_size: 'int') -> 'Iterator[pl.DataFrame]'` | Yield data in batches as Polars DataFrames. |
| `DatasetHandle.scan` | function | `(*, columns: 'list[str] \| tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'list[str] \| tuple[str, ...] \| None', limit: 'int \| None', memory_map: 'bool \| None', query_params: 'tuple[tuple[str, Any], ...] \| None') -> 'DatasetHandle'` | Return a new handle with an updated ReadSpec (immutable builder). |
| `FileLockBackend` | class | `(lock_dir: 'Path') -> None` | LockBackend backed by ``filelock.FileLock``. |
| `FileLockBackend.acquire` | function | `(resource_id: 'str', *, timeout_s: 'int') -> 'Iterator[None]'` | Acquire a file-based exclusive lock on resource_id. |
| `LockBackend` | class | `(*args, **kwargs)` | Abstract distributed lock (spec §4.5, §10.2 #5). |
| `LockBackend.acquire` | function | `(resource_id: 'str', *, timeout_s: 'int') -> 'Iterator[None]'` | Acquire an exclusive lock on resource_id, releasing it on context exit. |
| `ReadSpec` | class | `(columns: 'tuple[str, ...] \| None', where_sql: 'str \| None', order_by: 'tuple[str, ...] \| None', limit: 'int \| None', memory_map: 'bool', query_params: 'tuple[tuple[str, Any], ...] \| None') -> None` | A storage-agnostic read request. |
| `ReadSpec.is_full_scan` | function | `() -> 'bool'` | Return True when no columns, filter, ordering, limit, or params are applied. |
| `register_direct_provider` | function | `(type_key: 'str', builder: 'DirectProviderBuilder', *, override: 'bool') -> 'None'` | Register a direct-provider builder under *type_key*. |
| `register_provider` | function | `(key: 'str', factory: 'ProviderFactory', *, override: 'bool') -> 'None'` | Register a provider factory under a string key. · alias of `register_python_provider` (import: `from treasuryutils.datatools.serving import register_python_provider`) |
| `register_python_provider` | function | `(key: 'str', factory: 'ProviderFactory', *, override: 'bool') -> 'None'` | Register a provider factory under a string key. |
| `ServeMode` | callable | `(*args, **kwargs)` |  |
| `StreamingProvider` | class | `(*args, **kwargs)` | Provider capability: stream data as Arrow RecordBatches instead of a single DataFrame. |
| `StreamingProvider.collect_batches` | function | `(spec: 'ReadSpec', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` |  |
| `UniversalArtifactStore` | class | `(dataset_name: 'str', provider: 'SourceProvider', root: 'Path', postprocess: 'PostprocessFn \| None', lock_backend: 'LockBackend \| None', artifact_lock_timeout_s: 'int', config_fingerprint: 'str \| None', declared_columns: 'frozenset[str] \| None') -> None` | Materialize Arrow IPC and hive-parquet artifacts for a dataset. |
| `UniversalArtifactStore.fingerprint_matches` | function | `(kind: 'str') -> 'bool'` | Return True when the stored sidecar fingerprint matches ``self.config_fingerprint``. |
| `UniversalArtifactStore.get_handle` | function | `(*, memory_map: 'bool') -> 'DatasetHandle'` | Return a DatasetHandle backed by this store's provider and postprocess. |
| `UniversalArtifactStore.materialize` | function | `(*, kind: 'ArtifactKind', spec: 'ReadSpec', sort_cols: 'str \| list[str] \| tuple[str, ...] \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', force_refresh: 'bool') -> 'DataArtifact'` | Materialize a dataset artifact of the requested kind, using a lock to prevent races. |

## `treasuryutils.datatools.serving.artifacts`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArrowMmapArtifact` | class | `(dataset_name: 'str', path: 'Path', kind: 'str') -> None` | Continuous Arrow IPC file suitable for memory-mapped reads. |
| `ArrowMmapArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Read the Arrow IPC file into a Polars DataFrame. |
| `InMemoryArtifact` | class | `(dataset_name: 'str', df: 'pl.DataFrame', postprocess: 'PostprocessFn \| None', kind: 'str', location: 'Path \| None') -> None` | In-memory artifact wrapping a DataFrame. |
| `InMemoryArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Apply postprocess (if any) and return the in-memory DataFrame. |
| `ParquetHiveArtifact` | class | `(dataset_name: 'str', path: 'Path', postprocess: 'PostprocessFn \| None', kind: 'str') -> None` | Hive-partitioned parquet dataset directory. |
| `ParquetHiveArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Collect a full scan of the parquet dataset. |
| `ParquetHiveArtifact.collect_spec` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Collect a ReadSpec using Polars lazy operations / SQL when possible. |

## `treasuryutils.datatools.serving.artifacts.base`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ArrowMmapArtifact` | class | `(dataset_name: 'str', path: 'Path', kind: 'str') -> None` | Continuous Arrow IPC file suitable for memory-mapped reads. |
| `ArrowMmapArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Read the Arrow IPC file into a Polars DataFrame. |
| `InMemoryArtifact` | class | `(dataset_name: 'str', df: 'pl.DataFrame', postprocess: 'PostprocessFn \| None', kind: 'str', location: 'Path \| None') -> None` | In-memory artifact wrapping a DataFrame. |
| `InMemoryArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Apply postprocess (if any) and return the in-memory DataFrame. |
| `ParquetHiveArtifact` | class | `(dataset_name: 'str', path: 'Path', postprocess: 'PostprocessFn \| None', kind: 'str') -> None` | Hive-partitioned parquet dataset directory. |
| `ParquetHiveArtifact.collect` | function | `(*, memory_map: 'bool') -> 'pl.DataFrame'` | Collect a full scan of the parquet dataset. |
| `ParquetHiveArtifact.collect_spec` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Collect a ReadSpec using Polars lazy operations / SQL when possible. |

## `treasuryutils.datatools.serving.endpoints`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `EndpointConfig` | class | `(type: 'str', query: 'str \| None', auth_profile: 'str \| None', config: 'dict[str, Any]') -> None` | Normalized endpoint descriptor for provider selection. |

## `treasuryutils.datatools.serving.maintenance`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `delete_dataset_artifacts` | function | `(*, root: 'Path', dataset_name: 'str') -> 'None'` | Best-effort removal of all artifacts for a dataset. |
| `prune_runtime_artifacts` | function | `(*, root: 'Path', days_unused: 'int') -> 'None'` | Delete runtime artifacts that have not been accessed in `days_unused` days. |

## `treasuryutils.datatools.serving.providers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BigQueryDirectProvider` | class | `(dataset_name: 'str', project: 'str \| None', query: 'str', source_config: 'dict[str, Any]', authenticator: 'Any \| None') -> None` | Serve reads by executing SQL directly in BigQuery. |
| `BigQueryDirectProvider.collect` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Execute the configured query in BigQuery and return a DataFrame matching spec. |
| `BigQueryDirectProvider.collect_batches` | function | `(spec: 'ReadSpec', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches from BigQuery. |
| `DatabricksDirectProvider` | class | `(dataset_name: 'str', warehouse_id: 'str', query: 'str', authenticator: 'Any \| None', source_config: 'dict[str, Any]') -> None` | Serve reads by executing SQL directly in Databricks. |
| `DatabricksDirectProvider.collect` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Execute the configured query in Databricks and return a DataFrame matching spec. |
| `DatabricksDirectProvider.collect_batches` | function | `(spec: 'ReadSpec', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches from Databricks. |
| `DatasetChainProvider` | class | `(dataset_name: 'str', reader: 'CacheReader', source_datasets: 'tuple[str, ...]', source_table_names: 'tuple[str, ...]', query: 'str \| None') -> None` | Serve a derived dataset as a virtual DuckDB view over its upstream cache. |
| `DatasetChainProvider.collect` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Compose the virtual view over the upstream cache and return a DataFrame. |
| `DatasetChainProvider.collect_batches` | function | `(spec: 'ReadSpec', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream the virtual view over the upstream cache as Arrow RecordBatches. |
| `DatasetChainProvider.from_endpoint` | method | `(*, dataset_name: 'str', reader: 'CacheReader', config: 'dict[str, Any]', query: 'str \| None') -> 'DatasetChainProvider'` | Build a provider from a normalized serving endpoint's ``config`` + ``query``. |
| `FileDirectProvider` | class | `(dataset_name: 'str', path: 'Path', allow_outside_base: 'bool', scan_config: 'dict[str, Any] \| None') -> None` | Serve reads by scanning a local file directly (no lakehouse cache). |
| `FileDirectProvider.collect` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Scan the configured file and return a DataFrame matching spec. |
| `LakehouseCacheProvider` | class | `(dataset_name: 'str', table_name: 'str', reader: 'CacheReader', exporter: 'CacheExporter', state: 'StateStore') -> None` | Serve reads from the local lakehouse DuckDB cache. |
| `LakehouseCacheProvider.collect` | function | `(spec: 'ReadSpec') -> 'pl.DataFrame'` | Query the DuckDB cache and return a DataFrame matching spec. |
| `LakehouseCacheProvider.collect_batches` | function | `(spec: 'ReadSpec', *, batch_size: 'int') -> 'Iterator[pa.RecordBatch]'` | Stream query results as Arrow RecordBatches from the DuckDB cache. |
| `LakehouseCacheProvider.export_arrow_ipc` | function | `(*, sort_cols: 'str \| list[str] \| tuple[str, ...]', dest: 'Path') -> 'None'` | Export a sorted Arrow IPC file for full-scan reads. |
| `LakehouseCacheProvider.export_parquet_hive` | function | `(*, dest_dir: 'Path', partition_by: 'list[str] \| None') -> 'None'` | Export a hive-partitioned parquet dataset for full-scan reads. |
| `LakehouseCacheProvider.query` | function | `(sql: 'str') -> 'pl.DataFrame \| None'` | Execute SQL directly against the local lakehouse cache. |

## `treasuryutils.datatools.serving.resolver`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ManagerLike` | class | `(*args, **kwargs)` | Structural protocol describing what ProviderResolver needs from a manager. |
| `ManagerLike.has_cache` | function | `() -> 'bool'` |  |
| `ProviderResolver` | class | `(*, default_mode: 'ServeMode \| None') -> 'None'` | Resolve the active provider + optional artifact home for a DatasetManager. |
| `ProviderResolver.resolve_plan` | function | `(*, manager: 'ManagerLike', serve_mode: 'ServeMode \| None', memory_map: 'bool') -> 'ResolvedServingPlan'` | Resolve the active provider and artifact home for a dataset manager. |
| `ResolvedServingPlan` | class | `(provider: 'SourceProvider', home: 'ArtifactStore \| None', mode: 'ServeMode', artifact_root: 'Path \| None', postprocess: 'PostprocessFn \| None') -> None` | Resolved provider selection and artifact home for a single dataset serve. |

## `treasuryutils.datatools.serving.store`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `UniversalArtifactStore` | class | `(dataset_name: 'str', provider: 'SourceProvider', root: 'Path', postprocess: 'PostprocessFn \| None', lock_backend: 'LockBackend \| None', artifact_lock_timeout_s: 'int', config_fingerprint: 'str \| None', declared_columns: 'frozenset[str] \| None') -> None` | Materialize Arrow IPC and hive-parquet artifacts for a dataset. |
| `UniversalArtifactStore.fingerprint_matches` | function | `(kind: 'str') -> 'bool'` | Return True when the stored sidecar fingerprint matches ``self.config_fingerprint``. |
| `UniversalArtifactStore.get_handle` | function | `(*, memory_map: 'bool') -> 'DatasetHandle'` | Return a DatasetHandle backed by this store's provider and postprocess. |
| `UniversalArtifactStore.materialize` | function | `(*, kind: 'ArtifactKind', spec: 'ReadSpec', sort_cols: 'str \| list[str] \| tuple[str, ...] \| None', partition_by: 'list[str] \| tuple[str, ...] \| None', force_refresh: 'bool') -> 'DataArtifact'` | Materialize a dataset artifact of the requested kind, using a lock to prevent races. |

## `treasuryutils.datatools.sinks`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `create_message_sink` | function | `(endpoint_url: 'str', topic_name: 'str', headers: 'dict[str, str] \| None', batch_size: 'int', *, to_camel_case: 'bool', schema_config: 'dict[str, Any] \| None', max_retries: 'int', backoff_base_s: 'float') -> 'AnyDestination'` | Create a DLT destination that pushes data to an HTTP endpoint. |
| `create_partitioned_upsert_parquet_sink` | function | `(sink_dir: 'str \| Path', partition_by: 'list[str]', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', batch_size: 'int', schema_config: 'dict[str, Any] \| None') -> 'AnyDestination'` | Create a destination for hive-partitioned Parquet upserts. |
| `create_sink` | function | `(sink_config: 'SinkConfig', *, authenticator: 'Any \| None') -> 'SinkDriver'` | Instantiate the registered driver for ``sink_config``. |
| `create_upsert_parquet_sink` | function | `(file_path: 'str \| Path', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', batch_size: 'int', schema_config: 'dict[str, Any] \| None') -> 'AnyDestination'` | Create a destination for high-performance, serverless Parquet upserts. |
| `CsvFileSinkDriver` | class | `(sink_name: 'str', dialect: 'CsvDialect', authenticator: 'Any \| None') -> None` | Single-file CSV sink driver. |
| `CsvFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `CsvFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured CSV file. |
| `export_to_parquet` | function | `(df: 'Any', path: 'str \| Path', *, overwrite: 'bool') -> 'None'` | Safely export a DataFrame to a Parquet file using the Atomic Write pattern. |
| `get_sink_validator` | function | `(type_key: 'str') -> 'SinkConfigValidator'` | Look up a registered config validator, raising on miss. |
| `IdempotentSinkDriver` | class | `(*args, **kwargs)` | A driver that can be synced incrementally via a target cursor. |
| `IdempotentSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target. |
| `IdempotentSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the target with the given disposition. |
| `is_sink_driver_registered` | function | `(type_key: 'str') -> 'bool'` | Check whether a sink type has been registered. |
| `ParquetFileSinkDriver` | class | `(sink_name: 'str', compression: 'str', authenticator: 'Any \| None', sort_by: 'str \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | Single-file parquet sink driver. |
| `ParquetFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `ParquetFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured parquet file. |
| `register_sink_driver` | function | `(type_key: 'str', *, builder: 'SinkDriverBuilder', validate_config: 'SinkConfigValidator') -> 'None'` | Register a sink-driver builder + its config validator. |
| `SchemaAwareSinkDriver` | class | `(*args, **kwargs)` | A driver that enforces a schema on incoming data before writing. |
| `SchemaAwareSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the target with the given disposition. |
| `SinkConfigValidator` | callable | `(*args, **kwargs)` |  |
| `SinkDriver` | class | `(*args, **kwargs)` | Base sink capability: a named driver that writes Arrow batches. |
| `SinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the target with the given disposition. |
| `SinkDriverBuilder` | callable | `(*args, **kwargs)` |  |
| `SinkDriverContext` | class | `(sink_config: 'SinkConfig', authenticator: 'Any \| None') -> None` | Everything a sink-driver builder needs. |
| `SinkResult` | class | `(sink_name: 'str', dataset_name: 'str', status: "Literal['written', 'skipped', 'failed']", write_disposition: 'WriteDisposition', duration_seconds: 'float', rows_written: 'int \| None', rows_extracted: 'int \| None', cursor_min: 'Any \| None', cursor_max: 'Any \| None', error: 'str \| None', error_type: 'str \| None', error_code: 'str \| None') -> None` | Aggregate outcome of a single dataset→sink sync. |
| `SinkWriteResult` | class | `(rows_written: 'int', duration_seconds: 'float') -> None` | Outcome of one ``SinkDriver.write`` call. |
| `TransactionalSinkDriver` | class | `(*args, **kwargs)` | A driver whose ``write`` is atomic (all-or-nothing). |
| `TransactionalSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the target with the given disposition. |
| `WriteDisposition` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.datatools.sinks.drivers`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `create_message_sink` | function | `(endpoint_url: 'str', topic_name: 'str', headers: 'dict[str, str] \| None', batch_size: 'int', *, to_camel_case: 'bool', schema_config: 'dict[str, Any] \| None', max_retries: 'int', backoff_base_s: 'float') -> 'AnyDestination'` | Create a DLT destination that pushes data to an HTTP endpoint. |
| `CsvFileSinkDriver` | class | `(sink_name: 'str', dialect: 'CsvDialect', authenticator: 'Any \| None') -> None` | Single-file CSV sink driver. |
| `CsvFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `CsvFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured CSV file. |
| `MessageSinkDriver` | class | `(sink_name: 'str', endpoint_url: 'str', topic_name: 'str', headers: 'dict[str, str] \| None', to_camel_case: 'bool', max_retries: 'int', backoff_base_s: 'float', authenticator: 'Any \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | HTTP message sink driver. |
| `MessageSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | POST the incoming batches to the configured HTTP endpoint. |
| `ParquetFileSinkDriver` | class | `(sink_name: 'str', compression: 'str', authenticator: 'Any \| None', sort_by: 'str \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | Single-file parquet sink driver. |
| `ParquetFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `ParquetFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured parquet file. |
| `ParquetHiveSinkDriver` | class | `(sink_name: 'str', partition_by: 'list[str]', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', authenticator: 'Any \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | Hive-partitioned parquet sink driver. |
| `ParquetHiveSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Split the incoming batch by partition columns and upsert each file. |
| `validate_csv_file_config` | function | `(target: 'dict[str, Any]', config: 'dict[str, Any]') -> 'None'` | Validate csv SinkConfig target/config (catalog-load time). |
| `validate_parquet_file_config` | function | `(target: 'dict[str, Any]', config: 'dict[str, Any]') -> 'None'` | Validate parquet_file SinkConfig target/config (catalog-load time). |

## `treasuryutils.datatools.sinks.drivers.csv_file`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `CsvDialect` | class | `(delimiter: 'str', decimal: 'str', encoding: 'str', header: 'bool', date_format: 'str \| None') -> None` | Resolved CSV dialect options. |
| `CsvFileSinkDriver` | class | `(sink_name: 'str', dialect: 'CsvDialect', authenticator: 'Any \| None') -> None` | Single-file CSV sink driver. |
| `CsvFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `CsvFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured CSV file. |
| `validate_csv_file_config` | function | `(target: 'dict[str, Any]', config: 'dict[str, Any]') -> 'None'` | Validate csv SinkConfig target/config (catalog-load time). |

## `treasuryutils.datatools.sinks.drivers.message`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `create_message_sink` | function | `(endpoint_url: 'str', topic_name: 'str', headers: 'dict[str, str] \| None', batch_size: 'int', *, to_camel_case: 'bool', schema_config: 'dict[str, Any] \| None', max_retries: 'int', backoff_base_s: 'float') -> 'AnyDestination'` | Create a DLT destination that pushes data to an HTTP endpoint. |
| `MessageSinkDriver` | class | `(sink_name: 'str', endpoint_url: 'str', topic_name: 'str', headers: 'dict[str, str] \| None', to_camel_case: 'bool', max_retries: 'int', backoff_base_s: 'float', authenticator: 'Any \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | HTTP message sink driver. |
| `MessageSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | POST the incoming batches to the configured HTTP endpoint. |

## `treasuryutils.datatools.sinks.drivers.parquet_file`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ParquetFileSinkDriver` | class | `(sink_name: 'str', compression: 'str', authenticator: 'Any \| None', sort_by: 'str \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | Single-file parquet sink driver. |
| `ParquetFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `ParquetFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured parquet file. |
| `validate_parquet_file_config` | function | `(target: 'dict[str, Any]', config: 'dict[str, Any]') -> 'None'` | Validate parquet_file SinkConfig target/config (catalog-load time). |

## `treasuryutils.datatools.sinks.drivers.parquet_hive`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `ParquetHiveSinkDriver` | class | `(sink_name: 'str', partition_by: 'list[str]', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', authenticator: 'Any \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | Hive-partitioned parquet sink driver. |
| `ParquetHiveSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Split the incoming batch by partition columns and upsert each file. |

## `treasuryutils.datatools.sources`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `configure_dlt_for_pipeline` | function | `(*, duplicate_cursor_warning_threshold: 'int', dlt_naming_convention: 'str') -> 'None'` | Apply treasuryutils-specific DLT runtime tweaks. |
| `create_source` | function | `(_dataset_name: 'str \| None', meta_config: 'dict[str, Any] \| None', source_config: 'dict[str, Any] \| None', overrides: 'dict[str, Any] \| None', auth_registry: 'Mapping[str, Any] \| None', *, allow_batching: 'bool', manager_ref: 'DependencyReader \| None', write_target: 'CacheWriteTarget \| None', table_name: 'str \| None', dataset_name: 'str \| None') -> 'Any'` | Factory: Creates a DLT resource based on source configuration. |
| `load_resource_class` | function | `(class_path: 'str') -> 'Any'` | Dynamically import and return a class from a string path. |
| `register_source_driver` | function | `(src_type: 'str', factory: 'SourceFactory', *, validate_config: 'SourceConfigValidator') -> 'None'` | Register a source-driver factory + its config validator. |

## `treasuryutils.datatools.targets`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `create_message_sink` | function | `(endpoint_url: 'str', topic_name: 'str', headers: 'dict[str, str] \| None', batch_size: 'int', *, to_camel_case: 'bool', schema_config: 'dict[str, Any] \| None', max_retries: 'int', backoff_base_s: 'float') -> 'AnyDestination'` | Create a DLT destination that pushes data to an HTTP endpoint. |
| `create_partitioned_upsert_parquet_sink` | function | `(sink_dir: 'str \| Path', partition_by: 'list[str]', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', batch_size: 'int', schema_config: 'dict[str, Any] \| None') -> 'AnyDestination'` | Create a destination for hive-partitioned Parquet upserts. |
| `create_sink` | function | `(sink_config: 'SinkConfig', *, authenticator: 'Any \| None') -> 'SinkDriver'` | Instantiate the registered driver for ``sink_config``. |
| `create_upsert_parquet_sink` | function | `(file_path: 'str \| Path', primary_key: 'str \| list[str] \| None', sort_by: 'str \| None', batch_size: 'int', schema_config: 'dict[str, Any] \| None') -> 'AnyDestination'` | Create a destination for high-performance, serverless Parquet upserts. |
| `export_to_parquet` | function | `(df: 'Any', path: 'str \| Path', *, overwrite: 'bool') -> 'None'` | Safely export a DataFrame to a Parquet file using the Atomic Write pattern. |
| `get_sink_validator` | function | `(type_key: 'str') -> 'SinkConfigValidator'` | Look up a registered config validator, raising on miss. |
| `is_sink_driver_registered` | function | `(type_key: 'str') -> 'bool'` | Check whether a sink type has been registered. |
| `ParquetFileSinkDriver` | class | `(sink_name: 'str', compression: 'str', authenticator: 'Any \| None', sort_by: 'str \| None', schema_enforcer: 'SchemaEnforcer \| None') -> None` | Single-file parquet sink driver. |
| `ParquetFileSinkDriver.read_target_cursor` | function | `(*, target_resolved: 'dict[str, Any]', cursor_column: 'str') -> 'Any \| None'` | Return max value of cursor_column in the target file, or None. |
| `ParquetFileSinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the configured parquet file. |
| `register_sink_driver` | function | `(type_key: 'str', *, builder: 'SinkDriverBuilder', validate_config: 'SinkConfigValidator') -> 'None'` | Register a sink-driver builder + its config validator. |
| `SinkConfigValidator` | callable | `(*args, **kwargs)` |  |
| `SinkDriver` | class | `(*args, **kwargs)` | Base sink capability: a named driver that writes Arrow batches. |
| `SinkDriver.write` | function | `(batches: 'Iterator[pa.RecordBatch]', *, target_resolved: 'dict[str, Any]', write_disposition: 'WriteDisposition', primary_key: 'str \| list[str] \| None') -> 'SinkWriteResult'` | Write Arrow batches to the target with the given disposition. |
| `SinkDriverBuilder` | callable | `(*args, **kwargs)` |  |
| `SinkDriverContext` | class | `(sink_config: 'SinkConfig', authenticator: 'Any \| None') -> None` | Everything a sink-driver builder needs. |
| `SinkResult` | class | `(sink_name: 'str', dataset_name: 'str', status: "Literal['written', 'skipped', 'failed']", write_disposition: 'WriteDisposition', duration_seconds: 'float', rows_written: 'int \| None', rows_extracted: 'int \| None', cursor_min: 'Any \| None', cursor_max: 'Any \| None', error: 'str \| None', error_type: 'str \| None', error_code: 'str \| None') -> None` | Aggregate outcome of a single dataset→sink sync. |
| `SinkWriteResult` | class | `(rows_written: 'int', duration_seconds: 'float') -> None` | Outcome of one ``SinkDriver.write`` call. |
| `WriteDisposition` | callable | `(*args, **kwargs)` |  |

## `treasuryutils.logging_config`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `configure_logging` | function | `(level: 'str \| None', *, force: 'bool') -> 'None'` | Configure structured logging for the treasuryutils library. |
| `get_logger` | function | `(name: 'str \| None') -> 'structlog.stdlib.BoundLogger'` | Return a structlog logger proxy without implicit configuration. |
| `is_logging_configured` | function | `() -> 'bool'` | Return ``True`` when structured logging is configured. |
| `redact_sensitive_fields` | function | `(logger: 'WrappedLogger', method_name: 'str', event_dict: 'EventDict') -> 'EventDict'` | Structlog processor: redact common secret-bearing fields from logs. |
| `suppress_noisy_loggers` | function | `() -> 'None'` | Strip handlers from noisy third-party loggers so they propagate to root. |
