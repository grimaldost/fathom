# YAML Contracts Reference (generated)

- treasuryutils_version: `1.8.0`
- generated_at_utc: `2026-07-10T16:08:46.035900+00:00`

This file documents the DataTools YAML dataset contract schema.

## Model Fields

### DatasetConfig

Strict data contract for a dataset (validated from YAML).

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `annex` | `treasuryutils.datatools.config.models.AnnexModel \| None` | no | None | Typed non-contract annex (description / owner / domain / sla / column-level lineage). The top-level description defaults from annex.description one-directionally (D-W1-C). Does NOT carry migrations (a top-level field, PR04). Excluded from BOTH config_fingerprint (_BEDROCK_FP_EXCLUDE) AND contract_token. |
| `cache_table_name` | `str \| None` | no | None | Optional physical table name for the local lakehouse cache. |
| `columns` | `dict[str, Any]` | no | <factory:dict> | Column schema contract (e.g. { 'id': 'int64' }). |
| `contract_version` | `str` | no | '1.0.0' | Semantic contract version (MAJOR.MINOR.PATCH). Absence ⇒ "1.0.0" — none of the 24 canonical datasets declare it. Validated by _validate_semver; excluded from config_fingerprint (additive, no cache-key bump — see _fingerprint._BEDROCK_FP_EXCLUDE). |
| `dataset_name` | `str` | yes | (required) | Unique identifier for the dataset. |
| `depends_on` | `list[str]` | no | <factory:list> | Dataset names that must be refreshed first. |
| `description` | `str \| None` | no | None |  |
| `materialize` | `Literal['materialized', 'virtual']` | no | 'materialized' | §3.6 materialization strategy (D-W1-G). The serving resolver honors it: 'virtual' routes to DatasetChainProvider (a lazy fused view composed through the upstream serving); 'materialized' (default) serves from cache. A runtime-only field: excluded from BOTH config_fingerprint (_BEDROCK_FP_EXCLUDE) AND contract_token. |
| `migrations` | `dict[str, Any] \| None` | no | None | Optional migration mappings keyed by target contract_version. The SOLE home for migration mappings (the PR05 annex does NOT carry them). Required when contract_version bumps to MAJOR ≥ 2 — see _validate_migration_mapping (§3.5). Excluded from config_fingerprint. |
| `primary_key` | `str \| list[str] \| None` | no | None | Column(s) used for deduplication/upserts. |
| `provider` | `treasuryutils.datatools.config.models.ProviderConfig \| None` | no | None | Optional serving provider override (read path). |
| `refresh_policy` | `treasuryutils.datatools.config.models.RefreshPolicy \| None` | no | None | Optional refresh policy used by UpdateCoordinator.ensure_fresh(). |
| `schema_mode` | `Optional[Literal['strict', 'permissive']]` | no | None | Schema enforcement mode override. |
| `serve_mode` | `Optional[Literal['cache', 'direct', 'auto']]` | no | None | Per-dataset serving strategy override. |
| `serving` | `treasuryutils.datatools.config.models.ServingConfig \| None` | no | None | Optional artifact materialization defaults. |
| `source` | `treasuryutils.datatools.config.models.SourceConfig \| list[treasuryutils.datatools.config.models.SourceConfig]` | yes | (required) | Source configuration(s). |
| `update_key` | `str \| None` | no | None | Cursor column for incremental fetching (e.g., 'updated_at'). |
| `write_disposition` | `Literal['merge', 'replace', 'append']` | no | 'merge' | Strategy for updating data. |

### SourceConfig

Defines the extraction strategy for a dataset.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `auth_profile` | `str \| None` | no | None | Key for the auth provider (e.g., 'msal', 'gcp-identity'). |
| `config` | `dict[str, Any]` | yes | (required) | Driver-specific configuration (e.g., 'base_url', 'params'). |
| `inputs` | `dict[str, str] \| None` | no | None | Named multi-input map for a python source (spec §2, R3): kwarg name -> upstream dataset name. When set, the python source's builder must implement MultiInputPyBuilder and is invoked as run(inputs=<map of DependencyReader>, start_date=, end_date=) instead of the single-frame PyBuilderProtocol.run(start_date=, end_date=). Every value is auto-unioned into DatasetConfig.depends_on. Additive; omitted defaults to None (the existing single-frame path, unchanged); excluded from config_fingerprint. |
| `kind` | `str \| None` | no | None | Optional sub-kind discriminator for the source slot (additive bedrock field, e.g. annotating an 'unbound' slot). Excluded from config_fingerprint so the 24 frozen datasets stay byte-identical. |
| `query` | `str \| None` | no | None | Optional SQL query to filter/transform data immediately after extraction. |
| `refresh_on_build` | `bool` | no | False | Opt-in (per dataset) to the ADR-0085 dependency content-trigger: when true, this dataset is rebuilt whenever one of its depends_on upstreams has new content (its state_token changed), not merely a newer timestamp. Default-off means no dependency cascade. A runtime-only field: excluded from BOTH config_fingerprint (_BEDROCK_FP_EXCLUDE) AND contract_token. |
| `requires` | `list[str]` | no | <factory:list> | Binding keys a consumer must supply to make this source usable — surfaced in the 'unbound' slot's SourceAccessError fix=. Additive bedrock field; excluded from config_fingerprint. |
| `type` | `str` | yes | (required) | Driver type. Must match a registered source driver — built-ins are listed in ``SourceType``; project-local drivers register additional names via ``register_source_driver(...)``. Existence is enforced at parse time by :meth:`validate_driver_config` against the runtime driver registry — unknown types raise a clear ValueError there. |

### ServingConfig

