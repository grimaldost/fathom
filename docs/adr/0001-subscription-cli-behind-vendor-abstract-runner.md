# ADR-0001 — All model calls go through a vendor-abstract Runner; v1 binds it to the subscription Claude CLI

> **Note (0.8.0):** particulars were removed from this record for the standalone engine.

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

fathom spawns agents to attempt tasks and spawns judges to grade rubric axes. The
operator runs on a Claude subscription (headless `claude -p`, no API key), but the
framework must not be coupled to that transport: future arms may run on the
Anthropic API or other vendors' CLIs, and the judge transport must be swappable
without invalidating the longitudinal ledger. Published eval runners (Inspect AI,
promptfoo) draw their leverage from API-key orchestration, which does not help
here, while the subscription CLI is simultaneously the system under test and the
only authenticated transport.

## Decision

Every model invocation — task-attempt runs and judge calls alike — goes through a
`Runner` protocol (`execute(prompt, workspace, scenario) -> RunRecord`). v1 ships
exactly one adapter, `claude-cli` (subscription auth), vendored from an existing,
proven harness core (ADR-0004). No code outside `adapters/` may invoke a model
directly.

## Alternatives considered

- **Run on Inspect AI or promptfoo as the execution layer** — their model
  orchestration assumes API keys; the subscription CLI would have to be wrapped
  anyway, so the framework would add a dependency without removing any work.
- **Anthropic API directly** — marginal cost per run and couples the harness to
  one vendor's SDK; subscription capacity is already paid for.
- **No abstraction (call `claude -p` inline where needed)** — cheapest today,
  but vendor swap would then touch run, judge, and smoke code simultaneously and
  fork the ledger semantics.

## Consequences

- USD cost is an adapter-computed **estimate**; tokens, turns, and wall-clock are
  the primary economy currency in reports.
- Judge identity (resolved model + config hash) is recorded per grading record so
  a transport swap is visible in history rather than silent.
- New invariant: **model calls only via Runner adapters** — a review-checklist
  item; any direct subprocess/SDK model call outside `adapters/` is a defect.
