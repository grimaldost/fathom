---
name: dataset-creation
description: >
  Use to author a NEW treasuryutils dataset contract — define a dataset's
  schema, source, and keys so the catalog can serve it. Triggers for: "create
  a treasuryutils dataset", "author a dataset contract", "add a new dataset to
  the catalog", "write a DatasetConfig YAML", "scaffold a dataset", "validate a
  dataset config", "DATATOOLS__CATALOG_METADATA_PATH", "register a custom
  dataset", "what columns/source/keys does a dataset need", or "my dataset
  config is invalid / won't load". Drives the deterministic dataset tooling
  (scaffold-dataset / validate-dataset) — it does not invent the schema, the
  source query, or the keys (those are the consumer's judgment). For rebinding
  an EXISTING dataset's source, use setup-source-bindings instead.
---

# Create a DataTools Dataset Contract

You are guiding a **treasuryutils consumer** — a human developer *or* an LLM
agent — through authoring a **new dataset contract**: a `DatasetConfig` that
declares the dataset's columns (the data contract), its source driver, and its
keys, so the catalog can validate and serve it. This is **creation**, distinct
from **binding** (repointing an *existing* dataset's source — that is the
`setup-source-bindings` skill).

Your job is to **orchestrate the deterministic dataset tooling** for the
mechanical structure, and reserve your reasoning for the irreducible judgment —
the columns/dtypes, the source query/`class_path`, the keys, the dependencies —
which a tool cannot invent. The scaffold supplies the shape; you fill the
semantics from the dataset's intent.

> **Golden rule: the columns ARE the data contract — never invent them.** Column
> names, dtypes, the primary key, the source query/`class_path`, and the
> dependencies come from the dataset's real schema and the user — never from a
> guess. An invented column or dtype produces a contract that silently
> misrepresents the data. If you cannot determine a value and the user has not
> given it, **ask**.

---

## The deterministic core you drive

Public API on `treasuryutils.datatools` (Python), also exposed via
`python -m treasuryutils.datatools <command>` (the `cli` extra). Prefer the CLI
for interactive authoring; reach for the Python API for the structured results.

| Step | Python API | CLI | What it does |
| --- | --- | --- | --- |
| Diagnose | `config_status()` → `ConfigStatusReport`; render with `render_config_status(report)` | `doctor` | Lists every registered dataset — confirm your new name is NOT already taken and see the catalog you're adding to. |
| Scaffold | `scaffold_dataset(*, dataset_name, source_type, path=None, overwrite=False)` → YAML text | `scaffold-dataset --name N --source-type T [--path P] [--overwrite]` | Emits a commented `DatasetConfig` skeleton for the driver — the parse-required source keys uncommented-with-placeholder, the judgment fields (`columns` / `primary_key` / `update_key` / `write_disposition` / `depends_on` / `serve_mode`) as commented prompts. |
| Validate | `validate_dataset(source, *, connect=False)` → `list[DatasetValidationResult]` | `validate-dataset <file-or-dir> [--connect]` | Static checks (every `DatasetConfig` validator + a `depends_on` resolution check against the catalog); with `--connect`, also reads a sample and checks produced columns/dtypes against the declared `columns`. Classifies failures by `error_kind` (`config` / `not_found` / `contract_mismatch` / `unknown`). Exits non-zero on any failure. |

Supported scaffold drivers: `rest_api`, `file`, `bigquery`, `databricks`,
`python`, `dataset`. These are the **only** mechanisms you use to generate and
verify a dataset config — do not describe the `DatasetConfig` schema from memory.

---

## Prerequisite

The tooling lives in the installed `treasuryutils` package. The CLI needs the
`cli` extra (typer). If `python -m treasuryutils.datatools doctor` fails with a
"requires the typer package" message, install it:

```bash
uv add 'treasuryutils[datatools,cli]' --index https://packages.stone.tech/repository/pypi-group/simple/
```

(The Python API — `from treasuryutils.datatools import scaffold_dataset, validate_dataset` — works without the `cli` extra.)

---

## Workflow

Run the steps in order. Stop and report if any step cannot proceed.

### 1. Diagnose — confirm the name is new

```bash
python -m treasuryutils.datatools doctor
```

Confirm your intended `dataset_name` is **not** already registered (creation
cannot silently overwrite a canonical dataset) and see the catalog you are adding
to. The name must be `snake_case`.

### 2. Gather the contract — WITH the user (never guessed)

This is the judgment a tool cannot do. Collect, from the user and the real data:

- **Purpose** — a one-line description of what this dataset is.
- **Source** — which driver (`file` / `bigquery` / `databricks` / `rest_api` /
  `python` / `dataset`) and its specifics: the SQL `query` + warehouse/project,
  the file `path`, the REST `base_url`/`endpoint`, the builder `class_path`, or
  the upstream `dataset_name`.
- **The columns** — the column→dtype schema. This **is** the data contract.
  Read it from the source's real schema; never invent column names or dtypes.
  Recognized dtype tokens (case-insensitive): `date`, `datetime` / `timestamp`,
  `timestamptz` / `timestamp_tz` (tz-aware, UTC), `time`, `duration`, `bool`,
  `int8`/`int16`/`int32`/`int64` (also `int`/`integer`/`bigint`),
  `float32`/`float64` (also `float`/`double`/`numeric`/`decimal`),
  `string` (also `str`/`text`/`varchar`), `categorical`, `json`. A column may be a
  plain string (`rate: double`) or a mapping (`rate: {data_type: double, nullable:
  false}`). `validate-dataset` REJECTS an unrecognized dtype (it would otherwise be
  silently coerced to String). **Timezones:** `datetime`/`timestamp` are tz-NAIVE
  (a wall clock); use `timestamptz`/`timestamp_tz` when the column is a true UTC
  instant, so the served Polars dtype carries the zone and tz-aware comparisons do
  not raise.
- **Keys** — `primary_key` (for dedup/upsert) and `update_key` (the incremental
  cursor, if any).
- **Dependencies** — `depends_on` datasets that must refresh first.

### 3. Scaffold the structure

```bash
# Print to review:
python -m treasuryutils.datatools scaffold-dataset --name cdi_intraday --source-type bigquery
# Or write the skeleton straight to a file (recommended — see note):
python -m treasuryutils.datatools scaffold-dataset --name cdi_intraday --source-type file --path ./cdi_intraday.yaml
```

The skeleton's required source keys are uncommented-with-placeholder (it already
validates structurally); the judgment fields are commented prompts. It is a safe
no-op until you fill it in.

