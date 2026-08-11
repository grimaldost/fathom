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
- **Revision 2 (2026-08-11, still $0.00 spent).** An adversarial read of revision 1 confirmed
  fifteen defects in this report and in the instrument it describes. They are answered in place
  and listed in Part 4. Three verdicts move: claim 1 is scoped to the checks that had exposure,
  claim 2 splits into a proven half and a not-measurable half, and claim 3 splits into "the check
  fires where it was silent" (proven) and "the fire is a true positive" (not-proven). One new free
  measurement was made to close a gap rather than to describe it: the 44-doc control arm, re-run
  under both gates (§2.5).

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
rule. All three armed bodies stamp `Kit: 0.14.0` and `Kind: series`, so W1 sees no kit skew. The
stamp matching is not the same as the bodies agreeing with the ruler, and they do not — see the
A→B bullet below.

The contrast this buys, and it is the whole point of the fourth arm:

- **A → B** was described in revision 1 as measuring T0.5's relocation. **It does not: the pair is
  not one edit, and the second difference is scored against B.** Both bodies end with a fenced
  block restating the gate's contract, and B's block describes the gate at branch HEAD while the
  oracle is pinned at 0.14.0. The A12 clause is the demonstrated case: B and C tell the author a
  fold-ledger confirmation cell may be `artifact:lo-hi` (`kit-vnext-full.md:135` and `:195`;
  `kit-vnext-core.md:125` and `:185`), and `a-full-014` does not (`kit-full.md:265` says
  `artifact:line`). The pinned oracle is pre-T1.4 — `_oracle/keel/check_ready.py:903`
  `_LEDGER_ANCHOR_RE` has no range group and is `$`-anchored. Demonstrated by mutation, not
  argued: rewriting one confirmation cell in `repair-ledger-drift`'s reference solution from
  `tinyetl/config.py:11` to `tinyetl/config.py:9-11` — exactly what arms B and C are told they may
  do — raises *"no cell in this fold-ledger row is an `artifact:line` confirmation"* and flips
  `gate_part_a_passes` and `ledger_rows_anchor` to False. 17 of 19 criteria are unchanged; the two
  that move are one shared and one behaviour criterion, and the penalty falls only on B and C.
  So A→B measures **the relocation plus a ruler-mismatch penalty in one direction**, and an A-arm
  win on those two criteria is not evidence that the relocation cost anything.
  `tests/test_keel_kit_proof_assets.py` pins the divergence so it cannot be forgotten again.
- **B → C** measures the core cut in isolation — and `c-vnext-core` is a **strict
  order-preserving deletion** of `b-vnext-full` (every non-blank line appears, in order, in B),
  so a B→C gap is attributable to removed prose rather than to a rewrite. The two bodies' fenced
  blocks are **byte-identical** (27 lines each), which is what makes the pair clean on the ruler
  and, for the same reason, incapable of showing a difference on any criterion the fence states.
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

**And most of the cut is invisible to the instrument, which is a separate problem from power.**
Exact diff of the two vNext bodies: 21 removed lines, 231 words.

| what was removed | lines | words | share | a criterion can see it? |
|---|--:|--:|--:|---|
| Definition-of-Ready checklist items — "every invariant … named in Invariants touched, each with an ADR", "every non-obvious design choice has an ADR", "the spec is internally consistent", the post-fold coherence re-read, the eval/experiment measurement-profile item | 11 | 138 | **59.7%** | **no** — no criterion in `keelgate_verify.py` reads any of them |
| the A10 enforcement note, the A9 Reuse-notation note, the A11 anchor-range note | 7 | 93 | 40.3% | yes — `enforcement_claims_clean`, `reuse_refs_resolve`, `range_anchors_balanced` |

At unlimited n and perfect power the bank still cannot see the majority of the words it is being
used to license cutting. A B→C null is therefore evidence about 93 words, not about 231, and the
report of a null must say which. `tests/test_keel_kit_proof_assets.py` asserts the split so a later
asset edit cannot quietly restore the wider claim.

