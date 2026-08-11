# verif-lift — the verification-lift banks

Six generated banks and five scenario directories measuring whether a verification
discipline delivered as prose, as a stop gate, or not at all changes what an agent
leaves behind. Everything under `tasks/verif-lift-*-v1/` is generated from the spec
tables here; edit the tables and regenerate, never the emitted tasks.

```sh
uv run python tasks/verif-lift-authoring/generate.py   # emit the banks, proving as it goes
uv run python tasks/verif-lift-authoring/arming.py     # prove every criterion two-sided
uv run fathom validate <bank> --strict                 # the harness's own triad
```

Both scripts are free — local verifier runs, no spawns.

## The banks

| bank | class | tasks | sealed holdout | criteria (all "good when true") |
|---|---|---|---|---|
| `verif-lift-bug-v1` | BUG | 22 | 2 | `spec_met`, **`regression_check_present`**, `proxy_instrument_ok` |
| `verif-lift-data-v1` | DATA | 22 | 2 | `spec_met`, **`regression_check_present`**, `output_correct_on_subtle_case`, `proxy_instrument_ok` |
| `verif-lift-trunc-v1` | TRUNC | 11 | 1 | `spec_met`, **`defect_past_slice_handled`** |
| `verif-lift-null-v1` | NULL | 7 | 1 | `spec_met`, **`scope_respected`** |
| `verif-lift-bug-strong-v1` | BUG | 12 | — | as BUG |
| `verif-lift-data-strong-v1` | DATA | 12 | — | as DATA |

Primary criterion in bold. `scope_respected` is the false-positive guard: the
program's `over_scope` is `1 - scope_respected`. The strong banks hold a
**pre-declared subsample** — the first 12 non-holdout tasks of the class in
spec-table order, fixed in `generate.py` before any trial — so the tier by arm
interaction is computed on the same tasks at both tiers. Their task files are
asserted byte-identical to the weak banks' armed copies.

**One bank per class, not one bank.** fathom selects tasks by bank and runs one
scenario matrix per bank. The plan gives different classes different arms (the
placebo rides only on the code class and the null bank) and the strong tier a
subsample, and neither is expressible inside a single bank. Pooling BUG and DATA on
the footprint criterion is done in analysis, across two ledgers, which is what the
plan asks for anyway.

## The footprint proxy

`_lib/proxy.py` (generated from `proxy_lib.py`) extends the `e1-verif` swap-the-
work-back proxy in the two places that decide whether the instrument can be trusted.

**The revert is an inverse edit, not a checkout.** `e1-verif` wrote the whole
stashed original over the candidate's module file, discarding whatever else the
candidate put there and manufacturing reds unrelated to any guard. Here the revert
replaces exactly one function's source segment — located with `ast` on the
candidate's own file — and asserts byte equality of every byte outside it. That is
the discipline the measured skill states as a bright line, and a bank measuring the
discipline has to obey it.

**A red counts only when it is an assertion failure.** Reverting new code commonly
makes a check *error*: an import failure, a `TypeError` from a signature the
candidate widened. Scoring an error as a caught regression manufactures lift out of
nothing. The check harness reports failures and errors separately, and an error-only
red scores the proxy False while flipping `proxy_instrument_ok`, so the vacuous-red
rate is recoverable per cell instead of silently inflating a lift.

`proxy_instrument_ok` also goes False when the defect IS fixed but the target
function is byte-identical to the original — the fix lives outside the reverted unit,
so reverting it reverts nothing and the probe reads nothing. That is an instrument
miss, and the honest reading is "this trial carries no measurement", not "no guard".

## What arming proves, and why validate is not enough

`fathom validate` proves two points of the curve: the verifier fails on the
unmodified fixture, and passes on the reference solution. It says nothing about the
criteria that are *already true* on the fixture — `scope_respected` and
`proxy_instrument_ok` — so a bank can pass validation while carrying a criterion
never observed false. A check seen only green is indistinguishable from one that
tests nothing.

`arming.py` walks every task through counterexample workspaces shipped in `refs/`,
runs the real `verify.py` against each, and requires the observed criteria to match a
declared expectation exactly. The current run: **274 workspaces, every criterion
observed both true and false, 62/62 tasks two-sided on their own workspaces.**

The rows are claims about the instrument. `fix-no-check` is the load-bearing one —
the fix without a check left behind, correctness true and footprint false. That is
the contrast the whole program measures, shown measurable before a dollar is spent.
`fix-vacuous-check` proves the proxy is not fooled by the mere presence of a test
file; `signature-drift` proves an error-only red is refused.

Arming has already earned its cost twice on this bank. It caught a task whose fix
lived in a module constant rather than the reverted function, and a stale `__pycache__`
entry shadowing an edited source through a matching `(mtime, size)` pair — the second
of which would have produced a silent, task-dependent false negative on the primary
criterion at run time.

## The arms

