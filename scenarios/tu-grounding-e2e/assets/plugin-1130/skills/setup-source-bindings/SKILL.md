---
name: setup-source-bindings
description: >
  Use to set up treasuryutils data sources, configure source bindings, or
  rebind a dataset source so a consumer can read it with their own
  credentials. Triggers for: "set up treasuryutils data sources", "configure
  source bindings", "rebind a dataset source", "treasuryutils access denied /
  can't reach the Stone source", "SourceAccessError", "scaffold
  source_bindings.yaml", "what env vars does treasuryutils need",
  "DATATOOLS__SOURCE_BINDINGS_PATH", "bind a source programmatically /
  catalog.bind_source", or "use treasuryutils in a stateless / serverless
  container (AWS Lambda, Cloud Function, Cloud Run) — serve_mode direct,
  ParquetUpsert". Drives the deterministic DataTools bindings tooling
  (doctor / scaffold-bindings / validate-bindings) and the public binding
  primitives — it does not reimplement that logic.
---

# Set Up DataTools Source Bindings

You are guiding a **treasuryutils consumer** — a human developer *or* an LLM
agent — through making the library's required source configuration
**discoverable** and bootstrapping the artifacts. treasuryutils ships datasets
whose default sources point at Stone infrastructure (BigQuery, Databricks). A
consumer running against their *own* warehouse must **rebind** those primitive
datasets to sources they can reach — without forking the frozen data contract.

Your job is to **orchestrate the deterministic bindings tooling**, not to
hand-author YAML or re-derive which datasets need rebinding. Every mechanical
step below delegates to a real function or CLI command. Reserve your own
reasoning for **consent, inference, and interaction** — the parts a
deterministic tool cannot do.

> **Golden rule:** Never invent dataset names, columns, primary keys,
> credentials, project IDs, warehouse IDs, or file paths. Read them from the
> tooling output (for the contract side) or from the user / their repo (for the
> connection side). If you cannot infer a value and the user has not given it,
> **ask** — do not guess.

---

## The deterministic core you drive

All of these are public API on `treasuryutils.datatools` (Python) and are also
exposed as a CLI via `python -m treasuryutils.datatools <command>`. Prefer the
CLI for an interactive setup; reach for the Python API when you need the
structured result objects.

| Step | Python API | CLI | What it does |
| --- | --- | --- | --- |
| Diagnose | `config_status()` → `ConfigStatusReport`; render with `render_config_status(report)` | `doctor` | Reports the configured paths + `serve_mode`, and per-dataset: primitive vs derived, bound vs unbound, and whether the default source uses a proprietary driver (`bigquery`/`databricks`) — the signal for a primitive you may want to rebind to a non-default source you control. |
| Scaffold | `scaffold_bindings(*, path=None, drivers=None, overwrite=False)` → YAML text | `scaffold-bindings [--path P] [--driver D ...] [--overwrite]` | Emits a fully-commented `source_bindings.yaml` skeleton — one stanza per primitive, each annotated with the dataset's required columns + primary key. |
| Validate | `validate_bindings(*, path=None, connect=False)` → `list[BindingValidationResult]` | `validate-bindings [--path P] [--connect]` | Static checks (target exists, is a primitive, structurally valid `SourceBinding`); with `--connect`, also reads a small sample through each rebound source and asserts the produced columns/dtypes satisfy the frozen contract. Exits non-zero on any failure. |

These are the **only** mechanisms you use to inspect, generate, and verify
bindings. Do not parse the catalog yourself or describe the bindings schema from
memory — let `doctor` and `scaffold-bindings` tell you the truth for the
installed version.

---

## Prerequisite

The tooling lives in the installed `treasuryutils` package. The CLI needs the
`cli` extra (typer). If `python -m treasuryutils.datatools doctor` fails with a
"requires the typer package" message, install it first:

```bash
uv add 'treasuryutils[datatools,cli]' --index https://packages.stone.tech/repository/pypi-group/simple/
```

(If you only have the Python API, `from treasuryutils.datatools import config_status, scaffold_bindings, validate_bindings` works without the `cli` extra.)

---

## Workflow

Run the steps in order. Stop and report if any step cannot proceed.

### 1. Diagnose — run `doctor`

```bash
python -m treasuryutils.datatools doctor
```

Read the report to the user. It tells you three things you need:

- **The configured paths and serving mode** — `source_bindings_path` (default
  `./source_bindings.yaml`), `serve_mode` (default `cache`),
  `catalog_metadata_path`, and `sink_metadata_path` (optional consumer
  egress-sink dir; disabled by default).
