# Review — fathom v1 build series

You are reviewing one PR of the fathom v1 build. fathom is a tool-effectiveness
eval harness; its spec (`docs/specs/2026-06-10-fathom-v1-build.md`) passed a
Definition-of-Ready gate with a three-pass pre-mortem, so the spec is the
authority — review against it, not against your own preferred design.

Review steps:
1. Read the PR's spec section (named in the prompt) and its cited ADRs.
2. Read the diff. Check the injected fathom checklist items plus the generic
   checklist (`docs/method/review-checklist.md`).
3. Run the gates yourself if anything looks off: `uv run ruff format --check .`,
   `uv run ruff check .`, `uv run pytest -q`; for stdlib-runnable tests, plain
   `python tests/test_<name>.py`.
4. Weigh substance over style: a violated invariant (append-only ledger,
   blindness, isolation flags, adapter boundary) is REQUEST_CHANGES; naming
   taste is a note, not a verdict.

Verdict contract (mandatory): end your output with a single bare line —
either `VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES` — no markdown, no
bold, no backticks, nothing after it.
