---
name: fathom-eval
description: >
  Run and author scenario-blind tool-effectiveness evals with fathom — execute a
  scenario matrix against a task bank, render the blind scorecard, and gate spend
  with the real-spawn smoke check. Use when the user wants to measure whether a
  coding tool, skill, model tier, or execution strategy is worth it: "run a fathom
  eval", "A/B this skill", "does the pyeng skill actually help", "score this bank",
  "run the eval matrix", "compare bare vs armed", "author an eval bank/scenario/task",
  "regenerate the scorecard", "is the bare arm ever failing", "dry-run the cost",
  "smoke first". Covers the smoke→plan→run→report recipe, the flat-TOML
  scenario/bank/task schemas plus verify.py, the strategy catalog (single-session,
  gated-session, gated-review, reprompt-session, series/convoy), the cost rails, and
  the four invariants. Not for hand-editing the append-only ledger (never edit it);
  not for ordinary one-off coding or bug-fixing that is not an eval (that is plain
  implementation work); not for running the convoy multi-PR engine directly (that is
  convoy — fathom only drives it as the series arm).
---

# fathom — running and authoring tool-effectiveness evals

fathom measures whether an AI coding tool is worth using: it runs real coding
tasks under different execution strategies / tool configurations (**arms**),
scores results **blind to which arm produced them**, and joins quality with
economy (tokens, turns, wall-clock, USD) into longitudinal verdicts.

This is a **flexible** skill — guidance you adapt to the bank at hand — with a
few bright lines that are not negotiable because breaking them spends real money
wrongly or corrupts the longitudinal record:

- **Never run a paid matrix without `fathom smoke` passing first**, this session.
- **Never edit `ledger/<bank>.jsonl` by hand** — it is append-only; reports
  regenerate from it.
- **Never run fathom from the plugin's cache-clone.** The ledger is committed and
  lives in the user's own checkout — always run from `FATHOM_HOME` (below).
- **Pass `--scenarios-dir` for any bank that ships its own arms**, or the run
  silently uses the wrong arms.

## FATHOM_HOME — where fathom actually runs

fathom is a CLI harness that runs **inside its own repository** (it needs
`tasks/`, `scenarios/`, the `uv` env, and the committed `ledger/`). When invoked
through this plugin, resolve the user's canonical checkout and run there:

- If `FATHOM_HOME` is set, use it.
- Otherwise the current directory (or an ancestor) should be a fathom checkout
  (a `pyproject.toml` with `name = "fathom"`, plus `src/fathom/` and `tasks/`).
- If neither holds, ask the user for their fathom checkout path — do **not** run
  from the plugin install directory.

Every command runs from that directory as `uv run python -m fathom …` — the module
form, which is portable and sidesteps Windows Smart App Control blocking the
generated `fathom` console-script (os error 4551).

## The recipe

An **analysis** = a scenario matrix run against a task **bank**, scored into a
**scorecard**. Run it in this order:

```sh
# 1. Smoke — the real-spawn go/no-go gate. Proves credential isolation, headless
#    default-deny, injection arming, plugin mount, and the engine boundary on REAL
#    spawns before spending. Expect "ALL PASS (8/8 checks)". Spends a few cents.
uv run python -m fathom smoke

# 2. Plan — prints trial count + advisory USD ceiling + resume state. Spawns nothing.
uv run python -m fathom run <bank> --dry-run [--repeats K] [--scenarios-dir DIR]

# 3. Run — the real, paid matrix. Resumable: re-invoking skips completed trials.
uv run python -m fathom run <bank> [--repeats K] [--scenarios-dir DIR] [--limit N] [--max-budget-usd USD]

# 4. Report — render the scorecard from the ledger. Idempotent; regenerate any time.
uv run python -m fathom report <bank>
```

Slash commands wrap each step: `/fathom:smoke`, `/fathom:plan`, `/fathom:run`,
`/fathom:report`. The read-only MCP tools `plan`, `report`, and `smoke` do the
same for a synchronous, structured return (there is **no** `run` MCP tool — a
paid multi-hour matrix is a shell-out, not a tool call).

Banks live under `tasks/<bank>/` (`ls tasks/`). The reference self-contained bank
is **`skill-pyeng-v1`** — one task (`modernize-timeflow`) against **three arms**
(`bare`, `generic-nudge`, `pyeng-skill`) in `scenarios/skill-pyeng/`, so it needs
`--scenarios-dir scenarios/skill-pyeng` (e.g. `--repeats 3` → 3 arms × 1 task × 3 =
9 trials). Results land in `ledger/<bank>.jsonl` (committed) and
`report/scorecard-<bank>.md` (gitignored, regenerated).

