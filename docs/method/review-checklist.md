# Review checklist

Injected into the reviewer and blocking: any unchecked item is `REQUEST_CHANGES`.
The generic items come from the portable kit; the project-specific ones below
them are fathom's own.

This file is also the **promotion target for reflection triage** (Upgrade 3):
when a trap recurs across rounds, add a line here so it is caught mechanically
next time. That is how "a bug bites once" actually holds.

## Generic items

- [ ] **Scope** — single concern; cites exactly one spec section; no unrelated
      refactor ("while I'm here").
- [ ] **Correctness** — does what the cited section's acceptance criterion says.
- [ ] **Invariants** — respects every boundary/lock/immutability/contract named in
      the spec's "Invariants touched".
- [ ] **Typing** — fully typed; no new type-checker suppressions without reason.
- [ ] **Errors** — no silent `except`; failures surface; user-facing errors use the
      project's error format.
- [ ] **Tests** — behavior changes have tests; tests assert behavior, not
      implementation; no skip/xfail added to mask a real failure.
- [ ] **Docs** — public API/config/contract changes are documented.
- [ ] **No coupling smell** — no reaching through `getattr`/private attrs to dodge
      a boundary.
- [ ] **Gate completion** — every type/lint/test gate ran to completion (exit 0, no
      "fatal" / "source file found twice" halt), not merely error-count ≤ baseline; a
      checker that bailed early must fail the gate, not pass it.

## Project-specific items

- [ ] **Ledger** — no code path rewrites a `ledger/*.jsonl` line; a new record
      field is additive with a default, so legacy lines still load.
- [ ] **Resume keys** — a new scenario field is hashed conditionally (absent or
      empty must not shift `config_hash`); any task/fixture/verifier change
      bumps the bank's `dataset_version`.
- [ ] **Blindness** — nothing new reaches `verify.py` via argv or env; new
      engine artifacts are added to the result-view exclusions
      (`_EXCLUDED_ROOT_NAMES`, `src/fathom/grading/verifier.py`).
- [ ] **Stdlib core** — no third-party import added under `src/fathom/`; the new
      test runs as plain `python tests/test_<name>.py`.
- [ ] **Docs** — a new CLI flag, scenario/bank/task TOML field, env var, or MCP
      argument is documented in `skills/fathom-eval/reference/authoring.md`
      (schemas) or the SKILL / `commands/*.md` (flags) in the SAME change.

---
*Keep this file in version control with the project. Each promoted reflection
should cite the round/PR that motivated it, in a comment.*
