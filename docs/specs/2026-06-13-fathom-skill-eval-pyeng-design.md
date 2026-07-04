# fathom skill-eval (python-engineering) — design spec

**Date:** 2026-06-13
**Status:** Approved-pending-review design, pre-DoR
**Builds on:** `docs/specs/2026-06-10-fathom-v1-design.md` (the spine), ADR-0001 (vendor-abstract
runner), ADR-0003 (blind result-only scoring), ADR-0004 (vendor claude runner core).
**Subject skill:** `engineering-discipline:python-engineering` v0.1.2
(`SKILL.md` + bundled `scripts/doctor.py`).

## 1. Purpose

Use fathom to answer a **with/without effectiveness** question about a craft-collection skill:

> Does force-loading `python-engineering` make an agent modernize a legacy Python project to the
> skill's own standard — and does that compliance hold up under a correctness check — and at what
> token cost?

This is the **first fathom question that is not an execution-strategy comparison** — it is a
*context/tooling* comparison. It deliberately doubles as a dogfooding probe of fathom's fit for
skill-evaluation work. The whole spine (ledger, resume, blind verifier, economy, report) is reused
unchanged; the only new capability is **per-scenario system-prompt injection**.

### Why this is the honest scope

A skill has two separable questions. fathom answers one and is built to ignore the other:

- **Effectiveness** ("when the guidance is active, do outcomes improve?") — fits fathom's
  treatment-vs-control shape exactly. **This spec.**
- **Triggering** ("does it auto-activate on the right prompts?") — a v1 non-goal of fathom
  (`2026-06-10-fathom-v1-design.md` §2; the adapter dropped skill-activation extraction,
  `src/fathom/adapters/claude_cli.py:20`). Owned by `session-workflow:evaluate-skill`.

Force-loading the skill body sidesteps triggering by construction, isolating the effectiveness axis.

## 2. Goals and non-goals

### Phase-1 goals

1. A scenario can carry an **injected system prompt** (a skill body), recorded in `config_hash`,
   wired into the adapter via `--append-system-prompt-file`.
2. A new bank `skill-pyeng-v1`: one **legacy-modernization** task with a blind verifier that ports
   the skill's own `doctor.audit()` (compliance) and adds a layout-agnostic **behavior-preserved**
   test (correctness).
3. Three scenarios: `bare` (control, reused) · `pyeng-skill` (treatment: `SKILL.md` injected) ·
   `generic-nudge` (treatment control: a one-paragraph generic quality instruction injected).
4. One Phase-1 run → scorecard with a directional verdict on **compliance × correctness × economy**
   (including the input-token cost of carrying the skill).
5. A dogfooding feedback report on fathom's fit for skill-eval (with cost table), per the standing
   feedback-targets discipline.

### Non-goals (Phase 2+, interface-ready)

- **Quality axis via the pairwise judge** (architecture, readability, Protocol-at-seams,
  functional-core/imperative-shell). Phase 1 is **verifier-only**; the dark-shipped judge
  (`src/fathom/grading/judge.py:10`) is the natural next phase and gets its own spec.
- **Plugin-mount fidelity** (`--plugin-dir` to load the skill as actually shipped, triggering
  included) — Phase 1 force-loads to remove triggering as a confound.
- **Execution-based criteria** (`ruff`/`ty`/`mypy` actually pass, `uv sync`) — needs a provisioned
  or Docker workspace (fathom constraint C3). Phase 1 grades **config/file presence only**, which is
  exactly what `doctor.py` checks.
- **A discriminating multi-task bank / sealed holdout** — one task in Phase 1; bank breadth and a
  holdout are a Phase-2 concern once the single task is shown to discriminate.

## 3. Constraints and key decisions

| # | Decision | Consequence / rejected alternative |
|---|---|---|
| K1 | Reuse the spine; the **only** new capability is system-prompt injection | No new adapter, no new strategy — `single_session` suffices. |
| K2 | **Force-load** over plugin-mount for Phase 1 | Guarantees the guidance is present → removes triggering as a confound. Plugin-mount (`--plugin-dir`) is the higher-fidelity Phase-2 test. |
| K3 | Inject via `--append-system-prompt-file <path>` (flag confirmed in `claude --help`) | File, not inline `--append-system-prompt`: the skill body is large (arg/escaping limits). System-prompt level, not prepended-to-user-prompt, mirrors how skill context actually loads. |
| K4 | Grade against the skill's **own** `doctor.audit()` | `doctor.py` is read-only, stdlib, presence-based, path-in / exit-out — the `verify.py` contract already. Removes "criteria I invented" bias. The interesting question (does compliance imply *better*?) is what the correctness test and the Phase-2 judge are for. |
| K5 | Inject **`SKILL.md` only** (not `references/`, not `scripts/`) | References are progressive-disclosure and unreadable in a headless workspace anyway; documented fidelity gap. `--add-dir` of the skill dir is a Phase-2 fidelity option. |
| K6 | `config_hash` stability: the new `context.inject` field is hashed **only when set** | Absent==empty, exactly like `tools.allowed` (`src/fathom/scenario.py:141`), so the committed series-engine bank's ledger hashes do not shift and stay resumable. |
| K7 | **Loud-fail on an unarmed treatment arm** | Same failure class as matrix-run-1 defect D1 (single arms spawned unarmed under default-deny). If injection silently no-ops, the treatment arm is "un-skilled" and the verdict is invalid. A smoke assertion + a runner warning must confirm the treatment command actually carries the file. |

