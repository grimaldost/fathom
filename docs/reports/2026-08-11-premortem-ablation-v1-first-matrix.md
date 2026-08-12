# Ablating the pre-mortem directive — premortem-ablation-v1, first matrix

- **Date:** bank authored, run and reported 2026-08-11 (wave 2, branch `eval/wave-2`).
- **Gate:** keel's **KEEL-B09** — ~2,300 words of directive are dispatched on every pre-mortem and no
  with/without measurement has ever been run on them. The decision rule the item states is blunt:
  **retire every directive arm B matches.**
- **Verdict: on the structural axis, arm B matches arm A completely, at ~80% of the cost.** The
  finding-quality axis is not measured here and the retirement should not be taken on this alone.

## The three arms

| Arm | Treatment | Size |
|---|---|---|
| `arm-a-full` | the full directive: keel 0.14.0's `pre-mortem-prompt.md` `## Prompt` block plus its `## Output handling` section, verbatim | **15,619 bytes / 2,429 words** |
| `arm-b-core` | a ~500-word core: blind non-author, cite `file:line`, severity + `smallest_fix` + `disconfirming_test` + verdict token, in the same YAML shape | **1,471 bytes / 225 words** |
| `bare` | no directive at all — a bare adversarial spec review | — |

A **10.6× compression** on the injected body. The arms differ in nothing else: same model
(`claude-opus-4-8`, high effort), same tools (`Read`/`Grep`/`Glob`/`Write`, matching the bundled
reviewer agent's declared set plus the Write the task needs), same 900 s / 40-turn caps, same tasks.

**Which copy was exercised:** the directive was extracted from the **worktree** at
`C:/Users/grima/Documents/keel/src/keel/templates/pre-mortem-prompt.md` on merged `main` (keel
0.14.0), not from the installed plugin cache, which trails at 0.13.1. `fathom verify-arming` observed
both bodies in the real spawn argv at 15,619 and 1,471 bytes.

## The bank, and the two traps it was built around

`tasks/premortem-ablation-v1/` — 8 historical design specs, one task each, reviewed adversarially
before any code. **6 dev, 2 sealed holdout** (ADR-0005; this bank feeds a retirement decision).
Fixtures are the spec plus the repo-relative source files the spec names, staged at their real paths.

**Circular-eval discipline.** Not one task is built from the material under measurement. The
directive lives in keel; every staged spec comes from a **sibling** repo, so no fixture is a document
the directive was authored against or tuned on. Neither `docs/` nor another spec is staged into a
fixture: a second spec would be a second review surface, and a findings report postdates the spec it
reports on.

**What the verifier scores, and what it refuses to.** `premortem_verify.py` scores the **structural
contract** — 12 deterministic criteria — and deliberately does *not* adjudicate whether an emitted
finding is a real BLOCKER, nor the false-positive rate. Matching paraphrased findings against a truth
list is a judge, and a paraphrase scored as a miss manufactures a null in the compressed arm's
favour, which is the direction the decision already leans. That adjudication is a separate human pass
and is not in this bank.

The criteria split three ways, and the whole result lives in keeping them apart:

| class | criteria | what a gap means |
|---|---|---|
| **ask/shared** — both A and B request it | `findings_written`, `findings_ge_3`, `severity_vocabulary`, `every_finding_cites_evidence`, `every_finding_smallest_fix`, `every_finding_disconfirming_test`, `verdict_token` | the extra 1,800 words buying compliance with something both arms already asked for |
| **behaviour** — neither requests it in these words | `citations_path_exists`, `citations_line_in_range` | whether the emitted anchors resolve to a real file at a real line in the surface the reviewer was given — the closest deterministic proxy to groundedness, and the load-bearing pair |
| **ask/full-only** — only A requests it | `reviewer_identity`, `target_section_present`, `unverified_offline_line` | what compression costs in **form**; not evidence about finding quality |

## What was checked before spending

| Gate | Result |
|---|---|
| `uv run fathom smoke` | **ALL PASS (8/8)**, and again on resume |
| `uv run fathom validate premortem-ablation-v1` | **16 pass, 0 fail, 0 warn, 8 unverifiable** — 12/12 criteria start false on every unmodified fixture, and a shipped reference solution satisfies the verifier on all 8 tasks, so a null cannot be an unsatisfiable-verifier artifact |
| `uv run fathom verify-arming --scenarios-dir scenarios/premortem-ablation` | ALL VERIFIED (both bodies in the real argv, at their declared sizes) |
| `--dry-run` | 18 trials, ceiling $36.00 |
| cost pilot | `--limit 3` on the most expensive arm first, to set the rail from an observed figure rather than a guess |

**The prior was recorded before the run, as the skeleton demands:** FATH-B35 measured an in-session
structured review pass at the strong tier as **+0** against the same strategy without it, and `bare`
is the closest analogue. A +0 across all three arms would have been a reproduction, not a surprise.

## Result — 3 arms × 6 dev specs × 1 repeat = 18 trials, $20.13

### Per-criterion. The headline pass-rate is actively misleading here and the scorecard says so.

| Criterion | class | `arm-a-full` | `arm-b-core` | `bare` |
|---|---|---|---|---|
| `findings_written` | shared | 6/6 | 6/6 | 6/6 |
| `findings_ge_3` | shared | 6/6 | 6/6 | **0/6** |
| `severity_vocabulary` | shared | 6/6 | 6/6 | **0/6** |
| `every_finding_cites_evidence` | shared | 6/6 | 6/6 | **0/6** |
| `every_finding_smallest_fix` | shared | 6/6 | 6/6 | **0/6** |
| `every_finding_disconfirming_test` | shared | 6/6 | 6/6 | **0/6** |
| `verdict_token` | shared | 6/6 | 6/6 | **0/6** |
| `citations_path_exists` | **behaviour** | 6/6 | **6/6** | **0/6** |
| `citations_line_in_range` | **behaviour** | 6/6 | **6/6** | **0/6** |
| `reviewer_identity` | full-only | 6/6 | **0/6** | 0/6 |
| `target_section_present` | full-only | 6/6 | **0/6** | 0/6 |
| `unverified_offline_line` | full-only | 6/6 | **0/6** | 0/6 |
| **all-criteria** | | **6/6** | 0/6 | 0/6 |

Fisher exact two-sided, **p = 0.0022** for every 6/6-vs-0/6 cell. Arm A beats `bare` on ten criteria
at that p. Arm A beats arm B on **exactly three** — the three the core was never told to emit — and on
the other nine the two arms are **identical, 6/6 against 6/6, p = 1.0**.

**Read the headline row and you get the opposite answer.** The scorecard's Pass Rates table says
`arm-b-core` 0.0% and `bare` 0.0%, which reads as "the compressed core is no better than no directive
at all". That is false: the core matches the full directive on nine of twelve criteria including both
grounding checks, and beats `bare` on eight. The all-truthy pass rate collapses because of three
formatting conventions. This is FATH-B08's argument arriving as a concrete instance rather than a
prediction.

### Economy — the compressed arm is the cheapest and the fastest

| Arm | n | Turns min/med/max | In+out tokens min/med/max | $/trial (total) | Mean wall |
|---|---|---|---|---|---|
| `arm-a-full` | 6 | 5 / 10 / 13 | 15,057 / 23,788 / 28,886 | **$1.27** ($7.61) | 333 s |
| `arm-b-core` | 6 | 5 / **7** / 13 | 13,345 / **17,664** / 22,488 | **$1.01** ($6.05) | **257 s** |
| `bare` | 6 | 5 / 9 / 12 | 10,789 / 18,803 / 21,933 | $1.08 ($6.47) | 274 s |

Arm B runs at **80% of arm A's cost**, **74% of its median tokens** and **77% of its wall-clock**, for
identical structural output on everything both arms asked for. No trial in any arm came near the
40-turn cap (max 13), so no arm's rate is a truncation lower bound.

## Verdict against KEEL-B09's own decision rule

**On the axis this bank can measure, arm B matches arm A, and the rule fires.** The ~1,800 words
beyond a ~500-word core bought **nothing measurable** on the structural contract or on citation
groundedness — including the grounding checks, which are the closest thing here to a quality proxy and
which neither arm was explicitly told to satisfy. They bought three output-format conventions
(`reviewer_identity`, `target_section_present`, `unverified_offline_line`), and each of those is a
line of prose the core could carry for a few dozen words if it is wanted.

**And the directive as a whole is not worthless.** `bare` fails eleven of twelve criteria: a bare
adversarial review returns prose, not a machine-greppable contract, and a caller that gates on the
verdict token gets nothing to gate on. The value is overwhelmingly in *being asked at all* — which the
500-word core delivers in full.

### What this does NOT settle, stated plainly

1. **Finding quality is unmeasured.** Whether an emitted finding is an adjudicated real BLOCKER, and
   the false-positive rate, are the half the gate-banks spec assigned to a blinded human pass over the
   outputs. Eighteen blinded finding-lists now exist in the workspaces; the pass has not been run.
   **A retirement taken on this report alone would be retiring prose on a form check.**
2. **n = 1 per cell.** K = 6 distinct specs is the strength here (the interval is not one task's), but
   there is one trial per cell. Every observed cell is 6/6 or 0/6 with no variance at all, which is
   why p = 0.0022 despite the small n — but a criterion that is *nearly* saturated would be
   indistinguishable from one that is fully saturated at this power.
3. **Two specs are sealed** and were not run. Any tuning of arm B's wording against these results must
   be validated on the holdout, not on these six.
4. **Every spec is a design spec from one sibling repo.** The directive's SERIES-pass checklist,
   re-gate posture and rising-bar clauses address a *second-round* review over a decomposed PR set,
   which this bank never exercises. A round-2 ablation would be a different bank, and those clauses
   are exactly where the full body's remaining value would have to live if it has any.

**Recommended next step, in the spec's own terms:** run the blinded adjudication pass over the 18
existing finding-lists before touching the directive. If arm B's findings adjudicate as well as arm
A's, the rule fires on both axes and the compression is safe. If they do not, this report has located
precisely where the remaining value is — and it is not in the form.

## Two operator notes this run earned

- **A ~90-minute matrix has no progress signal and no closing summary.** The run was killed by the
  harness at trial 15 of 18 and its buffered stdout was lost with it; the only way to see where it had
  got to, throughout, was `wc -l` on the ledger. Resume was free and correct (append-only, dedupe on
  the resume key) and `fathom smoke` was re-run before resuming as the invariant requires — but this
  is FATH-B13 costing an operator directly rather than in principle.
- **`--limit N` is scenario-major, and that is the right shape for a cost pilot.** Three trials on the
  *most expensive* arm first gave a real $/trial figure before the rail was set, which is what the
  gate-banks spec asks for after last wave lost $2.04 to a cap set from a guess.

## Why the matrix stopped at one repeat

The skeleton priced the full design — 3 arms × 8 specs × 3 repeats = 72 trials — at **$11–43, most
likely ~$20**, from an assumed $0.15–0.60 per trial. The observed figure on this seat is **$1.12 per
trial**, roughly 2–7× that assumption, because a strong-tier spec review here costs about what a
strong-tier build costs elsewhere in the corpus.

At that rate the designed matrix over the 6 dev specs (3 × 6 × 3 = 54 trials) prices at **~$60** —
above the top of the skeleton's range and about **3×** its point estimate. The wave's own rail says a
plan exceeding its estimate by more than 50% is recorded and not run, so it was recorded and not run.
Repeats were the right thing to drop: every cell came back 6/6 or 0/6 with zero within-arm variance,
so the second and third repeats would have bought confirmation of a signal that is already at
p = 0.0022 — while **K**, the number of distinct specs, is what actually widens the claim, and this
matrix already spends its whole budget on K = 6 rather than on K = 2 with repeats.

| plan | trials | est. cost | run? |
|---|---|---|---|
| 3 arms × 6 dev specs × 1 repeat | 18 | $20.13 **actual** | **yes** |
| 3 arms × 6 dev specs × 3 repeats | 54 | ~$60 | no — over the rail |
| the two sealed holdout specs, 3 arms × 1 repeat | 6 | ~$7 | no — held for validating any arm-B rewording |
| the blinded human adjudication pass over the 18 finding-lists | 0 | operator time, no tokens | not run — and it is the half that settles the gate |

## Ledger

`ledger/premortem-ablation-v1.jsonl`, `dataset_version = 1`. 18 completed trials, 0 errored, 0 infra,
$20.13.