> **Prefer `--path` over `> file.yaml`.** `--path` writes the skeleton cleanly and
> refuses to clobber an existing file without `--overwrite` (a shell redirect has no
> such guard). Library logs go to stderr, so a `> file.yaml` redirect of the print
> form is not polluted by log lines — but `--path` is still the safer, explicit form.

### 4. Fill the judgment fields

Replace the placeholder source values with the real connection details, and
uncomment + fill the judgment fields from step 2: the `columns` contract, the
keys, `write_disposition` (`merge` default / `replace` / `append`), `depends_on`,
and `serve_mode`. **Do not guess** a column, dtype, query, or key.

### 5. Validate — `validate-dataset` (then `--connect` if reachable)

```bash
python -m treasuryutils.datatools validate-dataset ./my_dataset.yaml
python -m treasuryutils.datatools validate-dataset ./my_dataset.yaml --connect
```

Branch on the `error_kind` (read the structured result, never a prose summary):

- **`config`** — the YAML violates the `DatasetConfig` schema or a source-driver
  validator (bad identifier, missing required source key, bad semver). Fix and
  re-run.
- **`not_found`** — a `depends_on` name is neither registered in the catalog nor
  present in the same validate batch. Register the dependency first, **or** include
  the sibling dataset(s) in the same file/directory and validate them together
  (co-authored siblings resolve each other). Note: a `dataset`-type source's
  upstream (`source.config.dataset_name`) is checked for non-emptiness but not for
  catalog existence — a derived dataset reading from a not-yet-registered upstream
  validates clean (it mirrors the runtime graph, which only follows `depends_on`).
- **`contract_mismatch`** (connect only) — the sample read produced columns/dtypes
  that do not match your declared `columns`. Fix the source projection or the
  declared contract so they agree.
- **`unknown`** (connect only) — the source could not be read (not bound /
  unreachable). Connect pre-flight needs a reachable source; for a not-yet-bound
  dataset, rely on static validation and verify connectivity after registering +
  binding it.

`validate-dataset` exits non-zero on any failure, so it is safe to gate on.

> **`file`-driver connect caveats.** `--connect` reads the dataset through the
> REGISTERED catalog (not the YAML's own `path`), so a brand-new `file` dataset
> fails `--connect` with `error_kind='unknown'` until you register it (step 6) —
> static validation is enough to author it; connect-verify after registering. Also,
> `file` paths are sandboxed under `BASE_DATA_PATH`: a path outside it needs
> `allow_outside_base: true` in the source `config` (the read error names this fix).

### 6. Register + confirm

Drop the finished YAML under your `DATATOOLS__CATALOG_METADATA_PATH` (default
`./metadata`), then:

```bash
python -m treasuryutils.datatools doctor
```

The new dataset should now appear registered. If its source points at infra you
do not control, follow up with the `setup-source-bindings` skill to rebind it.

---

## Guardrails

- **Orchestrate, don't reimplement.** Use `scaffold-dataset` and `validate-dataset`
  for every mechanical step; never hand-derive the `DatasetConfig` schema or the
  per-driver required keys from memory — the tooling is the source of truth for the
  installed version.
- **The columns are the contract — never invent them.** Read column names and
  dtypes from the source's real schema. The same holds for the source query /
  `class_path`, `primary_key`, and `depends_on`.
- **Creation is not binding.** A new dataset declares a contract + source from
  scratch (this skill). Repointing an *existing* dataset's source without changing
  its contract is a **binding** — use `setup-source-bindings`. A binding cannot
  create a dataset; creation cannot silently overwrite a canonical one.
- **Validate before registering.** Only drop a YAML into the metadata path after
  `validate-dataset` passes (read `error_kind`). Use `--connect` once the source is
  reachable to confirm the declared columns match what the source produces.
- **Verify by re-reading the result fields.** Branch on `r.ok` / `r.error_kind` /
  `r.unresolved_dependencies` — never treat a printed summary as the pass signal.

---

## Fallback Rules

- If `python -m treasuryutils.datatools scaffold-dataset` fails because the CLI is
  unavailable, install the `cli` extra (see Prerequisite) or drive the Python API
  (`scaffold_dataset` / `validate_dataset`).
- If `scaffold-dataset` reports an unknown driver, use one of the supported types
  (`rest_api` / `file` / `bigquery` / `databricks` / `python` / `dataset`); a
  custom driver registered in your project is authored by hand (the scaffold covers
  the built-ins).
- If `treasuryutils` is not installed at all, stop and provide the install command.
- To rebind an existing dataset, or to read one once created, route to the
  `setup-source-bindings` and `treasuryutils-usage` skills respectively.
