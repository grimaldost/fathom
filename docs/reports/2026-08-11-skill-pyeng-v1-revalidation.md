# Re-validating the python-engineering reference bank under the fixed instrument — skill-pyeng-v1

- **Date:** run and report 2026-08-11. Bank: `skill-pyeng-v1` (one task, `modernize-timeflow`);
  arms `bare` / `generic-nudge` / `pyeng-skill` in `scenarios/skill-pyeng/`, differing only in
  `[context] inject`.
- **Question (operator):** a sibling backlog gates a compression-and-retirement decision on whether
  the flagship skills beat their own no-skill baseline, with the retirement criterion "where the
  bare arm matches, the prose goes". Two defects in this harness could have manufactured either
  answer — an arm that was never armed, and a bank that could not discriminate. **Does the existing
  verdict survive once both are closed?**
- **Standing:** this is a re-validation, not a new analysis. The 2026-06-13 first matrix
  (`2026-06-13-skill-pyeng-v1-first-matrix.md`) is the original; this report adds trials to the same
  `dataset_version` and re-reads the whole ledger.

## What was checked before spending

The three preconditions, in order, all free or near-free:

| Gate | Result |
|---|---|
| `fathom smoke` | ALL PASS (8/8) |
| `fathom validate skill-pyeng-v1` | 1 pass, 0 fail, 2 unverifiable — 5 of 6 criteria start false on the unmodified fixture |
| `fathom verify-arming --scenarios-dir scenarios/skill-pyeng` | ALL VERIFIED — both treatment arms' `--append-system-prompt-file` observed in the real argv, pointing at the declared body (235 and 15,587 bytes) |

Two of those three checks did not exist before this wave, and the bank-validation one initially
reported this bank as unmeasurable — a false positive in the new check, not in the bank. It read the
verifier's exit code, which this verifier gates on `behavior_preserved` (trivially true before the
agent starts), while the modernization signal lives in the five criteria that begin false. The check
was corrected to read the criteria before any of it was trusted.

## What was run

3 arms x 1 task x up to 4 repeats, single-session, `claude-opus-4-8` at high effort, headless
default-deny, 600 s trial cap, `max_turns = 80`. This wave added trials to the existing ledger at
`dataset_version = 1`; the resume key made the already-completed trials free.

**Ledger state this report is read against: `n = 4 / 4 / 3`** (bare / generic-nudge / pyeng-skill,
`status == "completed"` only), 14 trial rows and 14 run rows, ledger sha256 `c455b004…`. The stamp is
in `docs/reports/LEDGER-INDEX.md`, which is regenerated from the ledger and gated by
`tests/test_ledger_coverage.py`.

**Correction, 2026-08-11.** The first version of this report was written against a 10-trial snapshot
(`n = 4 / 3 / 3`, controls pooled 0/7, p = 0.0083). A fourth `generic-nudge` trial was appended to the
same ledger afterwards, in the same wave, and no document was updated. Every figure below has been
recomputed from the committed ledger; the pooled control pool is **0/8** and p = **0.0061**. The
direction of the verdict is unchanged and the separation is slightly stronger; what changed is that
the numbers now match the file they claim to read. The mechanism that let a report and its ledger
drift apart is fixed in `tests/test_ledger_coverage.py` (see the ledger index), not in this
paragraph.

## Result

### Pass rates — the headline is not the signal

| Arm | Pass | N | Rate | Wilson 95% CI |
|---|---|---|---|---|
| bare | 0 | 4 | 0.0% | [0.0%, 49.0%] |
| generic-nudge | 0 | 4 | 0.0% | [0.0%, 49.0%] |
| pyeng-skill | 3 | 3 | 100.0% | [43.8%, 100.0%] |

### Per-criterion — this is the signal

| Criterion | bare | generic-nudge | pyeng-skill |
|---|---|---|---|
| `behavior_preserved` | 4/4 | 4/4 | 3/3 |
| `dependency-groups` | 4/4 | 4/4 | 3/3 |
| `src-layout` | 4/4 | 4/4 | 3/3 |
| `pip-audit` | 1/4 | 1/4 | **3/3** |
| `ruff-single-quote` | **0/4** | **0/4** | **3/3** |
| `uv` | **0/4** | **0/4** | **3/3** |

Three criteria are saturated — every arm preserves behaviour, adopts `src/` layout and writes
`[dependency-groups]` unprompted. Those three measure nothing about the skill; a bank rebuilt today
would drop or harden them.

The separation lives in the other three, and on two of them it is total: `uv` and
`ruff-single-quote` are 3/3 for the skill arm and **0/8 across both control arms pooled** — Fisher's
exact two-sided p = 0.0061 for each, and the same for the all-criteria pass rate. These are the two
conventions a reader would call arbitrary — the choice of package manager and a quote style — which
is exactly the kind of specific, non-obvious convention a general-purpose model has no reason to
guess and a skill body can carry.

`pip-audit` moves in the same direction (3/3 against 2/8) but does **not** separate: p = 0.061. It
should not be counted toward the verdict, and three simultaneous criterion tests would want a
multiplicity correction in any case — at which point p = 0.0061 x 3 = 0.018 still holds for the two
that separate, and nothing else does.

`generic-nudge` — a short prompt telling the model to apply modern Python engineering practice, with
no skill body — scores identically to `bare` on every criterion. So the effect is not "being told to
care"; it is the content.

## Economy

