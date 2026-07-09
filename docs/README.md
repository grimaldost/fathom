# docs/

Map of the documentation tree. The root [`README.md`](../README.md) says what fathom is and how
to run it; [`CLAUDE.md`](../CLAUDE.md) is the operating manual (recipes, as-built schemas,
conventions). Everything else lives here.

Two kinds of document, two disciplines:

- **Live documents** — kept current as the system changes: `STATUS.md`, the two core specs, the
  series-engine contract, the method kit, this file.
- **Dated records** — specs, plans, run notes, and findings reports named `YYYY-MM-DD-*`. They
  are part of the longitudinal record: kept verbatim, corrected only with dated banners (see the
  2026-06-15 report for the pattern), never silently rewritten — the same discipline as the
  append-only ledger. References inside them reflect their date.

## Start here

| File | What it is |
|---|---|
| [`STATUS.md`](STATUS.md) | The index: analyses run (with verdicts and report links), open defects/items, next steps. |
| [`specs/2026-06-10-fathom-v1-design.md`](specs/2026-06-10-fathom-v1-design.md) | Architecture: purpose, constraints, module map, ledger and grading design (with as-built notes). |
| [`specs/2026-06-10-fathom-v1-build.md`](specs/2026-06-10-fathom-v1-build.md) | Build spec: numbered sections, invariants + enforcement table, PR manifest, pre-mortem certification. |
| [`specs/2026-07-03-series-engine-contract.md`](specs/2026-07-03-series-engine-contract.md) | The engine-agnostic contract the `series` arm drives; convoy is the reference producer. |

## adr/ — decisions

One decision per file; an accepted ADR is never edited, only superseded.

| ADR | Decision |
|---|---|
| [0001](adr/0001-subscription-cli-behind-vendor-abstract-runner.md) | All model calls go through a vendor-abstract `Runner`; v1 binds it to the subscription Claude CLI. |
| [0002](adr/0002-trial-run-append-only-ledger.md) | Two-level trial/run records in an append-only, committed JSONL ledger; resume by content hash. |
| [0003](adr/0003-blind-result-only-scoring.md) | Scoring is blind and result-only; trajectory and economy join after scoring. |
| [0004](adr/0004-vendor-claude-runner-core.md) | Vendor the proven claude_runner core; spawn-isolation properties asserted by the smoke gate. |
| [0005](adr/0005-sealed-holdout-tasks.md) | Every bank carries sealed holdout tasks; a spent holdout is dev data. |
| [0006](adr/0006-plugin-mount-fidelity.md) | Mount whole plugins via `--plugin-dir` to preserve triggering fidelity. |
| [0007](adr/0007-model-tier-calibration.md) | Model-tier calibration study design (hard-criteria fraction, ε + CI-overlap tier rule). |

## reports/ — the per-analysis record

Each analysis leaves a committed ledger (`ledger/<bank>.jsonl`), a design spec when one was
written, and a report here. **Run notes** record how the matrix went (invalid runs, resume
events, defects found); **findings reports** carry the full analysis. `STATUS.md`'s "Analyses
run" table is the authoritative index with verdicts; by series:

| Analysis series | Design / plan | Reports |
|---|---|---|
| Series engine v1 (single session vs multi-PR series vs bare, 2026-06-10) | in the v1 build spec §12–13 | run notes: [`2026-06-10-pr-pilot-v1-first-matrix.md`](reports/2026-06-10-pr-pilot-v1-first-matrix.md) |
| Skill effectiveness: `python-engineering` (2026-06-13) | [design](specs/2026-06-13-fathom-skill-eval-pyeng-design.md) · [plan](plans/2026-06-13-skill-eval-pyeng-plan.md) | run notes: [`2026-06-13-skill-pyeng-v1-first-matrix.md`](reports/2026-06-13-skill-pyeng-v1-first-matrix.md) |
| Plugin eval: humblepowers vs superpowers, v1–v4 (2026-06-14 → 06-16) | [design](specs/2026-06-14-fathom-humble-vs-super-design.md) | run notes: [`v1 first matrix`](reports/2026-06-14-humble-vs-super-v1-first-matrix.md) · findings: [`v1`](reports/2026-06-14-humblepowers-vs-superpowers.md), [`v2` (corrected by v3/v4)](reports/2026-06-15-humblepowers-0.4.0-vs-superpowers.md), [`v3/v4 powered confirmatory`](reports/2026-06-16-humble-vs-super-powered-confirmatory.md) |
| Model-tier calibration (2026-06-16 → 07-01) | [design](specs/2026-06-16-fathom-model-tier-calibration-design.md) · ADR-0007 | findings: [`calibration`](reports/2026-06-16-model-tier-calibration.md), [`Sonnet-5 recalibration`](reports/2026-07-01-model-tier-recalibration.md) |
| Context-size calibration: does volume shift the tier? (2026-06-16) | bank README `tasks/context-size-v1/README.md` (design + GO gate; its cited ADR-0008 was lost in the history squash — see STATUS open items) | findings: [`context-size`](reports/2026-06-16-context-size-calibration.md) |
| Series-engine usefulness + value ablation (2026-07-01) | [usefulness v2](specs/2026-07-01-pr-pilot-usefulness-v2-design.md) · [full ablation (superseded)](specs/2026-07-01-pr-pilot-full-ablation-design.md) · [ablation v2 brownfield](specs/2026-07-01-ablation-v2-brownfield-design.md) | findings: [`usefulness`](reports/2026-07-01-pr-pilot-usefulness-findings.md), [`beyond the engine` (analysis, no run)](reports/2026-07-01-pr-pilot-beyond-the-engine.md), [`ablation v2`](reports/2026-07-01-pr-pilot-ablation-v2-findings.md) |

Naming note: files named `pr-pilot-*` predate the engine's rename to **convoy** and are kept as
historical slugs; their prose says "the series engine".

## method/ — the development method, bound to this repo

The keel/convoy governed-series kit: [`method/README.md`](method/README.md) explains the slots;
[`method/method-bindings.md`](method/method-bindings.md) binds each to a fathom mechanism (gates,
DoR/DoD, pre-mortem, reflection sink). [`method/recalibration-playbook.md`](method/recalibration-playbook.md)
is the recurring model-tier recalibration recipe (rerun it when a new Claude model ships).

## plans/ — implementation plans

Planned-execution artifacts; historical once executed
([`2026-06-13-skill-eval-pyeng-plan.md`](plans/2026-06-13-skill-eval-pyeng-plan.md) built the
injection capability and the `skill-pyeng-v1` bank).

## What does NOT live here

- **Scorecards** — generated into `report/` (gitignored); regenerate with
  `uv run fathom report <bank>`.
- **Dogfooding feedback about fathom itself** — local, gitignored `feedback/` dir at the repo
  root; still-open promotions are swept into `STATUS.md` (see its "Open items" table).
- **PR briefs of the governed series that built fathom** — `pr-series/` at the repo root.