**Effective sample size is smaller than the trial count.** K = 8 briefs sit on **one** code
substrate: all eight tasks stage a byte-identical 12-file `tinyetl` tree, and only `brief.md` /
`spec.md` differ. Anchor resolvability, concept-path resolvability and `§N`-reference resolvability
are properties of that single tree, so behaviour-class outcomes are correlated across tasks and 48
trials are not 48 independent observations. Neither the plan nor revision 1 addressed the
between-task dependence; any "core matches full" null or "full wins" gap read off the per-criterion
table inherits it.

### 1.3 Gates cleared before spend

Every free gate in the discipline passed, in this session, on this worktree:

| gate | result |
|---|---|
| `ruff format --check .` | 801 files already formatted |
| `ruff check .` | all checks passed |
| `uv run pytest` | **641 passed**, 1 skipped, 134 subtests (629 in revision 1; +12 from the guards this revision adds) |
| `fathom validate keel-kit-ablation-v1 --strict` | **24 pass / 0 fail / 0 warn / 0 unverifiable** — see the two paragraphs below for what that does and does not prove |
| `tools/check_skeleton_refs.py keel-kit-ablation-v1` | every task discriminates; **2 of the 6 open tasks do so on a grounding failure**, the rest on construct absence |
| `tests/test_keel_kit_proof_assets.py` | **12 tests** — deletion-only, one-axis, sha pins, shared preamble, and (revision 2) the shared reference fence, the cut pair's identical fence, the relocation pair's differing one, and the cut's invisible share |
| `fathom run … --dry-run` | 4 scenarios × 6 tasks × 2 repeats = **48 trials** |
| resolved `config_hash` per arm | 4 distinct — no resume-key collision |

**What `validate --strict` proves is weaker than the plan claimed.** The plan (§7.5.1) read it as
"every criterion starts false on the unmodified fixture". `src/fathom/validate.py:13-14` defines
`PROP_FIXTURE_FAILS` as *at least one* verifier criterion starting false, and its own docstring
names the gap (`:23-24`): "what this property does NOT catch: a bank whose tasks are simply too
EASY". The command itself prints the fraction — on `repair-ledger-drift`, "3/19 criteria start
false".
Measured on the shipped repair fixtures, **15 of 18 criteria start TRUE on `repair-bijection` and
16 of 19 on `repair-ledger-drift`.** `range_anchors_balanced`, `reuse_refs_resolve` and (on two of
the three repair tasks) `enforcement_claims_clean` all start TRUE — i.e. on the runnable repair
tasks the **entire note-only class is pre-satisfied by the fixture and inherited free by every
arm**, so those tasks cannot show a full-versus-core gap in the one class where the two bodies'
text differs. The cut decision rests on the four authoring tasks alone.

**And the discrimination gate proved presence, not grounding.** Every `refs/skeleton/spec.md`
contains 0 `path:line` anchors, 0 `path:lo-hi` ranges, 0 `**Model-on:**`/`**Reuse:**` fields and no
`## Enforcement status` section; the solutions carry 4–18, 1–2, 1–2 and 1 respectively. The
criteria are conjunctions of presence AND correctness (`anchors_resolve = bool(anchors) and
clean("A6")`), so each of those failures is on the first conjunct. The tool now separates *absent*
from *unresolved* and reports the split: **2 of the 6 open tasks** (`repair-bijection`,
`repair-ledger-drift`) discriminate on a construct that is present and does not resolve; the four
authoring tasks discriminate because the shallow answer omits the construct entirely, which is
instruction-following. That is still a real anti-ceiling property — it is not the grounding
property revision 1 claimed for it.

Still owed, and all requiring the lock: `fathom smoke`, `fathom verify-arming --scenarios-dir
scenarios/keel-kit-proof`, then the matrix.

### 1.4 The budget rail, and a correction to the instruction

The run was specified with `--max-budget-usd 30`. **In fathom that flag is a per-spawn cap, not a
total-run rail** (`src/fathom/adapters/claude_cli.py`, `default_max_budget_usd = 5.0`; the value is
passed straight through to each `claude` spawn). Passing 30 would *raise* the per-spawn ceiling
six-fold and license a 48-trial ceiling near $1,440 — the opposite of a guard.

$30 is therefore read as the **total** ceiling it evidently means, enforced by staging rather than
by the flag:

0. **Cost probe first: `--repeats 1 --limit 2 --max-budget-usd 1.0`.** `fathom run` truncates a
   scenario-major plan (`src/fathom/cli.py:231`, `planned[:limit]`), so a small `--limit` cannot be
   balanced — these two trials are `a-full-014` only and are read for **price, not for signal**.
   Revision 1 dropped the plan's 3-trial pilot when it replaced the unbalanced staging with a
   balanced 24-trial stage, and in doing so removed the only observed-cost checkpoint before a
   24-spawn commitment. It is restored here as its own stage, because the two purposes are
   different: the pilot prices a trial, the balanced stage reads the instrument.
1. `--repeats 1` (24 trials, all four arms × six tasks — balanced; resumes, so the two probe trials
   are not re-spent), per-spawn cap `--max-budget-usd 1.0`, well under the $5 default.
2. Read actual spend from the ledger; the nearest sonnet-5 prior with an injected body
   (`inject-content-v1`) ran $0.368 mean / $0.600 max per trial, so stage 1 projects ≈ $9. If the
   probe measures > $0.80/trial, stage 1 is re-planned before it is run, not after.
3. `--repeats 2` only if stage 1 leaves headroom and the **saturation gate below** passes.
   Absolute worst case across both stages is bounded by the per-spawn cap at 48 × $1.00 = $48, so
   the stage-0 and stage-1 checkpoints are what hold the $30 line — not the flag.

**The saturation gate, amended.** As pre-registered (plan §9.5) it read: "at least 2 of the 3
piloted tasks must show `b-core` OR `c-bare` failing a behaviour or full-only criterion; if fewer,
the bank ceilings — stop." It cannot do its job. §7.7 of the same plan pre-registers that the bare
arm "will fail Part A structurally on the authoring tasks" and that reproducing the bare floor "is
not a finding, it is the floor" — so the only pre-spend anti-ceiling stop rule is satisfied by the
one observation the plan itself calls uninformative, and can never stop the spend on the contrast
that matters. It was also unreadable as specified: a `--limit 3` scenario-major pilot yields three
`a-full` trials and zero `b-core`/`c-bare` trials. The amended rule, read after the **balanced**
stage 1 and before any stage 2:

> At least 2 of the 6 tasks must show an **armed** arm (`a-full-014`, `b-vnext-full` or
> `c-vnext-core`) failing at least one behaviour or note-only criterion. `d-bare`'s failures do not
> count toward it. If fewer do, the armed arms have ceilinged: stop, report still-unmeasured, and
> buy no further stage.

The sealed holdout is **not** spent. The bank seals two tasks precisely because it feeds a
retirement decision, and spending them on a contrast that is pre-registered as probably
underpowered would burn them for nothing. They are worth opening only if the open tasks
discriminate.

Two things about that seal are weaker than ADR-0005 assumes, and both are now recorded in the bank
README. The mandatory pre-spend discrimination tool used to print each sealed task's discriminating
criteria — it iterates every task with a `task.toml` — which handed them to whoever was wording the
arms; it now reports nothing about a sealed task beyond pass/fail and excludes holdouts from its
aggregate. And the holdout is not an independent sample: all 8 tasks stage a byte-identical 12-file
`tinyetl` tree, the criteria are the same, and the holdout briefs reuse dev-task tokens
(`author-refactor-move` ↔ `author-single-change`; `repair-enforcement-overclaim` ↔
`author-schema-evolve`). It is a repeat measurement under a fresh brief. One consequence bites the
cut decision directly: `enforcement_overclaims_absent` — the bank's only criterion that is not a
re-reading of the oracle — exists **only** on the sealed repair task, so on every runnable task the
A10 half of the note-only class is scored by `enforcement_claims_clean` alone, i.e. by the pinned
pre-T1.3 A10 that is known to be defeatable in three reproduced ways. That biases the open tasks
toward "the A10 note buys nothing".

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
    --repeats 1 --limit 2 --max-budget-usd 1.0     # stage 0: price a trial, read no signal
uv run fathom report keel-kit-ablation-v1          # read observed cost/trial, then decide
uv run fathom run keel-kit-ablation-v1 --scenarios-dir scenarios/keel-kit-proof \
    --repeats 1 --max-budget-usd 1.0               # stage 1: balanced 24, resumes the probe
