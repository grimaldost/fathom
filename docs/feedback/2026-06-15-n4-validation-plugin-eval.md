# fathom feedback — N4 validation run (humblepowers 0.4.0 vs 0.3.1)

- **Date:** 2026-06-15
- **Tool/version:** fathom (current `main`); used the `humble-vs-super-v1` bank + `scenarios/humble-vs-super` arms.
- **Context:** Validated a craft-collection change (humblepowers 0.4.0, the N4 regression-test-after-fix calibration) by re-vendoring `humblepowers@0.4.0` into the bank, repointing the two humble arms, and re-running them on the 2 bug-fix tasks × 5 repeats. Goal: does `regression_test_present` close the gap to superpowers?
- **Outcome:** Clean, decisive verdict. The eval did exactly its job — the re-vendor + resume mechanism made the before/after a one-command comparison, and the result was unambiguous (50%/60% → 100%/100%, fix_correct + no_regression held 100%).

## What worked

- **Plugin-mount + vendored-version + resume is the right shape for a plugin-change A/B.** Re-vendoring only the treatment plugin changed only the humble arms' `config_hash`; `fathom run` then re-spawned *only* those two arms (20 trials) and skipped the 30 unchanged baseline trials automatically. The `@0.3.1` baseline stayed in the ledger, so the before/after was directly comparable from one append-only file — no separate baseline re-run, no manual bookkeeping.
- **`regression_test_present` is precisely the N4 signal.** The fix-task verifier already grades "the candidate's test fails on the original source and passes on the fix," which is exactly the behaviour the humblepowers change targets. Blind, verifier-first scoring meant the verdict didn't depend on a judge.
- **`config_hash` over working-tree file contents (not git HEAD)** meant the re-vendor took effect with no commit needed — the run hashed the working tree directly. Right call for fast iteration.

## Friction

- **[MED] `fathom smoke` and `fathom run` crash on Windows cp1252 when a spawn's output carries a non-cp1252 char.** Smoke's first 4 checks passed, then `print(...)` of a spawn result containing `👋` raised `UnicodeEncodeError: 'charmap' codec can't encode '\U0001f44b'` (cp1252 console). The checks themselves were fine — only the *print* died. Worked around with `PYTHONIOENCODING=utf-8`. On a paid matrix this could abort mid-run and waste trials. (phase: run / smoke output)
- **[LOW] The vendored-dir `@version` naming is easy to miss when re-vendoring.** The mount path is `.../plugins/humblepowers@0.3.1`, but the dir is easy to copy into as `.../plugins/humblepowers` (no suffix) — which the scenarios never read, so the run silently used the old plugin (`0 trials, 100 already done` on the dry-run was the only tell). A `git write-tree`-style or content-hash mismatch warning, or a re-vendor note in `VENDORED.md`, would catch this. (phase: authoring / re-vendor)
- **[LOW] `fathom run`'s streamed per-trial progress + cost summary didn't reach captured stdout in a headless/background invocation** — only the upfront planning line (`planned: 20 trials … ceiling $40`) was in the captured output; the per-trial results and any final cost line were not, so the actual USD of the run had to be read from the ledger rather than the run's own summary. (phase: run / observability)

## Misses

- None. The harness produced a correct, blind, reproducible verdict; the friction above is ergonomic, not a measurement defect.

## Vacuous gates

- None observed. The `regression_test_present` criterion is non-vacuous (it distinguishes a real red-green regression test from none, per the bank's verifier design), and the baseline arms (bare 0%, super 90%) bracket the signal correctly.

## Proposed promotions / changes

1. **[MED]** Force UTF-8 on the harness's own stdout — `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the top of `smoke.py` and the `fathom run` output path (mirroring what the craft-collection eval harness does in `run_triggers.py`/`aggregate.py`) — so a spawn emitting an emoji can't crash the gate or abort a paid matrix on a cp1252 console. Home: `src/fathom/smoke.py`, `src/fathom/cli.py`.
2. **[LOW]** Document the re-vendor step + the `@version` dir convention in `tasks/humble-vs-super-v1/plugins/VENDORED.md` (copy into a new `name@version` dir, repoint the arm scenarios), and consider a `fathom run` warning when a scenario's mounted plugin dir name's `@version` disagrees with the `version` in its `plugin.json` — the wrong-dir copy would have been caught immediately. Home: `VENDORED.md`, optionally `src/fathom/cli.py` (warn-on-mismatch).
3. **[LOW]** Emit a closing summary line to stdout on `fathom run` (`N trials completed, $X spent`) so headless/background captures record the cost without parsing the ledger. Home: `src/fathom/cli.py`.

## Cost

The focused validation run was 20 trials (2 humble arms × 2 bug-fix tasks × 5 repeats), opus@high, `Task` allowed. Per-trial ceiling $2 (printed); the run's actual USD was not surfaced in captured stdout (finding #3) — read from the ledger if a precise figure is needed. The resume mechanism meant the 30 baseline trials cost nothing to re-use.
