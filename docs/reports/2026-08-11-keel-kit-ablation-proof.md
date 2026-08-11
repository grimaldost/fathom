# Proving the keel kit core — the four-arm ablation and the reshaped-gate regression

- **Date:** 2026-08-11. Bank `keel-kit-ablation-v1`, arms `scenarios/keel-kit-proof/`, branch
  `eval/keel-gate`. Gate under test on the retro half: keel `feat/gate-empiricism`
  (11 reshape commits on `d99523d`).
- **Two independent questions, two independent instruments.** The ablation asks whether the kit's
  **prose** is necessary, holding the ruler fixed. The retro census asks whether the reshaped
  **gate** still catches what the old one caught, holding the corpus fixed. Neither answers the
  other, and the report keeps them apart.
- **Verdicts** are stated per claim at the end, in the operator's three-way vocabulary:
  proven / not-proven / not-measurable.

---

## Part 1 — the ablation

**Status: staged, gated, and NOT RUN. $0.00 spent. Blocked on the paid-run serialization lock,
which is held by a run that is no longer executing.** Everything below is real work product; the
only missing thing is the spend, and it needs one file removed by whoever owns the program.

### 1.1 The arms

The pre-registered bank shipped three arms in `scenarios/keel-kit/`. Between authoring and running,
keel's `feat/gate-empiricism` branch **changed the kit itself** (T0.5 relocated ~1,120 words out of
the two injected files into doctrine, the ADR template, the Definition of Done and the profile
sheet). That relocation shipped without a measurement, on the argument that it was
information-preserving.

The consequence is that "full versus core" is no longer one edit but two, and the original
three-arm shape cannot separate them. This run therefore adds **two** scenario files rather than
one, in a new directory. Nothing in `scenarios/keel-kit/` is edited; `a-full-014` injects the
byte-identical pre-registered asset by path, preserving its content-sha provenance pin.

| arm | injected body | words | sha256 (16) |
|---|---|--:|---|
| `a-full-014` | keel 0.14.0 as shipped — `scenarios/keel-kit/assets/kit-full.md`, reused not copied | 3,789 | `5685cfac7f3c3172` |
| `b-vnext-full` | the kit after T0.5 — `spec-template.md` + `definition-of-ready.md` at branch HEAD | 2,669 | `a8570b7f422462eb` |
| `c-vnext-core` | **the core-kit arm** — `templates/core/{spec-template,definition-of-ready}.md` | 2,438 | `f286c0a9eb92eff7` |
| `d-bare` | nothing | 0 | — |

Both vNext bodies are assembled by the identical recipe used for the pinned asset: the two-line
framing preamble every armed arm carries, then the spec template, then the DoR, joined by a `---`
rule. All three armed bodies stamp `Kit: 0.14.0` and `Kind: series`, matching the pinned oracle's
gate semantics, so no kit-skew confound is introduced.

The contrast this buys, and it is the whole point of the fourth arm:

- **A → B** measures T0.5's relocation — a 1,120-word edit that has never been measured.
- **B → C** measures the core cut in isolation — and `c-vnext-core` is a **strict
  order-preserving deletion** of `b-vnext-full` (every non-blank line appears, in order, in B),
  so a B→C gap is attributable to removed prose rather than to a rewrite.
- **D** is the floor.

### 1.2 The pre-registered power warning

This must be read before any result off these arms, and it is asserted by a test so it cannot be
quietly forgotten. The ablation was designed around a projected 3,740 vs 1,970 contrast. The arms
shipped at **2,669 vs 2,438 — a 231-word, 8.7% delta**, because most of the intended reduction left
through T0.5 instead. The bank now buys a much smaller decision (may the A9/A10/A11 template notes
and the DoR Part-B prose go?) with correspondingly less power.

**If B and C both pass everything, the correct report is *no power*, not a null.** That is the
bank's own pre-registration too: "All three arms passing everything is a ceiling — the bank had no
power. Report still-unmeasured and cut nothing."

### 1.3 Gates cleared before spend

Every free gate in the discipline passed, in this session, on this worktree:

| gate | result |
|---|---|
| `ruff format --check .` | 801 files already formatted |
| `ruff check .` | all checks passed |
| `uv run pytest` | **629 passed**, 1 skipped, 134 subtests |
| `fathom validate keel-kit-ablation-v1 --strict` | **24 pass / 0 fail / 0 warn / 0 unverifiable** |
| `tools/check_skeleton_refs.py keel-kit-ablation-v1` | every task separates a shallow answer from a good one |
| `tests/test_keel_kit_proof_assets.py` (new) | 8 tests — deletion-only, one-axis, sha pins, shared preamble |
| `fathom run … --dry-run` | 4 scenarios × 6 tasks × 2 repeats = **48 trials** |
| resolved `config_hash` per arm | 4 distinct — no resume-key collision |

Still owed, and all requiring the lock: `fathom smoke`, `fathom verify-arming --scenarios-dir
scenarios/keel-kit-proof`, then the matrix.

### 1.4 The budget rail, and a correction to the instruction

The run was specified with `--max-budget-usd 30`. **In fathom that flag is a per-spawn cap, not a
total-run rail** (`src/fathom/adapters/claude_cli.py`, `default_max_budget_usd = 5.0`; the value is
passed straight through to each `claude` spawn). Passing 30 would *raise* the per-spawn ceiling
six-fold and license a 48-trial ceiling near $1,440 — the opposite of a guard.

$30 is therefore read as the **total** ceiling it evidently means, enforced by staging rather than
by the flag:

1. `--repeats 1` (24 trials, all four arms × six tasks — balanced at every stage), per-spawn cap
   `--max-budget-usd 1.0`, well under the $5 default.
2. Read actual spend from the ledger; the nearest sonnet-5 prior with an injected body
   (`inject-content-v1`) ran $0.368 mean / $0.600 max per trial, so stage 1 projects ≈ $9.
3. `--repeats 2` only if stage 1 leaves headroom and shows something worth resolving. Absolute
   worst case across both stages is bounded by the per-spawn cap at 48 × $1.00 = $48, so the
   stage-1 checkpoint is what actually holds the $30 line — not the flag.

The sealed holdout is **not** spent. The bank seals two tasks precisely because it feeds a
retirement decision, and spending them on a contrast that is pre-registered as probably
underpowered would burn them for nothing. They are worth opening only if the open tasks
discriminate.

### 1.5 Why it did not run

`fathom smoke` and `verify-arming` spawn real models, so the matrix waits on the program's
paid-run serialization lock. The lock was held on arrival and never released:

```
holder=verification-lift MAP matrix (bare+skill)
pid=5395
started=2026-08-11T20:19:48Z
worktree=C:/Users/grima/Documents/.wt-verification/fathom
planned_trials=160
```

It is orphaned. The evidence, gathered over ~90 minutes of polling at the protocol's 10-minute
cadence:

- The holder's ledgers stopped growing at **20:56Z** and were still unchanged at 21:51Z — **51
  minutes idle**, well past that bank's own 900 s per-trial timeout.
- Full process enumeration, repeated: **no `fathom run` process exists**. The only processes whose
  command line mentions fathom are the plugin's long-lived MCP servers under
  `plugins/cache/fathom/…/mcp/fathom_server.py`, started at 06:36, and this session's own shells.
- Several *other* agents' shells are visible blocked on the same lock file, one of them waiting on
  a queued acquire task. The lock is deadlocking a queue, not protecting a run.

The lock was **not** removed. It is another program's coordination state; the serialization rule is
unconditional and governs paid spend, and a stale-lock exception is not something a peer agent
should grant itself. Clearing it is a one-line operator action, after which the matrix needs no
further preparation:

```sh
# once the lock is confirmed clear
uv run fathom smoke
uv run fathom verify-arming --scenarios-dir scenarios/keel-kit-proof
uv run fathom run keel-kit-ablation-v1 --scenarios-dir scenarios/keel-kit-proof \
    --repeats 1 --max-budget-usd 1.0
```

### 1.6 The three-arm table

Empty by construction — no trial ran, so every cell is unmeasured. It is published in this shape so
the run fills it in without re-deciding anything.

| criterion class | `a-full-014` | `b-vnext-full` | `c-vnext-core` | `d-bare` |
|---|---|---|---|---|
| ask/shared | — | — | — | — |
| **behaviour** (load-bearing) | — | — | — | — |
| ask/note-only (**the cut decision**) | — | — | — | — |
| integrity (Goodhart modes) | — | — | — | — |
| cost / trial | — | — | — | — |

