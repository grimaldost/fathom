# Routing policy

The task-to-tier routing policy below is the `choosing-models` skill as shipped: its
body, its scoring rubric, and its data file, copied verbatim. Apply it as written.

Where the policy names a model or an emission surface, the only vocabulary this
workspace uses is the tier: `weak`, `mid`, `strong`.

---

# Choosing Models

Capacity dispatch. choosing-tools decides which skill owns a task; this skill
decides how much model the task gets. The output is a **(model, effort)
pair** — model is capacity, effort is thinking depth, and the two are chosen
together, per task, at the moment work is delegated or priced. The rubric and
thresholds descend from a calibrated predecessor cycle and stay honest the
same way: observed-run evidence moves them, not taste.

This is a **flexible** skill: the procedure below is the default shape of the
decision; the judgment inside each step is yours.

## The procedure

1. **Score the task** with [references/scoring-rubric.md](references/scoring-rubric.md)
   — mentally, at authoring or spawn time, zero cost. The rubric owns *how to
   score*; it never moves without calibration evidence.
2. **Map score → tier** with the thresholds in [models.toml](models.toml) —
   the data file owns *what runs* (tier assignments, current lineup) and is
   the part that changes when models ship.
3. **Map tier → the surface's vocabulary** (table below).
4. **Apply the context modifiers** (next section).
5. **For batches** — a series, a workflow, a panel — present the per-task
   table (task, score, tier, model, estimated cost) with an all-top-tier
   comparison row, so the saving is visible.
6. **Persist the prediction.** A score that lives only in chat can never be
   reconciled with outcomes. Land the batch table where run telemetry can
   reach it — comments on each task block of the series file
   (`# choosing-models: score=42 tier=mid`) or the series design doc. Run
   feedback then checks predictions against gate results, and recurring
   misses become rubric evidence.

## Context modifiers

- **Oracle-coverage discount.** Downshifting one tier on implementation work
  is licensed by the *quality of the oracle around the task*, not by the
  presence of a gate. Ask what oracle will exist for **this** task in **this**
  run — including one about to be authored — not the one the environment
  already has. Downshift when the gate carries independent checks covering
  the task's dominant failure classes; a lint-plus-types-plus-tests gate does
  not qualify on its own. The discount also presumes the gated failure is
  **diagnosable at the discounted tier** — a red gate the cheaper model cannot
  read buys a repair loop, not a saving. Evidence and pending calibration:
  `models.toml`.
- **Ungated, hard-to-reverse, or interface-defining work** stays at or above
  its scored tier. The discount never applies where no oracle exists.
- **Review and design judgment route by stakes,** not by implementation
  score — the top tier for a hard-to-reverse call, a lower rung when the
  stakes don't justify it.
- **Escalation is an authoring or retry decision.** The frontier tier is
  never score-assigned; opt in when a strong-tier attempt failed and the
  retry needs more model, for the batch's highest-stakes hardest-to-reverse
  design work, or at score ≥ 90 when the task cannot be decomposed. No in-run auto-escalation — an
  engine that tried it cut it ("fired on the wrong signal"), and stronger
  models attempting more ambitious strategies can be *less* reliable on
  long-horizon irreversible work.
- **Cost caveats that keep getting re-learned:** cheaper per token is not
  cheaper per task (tokenizer and thinking-volume differences); cheaper is
  not faster wall-clock; a large prompt at max effort costs 5–10× the
  small-prompt baselines.

## Effort defaults

Defaults, not calibrated thresholds: `high` unless a row below applies —
mechanical, tightly scoped work runs `low`–`medium`; hard agentic or coding
work at the strong tier runs `xhigh` where the surface exposes it; `max` only
where correctness dominates cost. A surface without an effort knob (the Agent
tool today) inherits the session's setting — say so rather than pretending.

## Emission surfaces

Tier names are not shared across surfaces — emit each surface's own words:

| Surface | Emits | Vocabulary |
|---|---|---|
| series-file governance (e.g. convoy) | `tier` or `model`, plus `effort` | `weak/mid/strong/frontier` or API string |
| Agent-tool spawn | `model` | family alias (`haiku/sonnet/opus/fable`) |
| workflow `agent()` | `model` + `effort` | family alias + effort level |
| planning-tool per-PR tier (e.g. keel) | tier per task | family names — translate, don't assume |
| direct API tooling | model id | undated API string |

A workflow `agent()` with no `model` inherits the session model (possibly
frontier); no engine-level cap exists — under a tier cap, every call carries
an explicit `model`.

