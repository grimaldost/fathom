# convoy efficiency & model-tier recalibration — recurring playbook

**Purpose.** Keep convoy an efficient agentic-coding tool as the Claude lineup evolves: re-verify
that the tier map routes the cheapest-adequate model per task difficulty, on the *current* models.
**Trigger:** a new Claude model ships (esp. a tier's model — Haiku/Sonnet/Opus/Fable), or quarterly.
**Owner disciplines:** fathom method (ADR/spec/blind-grade/append-only ledger) + the model-policy owner bound in Step 0.

A zero-context operator can run this cold. Real spend is ≈ $0 under subscription auth (the numbers are
token×price *estimates*); still pass `--max-budget-usd` as a hard stop.

---

## Step 0 — Model freshness
**Role:** the model-policy owner — the single place the tier→model map and its downstream mirrors are
updated. **Bound to:** the humblepowers `choosing-models` skill and its `/refresh-models` command
(canonical data: `skills/choosing-models/models.toml`).

Run `/refresh-models`, land the changeset it proposes, then continue at Step 1. It owns convoy's
`src/convoy/core/governance.py` (`DEFAULT_TIER_MODELS`), `src/convoy/core/pricing.py` (`_FAMILY_RATES`),
`skills/convoy/SKILL.md`'s tier/cost table, `src/convoy/interface/scaffold.py`'s starter model, and
fathom's own `src/fathom/adapters/claude_cli.py` (`_PRICE_PER_1K`) and
`docs/method/series-toml-skeleton.md` pins — so you know what NOT to hand-edit. This playbook does not
co-own them; a mirror edit made here instead is how the two rituals drift apart.

**Fallback (owner not installed / no mirror binding registered).** `/refresh-models` walks its mirror
sites only when a mirror-sites table is registered in project or user memory, and that binding lives in
the operator's global config outside this repo — so a bare "run /refresh-models" silently no-ops when
the plugin or the binding is absent, and this playbook must not hard-depend on a plugin being installed.
When the owner cannot run, do the walk by hand:
1. Confirm current model IDs + pricing via the `claude-api` skill (never from memory).
2. convoy repo — edit `DEFAULT_TIER_MODELS` in `src/convoy/core/governance.py`
   (`weak`/`mid`/`strong` → the current Haiku/Sonnet/Opus ids), the per-family USD/MTok rates in
   `src/convoy/core/pricing.py` (`_FAMILY_RATES`), the tier/cost table in `skills/convoy/SKILL.md`
   (add a dated changelog row), and the starter model in `src/convoy/interface/scaffold.py`.
3. fathom repo — the `_PRICE_PER_1K` rates in `src/fathom/adapters/claude_cli.py` and the pinned
   model/effort strings in `docs/method/series-toml-skeleton.md`.
4. Update the governance/pricing-asserting tests; leave explicit-pin tests + historical fixtures alone.
5. Verify against the **repo source** (edits don't reach an installed CLI/plugin until reinstalled):
   `uv run --project . convoy validate <series.toml>` · `uv run --project . pytest -q`.

**What stays here:** thresholds. `/refresh-models` classifies a threshold or tier-assignment move as
needing calibration evidence and routes it back to this playbook — Steps 1-3 produce that evidence.
Lineup freshness there, threshold evidence here.

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
narrow distribution at small n → **update the model-policy owner's calibration note (choosing-models'
rubric changelog + `models.toml` provenance), not the thresholds** (record the run + the observed
direction). Over-fitting global defaults to one corpus is the trap.

## Step 3 — Record
- fathom report at `docs/reports/YYYY-MM-DD-model-tier-recalibration.md`.
- Model-policy owner updated — the choosing-models calibration note / `models.toml` provenance
  (evidence + decision); via `/refresh-models` where installed.
- This run-state pattern: keep a `docs/specs/YYYY-MM-DD-recalibration-run-state.md` current so
  auto-compaction can't lose the thread.

---

## Known limitation & the standing high-leverage fix
`model-tier-v1` **over-saturates**: 6/7 tasks are aced by every tier, so calibration rests on one task.
The single highest-leverage improvement is a **"boundary + heterogeneity" task set** — cross-module /
displaced-cause / backend-parity tasks that *reliably* separate tiers at graded difficulty (not flaky).
This both sharpens calibration AND unblocks the deferred efficiency study.

## Deferred: the efficiency study (needs budget + heterogeneity)
`pp-native-tier` (per-PR routing) vs `pp-all-<mid>` (flat) vs `pp-fixed-opus` (ceiling), plus a plain-Claude
`bare` baseline. The 2026-06-19 pre-mortem showed it **cannot produce signal without tier heterogeneity**
in the anchors (all reliable PRs cluster at one tier → routing = uniform downshift). Prerequisites before
spending: (a) the heterogeneity task set above; (b) validate a `series` arm under the harness
(engine spawns `bypassPermissions` — fathom's single-session arms are default-deny and unaffected, but the
series strategy must be smoke-tested as a subprocess); (c) separate budget approval.