```

### 1.6 The four-arm table, and what each row may be read as

Empty by construction — no trial ran, so every cell is unmeasured. It is published in this shape so
the run fills it in without re-deciding anything.

| criterion class | `a-full-014` | `b-vnext-full` | `c-vnext-core` | `d-bare` | what a gap here means |
|---|---|---|---|---|---|
| ask/shared | — | — | — | — | instruction-following; identical asks by definition |
| behaviour, **rubric-stated** (A6/A5/A8/A12) | — | — | — | — | armed vs bare: possession of the answer key. Armed vs armed: the fence is byte-identical, so a null is guaranteed, not measured |
| behaviour, **unstated** (`criteria_name_runnable_command`, `brief_requirements_covered`) | — | — | — | — | the only criteria no arm's body states; the only uncontaminated armed-vs-bare read this bank has |
| ask/note-only (**the cut decision**) | — | — | — | — | the only class whose asks differ between B and C — though most of the cut words fall outside every class (§1.2). Pre-satisfied on the repair fixtures, so only the four authoring tasks carry it |
| integrity (Goodhart modes) — **tripwire, not a rate** | — | — | — | — | binary and per-trial: did any arm forge, self-anchor, edit the tree or delete the defect. Exclude trials with `spec_written` false |
| cost / trial | — | — | — | — | |

Reading rules, corrected. Revision 1 carried one — read the per-criterion table, not the headline —
and a class definition that was false on inspection.

1. **The behaviour class is not "stated by neither body".** Every armed body ends with a fenced
   reference block that states the oracle's predicates verbatim — `kit-full.md:258-265`,
   `kit-core.md:162-169`, `kit-vnext-full.md:188-195`, `kit-vnext-core.md:178-185` — e.g. "A6 each
   `path:line` anchor: fail unless file exists, line in range, and any quoted snippet … matches"
   (= `anchors_resolve`),
   "A8 each bare intra-spec `§N` reference: fail unless it names a numbered section"
   (= `section_refs_resolve`), "A5 each concept->module path: fail unless exists(path) or 'to be
   created'" (= `concept_map_paths_resolve`), plus A9/A11/A12. `kit-full.md:228-233` restates three
   of them as DoR checklist lines. Both armed arms hold the grader's answer key; the bare arm does
   not. An armed-versus-bare gap on those four measures **rubric possession**, which is exactly the
   contamination the class split was created to exclude — the split narrows it to two criteria
   rather than removing it.
2. **The bank has no *armed but ruler-blind* arm** (the kit with the fence removed), so
   craft-guidance value and rubric possession cannot be separated at any n. Recorded as a named
   limitation; building that arm is a separate run, because removing the fence changes the injected
   body by far more than the edit under study.
3. **The cut is decided on the note-only class, and only if that class was exercised.** A match on
   shared or behaviour is not evidence for the cut: shared is identical by definition, and the
   fence is byte-identical between `b-vnext-full` and `c-vnext-core` (27 lines each, diff empty).
   The pre-registered rule that licensed the cut on "b-core matches a-full on shared **and**
   behaviour" (plan §9.6, row 1) therefore fires on a null guaranteed by construction, and is
   **withdrawn**. What replaces it:

   | observation | decision |
   |---|---|
   | `c-vnext-core` matches `b-vnext-full` across the note-only class, **and** at least one arm failed a note-only criterion somewhere in the matrix (the class was exercised) | the 231-word cut is licensed — with §1.2's coverage caveat, since only 93 of those words are visible to any criterion |
   | no arm ever fails a note-only criterion | the class was pre-satisfied, not passed. No power; cut nothing |
   | `b-vnext-full` beats `c-vnext-core` on note-only | the notes are load-bearing; the cut is falsified |
   | any armed arm forges a certification, self-anchors, edits the staged tree or deletes the defect | reported as a harm the kit caused, whichever arm did it |

4. **The integrity row is a tripwire.** All four criteria are true on all 24 shipped task variants,
   no fixture in the bank trips one, and when no `spec.md` is produced the verifier sets
   `no_self_certification` and `anchors_point_at_staged_files` true by construction
   (`keelgate_verify.py:463-470`) — so a `d-bare` trial that writes nothing scores the row
   perfectly. Averaging it rewards silence. Their failability is demonstrated by negative controls
   in `tests/test_keel_kit_ablation.py`, not by anything in the bank.

A note on the oracle for whoever runs this: `_oracle/` is pinned at keel `2bfc918` with 0.14.0 gate
semantics — i.e. the **pre-reshape** gate. That is deliberate (the ruler must not move while the
kit does), and it has two consequences that are not symmetric between arms. The ablation's
`enforcement_claims_clean` criterion inherits exactly the A10 defeatability that Part 2 measures
and the reshape fixes; and the pinned ruler **actively penalises** the two arms whose body
describes the newer gate (§1.1's A12 range clause). The two halves of this report are independent
instruments and should stay that way.

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

**Lost catches among the 7 checks that ever fired: 0. Lost catches, SHARP only: 0.** The
zero-regression requirement is met on everything the corpus can see.

**And 12 of the 19 checks are unexposed, so nothing was measured about them in either direction.**
The table's caption — "checks that never fired under either gate are omitted" — omits A0, A1, A2,
A3, A4, A7, A8, B1, B2, W1-pre, W2 and W3. They have no discriminating cell in this corpus, so the
census cannot detect a regression in them. A8 is the sharpest instance: **1,230 `§N` references
across 19 specs, zero fires under either gate**, the largest material base in the catalogue — it
could have been broken outright without moving a single cell here. Revision 1 stated this as "0
lost on every other check", which reads as a measurement and is not one. The honest form is the
heading above plus this paragraph.

Two of the five SHARP checks also rest on a thinner base than "SHARP" suggests, and zero loss on
them is correspondingly weaker evidence:

- **A5** — the census's own load-bearing statistic is the *robust core* (a check failing the same
  spec in all three trees). A5's robust core is **0**; it is the only member of the SHARP five with
  none. Its three cells are two different specs that each fire in some trees and not others: spec
  #12 in `retro_pre` and `retro` but not `head` (three paths the wave itself creates), spec #13 in
  `head` only. The census's own reading of A5 rests on the first, in the tree whose named bias in
  the same table is "over-fires on to-be-created targets". A5 is sharp under one tree's bias, and
  the census never stated that as the exception it is.
- **R1** — its entire positive record is one fire on spec #3 (`2026-06-10-fathom-v1-build.md`), and
  R1 shipped in 0.5.0 on 2026-06-13 (`CHANGELOG.md:524,536`). The only document R1 has ever caught
  was written before R1 existed. Its in-method record is 16 further certification opportunities
  with zero fires — structurally the same shape as A3 (0/19 in-method, 7/44 control) and A8 (0/19,
  17/44), which the census classifies "VACUOUS — internalised (power proven)". The 44-doc control
  arm is by construction a corpus of documents not written under the checks, so A1/A3/A4/A8/B1's
  fires are pre-check-era fires too; what distinguished R1 was only that its one pre-check-era
  document happened to sit inside the 19-spec list. Every author after 2026-06-13 knew about R1, so
  it carries the *maximum* in-method survivorship confound, not none.

Neither observation cuts anything: both keep their KEEP disposition, and both now carry the same
forward proof obligation as the rest of the catalogue (the gate ledger's opportunity and fire
counts). What changes is that "the SHARP five survived" is a statement about five checks of very
uneven evidential weight, and the zero-regression criterion inherits that unevenness.

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

**A10 fires where the old gate was silent — which is not the same as retiring the cut candidate,
and revision 1 conflated them.** The census classified A10 as
*VACUOUS — candidate, defeatability confound*: 17 silent opportunities, and a cross-vendor skeptic
panel that had **reproduced** A10 false negatives (line-wrap, backticked invariant names, common-word
negation tokens). Its silence was uninformative in both directions, so no verdict could be taken.
T1.3 closed those three defeats. The reshaped A10 immediately fires on a spec the old gate passed,
in all three trees:

> `2026-07-24-experiment-rigor-skill.md` line 86: claims 'run cross-check equality with a per-tier
> hand policy' is "enforced" but its enforcement status is 'planned'.

That is an enforcement over-claim of exactly the class A10 exists to catch, sitting undetected in
the corpus for the whole life of the old check. **A10 moves from "silence means nothing" to a check
that fires where the old one did not** — and revision 1 then over-read that. Three limits on it:

- **n = 1 spec.** The catch is one line, in one document, reached in all three trees — which is
  three cells of the same observation, not three observations.
- **The adjudication is not independent.** "This is a true positive" was decided by the same agent
  that authored the widening, with no blind check. The evidence is quoted above precisely so a
  second reader can disagree with it; nothing else about the finding is blinded.
- **The widening's false-positive rate is not bounded by the control arm** (§2.5): A10 can only
  fire where an `## Enforcement status` table is present, and **none of the 44 control documents
  has one**. What the in-method corpus does bound is the gross failure mode — 17 tables × 3 trees
  = 51 opportunities, 3 fires, all on the same claim — so the widened A10 is demonstrably not
  firing on everything it touches.