## 4. Architecture changes (contained)

### Concept → module map

| Concept introduced / changed | Module / file |
|---|---|
| `context.inject` scenario field + hashing | `src/fathom/scenario.py` |
| `--append-system-prompt-file` wiring | `src/fathom/adapters/claude_cli.py` (`build_command`, `ClaudeCliRunner`) |
| warn-on-unarmed-treatment | `src/fathom/cli.py` (`_default_runner_factory`) |
| compliance + correctness verifier | `tasks/skill-pyeng-v1/modernize-timeflow/verify.py` |
| legacy fixture | `tasks/skill-pyeng-v1/modernize-timeflow/fixtures/` |
| treatment / control scenarios | `scenarios/pyeng-skill.toml`, `scenarios/generic-nudge.toml` |
| unarmed-treatment smoke assertion | `src/fathom/smoke.py` |
| per-criterion compliance + correctness table | `src/fathom/report.py` |

### The changes

- **`scenario.py`** — add `ContextConfig(inject: str | None = None)` to `ScenarioConfig` /
  `ResolvedScenario`. Resolution validates and absolutizes the path. `_resolved_to_dict` includes
  an `inject` key **only when set** (K6). The injected *content hash* (sha256 of the file body),
  not just the path, goes into `config_hash` so editing `SKILL.md` forks history correctly.
- **`adapters/claude_cli.py`** — `build_command(..., append_system_prompt_file: str | None = None)`
  appends `["--append-system-prompt-file", path]` when set. `ClaudeCliRunner.__init__` gains the
  param; `execute` reads it off the resolved scenario. Pure command-assembly change; the injectable
  `Spawn` boundary keeps every test stub-only (no real spawns).
- **`cli.py` `_default_runner_factory`** — read `scenario.context.inject`; pass to the runner;
  print a loud `WARNING` when a scenario declares itself a treatment (inject set) but the path is
  missing/empty, mirroring the existing unarmed-arm warning (`src/fathom/cli.py:248`).
- **`tasks/skill-pyeng-v1/`** — `bank.toml` (`dataset_version = "1"`, no holdout in Phase 1) +
  task `modernize-timeflow`.
- **`scenarios/`** — `pyeng-skill.toml` and `generic-nudge.toml`; `bare.toml` reused as control.
- **`smoke.py`** — a check group asserting the treatment command carries
  `--append-system-prompt-file` and the control command does not (the K7 gate).
- **`report.py`** — add a **per-criterion pass-rate table** (each verifier criterion × scenario →
  % of scored trials that satisfied it). Required because the current scorecard scores a trial as
  passing only when *every* criterion is truthy (`src/fathom/report.py:36`), which would **conflate**
  compliance with correctness: a 5/5-compliant arm that trips `behavior_preserved` would score
  identically to a 0/5 arm. The per-criterion table is what shows compliance climbing
  bare → generic → skill while `behavior_preserved` holds ~100%. The existing all-truthy pass-rate
  stays as a secondary "fully compliant *and* correct" number.

## 5. The experiment

**Bank `skill-pyeng-v1`, `dataset_version` 1. Task `modernize-timeflow`.**

- **Fixture:** a flat-layout legacy project — `timeflow/parser.py` (`parse_timestamp`, `normalize`,
  a few functions), `tests/test_parser.py` (passing), and a legacy `pyproject.toml` with dev deps
  under `[project.optional-dependencies]`, no `[tool.ruff]`, no `src/`, no `[dependency-groups]`,
  no `pip-audit`. `doctor.py` on the untouched fixture scores ~0/5 — **no ceiling by construction**.
- **Instruction:** *"Modernize this project to production-quality standards."* Deliberately
  tool-agnostic — the skill's value is in knowing what "standard" means (uv, src-layout, ruff
  single-quote, PEP 735 groups, pip-audit), which a bare arm is unlikely to volunteer.