| Arm | N | Tokens (min/med/max) | Turns (min/med/max) | Sessions/trial |
|---|---|---|---|---|
| bare | 4 | 26,830 / 47,677 / 61,341 | 44 / 86 / **260** | 1.75 |
| generic-nudge | 4 | 25,707 / 34,859 / 39,726 | 52 / 58 / 64 | 1.00 |
| pyeng-skill | 3 | 25,018 / 36,835 / 39,846 | 51 / 52 / 59 | 1.00 |

**The armed arm is the cheapest and the tightest.** That is worth stating plainly because the usual
prior is the opposite — that a skill body costs context and turns for whatever quality it buys. Here
the control arm is the expensive one: bare's turn range runs to 260 against a median of 86, and its
1.75 sessions per trial means it needed retries the other arms did not.

That 260-turn trial is the whole argument for the spread columns this wave added. Bare's *mean*
turns is dragged by it; the median is not. Before this wave the scorecard printed the mean alone,
and a reader comparing arms on it would have read bare as uniformly wasteful rather than as usually
comparable with an occasional blow-up.

## Verdict

**The existing conclusion survives the instrument fix, and it points away from retirement.** The
`python-engineering` skill beats both its no-skill baseline and a generic nudge, on two criteria
where the controls score zero, at lower token cost and fewer turns. The sibling retirement criterion
— "where the bare arm matches, the prose goes" — is **not met**: the bare arm does not match.

Neither defect that could have manufactured this result is present. The treatment arms were observed
armed on real spawns, and the bank leaves five of six criteria false on the untouched fixture.

## Limitations, stated at the power the data actually has

1. **K = 1.** This bank has one task. n = 3-4 per arm narrows the interval on *`modernize-timeflow`*,
   not on Python modernization. The pooled Wilson interval is a heuristic width under a single
   cluster, and adding repeats cannot fix it — only adding tasks can. **This is the binding
   limitation and no amount of spend on the current bank addresses it.**
2. **Three of six criteria are saturated**, so the bank measures less than its criterion count
   suggests.
3. **The result generalises to one skill.** CRAF-B01 names five. This report says nothing about
   `data-engineering-discipline`, `test-driven-development`, `context-handoff` or `feedback-triage`.
4. **`ruff-single-quote` is a convention check, not a quality check.** It measures whether the arm
   adopted a specific stated preference. That is a legitimate measure of whether a skill body
   transmits its content, and it is *not* evidence that the resulting code is better.

## Two defects this run found at cost

- **A verifier crash that destroyed a correct result, and did so with an arm-correlated bias.** A
  $2.00 trial was scored `errored` with `verifier error: non-JSON/crash`. This verifier imports the
  agent's modified package to check behaviour preservation, so anything that package prints at
  import time lands on stdout ahead of the JSON. Reproduced locally: a one-line `print` in
  `timeflow/__init__.py` flips a clean parse into an unscoreable error, while a warning, a `src/`
  layout move and the unmodified fixture all parse fine. Whether the agent adds a print is a
  property of the *arm*, so the discard rate is arm-correlated — a silent bias, not merely a lost
  trial. Fixed harness-side for every bank: the criteria dict is now recovered from the last JSON
  object on stdout. `fathom validate` cannot catch this class, because it only ever runs the
  verifier against the *unmodified* fixture.
- **A per-spawn cap set below the arm's need burns the money and scores nothing.** A `$2.00` cap was
  set from a guess; the bare arm needs more, so the trial errored at the cap having spent $2.04. The
  cap must be set from an observed figure, which argues the same way as FATH-B04.

## The other reference bank: the process-discipline plugin arms

The same sibling item names a second existing bank — predecessor-versus-successor for the
process-discipline plugin (`humble-vs-super-v1` … `-v4`). Its five arms carry `[plugins] mount`,
which is the **exact axis that produced the recorded unarmed-arm result**, so the cheapest decisive
check was to point the new verifier at them rather than to re-run 120 trials:

```
verify-arming: 5 arm(s), 4 declaring a treatment axis   →   ALL VERIFIED
  humble-only   registered=['humblepowers']
  stack-humble  registered=['engineering-discipline', 'humblepowers', 'session-workflow']
  stack-super   registered=['engineering-discipline', 'session-workflow', 'superpowers']
  super-only    registered=['superpowers']
```

Every declared mount registers in a live spawn, and none of these plugins serves MCP tools, so the
denied-tool failure mode does not apply to them at all. `fathom validate` also passes on all four
banks (0 fail). **The existing humble-vs-super verdicts therefore stand un-invalidated** and needed
no re-spend.

**What this check does and does not prove.** It proves the plugin was *available* to the session —
registration at the CLI init layer. It does **not** prove any skill *fired*: availability and
activation are different questions, and the second one needs stream-level activation counting (which
`fathom.streams` now packages, and which the rg-2x2 study measured by hand). For a mount-based arm,
"registered but never triggered" remains a live failure mode this gate does not close.

## Ledger

Appended to `ledger/skill-pyeng-v1.jsonl` at `dataset_version = 1`. Two trials in this wave were
recorded `status="errored"`, and — as of this wave — carry `valid=false` with no criteria dict, so a
later reader cannot mistake them for measured failures. (A third `bare` errored row predates the
`valid` field; it too carries no criteria dict. All three are excluded from every count above, which
reads `status == "completed"` only.)

Per-arm completed counts and the ledger hash this report is bound to are stamped in
`docs/reports/LEDGER-INDEX.md`; `tests/test_ledger_coverage.py` fails if the ledger moves and the
stamp is not re-rendered. That gate exists because it did not: the first version of this report was
published against a 10-trial snapshot and an eleventh trial landed afterwards with nothing to catch
it.