The census's own recorded rule for a repeatedly-widened check ("a third widening means it is being
fitted to noise and re-enters review", `docs/evidence.md`) is the standard this widening was not
held to at the time. §2.5 is that standard applied retroactively, and it is now the standing rule
for the next one.

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

**What that identity does *not* cover: T0.4's change to what `spec_hash` covers.** The commit
(`e2957c6`) names its own blast radius — "changing what is hashed invalidates every `Spec-hash:`
already recorded in a saved pre-mortem artifact across sibling repos" — and this corpus has no cell
that could show it. Measured: **0 of the 19 specs record a `Spec-hash` at all**; 5 name a
certification artifact; and every artifact that resolves already mismatched, which is exactly why
the reshaped W5 set and the baseline B2 set agree string for string. There is no cell in the "hash
matched before" state for the change to break. The byte-identical message set is therefore evidence
that **the instrument cannot see this change**, not evidence that the change is safe — verdict 2b.
The migration it forces (a one-time W5 wave across sibling repos) is recorded in keel's
`docs/cli-reference.md` and remains unmeasured here.

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

### 2.5 The 44-doc control arm, re-run under both gates

The reshape widened three checks — A10's key window from prev/this/next line to the whole paragraph
(`2eeacd2`, `_paragraph_bounds`), W1 to the unstamped case, and A12's ledger regex to accept ranges
— and shipped with no false-positive measurement. `kg-retro.md` built the 44-doc control arm
(design documents in the same repos, never authored to the method) precisely as that probe, and
`kg_census2.py` / `kg_regress.py` contain no control pass: only 19 specs × 3 trees. This is the
missing pass, run free in this session (`kg_control2.py` → `control2.json`): the same 44 documents,
probed under the baseline gate (`keel_base/`, `d99523d`) and the reshaped gate.

