# Method bindings — fathom

The method is project-agnostic; this file binds each of its slots to a concrete mechanism in
this repository.

## Portability slots

| Slot (what it must provide) | fathom binding |
|---|---|
| **ADR home** — a numbered decision log | `docs/adr/` (`NNNN-slug.md`, template at `docs/adr/adr-template.md`) |
| **Spec format** — numbered sections, acceptance criteria | `docs/specs/` — design docs as `YYYY-MM-DD-<topic>-design.md`; build specs follow `docs/specs/spec-template.md` (numbered sections, a PR-to-section manifest) |
| **Guardrails + gate commands** — deterministic pass/fail | The gate list in [`CONTRIBUTING.md`](../../CONTRIBUTING.md#gates), with the reason for each gate. It is kept in that one place and not repeated here, so the two cannot drift apart |
| **Review checklist** — project-specific, blocking | `docs/method/review-checklist.md` (project items are promoted into it by reflection triage) |
| **Reflection sink** — feeds the next round | The pull requests of a series (their descriptions and review threads) carry what it surfaced; `docs/method/reflection-triage.md` turns that into checks, and anything still open after a triage is recorded in `docs/backlog.md`, so it travels with the repository. Analysis run notes and a status index of analyses belong to a data root (`docs/reports/`, `docs/STATUS.md` there), not to this repository |

## Upgrade bindings

| Upgrade | What it must provide | fathom binding |
|---|---|---|
| **DoR gate** | a spec-readiness check before decomposition | `keel check-ready <spec>` (keel CLI on PATH) |
| **Pre-mortem** | a stateless adversarial pass | keel's `pre-mortem-review` agent (blind, non-author), driven by `docs/method/pre-mortem-prompt.md` |
| **Series budget** | a forecast and a hard stop | convoy's per-phase `[governance.budgets]` (fathom pins them) and its budget-cap halt (`outcome = "budget"`, exit 4, series contract §7): a spawn that exceeds its cap stops un-integrated rather than overspending |
| **Edit-time invariant hook** | block edits that violate a boundary | none yet. Planned candidate: an append-only guard on `ledger/*.jsonl` that rejects in-place rewrites. The ledgers live in data roots, so the hook would ship for data roots to install |

## Orchestrator

| | fathom |
|---|---|
| Series runner | convoy: `convoy run series.toml` from the CLI, or its skill driving the `convoy_run` MCP tool in a session |
| Single-unit discipline | test first for behaviour changes; a failing test before a bug fix; verification (the gate list) before claiming a change complete |

*A slot left unbound is a warning that the method is not fully applied. The one deliberately
deferred binding is the edit-time hook, named above.*
