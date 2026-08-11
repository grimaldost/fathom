# ablation-v2: authoring the weak-tier series arm, and repairing the arm it is compared against

**Status: authored, statically validated, rehearsed end-to-end without spending. NOT YET RUN.**
Bank `ablation-v2`, task `exprlang`, dataset_version `1` (unchanged). Branch
`eval/series-vs-bare`.

The question this arm exists to answer: **at the weak tier, does routing a task through a
governed multi-PR engine beat handing the same model the same task in one brief?** The
comparators are already in `ledger/ablation-v2.jsonl` at the same model
(`claude-haiku-4-5`) and effort (`high`):

| arm | strategy | ALL-CRITERIA pass |
|---|---|---|
| `haiku` | one spawn, no gate | 3/8 |
| `haiku-gate` | one spawn + the project's visible suite as a gate + ≤2 fix spawns | 3/8 |
| `haiku-gate-sg` | as `haiku-gate` plus a harness-side type-contract probe | 9/10 — **historical only, see §1** |
| `haiku-series` (new) | five dependency-ordered PRs, each gated on the level it delivers | — |

The discriminating signal in this bank is narrow and known: twelve of the fifteen blind
criteria are at 100% for every arm. The whole spread lives in `type_bool_in_arith`
(haiku 3/8), `type_compare_bool` (7/8) and `not_op` (8/8). So the arm is really being
asked one question: *does decomposition get a weak model to apply the spec's type rules,
which it demonstrably drops when the spec arrives all at once?*

---

## 1. The `haiku-gate-sg` arm was broken, and its 9/10 is not reproducible

`scenarios/ablation-v2/haiku-gate-sg.toml` shipped its probe as the literal

```
python /path/to/fathom/tasks/ablation-v2/exprlang/type_probe.py .
```

A scenario's `[gate].extra` command is handed to the shell verbatim
(`strategies/gated_session.py`), so that path resolved to nothing. The probe never ran and
the arm silently degraded to plain `haiku-gate` — a strengthened-oracle arm with no
strengthening, and no way to tell from the outside, because a probe that cannot start
leaves the same trace as one that passes.

**The 9/10 is historical-only.** Neither the committed file (`config_hash` 0e07a4d2e036)
nor its pre-genericize ancestor at git `4041afa` (which carried a real absolute machine
path, 81739ab0adfe) reproduces the ledger's `08c2f05f2b21`. A sweep of ~170 000 candidate
forms — interpreter, path shape, quoting, trailing argument, tool allow-list, trial
timeout, arm name, strategy, plus three structural variants of how `[gate]` enters the
hash — found no preimage. The method is sound: the same reconstruction reproduces the
ledger hash exactly for all **fourteen** other `ablation-v2` arms. The scenario that
produced those ten trials was therefore never committed, and cannot be recovered.

Repair (commit `185f574`), per the file's own versioning note:

- Extra gate commands now expand `${task_dir}` and `${workspace}` **at run time**,
  mirroring the `[env]` block's existing spawn-time `${workspace}` convention. A gate runs
  with `cwd` = the trial workspace (a fresh temp dir), so a harness-side probe in the task
  directory is unreachable by any relative path and a machine-absolute path is neither
  portable nor committable — which is exactly how the broken placeholder got there.
  Substitution at run time means the portable *template* is what enters `config_hash`, so
  relocating the checkout does not fork history. A command with no placeholder is returned
  byte-identical; all fourteen untouched arms re-resolve to their ledger hashes.
- The arm is **forked, not renamed in place**: `haiku-gate-sg2`, `config_hash`
  2c3b7e20a7e1, starting at n=0. Pooling ten unreproducible trials with a repaired arm
  under one resume key would have buried the fact.

**Consequence for every downstream report: any claim resting on `haiku-gate-sg`'s 9/10 is
resting on an arm whose configuration is unknown.** The number is not wrong so much as
unattributable — it may be the probe arm, or it may be `haiku-gate` with n=10. Re-run
`haiku-gate-sg2` before citing the strengthened-gate result again.

## 2. Two instrument defects that would have biased this arm

Both were found while preparing the arm; both are committed separately from the
decomposition.