| | baseline | reshaped |
|---|---|---|
| documents that fire A1 / A3 / A4 / A5 / A6 / A8 / B1 | 44 / 7 / 44 / 44 / 2 / 17 / 44 | **44 / 7 / 44 / 44 / 2 / 17 / 44** |
| documents that fire anything else (A0, A2, A7, A9, **A10**, A11, **A12**, R1, B2, W4, W5) | 0 | **0** |
| documents that warn W1 | 0 | **44** |
| documents that warn W2 / W3 | 0 / 1 | 0 / 1 |

**The fired set is identical, document for document, on all 19 checks.** The three widenings
introduce no new failure on 44 non-method documents. The one behaviour change is W1's, which is the
intended one: it now warns on every unstamped document, which is every document.

Two honest limits on what that buys, both structural:

- **The control corpus has no material for two of the three widenings.** No control document
  carries an `## Enforcement status` table (A10) or a `### Fold ledger` (A12/A11), so their
  false-positive rate is *unmeasured here*, not measured at zero. What the pass does exclude is a
  widening that fires on ordinary prose generally.
- **A fire on a control document is not a defect** (the census's own rule: these documents were
  never claimed Ready). The comparison that matters is the *delta* between gates, and it is zero.

The rule this makes standing, recorded in keel's `docs/evidence.md`: a check widened to close a
false negative is re-run against the control arm before the widening is called a fix, and a
widening whose control corpus has no material for it is recorded as **unmeasured**, not as safe.

### 2.6 Artifacts

All under the session scratchpad, alongside the original census's:

| file | what it is |
|---|---|
| `kg_probe2.py` | the reshaped-gate probe — real `check_spec_ready`, native attribution |
| `kg_census2.py` → `census2.json` | the three-tree run under the reshaped gate |
| `kg_census1r.py` → `census1_repro.json` | the pre-reshape gate (`d99523d`) re-run in-session |
| `kg_regress.py` → `regress.json` | reproduction check, regression table, warning deltas |
| `kg_control2.py` → `control2.json` | **new in revision 2** — the 44-doc control arm under both gates (§2.5) |
| `kk_material.py` → `kk_material.json` | **new in revision 2** — per-variant criteria states split into absent / fired, the measurement behind §1.3 |
| `keel_base/` | `src/keel` exported at `d99523d`, the baseline gate |
| `corpus_integrity.json` | per-spec line counts against the census's record |

---

## Part 3 — verdicts, per claim

| # | claim | verdict | on what evidence |
|---|---|---|---|
| 1 | The reshaped gate loses **no** SHARP catch the census recorded | **PROVEN, scoped** | 0 lost cells on A5/A6/A11/A12/R1 and on A9/A10; identical specs, trees and violation counts. Baseline re-derived in-session and reproduced the recorded census over 1,083 cells with 0 mismatches. **Scope:** those 7 checks are the only ones with a cell in this corpus. 12 checks never fired under either gate and are unexposed — a regression in them is undetectable here, A8's 1,230-reference base most of all (§2.2). Two of the SHARP five (A5, R1) rest on one non-robust or pre-check-era hit each |
| 2a | The B2 → W4/W5 re-attribution loses no warning | **PROVEN** | B2's 57 warnings re-attributed to W4 (42) + W5 (15); the reshaped `{B2,W4,W5}` message set is byte-identical to the baseline `B2` set. B1/W2/W3 unchanged |
| 2b | T0.4's change to what `spec_hash` covers loses no warning | **NOT-MEASURABLE** | Its own commit message names the blast radius: "changing what is hashed invalidates every `Spec-hash:` already recorded in a saved pre-mortem artifact across sibling repos". Measured: **0 of 19 corpus specs record a `Spec-hash` at all**; 5 name a certification artifact, and every one that resolves already mismatched under BOTH algorithms — the identical `{B2,W4,W5}` message sets are the proof of that. There is not one cell in the corpus in the "hash matched before" state that the change could break, so the byte-identical message set shows the instrument cannot see this change, not that the change is safe |
| 3a | The reshaped A10 fires where the old gate was silent | **PROVEN** | 0 → 3 cells, 0 → 1 spec: `2026-07-24-experiment-rigor-skill.md` line 86, an "enforced" claim whose recorded status is `planned`, in all three trees |
| 3b | That fire is a true positive, i.e. A10 is a check with demonstrated value | **NOT-PROVEN** | n = 1 spec (3 cells of one observation), adjudicated by the agent that authored the widening with no blind check. The control arm cannot bound the false-positive rate because no control document has an Enforcement-status table (§2.5); what it does exclude is a widening that fires on ordinary prose. A10 stays KEEP-and-repaired, not promoted |
| 4 | W1's non-adoption is fixed at the authoring surface | **PROVEN** | W1 material 0 → 19 specs; 0 → 57 warnings, one message form ("this spec is unstamped"). The census's "dead by non-adoption" no longer holds. The control arm shows the same widening at 0 → 44 documents, which is the intended reach and not a false positive |
| 5 | Cause grouping fixes A6/A12 multiplicity (the NOISY charge) | **NOT-PROVEN** | 146 violations → 141 causes, a 3.4% reduction. On the corpus's dominant case (spec 19) 117 violations collapse to 3 grouped causes plus 114 with no cause key. The grouping covers `out-of-range`/`missing`/`drift-N` and not the snippet-mismatch class that dominates |
| 6 | The kit's **core** is sufficient — the cut prose is unnecessary | **NOT-MEASURABLE (blocked, and narrower than it looks)** | No trial ran; $0.00 spent. Blocked on an orphaned serialization lock (§1.5). Independently of the lock, the instrument can only see 93 of the 231 cut words (§1.2), and only through the four authoring tasks (§1.3) |
| 7 | T0.5's relocation cost nothing | **NOT-MEASURABLE (blocked and confounded)** | Same blocker, plus §1.1: `a-full-014` → `b-vnext-full` is not one edit. B's body describes the post-T1.4 gate while the oracle is pinned pre-T1.4, and an arm that follows B's own instruction on a fold-ledger range cell loses `gate_part_a_passes` and `ledger_rows_anchor`. The pair would have to be re-cut, or the two criteria excluded, before it could answer this |

