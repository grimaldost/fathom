# docs/

Map of the engine's documentation. Start elsewhere for everyday use:

- [`README.md`](../README.md) — what fathom is, install, `fathom init`, how the data root is
  found, the commands, the plugin.
- [`skills/fathom-eval/reference/authoring.md`](../skills/fathom-eval/reference/authoring.md) —
  the guide to building a bank and its arms, from `fathom init` to reading the scorecard.
- [`examples/data-root/`](../examples/data-root/) — a complete example data root, explained
  file by file.
- [`CLAUDE.md`](../CLAUDE.md) — for agents working on the engine: architecture, invariants,
  the data-root contract.
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — setup, the gate list, hooks, releases.

Everything under this directory documents the engine itself: its design, its decisions, and
the method it is developed with. Evaluation data and write-ups belong in a data root, not
here.

## specs/ — design

| File | What it is |
|---|---|
| [`specs/2026-06-10-fathom-v1-design.md`](specs/2026-06-10-fathom-v1-design.md) | Architecture: purpose, constraints, module map, ledger and grading design, with as-built notes. |
| [`specs/2026-06-10-fathom-v1-build.md`](specs/2026-06-10-fathom-v1-build.md) | Build spec: numbered sections, the invariants and how each is enforced. |
| [`specs/2026-07-03-series-engine-contract.md`](specs/2026-07-03-series-engine-contract.md) | The engine-neutral contract the `series` arm drives; convoy is the reference engine. |
| [`specs/2026-09-13-run-lock-and-credential-preflight-design.md`](specs/2026-09-13-run-lock-and-credential-preflight-design.md) | The run lock, the credential pre-flight, and decoding gate output. |
| [`specs/spec-template.md`](specs/spec-template.md) | The blank template a new spec starts from. |

Specs are dated records. Correct one with a dated note rather than rewriting it; where a spec
and the code disagree, the code and the authoring guide describe current behaviour.

[`backlog.md`](backlog.md) lists open improvements to the engine by area, with the items
declined and the ids already closed.

## adr/ — decisions

One decision per file. An accepted ADR is never edited, only superseded.

| ADR | Decision |
|---|---|
| [0001](adr/0001-subscription-cli-behind-vendor-abstract-runner.md) | All model calls go through a vendor-neutral `Runner`; the first binding is the Claude CLI on a subscription login. |
| [0002](adr/0002-trial-run-append-only-ledger.md) | Two-level trial and run records in an append-only, committed JSONL ledger; resume by content hash. |
| [0003](adr/0003-blind-result-only-scoring.md) | Scoring is blind and sees only the result; the trajectory and cost join after scoring. |
| [0004](adr/0004-vendor-claude-runner-core.md) | The spawn core is vendored; the smoke gate asserts its isolation properties. |
| [0005](adr/0005-sealed-holdout-tasks.md) | Banks carry sealed holdout tasks; a spent holdout is development data. |
| [0006](adr/0006-plugin-mount-fidelity.md) | Whole plugins are mounted with `--plugin-dir`, to keep their triggering behaviour. |
| [0007](adr/0007-model-tier-calibration.md) | Design of the model-tier calibration study (hard-criteria fraction, tier rule). |
| [0008](adr/0008-oracle-quality-crossing.md) | Oracle quality as a third calibration factor, crossed with model tier (proposed). |
| [0009](adr/0009-per-trial-tier-decision-statistic.md) | The per-trial statistic used to separate model tiers. |

[`adr/adr-template.md`](adr/adr-template.md) is the blank template for a new decision.

## method/ — how the engine is developed

The engine is developed with the keel governed-series method: a spec, a Definition of Ready
with a pre-mortem, a series of pull requests, and a Definition of Done.
[`method/README.md`](method/README.md) explains the slots each template fills, and
[`method/method-bindings.md`](method/method-bindings.md) binds each slot to a mechanism in
this repository.

| File | What it is |
|---|---|
| [`method/definition-of-ready.md`](method/definition-of-ready.md) | The gate a spec passes before it is split into pull requests. |
| [`method/definition-of-done.md`](method/definition-of-done.md) | The exit-of-review gate: guardrails and gate commands. |
| [`method/pre-mortem-prompt.md`](method/pre-mortem-prompt.md) | The fresh-eyes pre-mortem run against a ready spec. |
| [`method/review-checklist.md`](method/review-checklist.md) | The review checklist; also where recurring review findings are promoted. |
| [`method/reflection-triage.md`](method/reflection-triage.md) | Turning what a series' reflections surfaced into durable checks. |
| [`method/series-toml-skeleton.md`](method/series-toml-skeleton.md) | A blank `series.toml` skeleton, including the per-phase budget block. |
| [`method/measured-terms.md`](method/measured-terms.md) | The rule that a cost term in an estimate is measured, not modelled. |

## Not here

- **Banks, arms, ledgers, scorecards, write-ups and status pages** belong in a data root (see
  the root README). The only data in this repository is synthetic: `examples/data-root/` and
  `tests/fixtures/`.
- **Results of particular evaluations** — trial counts, spend, verdicts — stay with the data
  root that produced them. An engine document states the rule or the decision; where it needs
  an example, it uses a neutral one.
