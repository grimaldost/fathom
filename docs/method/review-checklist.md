# Review checklist

Injected into the reviewer and blocking: any unchecked item is `REQUEST_CHANGES`.
The generic items come from the portable kit; the project-specific ones below
them are fathom's own.

This file is also the **promotion target for reflection triage**: when a trap
recurs across rounds, add a line here so it is caught next time. That is how
"a bug bites once" actually holds.

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
      empty must not shift `config_hash`); a provenance-only field stays out of
      `config_hash` and the resume key; any task/fixture/verifier change bumps the
      bank's `dataset_version`.
- [ ] **Blindness** — nothing new reaches `verify.py` via argv or env; new
      engine artifacts are added to the result-view exclusions
      (`_EXCLUDED_ROOT_NAMES`, `src/fathom/grading/verifier.py`).
- [ ] **Stdlib core** — no third-party import added under `src/fathom/`; the new
      test runs as plain `python tests/test_<name>.py`.
- [ ] **Data root** — a default data path resolves against the data root, never
      against the engine checkout or the package's install location; an explicit
      path option keeps its usual meaning (relative to the working directory).
- [ ] **Docs** — a new CLI flag, scenario/bank/task TOML field, env var, or MCP
      argument is documented in `skills/fathom-eval/reference/authoring.md`
      (schemas) or the SKILL / `commands/*.md` (flags) in the SAME change.
- [ ] **No particulars** — engine code, comments, docs and examples carry no
      campaign's bank or arm names, results, trial counts, spend or dates, and no
      personal paths or private repository names; examples use neutral names.
      `tests/test_public_tree.py` checks the home path and a names list kept
      outside the repository; the rest is this item.

### Silent-failure items

Four questions aimed at false negatives: a gate that passes while never running,
an arm that is absent while the plan looks clean, a check that reads unarmed on an
arm that works. Calibrating a new gate against a known answer tends to catch its
false positives; nothing catches its false negatives unless someone asks. These
four make the question part of review.

- [ ] **Rails bind** — for any change touching a rail, budget or cap: name the spawn
      path the value actually reaches, and state what it does **not** cap. A rail
      whose name asserts a guarantee it does not make is the defect, not a weak
      guard. *(A per-spawn cap multiplied across a matrix is not a matrix total;
      read as one, it licenses far more spend than the operator meant.)*
- [ ] **Gate failure direction** — for any new or changed gate: state what it does on
      a **false negative**, and whether its documented escape is safe. A gate whose
      only way out is a blanket override is a hazard, not a gap — the defect's own
      pressure then points at disabling the check. *(See FATH-B52.)*
- [ ] **Denominator effect** — for any change to trial status, scoring or
      aggregation: state which trials leave the denominator, and which way that
      biases the arm. *(Mapping an engine's "blocked" exit to `errored` rather than
      to a scored failure conditions the pass rate on the engine succeeding.)*
- [ ] **Dated claims** — a claim of observed external behaviour, or that an artifact
      exists, carries the date it was checked and the path or command that showed it.
      *(This PR.)*

---
*Keep this file in version control with the project. Each promoted item should
cite the change or backlog id that motivated it.*