While an engine is series-global (no per-task keys): score every task anyway,
set the series tier to the modal tier, and consider splitting at a tier
boundary when the spread is two or more tiers — splitting buys tier fit at
coordination cost; sometimes accepting the overpay is right.
Silently pinning the top tier for a whole series is the failure mode this
skill ends.

## Staleness tripwires

- **Age (always fires):** `models.toml` carries `review_by`; past that date,
  offer `/refresh-models` before trusting the table.
- **Environment (partial):** `scripts/lineup_check.py <model id>` exits 1 when
  the session's own model is not in `models.toml` — run it rather than checking
  by hand. It cannot see a model the session doesn't know about; the age check
  and the quarterly refresh are for that.

## Data and overrides

`models.toml` stays thin: thresholds, tier assignments, aliases, calibration
provenance, typical-cost observations. Prices are read from the platform's
model reference at the point of use, not duplicated here. Calibration is
distribution-relative, so a **project-level override wins**: a project copy of
`models.toml` (project skill dir or a method binding) takes precedence over
the plugin's; project-specific corrections land there, not in the global
file. `/refresh-models` is the update path for all of it.

## Boundaries

- **choosing-tools** owns which skill or tool runs; this skill owns how much
  model. The two fire at the same moments and answer different questions.
- **toolkit-awareness** owns what is installed.
- **Model facts** (ids, prices, limits, API mechanics) come from the
  platform's model reference (e.g. the claude-api skill); this skill consumes
  those facts and owns only the routing policy.
- **skill-authoring** owns this description; when the skill wins or loses
  dispatch wrongly, fix the trigger surface there.

---

# Complexity Scoring Rubric

This rubric defines how to score a development task for model routing. The
score is 0-100, mapping to three tiers. Apply it mentally as you write or
read each task -- no external tool needed.

Ported near-verbatim from the predecessor cycle's calibrated rubric; the
worked calibration (trivial-task override, cross-shape floor, verification
discount) carries observed-run evidence and moves only on new calibration
evidence.

---

## Score Ranges and Tier Mapping

| Score  | Tier   | Character                                    |
|--------|--------|----------------------------------------------|
| 0-25   | weak   | Mechanical, pattern-following, single-file    |
| 26-55  | mid    | Multi-step, moderate reasoning, coordination  |
| 56-100 | strong | Deep reasoning, novel design, expert domain   |

> **Thresholds and model assignments live in [`../models.toml`](../models.toml)**
> -- data, calibratable, refreshed by `/refresh-models`. This file defines
> *how to score*; `models.toml` defines *what runs*.
>
> A fourth opt-in tier (`frontier`) exists above strong but is **never
> assigned by score** -- the author opts in manually. See the skill body for
> the criteria.

---

## Pre-check: Trivial Task Override

Before applying the point system, check: **does this task involve any
logic at all?** If the task is purely text substitution, config edits,
version bumps, typo fixes, or boilerplate documentation with no
conditional logic, start from a **base of 15** instead of 30.

This unlocks the 0-14 score range for truly mechanical work and prevents
simple tasks from clustering near the weak/mid boundary.

| Task type                                    | Base |
|----------------------------------------------|------|
| Has any logic, reasoning, or design decision | 30   |
| Pure text/config change, zero logic           | 15   |

---

## Cross-shape floor (root-cause locality)

Before the additive signals below, check whether this task is *cross-shape*: its
correctness depends on a site the prompt does NOT point at. The triggers key on
**what the prompt covers**, not on file counts -- a task can span many files and
not be cross-shape, or touch one file and be cross-shape.

If ANY trigger fires, **replace the score with 26** (the bottom of `mid`) when the
additive total is lower. The floor only ever raises a sub-26 score into `mid`; it
never lowers a task already at `mid`/`strong`, and it does NOT add to the additive
total -- deeper reasoning still scores up through the normal axes, so a genuinely
hard cross-shape task can land well above 26. A floored task is `mid` at `medium`
confidence by default; the low-confidence tier-bump below still applies, but reserve
`low` (which bumps mid -> strong) for a cross-shape task that is ALSO irreducibly
single-pass-hard -- not one merely uncertain because the prompt is thin (a thin
prompt is a reason to fire the floor, not to bump past mid).

