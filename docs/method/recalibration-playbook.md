# convoy efficiency & model-tier recalibration — recurring playbook

**Purpose.** Keep convoy an efficient agentic-coding tool as the Claude lineup evolves: re-verify
that the tier map routes the cheapest-adequate model per task difficulty, on the *current* models.
**Trigger:** a new Claude model ships (esp. a tier's model — Haiku/Sonnet/Opus/Fable), or quarterly.
**Owner disciplines:** fathom method (ADR/spec/blind-grade/append-only ledger) + the model-policy owner bound in Step 0.

A zero-context operator can run this cold. Real spend is ≈ $0 under subscription auth (the numbers are
token×price *estimates*); still pass `--max-spawn-usd` as a hard stop, and `--max-run-usd`
to bound what the whole invocation may spend.

---

## Step 0 — Model freshness
**Role:** the model-policy owner — the single place the tier→model map and its downstream mirrors are
updated. **Bound to:** the humblepowers `choosing-models` skill and its `/refresh-models` command
(canonical data: `skills/choosing-models/models.toml`).

Run `/refresh-models`, land the changeset it proposes, then continue at Step 1. **Which files it
owns is its own registry to answer, not this playbook's** — the list lives in the operator's
mirror-sites bindings file (`$MODEL_MIRRORS_FILE`, else `~/.claude/model-mirrors.toml`), and
`/refresh-models` walks it as a command. Restating the list here made this document a fourth copy of
it, which drifted: the entry naming this repo's adapter price table stayed after that table was
deleted, and the entry for `src/fathom/routing.py` — a real price mirror — was never here at all.
This playbook does not co-own the mirrors; a mirror edit made here instead is how the two rituals
drift apart.

**Fallback (owner not installed).** This playbook must not hard-depend on a plugin being installed,
so when the owner cannot run, do the walk by hand — but read the site list from the bindings file
rather than from here, for the reason above. An absent bindings file is a legitimate state in a fresh
environment; it is not "clean", and the walk says so rather than passing silently.
1. Confirm current model IDs + pricing via the `claude-api` skill (never from memory).
2. For each `[[site]]` in the bindings file, honour its `vocabulary`: a family-named copy is
   **translated**, never substituted, and a family-keyed price table is untouched by a model-id change
   inside that family but not by a repricing between generations.
3. Then grep every repo for the `[[retired]]` patterns — outgoing model ids AND outgoing price
   literals. The id-only grep is what let a family-keyed price table go unregistered.
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
4. Run: `... --repeats 5 --max-spawn-usd 75`. Resume-safe — re-run the same command to continue after
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