- **Which datasets are still on Stone defaults vs. on a consumer binding** —
  the `bound` / `unbound` column.
- **Which primitives are candidates for rebinding** — rows flagged
  `PROPRIETARY-DRIVER (rebind likely required)` use a `bigquery`/`databricks`
  default; rebind one when you intend to read it from a non-default source you
  control (the Stone defaults are reachable for internal consumers — credentials
  and permissions govern access). **Derived** datasets
  (`inherits binding from upstream`) are *not* rebound directly — rebind their
  upstream primitive instead.

Identify the set of primitives the user actually needs for their work. They do
not have to rebind every primitive — only the ones their code reads (directly,
or as an upstream of a derived dataset they read).

### 2. Infer from the repo — only with explicit consent

A consumer's project very often already encodes the connection details you
need. **Ask the user before scanning their repository.** For example:

> "I can scan this repo for existing source configuration — dbt
> `profiles.yml`, `.env` files, Airflow connections, settings modules — to
> pre-fill warehouse/project values and save you typing. Want me to look?"

If (and only if) they consent, search for and read:

- **dbt** — `profiles.yml`, `dbt_project.yml` (BigQuery project, dataset,
  Databricks host/http_path/warehouse).
- **`.env` / `.env.*` / `env_vars` docs** — existing connection env vars,
  including any `DATATOOLS__*` already set.
- **Airflow** — connection definitions / `airflow_connections` exports
  (BigQuery, Databricks conn extras).
- **Config modules** — `settings.py`, `config.py`, `pydantic-settings`
  models, or a `*.toml` that names a warehouse / project / catalog.

Treat anything you find as a **candidate** to confirm, never as final. Surface
exactly what you inferred and from which file, so the user can correct it.

> **Never read or echo secret *values*.** Reference secrets by env-var name and
> keep them as `${VAR}` placeholders in the YAML (see step 4). Do not paste a
> token, password, or key into the bindings file or your reply.

### 3. Scaffold the skeleton

Generate a `source_bindings.yaml` skeleton for the primitives that need
rebinding. Restrict to the relevant drivers with repeatable `--driver` flags so
the skeleton stays focused on what the user must fill in:

```bash
# Print the skeleton for just the proprietary-driver primitives, to review first
python -m treasuryutils.datatools scaffold-bindings --driver bigquery --driver databricks
```

Each emitted stanza is **fully commented** and carries the dataset's required
output columns and primary key, e.g.:

```yaml
  # --- cdi_daily (bigquery) ---
  #   required columns: ref_date, rate, factor, year
  #   primary key: ref_date
  # cdi_daily:
  #   source:
  #     type: bigquery
  #     query: SELECT ref_date, rate, factor, year FROM `your-project.your_dataset.your_table`
  #     config:
  #       project_id: your-project
```

The skeleton is a no-op until a consumer uncomments and fills a stanza, so it is
safe to write. A binding overrides only **source / provider / auth_profile** —
never contract fields (`columns`, `primary_key`); those stay single-sourced in
the canonical metadata.

### 4. Interact — fill what cannot be inferred