Optional serving materialization configuration.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `artifact_kind` | `Literal['auto', 'in_memory', 'arrow_mmap', 'parquet_hive']` | no | 'auto' | Preferred artifact kind for full-scan reads. |
| `force_refresh` | `bool` | no | False | If True, force artifact regeneration. |
| `memory_map` | `bool` | no | True | If True, enable memory-mapped reads when supported. |
| `partition_by` | `list[str]` | no | <factory:list> | Hive parquet partition columns (used when artifact_kind=parquet_hive). |
| `persist_artifacts` | `bool \| None` | no | None | If True, allow persisted artifacts to be created by reads. |
| `use_existing_artifacts` | `bool \| None` | no | None | If True, allow reads to use already-materialized persisted artifacts. |

### ProviderConfig

Serving provider configuration (read path only).

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `auth_profile` | `str \| None` | no | None | Optional auth profile key. |
| `config` | `dict[str, Any]` | no | <factory:dict> | Provider-specific configuration. |
| `query` | `str \| None` | no | None | Optional SQL for warehouse providers. |
| `type` | `Literal['auto', 'lakehouse', 'file', 'bigquery', 'databricks', 'python', 'dataset']` | no | 'auto' | Provider type for serving reads. |

### RefreshPolicy

Controls when a dataset should be refreshed automatically.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `max_age_seconds` | `int \| None` | no | None | Optional TTL in seconds. |
| `mode` | `Literal['if_missing', 'if_stale', 'always', 'never']` | no | 'if_missing' | Refresh mode: if_missing \| if_stale \| always \| never. |
| `stale_if_dependency_newer` | `bool` | no | True | Superseded by ADR-0085: retained unchanged for config_fingerprint stability but no longer consulted at runtime. The dependency refresh is now content-triggered via source.refresh_on_build (a timestamp-newer dependency no longer forces a rebuild). |

## Source Driver Rules

### `rest_api`

- Required config fields: `base_url, endpoint`
- Requires query: `False`
- request_headers must be dict[str, str] when provided
- request_params must be dict with string keys
- response.metadata_fields is only valid for JSON format
- params.date_param cannot be combined with params.start_param/params.end_param

### `file`

- Required config fields: `path`
- Requires query: `False`
- path must be provided in source.config

### `bigquery`

- Required config fields: `(none)`
- Requires query: `False`
- No model-level required config keys; query may be provided per source/query.

### `databricks`

- Required config fields: `warehouse_id`
- Requires query: `True`
- source.query is required for databricks sources

### `python`

- Required config fields: `class_path`
- Requires query: `False`
- class_path must resolve to an importable builder class

### `dataset`

- Required config fields: `dataset_name`
- Requires query: `False`
- dataset_name must reference an existing upstream dataset

## Known Validators

| Name | Location | Purpose |
| --- | --- | --- |
| `DatasetConfig._normalize_cache_table_name` | `treasuryutils.datatools.config.models` | Default and validate dataset_name / cache_table_name. |
| `ServingConfig._accept_aliases` | `treasuryutils.datatools.config.models` | Normalize legacy field aliases to canonical field names before validation. |
| `SourceConfig.validate_driver_config` | `treasuryutils.datatools.config.models` | Delegate driver-specific validation to the registered validator. |
| `resolve_schema_mode` | `treasuryutils.datatools.config.validation` | Resolve the effective schema mode for a dataset. |

## Baseline Templates

### `rest_api` driver

```yaml
dataset_name: external_rates
source:
  type: rest_api
  config:
    base_url: https://api.example.com
    endpoint: /v1/rates
```

Required: `['dataset_name', 'source.type', 'source.config.base_url', 'source.config.endpoint']`

Common errors:
- missing 'base_url' or 'endpoint'
- date_param combined with start_param/end_param

### `file` driver

```yaml
dataset_name: local_positions
source:
  type: file
  config:
    path: ./data/positions.parquet
```

Required: `['dataset_name', 'source.type', 'source.config.path']`

Common errors:
- missing 'path' in source.config

### `bigquery` driver

```yaml
dataset_name: warehouse_balances
source:
  type: bigquery
  query: SELECT * FROM project.dataset.table
  config:
    project: my-project
```

Required: `['dataset_name', 'source.type']`

Common errors:
- omitting query when no provider-side defaults exist

### `databricks` driver

```yaml
dataset_name: dbx_positions
source:
  type: databricks
  query: SELECT * FROM catalog.schema.table
  config:
    warehouse_id: abc123def456
```

Required: `['dataset_name', 'source.type', 'source.query', 'source.config.warehouse_id']`

Common errors:
- missing 'warehouse_id'
- missing source.query for databricks

### `python` driver

```yaml
dataset_name: custom_source_dataset
source:
  type: python
  config:
    class_path: my_package.builders.CustomBuilder
```

Required: `['dataset_name', 'source.type', 'source.config.class_path']`

Common errors:
- missing 'class_path' in source.config

### `dataset` driver

```yaml
dataset_name: downstream_enriched
source:
  type: dataset
  config:
    dataset_name: upstream_base
```

Required: `['dataset_name', 'source.type', 'source.config.dataset_name']`

Common errors:
- missing 'dataset_name' in source.config for dataset source

## Pitfalls

- 'dataset_name' and 'cache_table_name' must be snake_case (validated by TABLE_NAME_RE)
- 'databricks' source requires both 'source.config.warehouse_id' and 'source.query'
- 'params.date_param' cannot be combined with 'params.start_param' or 'params.end_param'
- 'response.metadata_fields' is only valid when response.format is 'json'
- 'params.chunk_days' must be a positive integer when provided
- 'serving' aliases are accepted but normalized to canonical field names
