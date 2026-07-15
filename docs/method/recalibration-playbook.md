# convoy efficiency & model-tier recalibration — recurring playbook

**Purpose.** Keep convoy an efficient agentic-coding tool as the Claude lineup evolves: re-verify
that the tier map routes the cheapest-adequate model per task difficulty, on the *current* models.
**Trigger:** a new Claude model ships (esp. a tier's model — Haiku/Sonnet/Opus/Fable), or quarterly.
**Owner disciplines:** fathom method (ADR/spec/blind-grade/append-only ledger) + `convoy:model-tiers`.

A zero-context operator can run this cold. Real spend is ≈ $0 under subscription auth (the numbers are
token×price *estimates*); still pass `--max-budget-usd` as a hard stop.

---

## Step 0 — Model freshness (convoy repo)
Update convoy's tier map + pricing to the current lineup and verify against the **repo source** (edits
don't reach the installed CLI/plugin until reinstalled — use `uv run` from the convoy repo). convoy
replaced pr-pilot, so the paths below are the as-built homes (not the old `pr_pilot` package):
1. Confirm current model IDs + pricing via the `claude-api` skill (never from memory).
2. Edit the tier→model map in `src/convoy/core/governance.py` (`DEFAULT_TIER_MODELS`:
   `weak`/`mid`/`strong` → the current Haiku/Sonnet/Opus ids), and the per-family USD/MTok rates in
   `src/convoy/core/pricing.py` (`_FAMILY_RATES`).
3. Mirror any tier/cost table documented in `skills/convoy/SKILL.md`; add a dated changelog row.
4. Update the governance/pricing-asserting tests; leave explicit-pin tests + historical fixtures alone.
5. Verify: `uv run --project . convoy validate <series.toml>` (a series' models resolve against the map)
   · `uv run --project . pytest -q` (convoy's own suite green).

## Step 1 — Calibration re-run (fathom repo), cheaply
Reuse the `model-tier-v1` bank and the `scenarios/model-tier/` arms. Because the ledger resume-key is
`(bank, dataset_version, task_id, config_hash, repeat)`, **unchanged arms are skipped for free** — only
the changed model costs.
1. Add a NEW arm file `scenarios/model-tier/<newmodel>.toml` (copy an existing arm; change only
   `name` + `model`). Do **not** mutate an existing arm (that conflates old/new under one name).
2. `uv run fathom smoke` — gate (expect 8/8; confirms real-spawn works in this environment).
3. Dry-run: `uv run fathom run model-tier-v1 --scenarios-dir scenarios/model-tier --repeats 5 --dry-run`
   → confirm it plans ONLY the new arm's trials ("planned N (… already done)"). If it plans the cached
   arms too, a shared field changed the `config_hash` — inspect before spending.
4. Run: `... --repeats 5 --max-budget-usd 75`. Resume-safe — re-run the same command to continue after
   any interruption (compaction/crash). Long: launch in the background.
5. `uv run fathom report model-tier-v1` → `report/scorecard-model-tier-v1.md`.

## Step 2 — Analysis lenses (use the scorecard)
- **On-diagonal rate** (predicted vs empirically-cheapest-adequate tier). Historically 1/7 — the map
  over-provisions on cross-module-bugfix distributions.
- **Per-task quality ladder** — where does the new model land vs neighbours? (the discriminating task,
  `fix-nonlocal-parse`, is the load-bearing one; most tasks saturate.)
- **Dose-response** (+quality per upgrade) and **cost-quality Pareto**.
- **Cost caveat** — a newer model can be token-heavier (new tokenizer, adaptive-thinking-on), so a lower
  per-token price ≠ lower per-task cost. Report tokens beside $; treat est $ as list-equivalent.

**Decision rule.** Change the numeric thresholds ONLY on a robust, cross-distribution shift. A single
narrow distribution at small n → **update the `model-tiers` calibration note, not the thresholds**
(record the run + the observed direction). Over-fitting global defaults to one corpus is the trap.

## Step 3 — Record
- fathom report at `docs/reports/YYYY-MM-DD-model-tier-recalibration.md`.
- convoy `model-tiers` calibration note + changelog updated (evidence + decision).
- This run-state pattern: keep a `docs/specs/YYYY-MM-DD-recalibration-run-state.md` current so
  auto-compaction can't lose the thread.

---

## Known limitation & the standing high-leverage fix
`model-tier-v1` **over-saturates**: 6/7 tasks are aced by every tier, so calibration rests on one task.
The single highest-leverage improvement is a **"boundary + heterogeneity" task set** — cross-module /
displaced-cause / backend-parity tasks that *reliably* separate tiers at graded difficulty (not flaky).
This both sharpens calibration AND unblocks the deferred efficiency study.

The plan of record for this fix is designed in
[`docs/specs/2026-07-14-tier-separating-bank-design.md`](../specs/2026-07-14-tier-separating-bank-design.md):
a `model-tier-v2` roster admitted by a cheap **weak-model-fails screen** (a task enters the bank only
after weak fails / strong passes its hard criteria), crossed **model × oracle-quality** to also settle
the `choosing-models` oracle-coverage discount (labeled a hypothesis until this runs). Authored, not yet
run — the paid matrix is a separate budget decision (§ *Deferred* below).

## Deferred: the efficiency study (needs budget + heterogeneity)
`pp-native-tier` (per-PR routing) vs `pp-all-<mid>` (flat) vs `pp-fixed-opus` (ceiling), plus a plain-Claude
`bare` baseline. The 2026-06-19 pre-mortem showed it **cannot produce signal without tier heterogeneity**
in the anchors (all reliable PRs cluster at one tier → routing = uniform downshift). Prerequisites before
spending: (a) the heterogeneity task set above; (b) validate a `series` arm under the harness
(engine spawns `bypassPermissions` — fathom's single-session arms are default-deny and unaffected, but the
series strategy must be smoke-tested as a subprocess); (c) separate budget approval.
