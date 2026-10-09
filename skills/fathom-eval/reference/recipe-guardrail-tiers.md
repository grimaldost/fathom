# Recipe: A/B a guardrail across model tiers

A worked example of one common question: does a short guardrail (a few lines appended to
the system prompt) help, and does it help the same on a cheaper model as on a dearer one?
It runs end to end on the example data root without spending anything, up to the one paid
command, which is shown and not run. Terms and parsers are in the
[authoring guide](authoring.md); this page is the walk-through.

Everything below is a copy of `examples/data-root` that you edit. The checked-in example
stays as it is. The model ids are examples: use the two you actually want to compare, and
check them against the claude CLI you run.

## The design

Two factors, two levels each, four arms (the cells of a 2 x 2):

| arm | model | guardrail |
|---|---|---|
| `bare-haiku` | the small tier | none |
| `guardrail-haiku` | the small tier | injected |
| `bare-sonnet` | the larger tier | none |
| `guardrail-sonnet` | the larger tier | injected |

Each arm is one scenario file. Two arms that share a model differ only in the `[context]`
table, so a difference between them is attributable to the guardrail. Two arms that share a
guardrail differ only in `model`, so a difference between them is attributable to the tier.
The comparison that answers the question is each guardrail arm against the bare arm of its
own tier: the effect on the small tier, the effect on the larger one, and whether they differ.

The report names the arm called `bare` as its anchor for pairwise deltas. These arms are
named by tier, so none is the anchor, and the comparison is declared in `bank.toml` as
contrasts instead (below).

## 1. Copy the example root

```sh
cp -r examples/data-root my-root
cd my-root
```

Every command below runs from inside the copy, so the relative `--scenarios-dir` resolves
against it (section 13 of the authoring guide). The copy keeps the example bank, `example`,
with one task, `add`, and its two synthetic arms in `scenarios/`. The new arms go in a
subdirectory so that they do not run with those two.

## 2. Write the guardrail from real bytes

The guardrail is a file whose content is appended to the system prompt, byte for byte, as
`[context] inject`. Its content's sha256 enters the arm's `config_hash`, so editing it later
starts a new history for the arm, and moving it does not. Keep it short and specific, and
write down what you expect it to change before you run anything. This one is neutral on
purpose:

```markdown
# scenarios/assets/guardrail.md
Read a file in full before you edit it. When you have finished editing, run the module once
with a small input and check the result against what the task asked for.
```

The first line of the block above is the path the file goes to and is not part of the file.

## 3. Write one scenario per cell

One flat TOML file per (arm, model) cell, under `scenarios/tiers/`. The `allowed` list is
the agent's whole tool set (a headless spawn has no tool that is not listed), and it is the
same in all four. Only `name`, `model` and the `[context]` table differ.

```toml
# scenarios/tiers/bare-haiku.toml
name = "bare-haiku"
adapter = "claude-cli"
model = "claude-haiku-5-5"
strategy = "single-session"
effort = "low"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep"]

[limits]
trial_timeout_s = 300
```

```toml
# scenarios/tiers/guardrail-haiku.toml
name = "guardrail-haiku"
adapter = "claude-cli"
model = "claude-haiku-5-5"
strategy = "single-session"
effort = "low"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep"]

[context]
# Relative to this file.
inject = "../assets/guardrail.md"

[limits]
trial_timeout_s = 300
```

```toml
# scenarios/tiers/bare-sonnet.toml
name = "bare-sonnet"
adapter = "claude-cli"
model = "claude-sonnet-5-5"
strategy = "single-session"
effort = "low"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep"]

[limits]
trial_timeout_s = 300
```

```toml
# scenarios/tiers/guardrail-sonnet.toml
name = "guardrail-sonnet"
adapter = "claude-cli"
model = "claude-sonnet-5-5"
strategy = "single-session"
effort = "low"

[tools]
source = "none"
allowed = ["Read", "Write", "Edit", "Glob", "Grep"]

[context]
inject = "../assets/guardrail.md"

[limits]
trial_timeout_s = 300
```

Keep `effort` equal across the tiers unless effort is itself a factor: a model comparison
that also changes effort measures both at once.

## 4. Declare the comparison

The two comparisons the question needs go in `bank.toml` as contrasts, and the study's
replication plan as `[plan] repeats_per_cell`: three completed trials per arm and task, the
repeats the paid run buys for each new arm. Nothing hashes either table, so adding them
changes no trial and needs no `dataset_version` bump. The block restates the example bank's
three required keys.

```toml
# tasks/example/bank.toml
name = "example"
dataset_version = "1"
holdout = []

[plan]
repeats_per_cell = 3

[[contrasts.pair]]
treatment = "guardrail-haiku"
control = "bare-haiku"

[[contrasts.pair]]
treatment = "guardrail-sonnet"
control = "bare-sonnet"
```

## 5. Check, then plan

`validate` is free. It runs the verifier on the fixture and on the reference solution, which
shows that the task discriminates and does not depend on any arm.

```sh
fathom validate example
```

The dry run is free too, and spawns nothing. Always pass `--scenarios-dir` for arms that live
in a subdirectory, or the run uses the two arms in `scenarios/` and says nothing:

```sh
fathom run example --scenarios-dir scenarios/tiers --repeats 3 --dry-run
```

