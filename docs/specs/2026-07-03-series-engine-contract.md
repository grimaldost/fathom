# Series-engine contract — producer (engine) × consumer (fathom)

> Draft 2026-07-03; updated 2026-07-03 when the binding landed. Defines the **engine-agnostic**
> interface that fathom's `series` arm drives, so any governed multi-PR engine implementing it can
> be run and scored as an eval arm. Doubles as the functional spec for a from-scratch (open-source)
> engine.
>
> Source of truth for the *as-built* consumer: `src/fathom/strategies/series.py`. The reference
> **producer** is **convoy** (`convoy run <series.toml>`); its own format docs are convoy's
> `docs/design/02-formats.md`. No engine name appears in fathom's `src/` — the engine binary is
> named entirely in the scenario (`[tools].repo` + the resolved invocation command).

## 1. Roles and boundary

fathom scores AI coding tools by running a task across **arms** (execution strategies) and
comparing results **blind** to which arm produced them. A **series engine** is one arm class: a
tool that decomposes a task into a sequence of PRs and drives an agent CLI to implement, review,
and integrate them under governance (budgets, gates, permission modes).

The engine is a **black-box subprocess**. fathom never imports it; it invokes the engine CLI and
reads back exactly two things: an **exit code** and a **telemetry file**. Everything the
comparison needs — per-spawn economy, failure kind, the final workspace state — crosses that
boundary as files and process results, not as an API.

```
                  series.toml (regenerated, pinned)
                  env: isolated CLAUDE_CONFIG_DIR
                  cwd: trial workspace (repo under test)
   fathom   ─────────────────────────────────────────────▶   engine CLI:  <cmd> run <series.toml>
   series                                                         │
   executor                                                       │ spawns agent CLI per PR
      ▲                                                           │ (impl → review → fix),
      │   exit code                                               │ runs gates, integrates
      │   spawns.jsonl  (per-spawn telemetry)   ◀────────────────┘ branches
      │   final integrated working tree
      ▼
   blind verifier  +  economy join  →  ledger  →  scorecard
```

The contract is deliberately narrow: implement §2–§7 and fathom can drive and score the engine
without knowing anything else about it. convoy is the first conforming implementation.

## 2. Invocation

fathom forms `<invocation> run <abs-path-to-series.toml>` and runs it as a subprocess.

| Aspect | Requirement |
|---|---|
| Command | A `run <series.toml>` subcommand. The invocation prefix is **scenario-supplied** (e.g. `uv run --project <repo> convoy`), never a bare PATH lookup. |
| `cwd` | The trial workspace — the repository under test. The engine operates here. |
| `env` | Carries an isolated `CLAUDE_CONFIG_DIR` (credential-only, ADR-0004) and is stripped of API-routing vars. **The engine must honor this env when it spawns its agent CLI** — no re-injecting keys, no rerouting to another endpoint. |
| Exit code | `0` integrated · `1` blocked (a blocking gate stayed red — a task failure) · `2` infrastructure (auth/usage-limit/retry — halt cleanly) · `3` usage (a malformed series.toml) · `4` budget (a spawn hit its per-spawn budget cap; partial work left un-integrated). Classified per §7. |
| Process tree | The engine and every agent CLI it spawns must die when the process tree is killed — fathom enforces a wall-clock timeout by killing the group. No orphaned grandchildren. |
| stdout / stderr | Free-form logs. fathom reads them only as an infrastructure-signature backstop (§7). |

*Consumed by:* `EngineRunner` protocol + `_default_run_engine` (series.py); invocation built at
cli.py `_DefaultResolver.build_tool_invocation_cmd`; `tool_invocation_cmd` scenario field
(scenario.py).

## 3. Input — the series spec (`series.toml`)

The task bank commits a **template**; fathom **regenerates** it before each trial — rewriting
`[paths]` to absolute, pinning `[governance]` from the resolved scenario, and stripping per-PR
overrides (§6). So the engine's parser must round-trip a spec that fathom wrote, not only a
hand-authored one. Keep the schema to plain TOML value types (scalars, arrays, tables,
arrays-of-tables) — fathom's regenerator (`dump_toml`, series.py) handles exactly those.

