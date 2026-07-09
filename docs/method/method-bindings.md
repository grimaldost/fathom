# Method bindings — fathom

The method is project-agnostic; this file binds each slot and upgrade to a
concrete mechanism in fathom.

## Portability slots

| Slot (what it must provide) | fathom binding |
|---|---|
| **ADR home** — a numbered decision log | `docs/adr/` (`NNNN-slug.md`, template at `docs/adr/adr-template.md`) |
| **Spec format** — numberable sections, acceptance criteria | `docs/specs/` — design docs as `YYYY-MM-DD-<topic>-design.md`; build specs follow `docs/specs/spec-template.md` (numbered §, PR↔§ manifest) |
| **Guardrails + gate commands** — deterministic pass/fail | `uv run ruff format --check .` · `uv run ruff check .` · `uv run pytest` (core tests also stdlib-runnable: `python tests/test_*.py`) · `uv run fathom smoke` (real-spawn isolation gate, built — §11; the go/no-go before any paid matrix) |
| **Review checklist** — project-specific, blocking | `docs/method/review-checklist.md` (project items promoted into it via reflection triage) |
| **Reflection sink** — feeds the next round | `feedback/` (local-only, gitignored) — per-session reports via session-workflow `tool-feedback`; triage via `docs/method/reflection-triage.md`; still-open promotions are swept into `docs/STATUS.md` so they travel with the repo. fathom is registered in the operator's global feedback-targets table (CLAUDE.md). Analysis run notes are not feedback — they live in `docs/reports/` |

## Upgrade bindings

| Upgrade | What it must provide | fathom binding |
|---|---|---|
| **DoR gate** | spec-readiness check before decompose | `keel check-ready <spec>` (keel CLI on PATH) |
| **Pre-mortem** | a stateless adversarial pass | `keel:pre-mortem-review` agent (blind, non-author) driven by `docs/method/pre-mortem-prompt.md` |
| **Wave budget** | forecast + drift gate | convoy's per-phase `[governance.budgets]` (fathom pins them) + its budget-cap halt (`outcome = "budget"` / exit 4, series contract §7) — a spawn that exceeds its cap stops un-integrated rather than overspending |
| **Edit-time invariant hook** | block edits that violate a boundary | none in v1 — planned candidate: append-only guard on `ledger/*.jsonl` (reject in-place rewrites) |

## Orchestrator

| | fathom |
|---|---|
| Series runner | convoy — `convoy run series.toml` (engine CLI) or the `convoy:convoy` skill driving the `convoy_run` MCP tool (in-session) |
| Single-unit discipline | humblepowers skills (brainstorming → planned-execution → TDD → receiving-code-review → verification-before-completion) — replaces superpowers |
| Cross-series memory | `.remember/` handoffs + session-workflow journaling → mantis corpus |

*A slot left unbound is a method-not-fully-applied warning. The one deliberately
deferred binding is the edit-time hook (planned, named above).*