**(a) An engine-blocked trial was silently dropped (commit `ab09e5f`).** The series
executor mapped engine exit 1 — a blocking gate still red after the bounded fix loop — to
`ERRORED`, under a comment calling it "a scored task failure" and against the series
contract §7, which says exit 1 *is* scored. Since FATH-B03 that has not been true:
`cli.py` drops `verifier_results` and writes `valid=false` for any non-completed trial,
and the report counts only `completed`. So every trial the engine refused to integrate
would have left the denominator, and the arm would have reported a pass rate conditioned
on the engine having succeeded — it would look better the more often it blocked. A block
is a real, gradeable result (convoy halts with the failing PR's branch checked out,
carrying every merged predecessor plus that PR's work), and it is the treatment the
single-spawn gated arms already get. It is now `COMPLETED` with the block recorded in
`detail`. Budget truncation (exit 4) keeps `ERRORED` — there the engine deliberately
leaves the work un-integrated, so there is no result to score. No committed ledger carries
series-arm trials, so nothing on disk moved.

**(b) `--max-budget-usd` was inert on a series arm (this commit).** The flag caps the
Runner, and the series executor ignores the Runner — the engine spawns the CLI itself
(ADR-0001). The only ceiling in force was `SeriesExecutor`'s own $20/$5/$3 default, so an
operator who set a rail had one that did not exist. The flag now reaches the engine's
per-spawn budgets.

## 3. The decomposition, PR by PR, and why each cut is where it is

Committed as `tasks/ablation-v2/exprlang/series.toml` + `prompts/`. It adds files to the
task directory only; the instruction, the fixtures and the verifier are untouched, so
`dataset_version` stays `1` and every existing resume key holds. Fixture staging copies
only `fixtures/`, so the series assets never enter the scored workspace.

**The organising principle: one PR per numbered item of the task instruction, plus a final
pass for the two requirements that span all of them.** The instruction is already a
decomposition — four numbered feature items, a precedence table, and a testing requirement
— and following its own seams is both the most defensible cut and the least inventive one.
On top of that, one rule decides where the type rules land: *each PR owns the type contract
for the operators it introduces, and the PR that introduces a new value type owns that
type's contract with the operators that already exist.*

| PR | phase | delivers | why the cut is here |
|---|---|---|---|
| **PR01** `boolean-values` | `bools` | `TypeMismatchError`; `true`/`false` literals; arithmetic and unary `-`/`+` reject boolean operands; the two operand guards later PRs reuse | The error type must exist before any operator can raise it, so it is the true first dependency. Arithmetic's type rule rides along **because PR01 is what creates the question**: the moment booleans are values, `true + 1` becomes reachable, and a PR that shipped booleans without answering it would leave a known-wrong intermediate state for PR02 to inherit. This is also the only part of the feature that modifies *pre-existing* behaviour rather than adding new behaviour. |
| **PR02** `comparison-operators` | `compare` | `== != < <= > >=`: two-character lexing, the precedence slot below `+ -`, numeric-only operands, boolean result | Instruction item 2, whole. Comparisons are the first *new* operator family, they consume PR01's guard rather than re-deriving it, and they must exist before `and`/`or` have anything interesting to combine. |
| **PR03** `and-or-short-circuit` | `boolops` | `and` / `or`: keywords, the two lowest precedence levels, boolean-only operands, short-circuit in both directions with the error-suppression consequence | Instruction item 3a. Split from `not` because it is the only part of the feature that changes the *shape* of evaluation — both operands are no longer always evaluated — while `not` is a placement problem. Bundling them would put two unlike difficulties in one turn, which is the failure mode the whole arm is testing. |
| **PR04** `not-operator` | `notop` | `not`: prefix, binding tighter than `and`/`or` and **looser** than the comparisons | Instruction item 3b. It gets its own PR because its precedence is the one counter-intuitive entry in the table: the language's other prefix operators bind tightest of all, and `not` binds loosest of the prefix positions, so a model that pattern-matches on unary `-` gets it wrong. `not_op` is one of the three criteria that ever fail in this bank. |
| **PR05** `conformance-pass` | `conform` | The precedence table verified across adjacent *and* non-adjacent pairs; the type-rule matrix verified for every operator family; the cross-cutting tests the instruction requires | Instruction item 4 and the precedence table are cross-cutting: each of PR01–PR04 could only see its own level and its own operator family. A requirement no single PR can verify needs a PR that can. Its gate is the project's whole visible suite. |

Dependencies are a straight chain (`PR01 → PR02 → PR03 → PR04 → PR05`); the DAG is
verified acyclic by convoy's own `core.dag.order`.

**Gating is cumulative, not per-PR-only.** Checks are phase-scoped, so each PR is judged on
its own level *and* every level already landed — a later PR cannot silently regress an
earlier one. A no-regression check on the baseline arithmetic suite runs after **every** PR
with no phase filter. By PR04 the selected checks are exactly the project's whole visible
suite; PR05 runs it as one command.

```
PR01  baseline-arithmetic, feature-bool-literals
PR02  baseline-arithmetic, feature-bool-literals, feature-comparisons
PR03  baseline-arithmetic, feature-bool-literals, feature-comparisons, feature-and-or
PR04  baseline-arithmetic, feature-bool-literals, feature-comparisons, feature-and-or, feature-not
PR05  baseline-arithmetic, visible-suite
```

### What the decomposition deliberately does NOT do

This is where an arm like this manufactures its own verdict, so the constraints are
explicit and mechanically checkable.

- **No harness-side oracle.** Every check is a subset of the project's OWN visible suite —
  the same suite `haiku-gate` is gated on in full. The `haiku-gate-sg2` type probe is
  absent on purpose; including it would confound decomposition with oracle strength and
  make the contrast two-factor. No check is `independent`, so none is implementer-
  unreachable, exactly as in the gated single-spawn arms.
- **No example in any prompt that is not verbatim in the task instruction.** The
  instruction contains exactly four worked examples (`false and (1 / 0 > 0)`,
  `true and (1 / 0 > 0)`, `1 < 2 and 3 < 4`, `not 1 < 2`) and states every type rule in
  prose without examples. An earlier draft of PR01 and PR02 illustrated the type rules with
  concrete expressions — and those expressions were, unavoidably, the blind oracle's own
  test inputs. They were removed. The rule is checkable by diffing the prompts against the
  instruction.
- **No implementation hints.** In particular, nothing in any prompt mentions that `bool` is
  a subclass of `int` in Python. That fact is the entire content of the dominant failure
  class, and it is what the `sg` probe's failure message hands over. The prompts state the
  rule the instruction states; how to satisfy it is the model's problem, as it is for
  every other arm.
- **The gate the fix loop sees is a proper subset of the acceptance oracle.** The visible
  suite contains no test for a boolean in an arithmetic expression at all, so
  `type_bool_in_arith` — the criterion that actually separates arms here — is invisible to
  every check this arm runs. The arm cannot pass it by being told; only by being asked at
  the right moment.
- **Tool and repair parity.** `[governance.tools]` is the same allow-list the single-spawn
  arms declare (`Read, Write, Edit, Glob, Grep, Bash(python:*)`), and
  `[review].max_fix_attempts = 2` matches the `GatedSessionExecutor` default the gate arms
  run under. What the arm legitimately gets *more* of is spawns — that is the treatment,
  and the economy axis prices it.

The honest disclosure for a reviewer: the decomposition was authored against the task
instruction's structure, but its author had already read the ledger's per-criterion table
and knew that item 4 is where weak-tier trials die. The cut that concentrates on item 4 is
defensible from the instruction alone (see PR01's row above), but it is not *innocent* of
the failure data, and a reviewer should weigh it as such.

## 4. Validation performed (no spend)

- `uv run ruff format --check . && uv run ruff check . && uv run pytest` — clean,
  **618 passed, 1 skipped, 112 subtests**.
- `uv run fathom validate ablation-v2` — 2 pass, 0 fail, 1 warn (the known, deliberate
  brownfield warn: the visible suite is red on the unmodified fixture), 0 unverifiable.
- **Spec round-trip through the real engine.** The committed template was put through
  fathom's own per-trial regeneration (absolute `[paths]`, pinned `[governance]`, stripped
  per-PR keys, re-serialized by `dump_toml`) and the result loaded by **convoy 0.8.0's own
  `load_series`** and ordered by its own `core.dag.order`. Every pin survives the round
  trip; every `phases` tag is declared by a PR; every PR is gated by ≥2 blocking checks; no
  blocking `independent` check lacks an asset.
- **Every check command executed in a real workspace.** On the base fixture: the baseline
  check is green and all five feature checks are red. On the reference solution: all six
  are green. A check that is red where it should be green (or the reverse) would have
  wasted a whole matrix.
- **End-to-end rehearsal against the real engine, zero tokens.** The convoy engine was
  driven over the committed decomposition with `claude` shadowed by fathom's own recorder
  shim:
  - *no-op agent* → the engine ran PR01's implementation and both fix spawns, blocked, and
    exited 1. fathom recorded the trial `completed` with
    `detail = "engine blocked (blocking gate stayed red); result scored"`, and the blind
    oracle scored the halted tree 6/15. Under the old classification this cell would have
    vanished.
  - *agent that installs the reference solution* → all five PRs implemented, gated and
    integrated in DAG order, the integration branch left checked out with five commits, and
    the blind oracle **15/15 pass**.
  - In both runs the pinned non-bypass `--permission-mode default` reached every spawned
    CLI invocation.
- `uv run fathom verify-arming --scenarios-dir scenarios/ablation-v2-series` — the arm
  declares no plugin / settings / env / context axis, so there is nothing to prove on a
  spawn (`control — nothing to verify`). Static substitute, per the arming gate's intent:
  the engine repo it mounts is asserted to exist and resolve (below).
- `uv run fathom smoke` — **7/8**. The seven credential- and injection-dependent checks
  pass, so the OAuth session that blocked earlier stages is working. The single failure is
  `engine-boundary: … engine spawned no claude invocation`, and its cause is the run
  precondition in §5, not a defect: from this worktree `../convoy` resolves to
  `.wt-closeout/convoy`, which does not exist. The rehearsal above exercises the same
  boundary successfully against an absolute engine path.

## 5. Run plan, and the precondition that must hold first

```sh
uv run fathom run ablation-v2 \
    --scenarios-dir scenarios/ablation-v2-series \
    --repeats 8 \
    --max-budget-usd 2.0
```

- **Planned cells: 8** (1 arm × 1 task × 8 repeats, 0 already done).
- **`--dry-run` ceiling: $16.00** — fathom's generic $2/trial ceiling, not a forecast. The
  ledger-grounded expectation is lower: weak-tier spawns on this task cost $0.20–0.30 each
  for the *whole* task, and a trial here is five narrower spawns plus fixes, so roughly
  $0.5–2.0 per trial, i.e. **$4–16 for the arm**. `--max-budget-usd 2.0` now genuinely caps
  each engine spawn (§2b) at ~8× the observed per-spawn cost, which trips only on a
  runaway; note that a budget bust halts the PR and errors the cell, so a tighter rail buys
  lost cells rather than savings.
- **Precondition — the engine path.** `[tools].repo` is resolved against fathom's CWD, not
  against the scenario file, so **the matrix must be invoked from a checkout whose sibling
  `../convoy` is the convoy checkout** — the canonical `Documents/fathom`, not a worktree.
  The resolved absolute invocation enters `config_hash`, so running from a different
  directory forks the resume key instead of resuming. Verified on disk: the canonical
  sibling exists and is convoy 0.8.0; the worktree sibling does not.
- **Wall clock.** `trial_timeout_s = 5400` (90 min) against an expected 10–15 min per
  trial; the per-spawn ceiling is 900 s, authored in the series template (fathom does not
  overwrite `timeout_seconds`). The headroom exists because a timeout is `ERRORED` and
  costs the cell.
- **The arm lives in its own scenarios directory** (`scenarios/ablation-v2-series/`)
  because `fathom run` globs a directory rather than naming an arm, and a series trial is
  ~20× the wall clock of a single-spawn one. Trials still land in
  `ledger/ablation-v2.jsonl` — the bank names the ledger, not the directory. Re-running
  `haiku-gate-sg2` has the same shape of problem and will need the same treatment or a
  full-group run.

## 6. What this arm can and cannot conclude

**n = 8 per arm buys detection of large effects only.** Against the 3/8 baselines
(`haiku`, `haiku-gate`), one-sided Fisher exact:

| series result | vs 3/8 |
|---|---|
| 8/8 | p = 0.013 |
| 7/8 | p = 0.059 |
| 6/8 | p = 0.157 |
| 5/8 | p = 0.310 |
| 4/8 | p = 0.500 |

So only a near-perfect arm separates from the baseline at conventional thresholds; 7/8 is
suggestive and nothing at or below 6/8 is distinguishable from doing nothing. A **null
result at this n is not evidence that decomposition does not help** — it is the expected
outcome of a small sample against a moderate effect, and it must not be written up as a
verdict against the engine. Retiring or promoting anything on this cell alone would be
concluding from a study without the power to say.

Three further limits a reader should carry:

1. **One task, one bank.** `exprlang` is a single brownfield task whose discriminating
   surface is one type-contract class. "Decomposition helps a weak model on exprlang" does
   not generalise to "decomposition helps weak models", and the bank cannot be asked to.
2. **The `haiku-gate-sg` comparison is unavailable** until `haiku-gate-sg2` is re-run (§1).
   Any framing of "engine vs strengthened gate" is not answerable from the current ledger.
3. **The comparison prices spawns, not just passes.** The series arm spends 5–11 spawns
   where `haiku-gate` spends 1–3. If the pass rates land equal, the economy axis is the
   verdict, and it will say the engine cost more for nothing on this task — which is a
   real finding, and a narrower one than "the engine does not work".
