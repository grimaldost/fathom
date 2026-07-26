# serena-nav-v2 — large-scale symbolic-navigation bank

Measures whether a semantic code-navigation tool (LSP-over-MCP, e.g. serena) beats
plain `Read`/`Grep` on a codebase too large to read exhaustively.

## Why v2 exists

`serena-nav-v1` (34 files) **saturated**: 11 of 12 criteria scored 100% for both arms,
because tasks that are hard for *grep* are not hard for a competent model *with* grep at
small scale. The whole arm difference rested on one trial of one criterion. v1's first
run was also **invalidated** for an unrelated reason — the armed arm was silently unarmed
(see `ledger/archive/serena-nav-v1.run1-invalid-unarmed-mcp-arm.jsonl` and
`feedback/2026-07-25-serena-nav-arming-defect.md`).

v2 moves the two variables that actually bind a navigation tool:

| lever | v1 | v2 |
|---|---|---|
| corpus | 34 files | **422 files**, 14 domains |
| textual noise | 11 grep hits / 11 genuine | **140 grep hits / 20 genuine** (120 decoy files to reject) |
| precision demanded | boolean criteria | **sha256 byte-identity on 153 decoys** — no partial credit |
| turn budget | 50 | **40** (v1 bare used ~18 turns on a 12× smaller repo) |

## Tasks

| task | kind | what discriminates |
|---|---|---|
| `rename-reconcile` | edit precision at scale | 20 genuine sites across 5 import shapes vs 120 decoys (same-named methods, `reconcile_batch`, docstrings, string literals). A global `sed` corrupts a decoy and fails on hash. |
| `impact-report` | **read-only** navigation | write the exact transitive call closure (34 modules) to `impact.json`; scored by set equality. Direct refs are greppable; the closure through aliases and re-exports is not. |
| `disambiguate-fee` | semantic disambiguation | four modules define `apply_fee`; only one is reachable from the daily pipeline. Fix that one, leave three frozen. Verified **behaviorally** (`10.0 × 0.125` → `1.25`, not `1.2`). |

## Ground truth is not reachable by the agent

`truth.json` (genuine sites, call closure, decoy hashes) sits **next to `verify.py`** in each
task dir. fathom stages only `fixtures/` into the workspace, so the answer key is
harness-side by construction.

## Regenerating

```sh
uv run python tasks/serena-nav-v2/generate_fixtures.py   # deterministic; overwrites all 3 fixture trees
uv run python tasks/serena-nav-v2/selftest.py            # every verifier RED on pristine, GREEN on a scripted solution
```

**Bump `bank.toml` `dataset_version` after any regeneration that changes content** — it is in
the resume key. The selftest is not optional: it caught a real authoring bug on first run
(`tests/test_engine.py` imports the symbol by name and was missing from the genuine-reference
set, so the reference solution failed pytest).

## Arms and the arming gate

Arms live in `scenarios/serena-nav-v2/`: `bare` / `brief-only` (inject, no tools) /
`serena` (inject + mounted MCP server). Run with
`--scenarios-dir scenarios/serena-nav-v2`.

**Before any paid run**, verify the armed arm is actually armed:

```sh
uv run python scenarios/serena-nav-v2/arming_probe.py scenarios/serena-nav-v2/serena.toml
```

Expect `ARMING: PASS (tools callable)`. A plugin-mounted server's tools are named
`mcp__plugin_<plugin>_<server>__<tool>` — **not** `mcp__<server>` — and the init event spells
the same server `plugin:<plugin>:<server>`. Allowing the wrong spelling silently denies every
tool and the arm measures nothing while the scorecard still renders a plausible number.