| Trigger -- any one fires the floor                                            |
|-------------------------------------------------------------------------------|
| **Uncovered displaced cause** -- the fix must land in a different file/function/layer than where the symptom is observed, AND the prompt points only at the symptom site (if the prompt already names the fix site, this does not fire) |
| **Uncovered shared-helper fan-out** -- the change is to shared / common / helper / base code, AND the prompt does not enumerate every caller that must stay correct (you need not know the exact count; if you cannot name all consumers from the prompt, treat it as fired) |
| **Uncovered backend / parity** -- two or more implementations (backends, dialects, code paths, an ETL-vs-serving pair) must produce equivalent results, AND at least one is not named in the prompt as an edit site (if the prompt names every implementation to change, that is breadth, not cross-shape -- do not fire) |

Every trigger keys on a site the prompt does NOT point at -- the *relationship*
between symptom and fix, not how many files or modules the task spans; raw
breadth or repo size never fires this floor.

Coverage governs in both directions, and the axes below read the same brief:
score the task **as briefed**, not the problem behind it. Where the prompt
already enumerates the edit sites, the decomposition, or the acceptance cases,
the structure and reasoning axes fall with it -- that thinking is done and
handed over. Every recorded mis-score ran the other way.

---

## Scoring Signals

Evaluate these signals and add/subtract points. Start at the appropriate
**base** (15 or 30 per the pre-check above), then adjust.

### Task structure (+0 to +25)

**"Files" means code files requiring distinct logic**, not data files
read/written. A script that reads 7 CSVs and writes 11 parquets is one
code file touching many data files -> score based on the script's logic,
not the number of data files.

| Signal                              | Points  |
|-------------------------------------|---------|
| Single-file change, clear pattern   | +0      |
| 2-3 files, straightforward logic    | +5      |
| 4+ files or cross-module            | +10     |
| Multi-system coordination           | +15     |
| Requires architectural decisions    | +20-25  |

### Reasoning depth (+0 to +25)

| Signal                              | Points  |
|-------------------------------------|---------|
| Copy/paste with substitutions       | +0      |
| Sequential steps, clear order       | +5      |
| Conditional logic, branching paths  | +10     |
| Trade-off analysis needed           | +15     |
| Novel algorithm or proof-like work  | +20-25  |

### Domain specificity (+0 to +15)

**Testing discount:** When writing tests for existing domain logic (not
implementing it) and the test cases are specified in the prompt, reduce
domain score by one level (e.g., +8 -> +5, +12 -> +8).

| Signal                              | Points  |
|-------------------------------------|---------|
| Generic CRUD / utilities            | +0      |
| Standard framework patterns         | +3      |
| Domain-specific rules               | +8      |
| Regulatory / compliance             | +12-15  |

### Context dependency (+0 to +10)

| Signal                              | Points  |
|-------------------------------------|---------|
| Self-contained, no external context | +0      |
| Needs awareness of codebase style   | +3      |
| Needs domain knowledge not in prompt| +7      |
| Needs both codebase + domain        | +10     |

### Output size (+0 to +5)

**Cap rule:** If reasoning depth scored +0 (copy/paste), output size is
capped at +0 regardless of actual length. Long boilerplate is still
boilerplate -- length does not imply cognitive complexity.

| Signal                              | Points  |
|-------------------------------------|---------|
| Short (< 50 lines of code)         | +0      |
| Medium (50-150 lines)              | +2      |
| Long (150-400 lines)               | +3      |
| Very long (400+ lines)             | +5      |

### Adjustment factors (-15 to +10)

| Signal                              | Points  |
|-------------------------------------|---------|
| Has mechanical verification (tests) | -5      |
| Clear, specific acceptance criteria | -5      |
| Boilerplate / template work         | -5      |
| Ambiguous requirements              | +5      |
| Security-sensitive code             | +5      |
| Performance-critical path           | +5      |

---

## Quick Heuristic Shortcuts

For speed, you can also pattern-match on keywords:

**Likely weak (0-25):**
- add field/column, rename, format, fix typo, bump version, add test for
  simple function, scaffold/template, change label/text, update docs,
  simple migration, add env var, boilerplate endpoint

**Likely mid (26-55):**
- refactor, pipeline, integrate API, migrate data, aggregate/transform,
  error handling, validation logic, multi-file change, webhook handler,
  batch processing, query optimization, add caching layer

**Likely strong (56-100):**
- architect, design system, regulatory/compliance, security audit, optimize
  performance, concurrent/race condition, novel algorithm, distributed system,
  consensus protocol, complex state machine, multi-stage migration with
  rollback, ML model integration with feature engineering

---

## Confidence Assessment

After scoring, also assess your confidence:

| Confidence | Meaning                                              |
|------------|------------------------------------------------------|
| high       | Clear signals, unambiguous task, confident in tier    |
| medium     | Some ambiguity, could be one tier higher or lower     |
| low        | Significant unknowns, recommend erring toward stronger|

**When confidence is low**, bump the tier up by one level, capping at strong
(`frontier` is never auto-assigned). The cost of a retry (wasted call +
developer time reviewing bad output) exceeds the cost difference between
tiers.

---

## Worked Examples

### Example 1: "Add an `updated_at` timestamp column to the `users` table"

- Pre-check: pure DDL/config change -> **base 15**
- Task structure: single-file, single table -> +0
- Reasoning: copy/paste with substitution -> +0
- Domain: generic CRUD -> +0
- Context: self-contained -> +0
- Output: short -> +0
- Adjustments: clear criteria (-5), boilerplate (-5)
- **Total: 15 + 0 - 10 = 5 -> weak, confidence: high**

### Example 2: "Refactor sales report query to two-step CTE with role-based filtering"

- Pre-check: has logic (CTE design, JOIN reasoning) -> **base 30**
- Task structure: 1-2 files, needs JOIN logic -> +5
- Reasoning: conditional logic (CTE ordering, filter rules) -> +10
- Domain: standard framework pattern -> +3
- Context: needs awareness of table schemas -> +3
- Output: medium -> +2
- Adjustments: clear criteria (-5)
- **Total: 30 + 5 + 10 + 3 + 3 + 2 - 5 = 48 -> mid, confidence: high**

### Example 3: "Design a multi-stage document approval state machine with audit trail and rollback"

- Pre-check: has deep logic -> **base 30**
- Task structure: multi-module, needs integration -> +15
- Reasoning: complex conditionals, state transitions -> +20
- Domain: domain-specific rules (approval workflows) -> +8
- Context: needs both codebase + domain -> +10
- Output: long -> +3
- Adjustments: security-sensitive (+5)
- **Total: 30 + 15 + 20 + 8 + 10 + 3 + 5 = 91 -> strong, confidence: high**

### Example 4: "Fix the trailing-zero formatting in the exported report total"

- Pre-check: trailing-zero trimming is conditional logic, not pure text
  substitution -> **base 30** (a rater who reads it as a pure "format" task starts
  at base 15 -> total 8; either way it is weak before the floor)
- Task structure: the prompt names one file (`report.py`) -> +0
- Reasoning: looks like a small formatting fix -> +0
- Domain: generic utilities -> +0
- Context: needs codebase awareness -> +3
- Output: short -> +0
- Adjustments: clear criteria (-5), has tests (-5)
- Additive total: 30 + 3 - 10 = 23 -> weak
- **Cross-shape floor:** the real fix is a shared `format_amount` helper whose
  callers are not all named in the prompt (uncovered shared-helper fan-out), so a
  fix touching only `report.py` can leave other consumers wrong -> **replace with 26
  -> mid, confidence: medium**
- Lesson: the prompt's surface (one named file, short) scored weak; the *defect
  shape* (a shared helper the prompt did not point at) set the tier.

### Example 5: "Rename `legacy_id` to `external_id` across all 6 model files (listed below) and their references"

- Pre-check: pure rename, no logic -> **base 15**
- Task structure: 6 files -> +10
- Reasoning: copy/paste substitution -> +0
- Domain: generic -> +0
- Context: needs codebase awareness -> +3
- Output: short -> +0
- Adjustments: clear criteria (-5)
- Additive total: 15 + 10 + 3 - 5 = 23 -> weak
- **Cross-shape floor: does NOT fire.** The change fans out across 6 files, but the
  prompt *enumerates every file and reference* -- coverage is complete, so this is
  breadth, not cross-shape. Raw file count never fires the floor.
- **Final: weak, confidence: high.** Contrast with Example 4: there the fix site was
  *uncovered* -> mid; here the brief names every one -> weak. Coverage, not breadth --
  and that same coverage is why reasoning scored +0 on a six-file change.

---

## models.toml (data)