One reading rule, inherited from the bank and worth repeating because a previous run in this repo
was misread: **report the per-criterion table, not the headline pass rate**, and treat the
*behaviour* class as load-bearing. The oracle is a component of the artifact under study, so the
armed arms are handed a description of the ruler; an A-arm win confined to the shared class
measures instruction-following, not value.

A note on the oracle for whoever runs this: `_oracle/` is pinned at keel `2bfc918` with 0.14.0 gate
semantics — i.e. the **pre-reshape** gate. That is deliberate (the ruler must not move while the
kit does), and it means the ablation's `enforcement_claims_clean` criterion inherits exactly the
A10 defeatability that Part 2 measures and the reshape fixes. The two halves of this report are
independent instruments and should stay that way.

---

## Part 2 — the reshaped-gate regression census

### 2.1 What was re-run, and how

The 2026-08-11 retrospective gate-hit census established the baseline: 19 historical specs from
`keel`, `fathom`, `craft-collection` and `mantis-research-runner`, each probed against three trees
— `retro_pre` (last commit strictly before the spec's own date, the tree the author had in hand),
`retro` (end of the spec's own date), and `head` (the repo's current tree). Its classification
named five checks **SHARP**: A5, A6, A11, A12 and R1.

This re-run changes **exactly one thing: the gate**. Same 19 specs, same three trees, same
commit-selection rule, same spec-text handling, same premortem-sidecar staging.

Two method upgrades over the original census, both of which make the comparison stronger rather
than merely different:

1. **The reshaped gate is probed directly, not replicated.** The original census used
   `kg_probe.py`, which re-implemented `check_spec_ready`'s control flow in order to attribute each
   violation to a catalogue id — the gate carried no id in code. The reshape (T0.1) put
   `Violation.check`, `Warning.check` and `GateResult.probes` into the gate itself, so
   `kg_probe2.py` calls the real `check_spec_ready` and reads attribution off the result. The
   replication risk the first census carried is gone on the new side.
2. **The baseline was re-derived in-session rather than trusted.** The pre-reshape gate was
   extracted from `d99523d` and re-run over the whole corpus with the original probe, producing
   `census1_repro.json`.

**Reproduction check — 1,083 (spec, tree, check) cells compared, 0 mismatches.** The re-derived
baseline reproduces the recorded census exactly, cell for cell. Everything below is therefore a
statement about the gate, not about harness drift.

Corpus integrity was confirmed separately: all 19 specs are byte-stable since the census. (The
line counts appear to differ by exactly −1 for every spec; that is a counting convention —
the original recorded `text.count("\n") + 1`, which counts the trailing newline as a line.)

### 2.2 The zero-regression table

A **cell** is one (spec × tree) pair in which a check produced at least one violation; 19 specs ×
3 trees = 57 cells available per check. A **lost catch** is a cell the baseline failed and the
reshaped gate passes. Checks that never fired under either gate are omitted.

| check | SHARP | baseline cells | reshaped cells | baseline specs | reshaped specs | baseline violations | reshaped violations | **lost** | gained |
|---|:--:|--:|--:|--:|--:|--:|--:|--:|--:|
| A5 | yes | 3 | 3 | 2 | 2 | 7 | 7 | **0** | 0 |
| A6 | yes | 24 | 24 | 10 | 10 | 270 | 270 | **0** | 0 |
| A9 | — | 2 | 2 | 1 | 1 | 6 | 6 | **0** | 0 |
| A10 | — | 0 | 3 | 0 | 1 | 0 | 3 | **0** | **+3** |
| A11 | yes | 3 | 3 | 1 | 1 | 12 | 12 | **0** | 0 |
| A12 | yes | 15 | 15 | 8 | 8 | 187 | 187 | **0** | 0 |
| R1 | yes | 3 | 3 | 1 | 1 | 3 | 3 | **0** | 0 |

**Lost catches, all checks: 0. Lost catches, SHARP only: 0.** The zero-regression requirement is
met, and met with room to spare — not one cell, on any check, sharp or not, went from failing to
passing.

Restricted to the census-comparable `retro_pre` tree, the reshaped gate reproduces the census's
§3 numbers exactly: A5 1 spec / 3 violations, A6 8 / 82, A11 1 / 4, A12 6 / 64, R1 1 / 1, with
B1 3 warnings and W2 4 warnings unchanged.

Per spec, every SHARP catch survives on the same spec, in the same trees:

| # | spec | baseline SHARP | reshaped SHARP | |
|---|---|---|---|---|
| 3 | `2026-06-10-fathom-v1-build.md` | R1 | R1 | ok |
| 9 | `2026-06-19-keel-0.8.0-spec.md` | A6 | A6 | ok |
| 11 | `2026-06-28-keel-0.10.0-spec.md` | A6 A12 | A6 A12 | ok |
| 12 | `2026-07-01-keel-0.11.0-spec.md` | A5 A6 A12 | A5 A6 A12 | ok |
| 13 | `0001-agent-researcher-pivot.md` | A5 A6 A11 A12 | A5 A6 A11 A12 | ok |
| 14 | `0002-agent-serving-mcp-plugin.md` | A6 A12 | A6 A12 | ok |
| 15 | `2026-07-06-keel-0.12.0-spec.md` | A6 A12 | A6 A12 | ok |
| 16 | `2026-07-10-keel-0.13.0-spec.md` | A6 A12 | A6 A12 | ok |
| 17 | `agent-portability.md` | A6 A12 | A6 A12 | ok |
| 18 | `2026-07-24-experiment-rigor-skill.md` | A6 | A6 | ok |
| 19 | `2026-07-25-experiment-discipline-wave.md` | A6 A12 | A6 A12 | ok |

### 2.3 What the reshape gained

**A10 acquired a real catch, and that retires a cut candidate.** The census classified A10 as
*VACUOUS — candidate, defeatability confound*: 17 silent opportunities, and a cross-vendor skeptic
panel that had **reproduced** A10 false negatives (line-wrap, backticked invariant names, common-word
negation tokens). Its silence was uninformative in both directions, so no verdict could be taken.
T1.3 closed those three defeats. The reshaped A10 immediately fires on a spec the old gate passed,
in all three trees:

> `2026-07-24-experiment-rigor-skill.md` line 86: claims 'run cross-check equality with a per-tier
> hand policy' is "enforced" but its enforcement status is 'planned'.

That is a genuine enforcement over-claim, of exactly the class A10 exists to catch, sitting
undetected in the corpus for the whole life of the old check. **A10 moves from cut-candidate to a
check with a demonstrated catch**, and the census's refusal to cut it on silence is vindicated.

**W1's input finally arrives.** The census recorded W1 as *dead by non-adoption*: zero material,
because **no authored spec in the corpus carries the kit stamp** even though the templates all do.
T0.3 moved the stamp into the visible header and widened W1 to the unstamped case — the only case
the census ever observed. W1 now has material on all 19 specs and fires on every one of the 57
cells with a single message form:

> WARN: this spec is unstamped — it declares no kit version, so kit↔gate skew is undetectable on
> it. Add `- **Kit:** 0.14.0` to the header beside Date and Status.

The check was never broken; the authoring surface was. The reshape fixed the surface.

**No warning was lost in the W4/W5 split.** T0.1 gave the two certification-artifact warnings their
own ids, which moves 57 warnings out of B2. This is pure re-attribution, verified by message-set
identity rather than by count alone:

| warning | baseline | reshaped |
|---|--:|--:|
| B1 | 9 | 9 |
| B2 | 57 | 0 |
| W4 (certification names no artifact) | 0 | 42 |
| W5 (artifact certified against an earlier revision) | 0 | 15 |
| W2 | 12 | 12 |
| W3 | 6 | 6 |

42 + 15 = 57, and the reshaped `{B2, W4, W5}` message set is **identical** to the baseline `B2`
message set — same specs, same trees, same strings.

One accounting note that is not a behaviour change: the *material* column moves for B2, R1 and W3
because the reshaped gate reports candidate counts natively via `GateResult.probes`, whereas the
original probe derived them by hand. Only violations and warnings are compared above.

### 2.4 What the reshape did not fix

The census's other charge against A6/A12 was **multiplicity** — "one cause → dozens of violations",
with spec 19's fold ledger named as the dominant case: 57 rows broken by a single insertion above
them. T1.2 added `Violation.cause` and `count_causes` to address exactly this. On this corpus it
barely moves:

| | violations | causes |
|---|--:|--:|
| A6 + A12, all failing specs, `retro_pre` | 146 | 141 |

**A 3.4% reduction.** The grouping works where the violations share a target file and a failure
kind — spec 14 collapses 4 A6 violations to 1 cause and 2 A12 to 1 — but on spec 19 it collapses
117 violations to 3 grouped causes plus **114 that carry no cause key at all** and therefore each
count as their own. The reason is mechanical: spec 19's violations are the *snippet-mismatch*
class, and only the `out-of-range` / `missing` / `drift-N` classes get a cause key. The census's
own reading — that the corpus's 146 violations trace to "roughly ten distinct causes" — was an
analyst's judgement that the automated grouping does not yet reproduce.

This is not a regression: nothing was lost, and the unit-of-report complaint was never a
correctness claim. It is an **unmet** improvement, and the honest status for the multiplicity
remediation is *not-proven*, not *fixed*.

### 2.5 Artifacts

All under the session scratchpad, alongside the original census's:

| file | what it is |
|---|---|
| `kg_probe2.py` | the reshaped-gate probe — real `check_spec_ready`, native attribution |
| `kg_census2.py` → `census2.json` | the three-tree run under the reshaped gate |
| `kg_census1r.py` → `census1_repro.json` | the pre-reshape gate (`d99523d`) re-run in-session |
| `kg_regress.py` → `regress.json` | reproduction check, regression table, warning deltas |
| `keel_base/` | `src/keel` exported at `d99523d`, the baseline gate |
| `corpus_integrity.json` | per-spec line counts against the census's record |

---

## Part 3 — verdicts, per claim

| # | claim | verdict | on what evidence |
|---|---|---|---|
| 1 | The reshaped gate loses **no** SHARP catch the census recorded | **PROVEN** | 0 lost cells on A5/A6/A11/A12/R1, and 0 lost on every other check; identical specs, trees and violation counts. Baseline re-derived in-session and reproduced the recorded census over 1,083 cells with 0 mismatches |
| 2 | The reshape loses no **warning** either | **PROVEN** | B2's 57 warnings re-attributed to W4 (42) + W5 (15); the reshaped `{B2,W4,W5}` message set is byte-identical to the baseline `B2` set. B1/W2/W3 unchanged |
| 3 | Closing A10's defeats converts it from a cut-candidate into a check with value | **PROVEN** | A10 fires on `2026-07-24-experiment-rigor-skill.md` line 86 in all three trees — a real "enforced" claim whose status is `planned` — where the old gate was silent. 0 → 3 cells, 0 → 1 spec |
| 4 | W1's non-adoption is fixed at the authoring surface | **PROVEN** | W1 material 0 → 19 specs; 0 → 57 warnings, one message form ("this spec is unstamped"). The census's "dead by non-adoption" no longer holds |
| 5 | Cause grouping fixes A6/A12 multiplicity (the NOISY charge) | **NOT-PROVEN** | 146 violations → 141 causes, a 3.4% reduction. On the corpus's dominant case (spec 19) 117 violations collapse to 3 grouped causes plus 114 with no cause key. The grouping covers `out-of-range`/`missing`/`drift-N` and not the snippet-mismatch class that dominates |
| 6 | The kit's **core** is sufficient — the cut prose is unnecessary | **NOT-MEASURABLE (blocked)** | No trial ran; $0.00 spent. The arms are built, hashed, guarded and every free gate passed, but the paid matrix is blocked on an orphaned serialization lock (§1.5) |
| 7 | T0.5's relocation cost nothing | **NOT-MEASURABLE (blocked)** | Same blocker. `a-full-014` → `b-vnext-full` is the arm pair that would answer it, and it has never been measured — the relocation shipped on argument alone |

**Nothing is cut on this evidence.** Claims 6 and 7 are unmeasured, not null; and per the standing
rule a cut requires the instrument to have had the power to see value and to have seen none.
Claim 5 is a named, unmet improvement rather than a defect — the reshaped gate is strictly
better than the one it replaces on every axis measured here.