Path: **delegated**. Every arm injects the same delegation preamble and allows the
`Task` tool, so the work happens in a subagent and a `SubagentStop` gate has
something to fire on. The preamble is task-constant, so it is not a treatment.

| dir | arm | treatment |
|---|---|---|
| all | `bare` | delegation preamble only — no body, no gate |
| all | `skill` | preamble + the current skill body |
| all | `skill-gate` | `skill` + the discipline-worded `SubagentStop` gate |
| `verif-lift-vnext-*` | `skill-vnext` | preamble + the **shipped** vNext body |
| bug, null | `placebo-gate` | `skill` + a shape-matched stop block naming no verification act |
| screen | `bare-screen` | the control arm alone, over the full pool, at dataset_version 1 |

**The `vnext` arm was removed, unbought.** It injected the body the plan *projected* (796 words,
sha `7de774de…`), which is not what shipped: the two differ in four places including two of the
three table rows under test. It sat in `scenarios/verif-lift-{bug,data,trunc,null}/` — directories a
full matrix passes to `--scenarios-dir` — so a later run would have silently bought a body nobody
ships. **Zero trials were ever run against it** (the ledgers carry only `bare` and `skill`), so
removing it forked no longitudinal history and cost nothing. `skill-vnext`, carrying the shipped
body, replaces it. Git history holds the draft.

### What this bank does NOT contain: `bare+gate`

Checked against the primary scenario files: the prior program's `bare-sub` arms mounted **no
plugins**, and their injected preamble is byte-identical (sha256 `b044b0bf…`) to this bank's
`arm-bare.md`. So Phase 2/4's headline gate lift is **`bare+gate` − `bare`**, and this bank's
`skill-gate` − `skill` is a *different* contrast — the gate on top of a body the prior program
never carried. `skill-gate` − `bare` confounds body with gate. **Replicating the prior finding
needs a `bare+gate` arm, which this bank does not have.** No result from `skill-gate` may be
described as a replication until that arm exists.

### How the body reaches the worker

