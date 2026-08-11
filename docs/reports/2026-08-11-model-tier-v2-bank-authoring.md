# model-tier-v2 — the tier-separating bank, authored and validated (unrun)

**Date:** 2026-08-11 · **Bank:** `model-tier-v2` · **Spend:** $0 · **Ledger:** none

The bank the recalibration playbook has been calling its "known limitation" now exists.
It is authored, validated and offline-demonstrated; it has not been run. This note
records what was built, what the offline evidence establishes, and — the part a reader
needs most — what it deliberately does not.

Full detail lives with the instrument, in
[`tasks/model-tier-v2/README.md`](../../tasks/model-tier-v2/README.md). Design of record:
[`docs/specs/2026-07-14-tier-separating-bank-design.md`](../specs/2026-07-14-tier-separating-bank-design.md).

## Why

`model-tier-v1` is saturated. Six of its seven scored tasks are aced by every tier, no
task resolves empirically to mid or strong, and a 10/10 cell carries a Wilson 95% CI of
[0.72, 1.00]. Its on-diagonal 1/7 has reproduced three times, and each time the honest
reading was that the null is manufactured by the bank rather than observed about the
rubric. The CRAF-B11 question — *does the choosing-models score separate model tiers on
outcome?* — has no power on that instrument. This bank is the instrument with headroom.

## What was built

Nine bug-fix tasks, each planting a displaced cause: the fault surfaces where the
instruction points and the fix belongs somewhere a second, unnamed consumer also depends
on. Scores span 20 to 71 on the pinned model-complexity rubric. Three arms —
`haiku` / `sonnet5` / `opus5`, identical but for `model`, undated aliases. Nine tasks,
one sealed holdout, eight in the run set.

Every task ships three harness-side overlays and every one of them was run through the
real verifier:

| what | claim it settles | result |
|---|---|---|
| `fixtures/` untouched | the arm has something to fix | 5-6 of 8-9 criteria start false on all nine tasks |
| `solution/` | the verifier is satisfiable — no arm is asked the impossible | every criterion true, exit 0, on all nine |
| `counter/` | the criteria are violable, and the separation mechanism is real | passes **every** thin criterion, fails ≥1 standard criterion, on all nine |
| `counter-strong/` | the standard→strong contrast is not vacuous | passes the **whole** standard oracle, fails ≥1 strong criterion, on all nine |

`tests/test_bank_model_tier_v2.py` is that evidence as a gate: 17 tests, 117 subtests,
36 verifier passes, ~2 minutes, stdlib-runnable.

`fathom validate model-tier-v2 --strict`: **27 pass, 0 fail, 0 warn, 0 unverifiable**.
`fathom verify-arming --scenarios-dir scenarios/model-tier-v2`: 3 arms, 0 declaring a
treatment axis — model-only controls, so arming is structurally satisfied with zero
spawns and nothing is deferred.

## The oracle axis, at a third of the design's cost

The design specifies model × oracle-quality as nine arms and 405 spawns. This bank runs
three arms and gets the same experiment, because the crossing is **open-loop**: the arm
produces an artifact, the verifier grades it afterwards, and the oracle never reaches the
spawn (single-session arms run no gate; `verify.py` never enters the workspace). Three
same-model arms differing only in `verify.py` would sample the same artifact distribution
three times. So each verifier emits one criterion dict covering thin ⊂ standard ⊂ strong,
`oracles.toml` records the levels, and the exit code gates on standard — the v1 contract,
so headline pass rates stay comparable. The nesting becomes exact per artifact instead of
true in expectation, which is strictly better for estimating the interaction.

The design's own worry about this axis — that the standard→strong leg could come back
null for measurement reasons — is answered as far as authoring can answer it: on every
task a patch exists that satisfies the entire standard oracle and still fails a strong
criterion, and a test asserts it.

## The plan, and the rail

```sh
uv run fathom run model-tier-v2 --scenarios-dir scenarios/model-tier-v2 --repeats 2 --dry-run
# fathom run: bank=model-tier-v2  scenarios=3  tasks=8  repeats=2
# planned:  48 trials (0 already done)  ceiling: $96.00
```

Stage one is 48 trials, $96.00 at the flat $2/trial rail — under the $100 program rail.
The rail is a ceiling, not an expectation: v1's comparable 42-trial pilot cost about $6
in observed tokens. `--repeats 5` (120 trials, $240 ceiling) is the power target and
needs its own approval; resume makes the staging free.

**A trap specific to this bank:** the default `scenarios/` glob also resolves to exactly
three arms, so omitting `--scenarios-dir` prints an identical plan line and silently runs
`bare` / `series` / `single-long-session` instead. The arm names in the ledger are the
only tell.

## What this does not establish

- **The admission screen has not run.** The design admits a task only after a
  weak-vs-strong screen at `--repeats 5` with unanimity. That is ~90 trials and a $180
  ceiling — over this program's rail. The offline demonstrations prove the *instrument*
  can separate; only the screen proves the *tiers* do. A task that saturates in practice
  would still show up in stage one as 100% across all three arms.
- **The counters are authored patches**, chosen as the plausible shortcut. They are not
  evidence that a weak model writes them.
- **`scores.toml` has one rater, not two.** The design asks for two blind raters. The
  bank was authored in a single non-interactive session with no way to convene a second.
  The per-axis breakdown is recorded in full so the gap is cheap to close, and a test
  asserts the axes sum to the score. Until then the band populations are provisional.
- **The weak band holds one task.** `fix-strip-unicode` was authored as a ~22 rung and
  scored 40; once a task is substantial enough to plant a displaced cause in, the
  rubric's cross-shape floor lifts it to at least 26. So the "weak tier suffices for
  trivial work" leg will rest on K=1, and repeats cannot fix K. The 25 edge has one rung
  (Δ5); the 55 edge is double-covered (Δ1 below, Δ5 above), which the design expected the
  rubric to refuse.
- **No oracle result renders yet.** `calibration.py` has no oracle axis; the slope
  estimator that reads `oracles.toml` is unbuilt and stays gated behind **ADR-0008**,
  which is unaccepted. That is analysis over an existing ledger and can follow the run.
- **At `--repeats 2` a cell pools 4-6 Bernoulli draws** (Wilson 95% CI on 6/6 ≈
  [0.61, 1.00]). Stage one can show the ladder's shape and catch a ceiling. It cannot
  move a tier cut, and nothing of the form "tier X should be retired" follows from it.

## Incidental: `fathom smoke` is 7/8, and the failure is not credentials

Run during this authoring pass: every credential-dependent check **passes** (isolated
config, credential-only spawn, stream parsing, default-deny refusal, system-prompt
injection, both plugin-mount checks). The single failure is
`engine-boundary: non-bypass permission mode reaches the spawned CLI — engine spawned no
claude invocation (boundary not exercised)`, which concerns the convoy series arm and is
untouched by this bank's single-session arms. Recorded here because a stale note had the
suite failing 5/8 on an expired OAuth session; that is no longer the failure mode.
