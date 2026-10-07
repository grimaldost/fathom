# Bank design

<!-- Line budget: 175 lines. The guide is three files; an addition that would take this
file past its budget displaces something first (tests/test_authoring_guide.py). -->

Part of the authoring guide, which starts at [`authoring.md`](authoring.md). That file maps
the guide's three files, defines its terms (`authoring.md`, section 1) and lists the parsers
everything here is written against. Sections are numbered across the three files: a bare
section number here is a section of this file, and a section in another file is cited with
that file's name.

This file covers what lets a bank tell arms apart: criteria, scale, the turn budget, a pilot,
a holdout, an answer key beside the verifier, the naive-fix check and calibration banks
(section 9); and the checklist before the first paid run (section 15).

## 9. Making a bank discriminate

A bank is only useful if arms can score differently on it. The common failure is a
**ceiling**: every arm passes every criterion, and the analysis reports no difference because
the tasks could not show one. A ceiling costs the full price of the matrix and looks exactly
like a finding that the treatment does not help.

What helps:

- **Criteria that are not all easy.** Pair the criteria a first attempt will meet with at
  least one that only a careful attempt meets: an edge case, a second caller that also needs
  the fix, behaviour that must be preserved. Read the Per-Criterion Pass Rates table, not only
  the headline pass rate.
- **Scale.** Differences between arms tend to come from how much material the agent has to
  work through and from the turn budget, more than from how clever a task is. A small fixture
  can ceiling even with deliberate decoys where a larger one separates the arms.
- **A turn budget from evidence.** Set `max_turns` from what a pilot used. A trial that reaches
  the cap was cut short, and its arm's pass rate is a lower bound.
- **A pilot before the matrix.** `fathom run <bank> --tasks ID[,ID…] --repeats 1` buys a small
  screen. Check that the control arm fails some criterion before paying for repeats.
- **A holdout.** Keep one or more tasks in `holdout` to confirm a result on tasks the bank was
  not tuned against.

### An answer key beside the verifier

Some criteria compare the result with an exact answer: set equality (the agent lists every
call site it had to change, and one missed or one extra fails the criterion) or byte identity
(an output file must equal the expected bytes, compared directly or by sha256). Keep that
answer in a `truth.json` beside `verify.py`, never in the fixture: only `fixtures/` is staged,
so the key is not in the workspace the agent works in (`authoring.md`, section 6). The verifier
starts in an empty working directory, so it reads the key through its own path:

```python
TRUTH = json.loads(Path(__file__).with_name("truth.json").read_text(encoding="utf-8"))
```

In the example data root the key would go in
[`examples/data-root/tasks/example/add/`](../../../examples/data-root/tasks/example/add/), next
to its `verify.py`; that verifier computes its answer instead of storing one. Commit the key,
and let `fathom validate` show that the reference solution meets it (`authoring.md`,
section 8). Outside the workspace is not out of reach: an arm whose tools read beyond the
workspace, or agent code that a gate runs, can still find the key, and fathom checks only
`fixtures/` for changes between trials (`arming.md`, section 10).

### The naive-fix check

`fathom validate` shows that each task leaves work to do and can be solved. It does not show
that any criterion is hard: a bank can pass it and still ceiling because the first fix an agent
tries meets every criterion. `tools/check_naive_refs.py` checks that gap for tasks that opt in.

The check is optional: neither `fathom validate` nor `fathom run` requires it. Skip it only
for a task that exists to demonstrate or test the setup. For any task whose results will
inform a decision, write the naive fix down; it is the cheapest evidence that the task can
separate a careful attempt from a quick one.

A task opts in by describing the fix a first attempt would reach for, in `task.toml`:

```toml
[naive]
must_pass = ["correctness"]         # criteria the naive fix should meet
must_fail = ["handles_overflow"]    # criteria it must NOT meet; the trap
# control = true                    # a control task: may leave must_fail empty (needs must_pass)
```

and shipping that fix as an overlay in `<task>/refs/naive/`, laid out like `solution/`. The
tool copies the overlay over a staged fixture, runs the verifier, and reports for each task:

| Status | Meaning |
|---|---|
| `PASS` | the naive fix meets every `must_pass` criterion and none of the `must_fail` ones |
| `FAIL` | the naive fix meets a `must_fail` criterion (the task is not a trap; rework it before spending), misses a `must_pass` criterion (the overlay is too weak to stand for the easy path), the verifier errored, or `[naive]` names a criterion the verifier does not emit |
| `CONTROL` | a declared control: the obvious fix meets `must_pass` by design; never counted as discriminating |
| `UNVERIFIABLE` | no usable `[naive]` table, or no `refs/naive/` directory; blocks only under `--strict` |

It exits `0` when nothing blocks and `3` otherwise, and spends nothing. The tool is not in the
installed Python package, but it is in the engine repository and so in the installed plugin,
whose directory is a copy of the repository: run it from either with a Python 3.12 interpreter.
From the data root:

```sh
python <engine clone or plugin directory>/tools/check_naive_refs.py <bank> [--tasks-dir tasks] [--strict]
```

`--tasks-dir` defaults to `tasks` under the current directory.

A pass is a statement about consistency: the overlay and its contract are written by the same
author and no agent runs. It bounds one easy path, not every easy path. Report it as "the naive
overlays meet their declared contract", not as "the tasks discriminate". Only the control arm's
measured failures show that.

### What no check covers

No check can tell that tasks are simply too easy for every arm. The turn budget, the scale of
the material and a pilot's results remain the author's judgement.

### Optional: calibration banks

A bank that ships `tasks/<bank>/scores.toml` and `[verify] hard_criteria` on its tasks gets
extra calibration sections on its scorecard (model-tier routing; ADR-0007 to ADR-0009). Other
banks are unaffected.

```toml
# tasks/<bank>/scores.toml
[scores]
add = 18        # 0-100 per task; predicted tier: 0-25 weak, 26-55 mid, 56-100 strong
```

`scores.toml` may also hold one positive control (`[control]` with `task`, `weak_arm`,
`strong_arm`, `alpha`, `min_repeats`) and the routing tables `[reduced]`, `[genre]` and
`[analysis]`. A task's `[context]` table (`size = "small" | "large"`, `pair = "<name>"`)
switches the calibration heading from model tier to context size and groups matched pairs;
only the exact values `small` and `large` are grouped. The calibration views read the bank at
`tasks/<bank>/` in the data root, so a bank kept under another `--tasks-dir` renders without
them.

## 15. Checklist before the first paid run

- [ ] The data root has `fathom.toml` with `[data_root]` and `schema = 1`, and is a git
      repository.
- [ ] `FATHOM_HOME` is unset or names this data root, and the `data root:` line that
      `fathom run --dry-run` prints is this one (`authoring.md`, section 2).
- [ ] `bank.toml` `name` equals the bank's directory name; `dataset_version` is set.
- [ ] Every task has an instruction that states the requirement completely.
- [ ] Every verifier reads only `argv[1]`, prints the criteria last, emits every criterion on
      every run, imports only the standard library, and runs the agent's code in a child
      process started in the result view (`authoring.md`, section 7).
- [ ] Every numeric value an oracle checks was computed again against the final instruction
      text, after the last edit to the instruction: an edit can change the right answer.
- [ ] Criteria score structured fields (a key in a JSON file the task asks for, a return
      value, a file's exact bytes), not free-text heuristics such as a keyword search in
      the agent's prose.
- [ ] No hook script a `[settings]` file runs, and no `[env]` value, names a path in the
      data root (`arming.md`, section 10).
- [ ] Every task ships `solution/`, and `fathom validate <bank> --strict` passes (or its
      warnings are understood), with `--scenarios-dir` naming the arms you will run when
      they are not in `scenarios/`, so their `[gate] extra` paths are checked
      (`authoring.md`, section 8).
- [ ] Every task whose results will inform a decision declares `[naive]` with `refs/naive/`,
      and the naive-fix check passes. A task kept only to demonstrate or test the setup may
      skip this; nothing enforces it (section 9).
- [ ] The control arm is named `bare` and has the same allowlist as the treatment arms.
- [ ] No arm has an empty `allowed` list, unless it is a series arm.
- [ ] When the data root holds more than one bank, each bank's arms sit in their own
      directory, passed with `--scenarios-dir` (`arming.md`, section 10).
- [ ] `fathom run --dry-run` shows the intended arms, trial count and ceiling.
- [ ] `fathom smoke` passes in this session.
- [ ] A small pilot shows the control arm failing some criterion.