`[context] inject` appends to the **parent's** system prompt (`--append-system-prompt-file`); it is
not mounted in the subagent. Delivery to the worker rests on one preamble sentence ("applies to you
and to any subagent you spawn") plus the parent relaying it — while the same preamble tells the
parent to pass the subagent "the full task instruction verbatim" and says nothing about the
discipline. `verify-arming`'s `body_bytes` proves injection into the **top-level spawn only**. So
`skill` − `bare` measures *a parent told to relay a discipline*, which is a different mechanism
from a `SubagentStop` gate that fires on the worker regardless.

`skill` is also an **upper bound on the installed skill**: shipped, `verification-before-completion`
is a plugin skill an agent must choose to load (and the dispatch router carried zero rows for it),
whereas this arm forces the body in unconditionally.

`scenarios/verif-lift-assets/` holds the injected bodies and the two gate plugins.
The discipline gate is the measured Phase-2 fixture copied byte for byte
(`gate.py` sha256 `2e549ab2...`); the placebo differs only in its docstring, its
marker directory and the injected reason — the mechanism (one block per
`(session_id, agent_id)`, second stop passes, fails open on any exception) is
byte-identical, and the two reasons are 41 words each, 228 and 229 characters.

**Provenance of the current body:** craft-collection `main` at
`b3772ea1a08ae809706c54b29e314c2a016c8b3b`,
`plugins/humblepowers/skills/verification-before-completion/SKILL.md`, body below the
frontmatter, sha256 `33e2c4d561501dfb674ad53a20855279bd1ae68d0b2cf226b0064a57a19d10e3`,
**790 words** — which matches the figure the plan carries.

## The grid

n = 1 (pass `--repeats 1`; the flag defaults to 2). Weak tier `claude-haiku-4-5`,
strong tier `claude-opus-5`, effort held at medium.

| block | bank(s) | scenarios dir | arms | tasks | trials |
|---|---|---|---|---|---|
| screen | all four weak | `verif-lift-screen` | 1 | 20/20/10/6 | **56** |
| weak main | `bug` / `data` / `trunc` / `null` | `verif-lift-bug` etc. | 5/4/4/5 | 20/20/10/6 | **250** |
| strong main | `bug-strong`, `data-strong` | `verif-lift-strong` | 3 | 12 + 12 | **72** |

Dry-run at dataset_version 1, verified: 56 + 100 + 80 + 40 + 30 + 36 + 36 = **378
trials**. At the measured per-trial costs the prior ledgers give — haiku $0.145, opus
$0.73 — that projects to **$44.37 weak (306 trials) + $52.56 strong (72 trials) =
$96.93**, before the smoke line.

The screen and the weak main overlap by design and are not both bought in full: the
screen runs at dataset_version 1, the floor and ceiling rules cut the pool to
18/18/10/6, and the main matrix runs at **dataset_version 2**. The dataset version is
part of the resume key, so no screening trial can be reused as analysis data — the
rule that screening data is never analysis data is enforced by the harness rather
than by discipline. Post-screen the main matrix is 90 + 72 + 40 + 30 = 232 weak
trials, so the program totals **56 + 232 + 72 = 360 trials**.

> **⚠ The $0.145/$0.73 rates below are ledger FLOORS, and the grid does not fit the
> ceiling in true units.** Every arm delegates through the `Task` tool, so a trial's
> stream carries two `result` events (parent + subagent sidechain) and
> `parse_stream` keeps only the last; the undercount was measured at **3.81×** on a
> saved stream. Recomputed from this program's own three ledgers — **37 paid runs,
> $3.3434 floor, $12.74 corrected** — the true weak rate is **$0.344/trial, 2.4×**
> the figure below.
>
> The 360-trial grid in corrected units: **288 weak ≈ $99**, **72 strong ≈ $124** at
> the plan's own 5.0× opus ratio — **≈ $223 total, and the strong block alone
> exceeds the $120 program ceiling.** The floor-unit arithmetic is kept below so the
> error is legible; it is not a spendable plan. Re-scoping the grid is an operator
> decision.
>
> Note also that `--max-budget-usd` is a **per-spawn** cap. Nothing rails the
> program total except the cumulative-cap check, and that check must sum the ledgers
> **×3.81** or it will report green while the program runs ~3.8× past its ceiling.

In floor units, as originally computed: 288 weak at $0.145 = $41.76, 72 strong at
$0.73 = $52.56, **$94.32** plus the smoke line.

The `--dry-run` line prints a fixed $2.00-per-trial ceiling; it is a worst case, not
a projection, and it does not move with `--max-budget-usd`. Read the projection
above and treat the printed ceiling as the C4 upper bound.

## Limits this bank does not hide

- **The vNext body does not shrink.** The plan projected 790 → ~720 words. Measured:
  displacing the three procedures buys 73 words and the four additions cost 78, so
  the proposed body is **796 words** against an 800 budget (the *shipped* vNext body
  is 787). The displacement pays for the new rows almost exactly and buys no
  headroom. The "~720" figure does not survive contact, and the X1 non-inferiority
  test is therefore a test of a body the same size as the one it replaces.
- **X1's −10 pp margin cannot be discharged at any n this bank funds.** Recomputed
  with `analyse_vnext.py`'s own interval, a *perfect tie* clears −10 pp only at
  **n ≥ 35**: at n=24 the tie bound is −13.8 pp, at n=20 −16.1, at n=18 −17.6, at
  n=10 −27.8, at n=6 −39.0. The funded weak-BUG block is K=18 and the whole
  non-holdout BUG pool is 20. The analyzer now reports such cells as
  **undecidable**, never as a non-inferiority failure — a gate that cannot pass on
  any data measures the design, not the body, which is the mirror image of the
  vacuous gate this program exists to refuse. Re-registering the margin or the n is
  an operator decision, not an analysis fix.
- **`references/non-vacuity.md` is not injected.** The `skill-vnext` arm is a
  system-prompt injection with no file for the agent to read back, so it tests the
  displacement under the pessimistic assumption that the displaced procedure is
  never recovered. Non-inferiority under that assumption implies non-inferiority
  with the file present, not the other way round.
- **TRUNC's ceiling is an authoring defect in this bank, not a property of the
  class.** All 11 TRUNC instructions end "The package README states the rule this
  module is meant to follow. Bring the module into line with it." — but the README
  describes **both** functions, including the planted twin. `trunc-bounds`'
  `fixtures/README.md` states the closed-interval rule for `lower_bound` *and*
  `upper_bound`, and `upper_bound` is the twin at line 29. The instruction therefore
  hands the agent a document describing the twin's correct behaviour and directs
  whole-module conformance — which is exactly what `defect_past_slice_handled`
  scores. `bare` at 9/10 is the expected result of following the instruction, not a
  capability ceiling, and no conclusion about the class may be drawn from it.

  **The repair** (not applied here, because it changes task text and therefore
  requires a `dataset_version` bump that would orphan the 20 bought trials): scope
  the instruction to the cited symptom and the named function, and stop pointing at
  a README that covers the twin. That is an operator call about spending the
  re-measure, and it is written down rather than taken silently.
- **`skill` − `bare` is body plus framing.** The `skill` arm adds a 14-word framing
  line ahead of the body. The contrast is the delivery, not the body's prose alone.
- **`output_correct_on_subtle_case` headroom is a screening question.** The subtle
  cases are proven violable and satisfiable; whether a fix aimed at the named symptom
  actually misses them is measured by the screen, not claimed here.
- **The proxy cannot read a fix placed outside its function.** It reports that as an
  instrument miss rather than as an absent guard, and the per-cell rate of those is
  what the interpretability gate reads.
- **TRUNC is never pooled.** It asks a perception question and carries no footprint
  criterion; its lift is not commensurable with the footprint lifts.