## Cost, and when not to run

- **~$2/trial** advisory ceiling, printed upfront; a full v1 matrix is **~$20-40**.
- **`--max-budget-usd`** is the real per-**spawn** hard cap (adapter default 5.0).
  A `series` trial spawns several subagents, so it can spend several times the cap.
- **`--limit N`** caps fresh trials (applied after resume filtering) — a partial-
  matrix spend rail.
- Prefer a small `--dry-run` and a `--limit`ed pilot before committing to a full
  matrix. Re-run to resume; nothing is wasted.

Do **not** start a paid run when: smoke has not passed this session; the plan/USD
ceiling has not been reviewed; the bank ships its own arms but `--scenarios-dir`
was not set; or you only need to re-read an existing verdict (`report` is free).

## Strategy catalog

A scenario's `strategy` field selects how one task becomes 1..N spawns (it is a
**required** key — there is no default):

| strategy | what it does | spawns |
|---|---|---|
| `single-session` | one plain session — the **bare** anchor for pairwise reads | 1 |
| `gated-session` | impl, then run the task's gate + a bounded fix loop | 1 + ≤2 fixes |
| `gated-review` | gated-session plus one structured review pass | more |
| `reprompt-session` | impl + one unconditional generic reprompt (gate-info control) | exactly 2 |
| `series` | drives the **convoy** multi-PR engine (the one sanctioned non-adapter path) | many, long |

`series` needs the convoy engine repo present (`[tools] source="repo"
repo=<convoy>`); it is paid and long (`trial_timeout_s=3600`) and dominates
matrix cost. `gated-*` are meaningless for a task with no gate — the bank must
ship one.

## The four invariants (each has an ADR under `docs/adr/`)

- **Blindness** (ADR-0003) — verifiers see only the final workspace; judges see
  outputs labeled A/B with scenario identity removed; economy joins **after** scoring.
- **Append-only ledger** (ADR-0002) — no code rewrites a ledger line; resume key =
  `(bank, dataset_version, task_id, config_hash, repeat)`; only `status=="completed"`
  counts as done.
- **Spawn isolation** (ADR-0004) — credential-only temp `CLAUDE_CONFIG_DIR`; headless
  default-deny (never `bypassPermissions`); explicit allow/disallow lists.
- **Stdlib core** — modules under `src/fathom/` import stdlib only.

## Authoring a bank / scenario / task

See [`reference/authoring.md`](reference/authoring.md) for the as-built flat-TOML
schemas (scenario, `bank.toml`, `task.toml`), the `verify.py` contract, and the
`config_hash` resume mechanics. Two things that bite: bump `dataset_version` on
**any** task/fixture/verifier change (it is in the resume key), and editing a
`[context]` inject brief or a mounted plugin file forks `config_hash` and
re-spends resumed trials.

## Reading the scorecard

After `fathom report <bank>`, read `report/scorecard-<bank>.md`. The sections, and
how to read them:

- **Per-Criterion Pass Rates** — the discriminating quality signal. Lead with it,
  not the headline pass-rate: an arm difference shows where the bare arm passes the
  anchor but trips a hard criterion.
- **Economy** — per-arm `Tokens | Turns | Wall-clock (s) | Sessions/Trial | Est. USD`.
  This is the cost axis the verdict joins to quality.
- **Efficiency** — per-trial means plus `Quality / 100k Tok` and a **Pareto** ★ flag
  (an arm is starred when no other arm strictly dominates it on both quality and total
  tokens). This is where "is the armed arm worth its cost?" is answered.
- **Pairwise vs Bare Anchor** — **always empty in v1** (the judge ships dark); do not
  read it as a populated quality axis.
- **Calibration** — renders only for banks that ship `scores.toml` + `hard_criteria`.

## When not to use this skill

- The task is ordinary implementation or debugging, not an eval — just do the work.
- You want to run convoy's multi-PR engine on real PRs — that is convoy directly;
  fathom only drives it as a measured arm.
- You want to change a past result — you cannot; the ledger is append-only, and an
  invalidated run is archived (`ledger/archive/`), never edited.
- You only need whether a tool "feels" better without a scored, blind comparison —
  that is not what fathom is for.
