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

- **ask/shared** — stated by both injected bodies. A gap here is the extra ~1,680 words buying
  compliance with something both arms already asked for: instruction-following, not value.
- **behaviour** — stated by neither, in these words. Do the anchors resolve, do the concept paths
  exist, do the section references land, do the acceptance criteria name something runnable, is
  the brief covered. The load-bearing class.
- **ask/note-only** — stated by the full body as a worked template note, and by the core body only
  as one line of the fenced reference list (A9 reuse refs, A10 enforcement claims, A11 range
  anchors). This class **is** the ~490-word cut decision. It is deliberately not called
  "full-only": the core keeps the whole reference fence, so the contrast is worked-note versus
  one-line entry, not presence versus silence.
- **integrity** — the Goodhart modes, and the only criteria that can fail *worse* in an armed arm
  than in the bare one: forging a certification, anchoring at a file the arm wrote itself, editing
  the staged tree so a stale anchor resolves, deleting the defective section instead of repairing
  it. An armed arm that games or forges is a harm the kit caused, and it is reportable as such.

One criterion, `enforcement_overclaims_absent` (holdout task only), is the bank's own predicate
rather than a reading of the oracle: it is a strictly stronger shadow of the gate's A10 that does
not let an invariant key containing a negation word suppress claims about itself.

## The oracle, and the circularity

The structural criteria are decided by the readiness gate itself, vendored byte-for-byte into
`_oracle/` and sha256-pinned in `_oracle/PIN.json`. The verifier asserts the pin at start-up and
refuses to score if it moved; it also reports (never acts on) divergence from the live checkout
the copy was taken from. The gate runs `structure_only`: Part B needs a non-author reviewer, which
no arm has, so scoring it would fail every arm identically.

The oracle is a component of the artifact under study. Three consequences, which belong at the top
of the report and not in a footnote:

1. The armed arms are handed a description of the ruler. `a-full` is advantaged on anything the
   kit states verbatim, which is why the classes are split and why **behaviour** is load-bearing.
2. What is measured is gate-satisfaction and prose-necessity, at one model tier. Not whether the
   spec is right, not whether the feature ships, not whether the wave succeeds.
3. A null licenses cutting **prose**. It licenses nothing about any check.

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

## Pre-registered, before the data arrives

- `c-bare` fails the shared class structurally on the authoring tasks. The nearest prior had its
  bare arm fail 11 of 12 criteria; reproducing that is the floor, not a finding.
- `b-core` matching `a-full` is a **reproduction**, not a surprise: in the nearest prior, a
  225-word core matched a 2,429-word body on nine of twelve criteria.
- A full arm *worse* than core on `brief_requirements_covered` is a live hypothesis, not a fluke:
  piling requirements together has a measured collective-degradation effect.
- All three arms passing everything is a **ceiling** — the bank had no power. Report
  still-unmeasured and cut nothing.