Read three things in its output before you spend:

- **The arms line.** It must name the four arms you designed and no others, each with the
  first twelve characters of its `config_hash`. Four different prefixes are four separate
  histories. An arm that shows the prefix of another arm has the same configuration, so the
  two pool their trials: you did not change what you meant to.
- **The trial count.** Four arms times one task times three repeats is 12 trials. The
  `replication:` line under it says the run asks for the three repeats the plan declares; a
  run at fewer would be a screen, and the line would say its contrasts are directional.
- **The ceiling and the expected spend.** The ceiling is a worst case (planned trials times
  the per-spawn cap). The `expected:` line is an estimate from what trials of this strategy
  and, for a model with at least five trials, that model have cost in this ledger. An empty
  ledger prints none, and a strategy with no history is named as unpriced. A tier that is
  new to the ledger is priced from the other models' trials, which can understate it, so
  trust the ceiling and `--max-run-usd` for the first run of a new tier.

## 6. The paid run

Not run here. Before it, `fathom smoke` must pass this session, and `fathom verify-arming`
proves each injected arm's guardrail reaches a live spawn (`fathom run` repeats it before it
spends, unless `--skip-arming-check`). Both spend a little, so they are left out of this
recipe's commands. Then:

```sh
fathom run example --scenarios-dir scenarios/tiers --repeats 3 --interleave --max-run-usd 5
```

`--interleave` orders the trials repeat by repeat, so a run stopped by the spend cap has
still compared every arm on the repeats it bought. `--max-run-usd` stops the invocation
between trials once it has spent that much (exit 14); re-running resumes where it stopped.

## 7. Verify blind

The verifier decides what each trial achieved, and it reads only the result view, a copy of
the final workspace with no arm name in its arguments or environment (ADR-0003). A guardrail
experiment keeps that property by keeping the guardrail out of the verifier: the verifier
checks the work, never whether the guardrail was followed. Cost joins after scoring. The
pairwise judge is not part of `fathom run`, and this recipe does not use it.

## 8. Manipulation checks

A manipulation check asks whether the treatment reached the behaviour it was meant to change.
Two cheap ones:

- `fathom verify-arming` (above) shows that the injected bytes reach a live spawn. It does
  not show that the model acted on them.
- A neutral self-report field that every arm answers the same way. Put the question in the
  task's instruction, not in the guardrail, so the arms differ only in the injection: for
  example, ask the agent to end by writing a notes file whose first line names the command
  it ran to check its work, or says `none`. The verifier records whether that line is present
  as a criterion beside the correctness one. Bump `dataset_version` when you add it, since
  the instruction changed.

Read a self-report as weak evidence. A small model is an unreliable narrator: it may claim a
check it did not run, or run one and not say so. Where it matters, compare the report with
the kept streams (`.fathom/streams/example/`), which hold the tool calls the spawn made.

## 9. Read the scorecard

```sh
fathom report example
```

It renders `report/scorecard-example.md` from the ledger and can be re-run at any time.
In the copy of the example root the ledger holds only the example's own two arms, so before
the paid run the four new arms have no rows and each contrast prints a `Not compared` line.
The line under the title holds the ledger to the plan: while any arm x task cell has fewer
than three completed trials it starts `> **Directional:**`. The example's own cells hold two
(`bare/add`, `nudge/add`) and one (`nudge-draft/add`), and the paid run adds nothing to them,
so the line stays Directional after the run too ("3 of 7 arm x task cells"), and the
`fathom reconcile` below warns `short:bare/add` and `short:nudge/add` (the copied
`fathom.toml` already excuses `short:nudge-draft/add`). The four new arms' cells are the ones
the run fills to three. `nudge-draft` has no scenario file, so its cell cannot be topped up
and the line stays Directional in this copy whatever else is bought. After the run, read the
scorecard in this order:

1. **Per-Criterion Pass Rates.** Where arms usually differ. Lead with it.
2. **Hard-Criteria Fraction.** Criteria met over criteria present, per arm. Two arms with the
   same pass rate can differ here, because a trial that misses one criterion still counts
   the ones it met. A task that declares `[verify] hard_criteria` counts only those, so an
   added manipulation-check criterion does not dilute the figure.
3. **By tag.** Appears only when tasks declare `[tags]`; a bank of many tasks can tag them by
   difficulty or area and see whether the guardrail helps one kind of task. A tag that
   covers one task is that task's own result.
4. **Contrasts.** One row per pair declared in `bank.toml`: each arm's passes over completed
   trials, a Wilson interval, a one-sided Fisher exact p for the guardrail passing more often
   than its control, and Holm's step-down across the pairs. With twelve trials and one task
   the cells are small and the trials pooled across repeats are correlated, so read a
   contrast as directional, not as proof.
5. **Economy and Efficiency.** Whether the guardrail changed the cost, and by how much. When
   every arm passes nearly every task, the Pass Rates section prints a saturation line
   saying so, and cost is then the axis that separates the arms.

Then write the result up under `docs/reports/`, list it in `docs/STATUS.md`, and run
`fathom reconcile` and `fathom index --write` to keep the derived records current. The
reconcile exits 0 with the two `[WARNING] [replication]` lines above: a warning never fails.
