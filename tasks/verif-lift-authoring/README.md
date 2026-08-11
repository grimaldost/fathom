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
| weak | `vnext` | preamble + the proposed body (displacement + three new rows + the duration clause) |
| bug, null | `placebo-gate` | `skill` + a shape-matched stop block naming no verification act |
| screen | `bare-screen` | the control arm alone, over the full pool, at dataset_version 1 |

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
trials, so the program totals **56 + 232 + 72 = 360 trials ≈ $88.81** plus smoke.

The `--dry-run` line prints a fixed $2.00-per-trial ceiling; it is a worst case, not
a projection, and it does not move with `--max-budget-usd`. Read the projection
above and treat the printed ceiling as the C4 upper bound.

## Limits this bank does not hide

- **The vNext body does not shrink.** The plan projected 790 → ~720 words. Measured:
  displacing the three procedures buys 73 words and the four additions cost 78, so
  the proposed body is **796 words** against an 800 budget. The displacement pays for
  the new rows almost exactly and buys no headroom. The "~720" figure does not
  survive contact, and the X1 non-inferiority test is therefore a test of a body the
  same size as the one it replaces, not of a smaller one.
- **`references/non-vacuity.md` is not injected.** The `vnext` arm is a system-prompt
  injection with no file for the agent to read back, so it tests the displacement
  under the pessimistic assumption that the displaced procedure is never recovered.
  Non-inferiority under that assumption implies non-inferiority with the file
  present, not the other way round.
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
