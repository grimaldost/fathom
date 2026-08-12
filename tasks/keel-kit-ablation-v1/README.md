# keel-kit-ablation-v1

Is the spec kit's **prose** necessary to produce a design spec that the method's own readiness
gate accepts?

Three arms, differing in exactly one thing — the body injected into the spawn's system prompt:

| arm | injected body | words |
|---|---|---:|
| `a-full` | today's kit: the spec template + the Definition of Ready, verbatim | 3,789 |
| `b-core` | a candidate core — a **strict deletion** of the full body, nothing reworded | 2,109 |
| `c-bare` | nothing | 0 |

Arms live in `scenarios/keel-kit/`, so **`--scenarios-dir scenarios/keel-kit` is mandatory** on
every `fathom run` against this bank; `fathom run` globs `scenarios/` by default and would
silently run the wrong arms.

`scenarios/keel-kit-proof/` holds the four arms the executed plan uses instead — `a-full-014`
(this table's `a-full`, injected by path), `b-vnext-full`, `c-vnext-core`, `d-bare` — because the
kit itself moved between authoring and running, so "full versus core" became two edits. See
`docs/reports/2026-08-11-keel-kit-ablation-proof.md` §1.1.

## The tasks

Six development tasks and two sealed holdout, all staged against one invented package (`tinyetl`,
a small batch loader for order records). No fixture is a method document and no brief is about
specs, gates or method: an arm that could read the material under measurement is not an arm.

| id | shape | what it exercises |
|---|---|---|
| `author-cli-flag` | authoring | anchors into staged files, concept map, a five-PR manifest |
| `author-schema-evolve` | authoring | requirement coverage, "to be created" claiming, a version bump |
| `author-two-consumer` | authoring | naming what a change reaches, in the spec's own text |
| `author-single-change` | authoring | the relaxation path — a one-PR change whose correct declaration is `single-change` |
| `repair-bijection` | repair | a broken PR↔section bijection and a concept row naming a module that is not there |
| `repair-ledger-drift` | repair | twelve fold-ledger rows uniformly shifted, one row missing a cell |
| **holdout** `author-refactor-move` | authoring | sections that relocate files — the pre-move anchor trap |
| **holdout** `repair-enforcement-overclaim` | repair | enforcement over-claims, including forms the gate's own window heuristic misses |

Holdouts are sealed (ADR-0005) because this bank feeds a retirement decision. Run them
deliberately with `--include-holdout`; the trials are marked holdout in the ledger.

## Criterion classes — the report must keep them apart

`keelgate_verify.py` scores four classes, and reading the headline pass-rate instead of the
per-criterion table is how a previous run in this repo was misread.

- **ask/shared** — stated by both injected bodies. A gap here is the extra words buying compliance
  with something both arms already asked for: instruction-following, not value.
- **behaviour** — do the anchors resolve, do the concept paths exist, do the section references
  land, do the acceptance criteria name something runnable, is the brief covered. The closest
  deterministic proxy to groundedness this bank has — **and a contaminated class.** Every armed
  body ends with the same fenced reference block, and that block states four of the six predicates
  in the oracle's own words (A6, A5, A8, A12/R1). The armed arms hold the grader's answer key for
  those four, the bare arm does not, so an armed-versus-bare gap on them measures rubric
  possession. Only `criteria_name_runnable_command` and `brief_requirements_covered` are stated by
  no body. Armed-versus-armed stays readable because the fence is byte-identical across armed
  bodies — which is also why a full-versus-core null on those four is guaranteed by construction
  rather than measured. The bank has no *armed but ruler-blind* arm (the kit minus the fence), so
  craft-guidance value and rubric possession cannot be separated at any n.
- **ask/note-only** — stated by the full body as a worked template note, and by the core body only
  as one line of the fenced reference list (A9 reuse refs, A10 enforcement claims, A11 range
  anchors). It is deliberately not called "full-only": the core keeps the whole reference fence, so
  the contrast is worked-note versus one-line entry, not presence versus silence. **This is the
  only class whose asks differ between the two bodies** — shared is identical by definition and the
  fence is byte-identical — so it is the only class the cut decision can be read from. Most of what
  the core drops is prose no class covers at all, which is a coverage gap, not a null. Two further
  measured limits: the repair fixtures start it entirely TRUE
  (every arm inherits it free there), and on the authoring tasks it fails the skeleton by construct
  *absence*, so it measures whether the note causes the construct to be written, not written well.
- **integrity** — the Goodhart modes, and the only criteria that can fail *worse* in an armed arm
  than in the bare one: forging a certification, anchoring at a file the arm wrote itself, editing
  the staged tree so a stale anchor resolves, deleting the defective section instead of repairing
  it. An armed arm that games or forges is a harm the kit caused, and it is reportable as such.
  **Read this class as a tripwire, never as a rate:** all four are true on all 24 shipped task
  variants, no fixture trips one, and a trial that writes no spec at all scores two of them true by
  construction. Exclude any trial with `spec_written` false from the row instead of counting it
  clean. `tests/test_keel_kit_ablation.py` carries one negative control per criterion, so "always
  true" cannot quietly mean "cannot fail".

One criterion, `enforcement_overclaims_absent` (holdout task only), is the bank's own predicate
rather than a reading of the oracle: it is a strictly stronger shadow of the gate's A10 that does
not let an invariant key containing a negation word suppress claims about itself.

## The oracle, and the circularity

The structural criteria are decided by the readiness gate itself, vendored byte-for-byte into
`_oracle/` and sha256-pinned in `_oracle/PIN.json`. The verifier asserts the pin at start-up and
refuses to score if it moved; it also reports (never acts on) divergence from the live checkout
the copy was taken from. The gate runs `structure_only`: Part B needs a non-author reviewer, which
no arm has, so scoring it would fail every arm identically.

The oracle is a component of the artifact under study. Four consequences, which belong at the top
of the report and not in a footnote:

1. The armed arms are handed a description of the ruler — literally: the fenced reference block at
   the end of every armed body states the gate's predicates verbatim.
2. That reaches further than the class split first admitted. It covers four of the six *behaviour*
   criteria, so the split narrows the contamination but does not remove it, and only an
   armed-versus-armed contrast holds the fence constant. See the class list above.
3. What is measured is gate-satisfaction and prose-necessity, at one model tier. Not whether the
   spec is right, not whether the feature ships, not whether the wave succeeds.
4. A null licenses cutting **prose**. It licenses nothing about any check.

## Before any spend

```sh
uv run ruff format --check . && uv run ruff check . && uv run pytest
uv run fathom validate keel-kit-ablation-v1 --strict
python tools/check_skeleton_refs.py keel-kit-ablation-v1
uv run fathom smoke
uv run fathom verify-arming --scenarios-dir scenarios/keel-kit
uv run fathom run keel-kit-ablation-v1 --scenarios-dir scenarios/keel-kit --repeats 1 --dry-run
```

`tools/check_skeleton_refs.py` is the discrimination gate `fathom validate` does not have: each
authoring task ships `refs/skeleton/` — the spec a competent author writes from the headings alone
— and it must pass the shared class while failing at least one behaviour or note-only criterion. A
task whose skeleton passes everything rewards structure only and is re-authored before the bank
runs. Repair tasks are held to the matching property: the planted defect must show outside the
shared class.

**What that gate proves here, measured.** It splits each failure into *absent* (the construct is
not in the document, so the criterion fails on its presence conjunct), *unresolved* (the construct
is present and the oracle fires — a grounding failure) and *content*. On this bank, **2 of the 6
open tasks discriminate on a grounding failure**; the four authoring tasks discriminate because the
skeleton omits anchors, ranges, `Reuse:` fields and the Enforcement-status table entirely. That is
real discrimination, but it is instruction-following: an arm told the construct exists writes one
and passes. Do not read those four as evidence about grounding.

`fathom validate --strict` proves less than its name suggests and is not a substitute: its property
is *at least one* criterion false on the unmodified fixture, and on the shipped repair fixtures 15
of 18 and 16 of 19 criteria start TRUE. In particular the whole note-only class starts TRUE on the
runnable repair tasks and is inherited free by every arm.

**Holdouts stay sealed through this gate.** `check_skeleton_refs.py` runs against every task,
holdouts included, but reports nothing about a sealed one beyond pass/fail, and excludes them from
its aggregate — a mandatory pre-spend tool that printed a sealed task's discriminating criteria
would hand them to whoever is wording the arms.

**Independence of the holdout is limited, and the limit is measured.** All 8 tasks stage a
byte-identical 12-file `tinyetl` tree (only `brief.md` / `spec.md` differ), the criteria are the
same, and the holdout briefs reuse dev-task tokens (`author-refactor-move` ↔ `author-single-change`
on `normalize_currency`; `repair-enforcement-overclaim` ↔ `author-schema-evolve` on `retry_after_s`
/ `schema_version` / `migrate_v1_to_v2`). Treat the holdout as a repeat measurement under a fresh
brief, not as the fresh sample ADR-0005 sealing assumes. One criterion,
`enforcement_overclaims_absent`, exists **only** on the sealed repair task — so on every runnable
task the A10 half of the cut decision is scored by `enforcement_claims_clean` alone, i.e. by the
pinned pre-T1.3 A10 that is known to be defeatable in three reproduced ways. That biases the
note-only class toward "the A10 note buys nothing" on exactly the tasks the budget will run.

## Pre-registered, before the data arrives

- `c-bare` fails the shared class structurally on the authoring tasks. The nearest prior had its
  bare arm fail 11 of 12 criteria; reproducing that is the floor, not a finding. **It therefore
  cannot satisfy an anti-ceiling stop rule** — the saturation gate reads armed arms only.
- `b-core` matching `a-full` is a **reproduction**, not a surprise: in the nearest prior, a
  225-word core matched a 2,429-word body on nine of twelve criteria.
- A full arm *worse* than core on `brief_requirements_covered` is a live hypothesis, not a fluke:
  piling requirements together has a measured collective-degradation effect.
- All three arms passing everything is a **ceiling** — the bank had no power. Report
  still-unmeasured and cut nothing.
- **The cut is decided on the note-only class, and only when that class was exercised.** A match on
  shared or behaviour is not evidence for it: shared is identical by definition and the reference
  fence is byte-identical across armed bodies, so a null there is guaranteed by construction. If no
  arm ever fails a note-only criterion anywhere in the matrix, the class was pre-satisfied and the
  correct report is *no power*, not *no difference*.
- **K is 8 briefs on n=1 code substrate.** Anchor, concept-path and section-reference resolvability
  are properties of the one staged tree, so behaviour-class outcomes are correlated across tasks:
  48 trials are not 48 independent observations, and neither a null nor a gap read off the
  per-criterion table should be treated as though they were.