| Section | Fields | Meaning | Set by |
|---|---|---|---|
| `[series]` | `id`, `version` | Series identity | bank |
| `[branches]` | `base`, `integration` | Git: fixture staged on `base`; integrated result on `integration` | bank |
| `[paths]` | `prompts` (dir), `outputs` (dir) | Asset locations. **Must accept absolute paths** so assets live outside the scored workspace | fathom rewrites |
| `[governance]` | `model`/`tier`, `effort`, `permission_mode`, `timeout_seconds` | Per-spawn governance | fathom pins |
| `[governance.budgets]` | `implementation`, `review`, `fix` | USD ceiling per phase — **TOML numbers, not strings** | fathom pins |
| `[governance.tools]` | `implementation`, `review`, `fix` | Tool allow-list per phase (arrays of strings) | bank (or fathom) |
| `[review]` | `blocking`, `max_fix_attempts` | Review gate + bounded fix loop | bank |
| `[[checks]]` | `name`, `run`, `blocking`, `independent` | Shell checks (tests/lint); a blocking failure stops the phase | bank |
| `[[prs]]` | `id`, `branch`, `prompt`, `phase` (string), `depends_on` | The PR decomposition as a DAG | bank |

## 4. Runtime behavior

Given a spec, the engine must:

1. **Stage** — start from `[branches].base` (fathom has staged the fixture there).
2. **Decompose & order** — walk `[[prs]]` as a DAG (`phase` groups, `depends_on` edges).
3. **Implement each PR** — spawn the agent CLI against the PR's `prompt`, on the PR's `branch`,
   under the pinned `[governance]` model / effort / permission / budget / tools.
4. **Review** (when `[review].blocking`) — on a blocking red, run up to `max_fix_attempts` fix
   spawns, re-gating after each.
5. **Gate** — run `[[checks]]`; a blocking check that fails must block, never be silently skipped.
6. **Integrate** — merge / stack PR branches onto `[branches].integration`.
7. **Leave the integration branch checked out at exit** — that tree, carrying every PR's merged
   work, is what the blind verifier scores.

The review/fix loop (4), the DAG (2), and multi-branch stacking (6) are the "governed" part —
§8 says what an MVP can defer.

## 5. Output — telemetry (`spawns.jsonl`)

An **append-only JSON-lines** file (path derivable from `[paths].outputs`). This is fathom's only
source for the **economy axis**, so it is the highest-fidelity part of the contract. Every line
carries `schema_version` and an `event` tag; a consumer keys on both and ignores unknown fields.

| Event | Required fields | Role |
|---|---|---|
| `run_start` (once) | `schema_version`, `event`, `run_id`, `series_id` | groups one invocation's events |
| `spawn_complete` (one per spawn) | `schema_version`, `event`, `run_id`, `pr_id`, `role` (`implementation` / `review` / `fix`), `exit_code`, `input_tokens`, `output_tokens`, `num_turns`, `duration_s`, `cost_usd`, `effective_model` | fathom materializes **one economy record per event** |
| `run_complete` (once) | `schema_version`, `event`, `run_id`, `outcome` (`completed` / `blocked` / `infrastructure` / `budget`), `integrated` | the engine's own terminal verdict |

Cross-cutting:

- **`run_id`** — a lexicographically-sortable stamp (`%Y%m%dT%H%M%SZ` + short suffix) grouping one
  invocation's spawns. fathom selects the most-recent run id not present before the invocation, so
  a reused outputs dir is safe.
- **`cost_usd` fallback** — when the provider reports `0.0` under subscription auth, the engine
  substitutes a token×price estimate and sets `cost_estimated: true` on that line, so a consumer
  never silently reads a real run as free. (This is why fathom's series arm needs no cost fallback
  of its own — the engine already did it; cf. the resolved D2.)
- **Hard requirement — per-spawn granularity.** Tokens / turns / duration / cost must be reported
  *per spawn*, not just as a run total. A total-only engine cannot be economy-joined and is
  useless to fathom's headline verdict.
- **Versioning discipline** — `schema_version` is present from day one; evolution is additive (a
  new optional field bumps nothing, a rename/retype bumps the version).

*Consumed by:* `_read_events`, `_event_to_record`, `_materialize_runs`, `_final_run_outcome`
(series.py).

## 6. Configuration & parity

Cross-arm comparison only means something if arms differ *only* in strategy. So the engine must
let fathom **override** these, and must never force its own:

| Knob | Requirement | Why it matters |
|---|---|---|
| `permission_mode` | Overridable; support `default` / `acceptEdits` / `plan` / `bypassPermissions`. Governance resolution **never defaults to `bypassPermissions`** | An arm that auto-approves everything is not comparable to a default-deny arm |
| model / effort | Pinned per phase from the scenario; **per-PR overrides rejected** at spec-load (`model`, `tier`, `effort`, `budget`) | Otherwise the arm silently uses a stronger model per PR — measuring *models*, not *strategy* |
| per-spawn budgets | Pinned, recorded (as TOML numbers) | Bounds cost; an explicit recorded choice, not an engine default |
| parallelism | Off (sequential) | Determinism + clean per-spawn attribution |
| asset / output paths | Relocatable outside `cwd` via absolute path | Engine assets must not land in the scored workspace — the verifier would fingerprint the arm and break blindness |

*Consumed by:* `_PER_PR_PINS`, `NON_BYPASS_PERMISSION_MODE`, pinned budgets (series.py). convoy
also enforces the per-PR parity guard itself (`spec.py` rejects the forbidden keys), so fathom's
stripping is belt-and-braces.

## 7. Failure classification

fathom must tell **infrastructure** failure (auth expired, subscription usage-limit, transient
retry exhausted) apart from **task** failure (the agent tried and produced a wrong result). The
engine surfaces the difference explicitly, so a bare nonzero exit is never blindly scored:

- **Infra signals** — exit code `2` and a `run_complete` `outcome = "infrastructure"`; plus an
  auth/usage-limit signature on the engine's own stdout/stderr as a backstop (matching the
  single-spawn adapter's `_spawn_is_infrastructure`).
- **Task failure** — exit `1` (a blocking gate stayed red) is scored; exit `3` (a malformed
  series.toml) is fathom's own bug, surfaced loudly, never scored as the task.
- **Budget truncation** — exit `4` and a `run_complete` `outcome = "budget"`: a spawn hit its
  per-spawn budget cap and the engine left the partial work **un-integrated**. This is a
  governance halt, not a task result, so fathom records the trial `errored` (excluded from the
  pass rate — the report counts only `completed`) rather than scoring truncated work as a
  failure. Unlike infrastructure it does **not** halt the whole matrix — a per-spawn cap is
  trial-specific; the cell is re-runnable after raising `--max-budget-usd`.
- **Effect** — infra halts the matrix **cleanly** (re-runnable later, ADR-0002 resume); task
  failure is **scored**; a budget truncation is recorded non-scored and re-runnable.

*Consumed by:* `_classify` (series.py), shared with the single-spawn adapter's
`_spawn_is_infrastructure`.

## 8. Minimum viable engine

The smallest engine fathom can drive and score:

> CLI `run <series.toml>` · PRs run **sequentially** (ignore the DAG; honor list order) · one
> **implementation** spawn per PR (no review/fix) · one blocking **quality gate** (the test
> command) · `spawns.jsonl` emitting `spawn_complete` with per-spawn cost/tokens/turns · correct
> **exit code** · the `[governance]` and `[paths]` overrides from §6.

Deferrable without breaking fathom: the review/fix loop, the `depends_on` DAG, multi-branch
stacking, parallelism, per-PR model routing.

Get right early: **§5 per-spawn telemetry** and **§6 overridability**. Those are the two that,
if wrong, *silently corrupt the comparison* rather than fail loudly.

## 9. fathom's side — done

The consumer side is implemented and gate-green:

- The strategy is `series` (`KNOWN_STRATEGIES`, the cli dispatch, the scenario `strategy` field,
  the smoke arm). No engine name in `src/` — the binary lives in the scenario.
- `src/fathom/strategies/series.py` regenerates convoy-schema `series.toml` (§3) and parses
  convoy's `spawns.jsonl` (§5), preserving the `RunRecord` economy contract byte-for-byte.
- The `smoke` engine-boundary (§11) drives **real convoy** with a token-free `claude` shim and
  asserts the pinned non-bypass permission mode reaches the spawn.
- The scenario `scenarios/series.toml` points `[tools].repo` at the convoy repo.

Any conforming engine is drop-in: point a scenario's `[tools].repo` + invocation at it.

## 10. Decisions (resolved)

1. **Telemetry format** — `spawns.jsonl` (append-only JSONL) with a `schema_version` on every
   line. **Resolved: versioned from day one.**
2. **Field naming** — the engine owns its names (`spawn_complete`, `role`, `input_tokens`, …);
   fathom's parser adopts them. **Resolved: convoy's versioned names are canonical; fathom's
   parser was updated to them.**
3. **Integration / scoring** — **Resolved:** the engine leaves the **integration branch checked
   out** (carrying every merged PR); that working tree is what fathom scores.
4. **Strategy name** — **Resolved: `series`.**
