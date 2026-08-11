# Re-running the python-engineering reference bank against the MERGED skill body — skill-pyeng-v1

- **Date:** run and report 2026-08-11 (wave 2, branch `eval/wave-2`). Bank: `skill-pyeng-v1`
  (one task, `modernize-timeflow`); arms `bare` / `generic-nudge` / `pyeng-skill` in
  `scenarios/skill-pyeng/`, differing only in `[context] inject`.
- **Question (operator):** the 2026-08-11 re-validation
  (`2026-08-11-skill-pyeng-v1-revalidation.md`) closed the two instrument defects and found the
  verdict intact — but it measured a **2026-07-03 snapshot** of the skill body, not the skill that
  is shipped today. Does the verdict hold for the **merged** plugin content?
- **Standing:** a re-run at a forked `config_hash`, not a new analysis. Same bank, same
  `dataset_version = 1`, same model pin; the only variable changed is the injected body.

## Which copy of the skill was exercised — the whole point of this run

The collection's own feedback rule asks which copy of a tool a measurement actually touched. Here
the answer is unambiguous and was verified on a real spawn, not asserted:

| | |
|---|---|
| **Exercised** | `C:/Users/grima/Documents/craft-collection/plugins/engineering-discipline/skills/python-engineering/SKILL.md` — the **worktree** on merged `main` (`07fea4f`), engineering-discipline **0.4.0** |
| Copied verbatim to | `scenarios/skill-pyeng/assets/python-engineering.md` (17,895 bytes, sha256 `4e311b5d…`) |
| Replaced | the 2026-07-03 snapshot (15,587 bytes, sha256 `ee154e4a…`) |
| **Not** exercised | the installed plugin cache `~/.claude/plugins/cache/craft-collection/engineering-discipline/0.3.0` — which is a **release behind** the worktree |
| Verified how | `fathom verify-arming --scenarios-dir scenarios/skill-pyeng` → `pyeng-skill: [PASS/verified] … body_bytes=17895`, and the same check re-ran as the run's own pre-flight |

The delta is substantive, not cosmetic: the merged body adds a whole **"Modifying existing code (the
edit lane)"** section, an `httpx` row, the PEP 698 `@override`-vs-`Protocol` caveat, and a
tests-never-inside-`src/` rule. `modernize-timeflow` is a modernization task, so the edit-lane
section is *not* the lane this task exercises — which makes the re-run a fair test of whether ~2.3 KB
of added, partly off-task prose degrades the on-task result.

**The environment is stale across the board and this matters for reading any of wave 2.** Every
installed plugin cache trails its merged worktree: engineering-discipline 0.3.0 vs 0.4.0,
humblepowers 0.8.0 vs 0.9.0, session-workflow 0.20.0 vs 0.21.0, keel 0.13.1 vs 0.14.0, convoy 0.7.0
vs 0.8.0, mantis-research 0.1.2 vs 0.2.0, fathom 0.1.0 vs 0.2.0. Every measurement in this wave
reads from the **worktrees**.

## The model pin was checked rather than assumed

The wave brief expected `claude-opus-4-8` to be superseded by `claude-opus-5` and the pin to need
updating. **It does not.** A three-way probe against the live seat:

| pin | `modelUsage` key returned | verdict |
|---|---|---|
| `claude-opus-4-8` | `claude-opus-4-8` | still served |
| `claude-opus-5` | `claude-opus-5` | served |
| `claude-bogus-9` | *(empty)* + "may not exist or you may not have access" | fails loud |

So the CLI does **not** silently alias an unknown id — it refuses — and the existing pin resolves to
the model it names. The pin was therefore **left unchanged**, which is the stronger design: it holds
model constant and forks `config_hash` on the injected body alone, and it lets both control arms
resume-reuse their existing trials for free. Changing the pin would have re-purchased all three arms
and confounded the content change with a model change.

*(Side finding, relevant to FATH-B16's cross-review: those probe calls reported a real non-zero
`total_cost_usd` — ~$0.19 for a single one-turn Opus call — on this subscription seat. That
corroborates convoy's finding that the terminal result event carries a real cost, against the
standing D2 premise that subscription auth always reports `0`.)*

