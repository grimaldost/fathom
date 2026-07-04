# Review — fathom humble-vs-super plugin-eval series

You are reviewing one PR of the fathom humble-vs-super build. fathom is a
tool-effectiveness eval harness; this series' spec
(`docs/specs/2026-06-14-fathom-humble-vs-super-design.md`) passed a keel
Definition-of-Ready gate with a two-round blind pre-mortem (verdict CERTIFIED),
so the spec is the authority — review against the PR's cited numbered section,
not against your own preferred design.

Review steps:
1. Read the PR's spec section (the `§N` named in the prompt) and its cited ADRs.
2. Read the diff. Check the injected fathom checklist items plus the generic
   checklist (`docs/method/review-checklist.md`).
3. Run the gates yourself if anything looks off: `uv run ruff format --check .`,
   `uv run ruff check .`, `uv run pytest -q`; for stdlib-runnable tests, plain
   `python tests/test_<name>.py`.
4. Weigh substance over style. A violated invariant is REQUEST_CHANGES; naming
   taste is a note, not a verdict. Invariants for THIS series specifically:
   - **config_hash stability** (§2): scenarios with no `[plugins] mount` must
     leave the committed `pr-pilot-v1` / `skill-pyeng-v1` config_hashes
     byte-identical (absent == empty); a mounted set is hashed as
     `(name, version, tree_sha)`; `tree_sha` is git-tree at the pinned commit,
     not a naive content hash that churns on `__pycache__`.
   - **Spawn isolation** (ADR-0004): `--plugin-dir` adds plugins per session;
     still no `--permission-mode` / `--dangerously-skip-permissions` on harness
     spawns; the credential-only temp config is untouched.
   - **Blindness** (ADR-0003): verifiers read only the result-view (argv[1]),
     carry no scenario/arm identity; §10's scrub must not change verifier output.
   - **Append-only ledger** (ADR-0002): §11 may ADD a cost field to the ledger
     record, but no code path rewrites an existing ledger line.
   - **Armed treatment** (§5): the mount/available smoke check asserts plugin
     skills are present in the spawn's init event — it does not (and must not)
     claim to prove auto-firing.
   - **Stdlib core**: new modules under `src/fathom/` import stdlib only.

Verdict contract (mandatory): end your output with a single bare line —
either `VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES` — no markdown, no
bold, no backticks, nothing after it.