- **Verifier (`verify.py`, blind, harness env):**
  - **compliance** — port `doctor.audit()`: 5 binary criteria (`src-layout`, `uv`,
    `ruff-single-quote`, `dependency-groups`, `pip-audit`), emitted as per-criterion booleans.
  - **correctness** — locate the package whether it ended up flat or under `src/`
    (`importlib.util.spec_from_file_location`), run a held-out behavioral assertion on
    `parse_timestamp`/`normalize` → `behavior_preserved: bool`. Layout-agnostic, so a *correct*
    src migration passes and a *broken* refactor fails.
  - **output** — a flat boolean dict: the 5 compliance criteria **plus** `behavior_preserved`,
    emitted as JSON (exit 0 iff `behavior_preserved` — conventional only; the report scores on
    criterion truthiness, not the exit code, `src/fathom/cli.py:188`). The **per-criterion table**
    (report.py change) is the primary view — it separates the compliance axis (expected to climb
    across arms) from correctness (`behavior_preserved`, expected ~100%), which the blended
    trial-level pass-rate cannot.
- **Arms:** `bare` · `generic-nudge` (inject a one-paragraph "write production-quality,
  well-structured, idiomatic Python with proper tooling and tests") · `pyeng-skill` (inject
  `SKILL.md`). All three share `bare.toml`'s identity — `model = claude-opus-4-8`, `effort = high`,
  `strategy = single-session`, `trial_timeout_s = 600`, and the allowlist
  `["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]`. The treatments differ **only** by
  the injected prompt. The allowlist has no `uv` and no network, so every arm modernizes by editing
  files — precisely what the presence-based verifier grades — keeping trials offline and
  deterministic.
- **Repeats:** 3 (LLM nondeterminism; verifier-only single-session trials are cheap).
- **Matrix:** 3 arms × 1 task × 3 repeats = **9 trials**. Ceiling ≈ $2/trial → ≤ $18 worst-case;
  realistically far less (the v1 bare arm ran ~60 s and $0 on subscription).

**Predicted signal (the run confirms or refutes):** `bare` low (~1/5), `generic-nudge` middling
(~2–3/5), `pyeng-skill` high (~4–5/5); `behavior_preserved` high across arms (the module is small).
If `bare` already lands 4–5/5, that is itself the finding — the task does not discriminate, same
lesson as the series-engine bank.

## 6. Done-when (Phase 1)

1. `fathom run skill-pyeng-v1` executes the 9-trial matrix resumably (interrupt + re-invoke
   re-spawns nothing already complete — demonstrated, not asserted).
2. `fathom smoke` passes including the **unarmed-treatment** assertion (K7).
3. Stdlib-only unit tests pass for: `inject`-field hashing (absent==empty keeps the series-engine bank's
   hashes stable; content-hash forks on body edit), `build_command` injection, and the verifier's
   compliance + correctness parsing.
4. `fathom report skill-pyeng-v1` renders the **per-criterion** table (each compliance criterion and
   `behavior_preserved`, % per arm) and the economy table — the treatment arms' extra input tokens
   visible. The per-criterion view, not the blended pass-rate, carries the verdict.
5. A dogfooding feedback report under `docs/feedback/` on fathom's skill-eval fit, with a cost table.

## 7. Open items (resolve before/at DoR)

1. **SKILL.md fidelity** — body-only injection means the skill's "Read `references/…`" pointers
   resolve to nothing in a headless workspace. Accept and document for Phase 1, or `--add-dir` the
   skill dir so references resolve? (Recommend: body-only; note the gap.)
2. **`generic-nudge` in Phase 1 or deferred?** — Recommend *in*: it separates "the skill helped"
   from "any nudge helped," and verifier-only trials are cheap.
3. **Content-hash vs path-hash for `inject`** — settled to content-hash (K6 rationale); confirm no
   churn against the committed ledger.
4. **Execution lane** — see below; not a spec-content item but a routing decision.

## 8. Decision log

| Decision | Choice | Rejected |
|---|---|---|
| Which skill question | Effectiveness (force-load) | Triggering — `evaluate-skill` owns it; fathom design §2 non-goal |
| Injection mechanism | `--append-system-prompt-file SKILL.md` | inline `--append-system-prompt` (size/escaping); `--plugin-dir` mount (re-introduces triggering — Phase 2); prepend-to-user-prompt (frames the skill as task requirements) |
| Grading | Port the skill's own `doctor.audit()` + a behavior-preserved test | Hand-authored criteria (bias); judge-only (expensive, unvalidated, Phase 2) |
| Task | Modernize a legacy project | Scaffold greenfield (thinner correctness, on-rails); minimal wiring-test (no real verdict) |
| Arms | `bare` + `generic-nudge` + `pyeng-skill` | `bare`+`skill` only (cannot separate skill content from a generic nudge) |
| Scope | Verifier-only Phase 1, judge in Phase 2 | One-shot full build (couples an unvalidated judge to the first result) |