```toml
# Single source of truth for the choosing-models tier data. The SKILL.md and
# rubric cite this file instead of hardcoding lineup or thresholds in prose;
# /refresh-models updates it (mechanical lineup changes on approval; threshold
# changes only with calibration evidence).
#
# Deliberately thin: NO sticker prices here — the platform's model reference
# (e.g. the claude-api skill) is the price source, read at the point of use.
# Duplicating prices would create one more unowned mirror.
#
# Project override chain: a project-level copy of this file (project skill dir
# or a method binding) wins over the plugin's copy. Calibration is
# distribution-relative — project-specific corrections land in the override,
# not here.

schema_version = '1'

[meta]
last_reviewed = "2026-08-11"   # stamped by /refresh-models; mirrored nowhere else
review_by = "2026-11-11"       # age tripwire — past this date, refresh before trusting
calibration = "model-tier calibration runs of 2026-06-16, 2026-07-01 and 2026-08-11 (fathom model-tier-v1; the last is 5 arms x 7 tasks x 5 repeats, adding claude-opus-5). Thresholds are still ported defaults, and the 2026-08-11 decision was to change neither them nor the scoring mechanics: the bank has no power to move a cut. On-diagonal is 1/7 in all three runs, but 6 of 7 tasks sit at 100% for every arm, no task resolves empirically to mid or strong, and a 10/10 cell carries a Wilson 95% CI of [0.72, 1.00] - so a null here is manufactured by saturation, not observed. The tier-separating bank that would have the power is designed and unrun (fathom docs/specs/2026-07-14-tier-separating-bank-design.md). Observed direction, recorded not acted on: over-provisioning persists - 5 of 7 tasks were served by the weak tier, and the newest strong model was quality-flat against its predecessor at ~1.4x the per-task cost."
oracle_discount = "Labeled hypothesis, pending the crossed model x oracle-quality calibration in the same unrun bank. Established: a suite-only gate at the weak tier neither detects nor lifts (gates green, escapes reach the oracle), so gate value tracks the independence and coverage of the checks; and, twice over, scored tiers over-provision in the small while an iterative implement-gate-fix loop beat a bigger one-shot model on feature-refactor shapes. New 2026-08-11 (fathom model-tier-v1, n=30/arm, directional): the executing model authored a regression test in 70% of trials where four other models did so in 0-3%, so the oracle a task will have is partly a function of which model runs it - which is why the discount asks what oracle will exist for this run, not what exists now."
lineup_reconciled = "2026-08-11 against the platform model reference: strong was pinned to a model the machines are no longer served. Direction settled before any mirror walk - the sibling PRICE mirrors are keyed by family substring (opus/sonnet/haiku/fable), so a model-id change inside a family does not touch them and they are correct today; the one sibling tier-to-model map carried the same stale strong entry, so the walk propagates a corrected lineup rather than a stale one."

# Score -> tier. Calibratable data, not doctrine: the rubric owns how to
# score, these bands own where the cuts sit. frontier is opt-in only and
# never score-assigned (criteria in SKILL.md).
[thresholds]
weak = "0-25"
mid = "26-55"
strong = "56-100"

[[models]]
tier = 'weak'
api_string = 'claude-haiku-4-5'   # undated alias, never a dated snapshot
harness_alias = 'haiku'           # Agent tool / workflow agent() vocabulary
display = 'Haiku 4.5'
available = true
notes = ''

[[models]]
tier = 'mid'
api_string = 'claude-sonnet-5'
harness_alias = 'sonnet'
display = 'Sonnet 5'
available = true
notes = 'intro pricing through 2026-08-31; tokenizer ~30% more tokens for the same text vs Sonnet 4.6 — cheaper per token is not cheaper per task'

[[models]]
tier = 'strong'
api_string = 'claude-opus-5'
harness_alias = 'opus'
display = 'Opus 5'
available = true
notes = 'same price as Opus 4.8; thinking is ON by default, and disabling it is rejected above `high` effort'

[[models]]
tier = 'frontier'
api_string = 'claude-fable-5'
harness_alias = 'fable'
display = 'Fable 5'
available = true
notes = '2x Opus 5 pricing; opt-in only — never score-assigned'

# Per-task cost observations from calibration/production runs — provenance
# above. Small-prompt baselines; a large prompt at max effort runs 5-10x.
# These are observations for batch-table estimates, not sticker math.
[typical_cost]
weak = "$0.01 small-prompt baseline"
mid = "$0.06 small-prompt baseline"
strong = "$0.15 small-prompt baseline"
frontier = "$0.29 small-prompt baseline"

# Authoring guidance for per-tier budget ceilings (implementation / review /
# fix), where the executing engine takes them. Ported defaults; engines may
# carry their own flat fallback.
[budget_guidance]
weak = { implementation = 3.00, review = 2.00, fix = 2.00 }
mid = { implementation = 8.00, review = 3.00, fix = 3.00 }
strong = { implementation = 20.00, review = 5.00, fix = 3.00 }
frontier = { implementation = 30.00, review = 10.00, fix = 6.00 }
```