For each primitive to rebind, you now compose the concrete binding. You have the
**contract side** for free (the required columns + primary key are in the
scaffold comments and the `doctor` output). You must obtain the **connection
side** from the user (or from step 2's confirmed inferences):

- `bigquery` → project ID, dataset, table, and the `SELECT` projection (it
  **must** emit every required column).
- `databricks` → warehouse ID, catalog/schema/table, and the projection.
- `file` → the local/remote path and format. `file` paths are sandboxed under
  `BASE_DATA_PATH`: a path outside it needs `allow_outside_base: true` in the
  source `config` (the read error names this fix). A relative `path:` resolves
  under `BASE_DATA_PATH`; when it is unset, the default resolves to a root that
  produces a misleading "no files found" error — set `BASE_DATA_PATH` explicitly
  for offline/self-hosted `file` bindings.
- any other driver → the driver-specific connection details.

Ask for each missing value explicitly. Use env placeholders — `${MY_VAR}` or
`${MY_VAR:-default}` — for anything environment-specific or secret, so the file
is safe to commit and portable across environments. **Do not guess** a project
ID, warehouse, credential, or path: an unconfirmed value produces a binding that
silently reads the wrong data or fails at connect time.

### 5. Write the artifacts

Write the filled `source_bindings.yaml`. By default the library resolves it at
`./source_bindings.yaml` (relative to the working directory). Either:

- write to the default path and let the library pick it up, **or**
- write elsewhere and tell the user to point the config at it via the
  `DATATOOLS__SOURCE_BINDINGS_PATH` environment variable.

If you collected secrets as `${VAR}` placeholders, also produce or update a
`.env` skeleton listing those variable **names** (no values) so the user knows
what to set. Relevant config env vars to mention:

| Env var | Controls |
| --- | --- |
| `DATATOOLS__SOURCE_BINDINGS_PATH` | Location of the bindings file (default `./source_bindings.yaml`). |
| `DATATOOLS__SERVE_MODE` | Default serving strategy: `cache` (default) / `direct` / `auto`. |
| `DATATOOLS__CATALOG_METADATA_PATH` | Optional consumer dataset metadata path (default `./metadata`). |
| `DATATOOLS__SINK_METADATA_PATH` | Optional consumer egress-sink metadata dir — register sinks for existing datasets from your own dir (disabled by default). |
| `BASE_DATA_PATH` | Root for `file`-source relative paths (sandbox); set it for offline/self-hosted `file` bindings. |

You may write the skeleton via the CLI directly:

```bash
python -m treasuryutils.datatools scaffold-bindings --path ./source_bindings.yaml --driver bigquery
# then edit in the connection details and uncomment the stanzas you need
```

(`scaffold-bindings` refuses to clobber an existing file unless you pass
`--overwrite`.)

### 6. Verify — `validate-bindings --connect` then `doctor`

Confirm the rebound sources satisfy each dataset's frozen contract:

```bash
python -m treasuryutils.datatools validate-bindings --connect
python -m treasuryutils.datatools doctor
```

- **Static failures** (unknown dataset, target is derived, structurally invalid
  binding) mean the YAML itself is wrong — fix it and re-run.
- **Connect failures** mean the bound source could not be read or its sample did
  not satisfy the contract (missing column, or a dtype-family mismatch). Adjust
  the source query/projection or credentials and re-run.
- The follow-up `doctor` should now show the rebound datasets as **bound**.

`validate-bindings` exits non-zero if any entry fails, so it is safe to gate on
in a script.

> **Upgrading to v1.1:** clear the lakehouse cache once before re-verifying — source
> column names are now authoritative (DLT snake_case normalization removed), so a cache
> written by an older version is stale until cleared. Delete the cache root
> (`DATATOOLS__DATA_CACHE_DIR`, or the default `<user-data-dir>/lakehouse`). See
> `docs/migration/v1.1.0.md`.

### 7. Report status + next steps

Summarize for the user:

- Which primitives are now **bound**, and which intentionally remain on Stone
  defaults.
- The verification result (static + connect).
- **`serve_mode` choice.** Source rebinding pairs with `serve_mode='direct'`,
  the **remote-execution tier** that reads live from the (rebound) source on
  every call with no local lakehouse — set it per call
  (`DatasetClient(..., serve_mode='direct')` / `handle(serve_mode='direct')`),
  per dataset (a `serve_mode:` key in the contract), or globally
  (`DATATOOLS__SERVE_MODE`). The default `cache` mode builds and serves a local
  copy instead; **derived datasets must stay on `cache`** (their source *is* the
  cache). See `docs/datatools/serving.md`.
- **If a bound source is still inaccessible at read time** (expired token,
  missing permission, table not found), a `direct`-mode read raises a
  `SourceAccessError` (`treasuryutils.datatools.exceptions`) carrying a
  copy-pasteable **rebind recipe** — the dataset's required columns and primary
  key included — instead of a raw cloud-SDK traceback. Treat that recipe as the
  next iteration of this same workflow: re-bind to a reachable source and
  re-run step 6.

---

## Programmatic & stateless / serverless deployment

The file + CLI workflow above is for **interactive setup**. A consumer deploying
treasuryutils into a **stateless / serverless** runtime (AWS Lambda, Cloud
Functions, Cloud Run, an ephemeral job) usually cannot ship or edit a
`source_bindings.yaml` on disk and has **no durable DuckDB cache**. The same
binding contract is available through public primitives — point at them; do not
hand-roll the binding or the read. Every binding rule above still holds.

### Bind from the environment at cold start

`catalog.bind_source(...)` is the programmatic equivalent of one
`source_bindings.yaml` entry, applied immediately and before the first read —
use it to bind from env/secrets at startup, with no file on disk:

```python
import os
from treasuryutils.datatools import catalog

catalog.bind_source(
    'cdi_daily',
    source={'type': 'file', 'config': {'path': os.environ['CDI_PARQUET_URI']}},
)
```

It rebinds an existing **primitive** only, changes only `source` / `provider` /
`auth_profile` (never contract fields), and re-validates the merged config. The
**never-guess** and **secrets-as-`${VAR}`** guardrails hold — read connection
values from the environment, never from assumptions.

### Serve `direct` — no local cache

A stateless container has no persistent lakehouse, so set
`DATATOOLS__SERVE_MODE=direct` (or `DatasetClient(..., serve_mode='direct')`).
`direct` reads live from the bound source on every call and sidesteps the
single-writer DuckDB lock. If anything still needs to cache, point
`DATATOOLS__DATA_CACHE_DIR` at the only writable path (e.g. `/tmp` on Lambda).
`DatasetClient` is the canonical read class; `DatasetManager` remains a
back-compat alias.

```python
from treasuryutils.datatools import DatasetClient

df = DatasetClient('cdi_daily').get()   # reads straight from the bound source
```

**BigQuery direct + auth (headless/CI).** A `bigquery` `direct` read resolves credentials
through the configured authenticator (the `gcp-identity` / `GoogleAuthenticator` profile)
via the `GoogleCredentialsProvider` protocol — an authenticator that cannot supply BigQuery
credentials now fails loud (`TypeError`) instead of silently falling back to ADC. In a
headless/CI runtime set `allow_interactive=False` on the profile so an un-ADC'd environment
fails fast rather than blocking on a browser prompt; or omit the authenticator to use ADC
explicitly. `bigquery` / `databricks` `direct` reads bind `@start_date` / `@end_date` /
`@cursor` (`:`-style for Databricks) query parameters from `source.config.params`.

### One-shot materialization without DuckDB

For an extract-and-write job (land Parquet to `/tmp`, then ship to object
storage), `ParquetUpsert(dataset, sink_file_path).run_upsert()` does an atomic,
incremental upsert using the Parquet file itself as the high-watermark — no
DuckDB required. The dataset must resolve to `serve_mode: direct`.

```python
from treasuryutils.datatools import ParquetUpsert

ParquetUpsert('cdi_daily', sink_file_path='/tmp/cdi_daily.parquet').run_upsert()
```

**Verify at build/CI time, not in the hot path.** A container cannot run an
interactive `doctor`. Run `validate-bindings --connect` (or
`validate_bindings(connect=True)`) in CI or the image build against the
deployment's bindings, so a broken contract fails the pipeline rather than
production. See `docs/datatools/source_bindings.md` and
`docs/datatools/serving.md`.

---

## Guardrails

- **Orchestrate, don't reimplement.** Use `doctor`, `scaffold-bindings`, and
  `validate-bindings` for every mechanical step. Never hand-derive the list of
  primitives, the required columns, or the binding schema from memory — the
  tooling is the source of truth for the installed version.
- **Consent before scanning.** Do not read the user's repository for inference
  until they explicitly agree (step 2).
- **Never guess connection details.** Project IDs, warehouses, catalogs,
  credentials, and file paths come from the user or confirmed repo inference —
  not from assumptions.
- **Secrets stay as placeholders.** Use `${VAR}` / `${VAR:-default}`; never read
  back or write secret values. List secret env-var *names* in a `.env`
  skeleton.
- **Bindings rebind existing primitives only.** A binding cannot create a new
  dataset, cannot target a derived dataset, and cannot change contract fields
  (`columns`, `primary_key`). It changes only `source` / `provider` /
  `auth_profile`. If the user needs a brand-new dataset, that is dataset
  authoring via `DATATOOLS__CATALOG_METADATA_PATH`, not a binding — use the
  `dataset-creation` skill. Likewise, to register an
  egress **sink** on an existing dataset from your own metadata dir, use
  `DATATOOLS__SINK_METADATA_PATH` (not a binding).
- **Programmatic = same contract safety.** `catalog.bind_source(...)` and
  `ParquetUpsert` obey every rule above — rebind primitives only, never change
  contract fields, never guess, secrets via env placeholders. In stateless
  deployments, verify bindings in CI / the image build, not at runtime.
- **Verify before claiming success.** Only report a dataset as set up after
  `validate-bindings --connect` passes for it and `doctor` shows it `bound`.

---

## Fallback Rules

- If `python -m treasuryutils.datatools doctor` fails because the CLI is
  unavailable, install the `cli` extra (see Prerequisite) or drive the Python
  API (`config_status` / `render_config_status`) instead.
- If `treasuryutils` is not installed at all, stop and provide the install
  command from the Prerequisite section.
- If `doctor` shows **no datasets**, the catalog did not load — check
  `DATATOOLS__CATALOG_METADATA_PATH` and that the install includes the
  `datatools` extra.
- For broader treasuryutils usage (which module to call, how to read a dataset
  once it is bound), route to the `treasuryutils-usage` skill.