**Nothing is cut on this evidence.** Claims 6 and 7 are unmeasured, not null; and per the standing
rule a cut requires the instrument to have had the power to see value and to have seen none.
Claim 5 is a named, unmet improvement rather than a defect — the reshaped gate is no worse than the
one it replaces on every axis measured here, and better on W1's reach and A10's exposure.

---

## Part 4 — what revision 2 corrected

Fifteen confirmed defects. Every one is answered above; this table exists so a reader of revision 1
can find what moved, and so no correction is left as a note in a commit message.

| # | defect in revision 1 / the instrument | where it is answered | what changed |
|---|---|---|---|
| 1 | The behaviour class was defined as "stated by NEITHER body". Every armed body's fenced reference block states four of its six predicates verbatim | §1.6 rule 1; `keelgate_verify.py` docstring; `bank.toml`; the bank README | class redefined and split into rubric-stated / unstated; the missing *ruler-blind* arm recorded as a limitation |
| 2 | The pre-registered cut rule fired on a null guaranteed by construction — B's and C's fences are byte-identical, and shared is identical by definition | §1.6 rule 3 | the rule is withdrawn and replaced; the cut is decided on the note-only class, and only if that class was exercised |
| 3 | The discrimination gate proved construct-presence and called it grounding | §1.3; `tools/check_skeleton_refs.py` | the tool splits absent / unresolved / content and reports 2 of 6 open tasks on grounding |
| 4 | `validate --strict` was described as "every criterion starts false"; it asserts *at least one* | §1.3 | measured: 15/18 and 16/19 criteria start TRUE; the note-only class is pre-satisfied on the repair tasks |
| 5 | The integrity class had no negative control and defaults to PASS when nothing is written | §1.6 rule 4; `tests/test_keel_kit_ablation.py` | read as a tripwire, excluded from averages; six negative controls added |
| 6 | A→B was called one edit; the pinned ruler penalises the newer kit's own instruction | §1.1; `tests/test_keel_kit_proof_assets.py` | confound stated, demonstrated by mutation, pinned by a test; claim 7 downgraded |
| 7 | 59.7% of the B→C cut is invisible to every criterion | §1.2 + its table | measured and asserted by a test |
| 8 | R1 classified SHARP on a pre-check-era document with maximum in-method survivorship confound | §2.2; keel `docs/evidence.md` | reclassified in prose, KEEP retained, forward obligation added |
| 9 | A5 classified SHARP against the census's own load-bearing statistic (robust core 0) | §2.2; keel `docs/evidence.md` | stated as the exception it is |
| 10 | "Lost catches, all checks: 0" over-claimed — 12 checks are unexposed | §2.2; claim 1 | restated and scoped |
| 11 | Claim 2 read a saturated cell as a verdict: 0/19 specs record a `Spec-hash` | claim 2b | split; the T0.4 half is NOT-MEASURABLE |
| 12 | Three widenings shipped with no control-arm re-run | §2.5 (new measurement); keel `docs/evidence.md` | the control arm re-run under both gates — identical fired sets; the standing rule recorded |
| 13 | The saturation gate was vacuous (satisfiable by the bare floor) and unreadable (`--limit 3` yields three `a-full` trials); the balanced stage removed the cost checkpoint | §1.4 | gate amended to read armed arms only after a balanced stage; a 2-trial cost probe restored ahead of it |
| 14 | The mandatory pre-spend discrimination tool printed the sealed tasks' discriminating criteria; and the holdout is not an independent sample | §1.4; `tools/check_skeleton_refs.py`; bank README | the leak is closed (sealed tasks report pass/fail only, and are excluded from the aggregate); the weak independence is recorded, not repaired |
| 15 | Effective sample size overstated — K = 8 briefs on one code substrate | §1.2; bank README | between-task dependence stated; a null or a gap off the per-criterion table inherits it |

One item is recorded rather than repaired, because repairing it means building a different
instrument: the bank has no *armed but ruler-blind* arm (§1.6 rule 2), so craft-guidance value and
rubric possession cannot be separated at any n. Two others are repaired only as far as disclosure
allows — the A→B pair stays confounded until the arms are re-cut (defect 6), and the holdout stays
a repeat measurement over the same tree (defect 14).