## What was checked before spending

| Gate | Result |
|---|---|
| `uv run fathom smoke` | **ALL PASS (8/8)** |
| `uv run fathom validate skill-pyeng-v1` | 1 pass, 0 fail, 2 unverifiable — 5 of 6 criteria start false on the unmodified fixture |
| `uv run fathom verify-arming --scenarios-dir scenarios/skill-pyeng` | ALL VERIFIED — `body_bytes=17895`, the merged body, in the real spawn argv |
| `--dry-run` | 3 trials planned, 6 already done, ceiling $6.00 |
| pilot | `--repeats 1` (1 trial) first, to measure real per-trial cost before buying the rest |

## What was run

3 new `pyeng-skill` trials at the forked `config_hash` `85f168419bbb…`, single-session,
`claude-opus-4-8` at high effort, headless default-deny, 600 s cap, `max_turns = 80`,
`--max-budget-usd 5.00` (set above the observed ~$2/trial after the previous wave lost $2.04 to a cap
set from a guess). Both control arms resume-reused: their `config_hash` did not change, so they cost
**$0**.

**Total spend for this measurement: $5.83** (3 trials, $1.58 / $1.88 / $2.37).

## Result

### Per-criterion — read this, not the headline

Pooled controls = `bare` (n=4) + `generic-nudge` (n=4), which are identical on every criterion.

| Criterion | pooled controls | pyeng-skill (2026-07-03 snapshot) | **pyeng-skill (MERGED 0.4.0)** |
|---|---|---|---|
| `behavior_preserved` | 8/8 | 3/3 | **3/3** |
| `dependency-groups` | 8/8 | 3/3 | **3/3** |
| `src-layout` | 8/8 | 3/3 | **3/3** |
| `pip-audit` | 2/8 | 3/3 | **3/3** |
| `ruff-single-quote` | **0/8** | 3/3 | **3/3** |
| `uv` | **0/8** | 3/3 | **3/3** |
| all-criteria pass rate | 0/8 | 3/3 | **3/3** |

`uv` and `ruff-single-quote`: 3/3 against **0/8** pooled controls → Fisher exact two-sided
**p = 0.0061** each (0.0182 after a Bonferroni ×3 for the three non-saturated criteria). The
all-criteria pass rate carries the same p. `pip-audit` moves the same way (3/3 vs 2/8) but does not
separate: p = 0.061.

The merged body reproduces the snapshot body **criterion for criterion, exactly**.

### Economy — the merged body is cheaper than the body it replaced

Computed **by `config_hash` from the ledger**, not from the scorecard (see the defect below).

| Arm (content) | n | Turns min/med/max | In+out tokens min/med/max | $/trial |
|---|---|---|---|---|
| `bare` | 4 | 44 / 61 / 136 | 35 / 26,830 / 39,815 | (3 errored runs; see note) |
| `generic-nudge` | 4 | 52 / 59 / 64 | 25,707 / 35,189 / 39,726 | — |
| `pyeng-skill` (snapshot) | 3 | 51 / 52 / 59 | 25,018 / 36,835 / 39,846 | — |
| **`pyeng-skill` (merged 0.4.0)** | 3 | **43 / 43 / 59** | **18,930 / 22,829 / 24,612** | **1.58 / 1.88 / 2.37** |

The merged arm is the **cheapest and tightest arm in the bank on every axis** — fewer turns than the
snapshot arm it replaces (median 43 vs 52) and roughly **38% fewer in+out tokens** (median 22,829 vs
36,835), while scoring identically. A 15% larger skill body bought a smaller run. That is the
opposite of the usual prior and it is the second time this bank has produced it.

*(`bare`'s 136-turn / 35-token row is one of its three `errored` runs, not a completed trial; those
rows now carry `valid=false` and no criteria dict.)*

## A reporting defect this run walked into — the scorecard pooled two content versions

`fathom report` keys arms by **scenario name** and maps `config_hash → name`, so two `config_hash`es
that share an arm name are pooled in Economy, Efficiency and Arm Health. Because this run forked
`pyeng-skill`'s hash without renaming the arm, the rendered scorecard reported, for `pyeng-skill`:

- `Sessions/Trial 2.00` — six run rows (three old + three new) attributed to three trials;
- `Turns (min/med/max) 94/102/111` — the two versions' turns **summed** per cell;
- `Arm Health: 3/3 trials at/over max_turns` — an artifact of that summing (the real turns are
  43/43/59, all comfortably under the cap of 80), carrying the footnote "its pass rate is a **lower
  bound**, not a score", which here is simply false.

Pass Rates and Per-Criterion are **unaffected** — they key on `(scenario, task, repeat)` with
last-write-wins, so the newer trials correctly displaced the older ones. Only the economy views
conflate. This is a live mis-read risk for exactly the operation this wave performs — re-running an
arm against updated tool content — and the workaround (aggregate by `config_hash` off the ledger) is
the same hand-join FATH-B13 already records. Filed as **FATH-B49**.

## Verdict — CRAF-B01, `python-engineering`: CONFIRMED at the merged version

The gate's decision rule is "where the bare arm matches, the prose goes". Against the **merged
0.4.0** body the bare arm does not match: it scores **0/8 on `uv` and `ruff-single-quote`** where the
skill scores 3/3, p = 0.0061, and it does so while the skill arm is the cheapest arm in the bank. The
2026-08-11 verdict **holds for the shipped content**, and it points away from retirement, more
strongly than before on economy and identically on quality.

`generic-nudge` remains indistinguishable from `bare` on every criterion, so the effect continues to
be the skill's content rather than the fact of being told to care.

## Limitations — unchanged, and still binding

1. **K = 1.** One task. n = 3 narrows the interval on `modernize-timeflow`, not on Python
   modernization. Repeats cannot fix it; only tasks can. This remains the binding limitation.
2. **Three of six criteria are saturated** (all arms 100%), so the bank measures less than its
   criterion count suggests.
3. **One skill of the five CRAF-B01 names.** Nothing here speaks to
   `data-engineering-discipline`, `test-driven-development`, `context-handoff` or `feedback-triage`.
4. **`ruff-single-quote` is a transmission check, not a quality check** — it measures whether a
   stated preference crossed into the output, which is legitimate evidence that a skill body
   transmits, and is not evidence that the code is better.
5. The controls' trials were purchased in earlier waves. They are reused because their
   `config_hash` is byte-identical, which is exactly what the resume key promises — but they are not
   contemporaneous with the treatment trials.

## The other half of CRAF-B01: the process-discipline banks — planned, priced, NOT run

`humble-vs-super-v1…v4` mount whole plugin trees. Their vendored copies are far behind merged:

| tree vendored in the bank | vendored version | merged worktree |
|---|---|---|
| `humblepowers@0.4.0` | 0.4.0 | **0.9.0** |
| `engineering-discipline` | 0.1.2 | **0.4.0** |
| `session-workflow` | 0.2.2 | **0.21.0** |

A re-run at merged content is a genuinely new measurement rather than a reproduction — but it is
**unaffordable inside this wave's ceiling**:

| shape | trials | est. cost |
|---|---|---|
| `humble-vs-super-v2` at its published power (3 arms × 4 dev tasks × n=20) | 60 | **~$120** |
| a 1-repeat pilot (3 arms × 4 dev tasks × 1) | 12 | **~$24** |

Either figure displaces a whole sibling gate at the $130 ceiling, so **neither was run**, and the
prior wave's finding stands unchanged: the four banks pass `fathom validate`, all four mount arms
verify armed, and the published v1–v4 verdicts remain **un-invalidated at the versions they
measured** (0.3.1 / 0.4.0). They are **not** re-validated at 0.9.0, and this report does not claim
they are. Note also that the v3/v4 banks are the two the backlog already declines to re-run because
their ceiling is the mode `fathom validate` cannot detect.

## Ledger

Appended to `ledger/skill-pyeng-v1.jsonl` at `dataset_version = 1`, `config_hash`
`85f168419bbb…` (the merged body). The snapshot-body rows at `4915739e2519…` are untouched and
remain distinguishable — which is the append-only ledger doing exactly its job.
