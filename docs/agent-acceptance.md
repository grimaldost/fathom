# Fresh-Agent Acceptance Test for fathom

This document describes the acceptance test for the installed fathom plugin. It answers one question: **can a fresh Claude Code agent, given only a user's goal and the fathom plugin's exposed surfaces, actually use fathom end-to-end without fathom-specific instructions?**

## What it measures

The test spawns headless Claude agents with three real-world scenarios:

- **S1: existing-data** — Explore a data root, run consistency checks, and plan a dry-run cost estimate (no spend allowed).
- **S2: from-scratch** — Author a bank with two arms from scratch, run it within budget, and render the scorecard.
- **S3: unnamed-discovery** — Discover fathom without being told its name and show what a measurement would look like on existing data.

Agents learn to use fathom by:
- Reading available tool names and skills (Skill tool, MCP servers, slash commands).
- Exploring the plugin's documentation.
- Calling the exposed surfaces: `fathom:` slash commands, the `fathom-eval` skill, or MCP tools like `plan` and `report`.

No agent receives a fathom command, flag, skill name, or MCP tool name in its prompt. Everything it learns comes from what the plugin exposes.

## Cost and safety rails

- **Spend limit per scenario**: $0.20 (S1, S3 no-spend check) or $1.50 (S2 budget × 1.5 buffer).
- **Wall-clock timeout**: 30 minutes per scenario.
- **Permission mode**: agents run headless with explicit allow/disallow lists (no WebFetch, WebSearch, `git push`, or `gh`).
- **Real-spawn isolation**: each agent runs in an isolated `CLAUDE_CONFIG_DIR` with no inherited `FATHOM_HOME` or working-directory state.
- **Workspace preservation**: workspaces live under `--out` and are kept for inspection.

## How to run

### Dry run (prepare workspaces, print commands, no spawn)

```sh
uv run python tools/agent_acceptance.py --dry-run --data-root <your-data-root>
```

Shows:
- Exact `claude` command lines for each scenario.
- Environment deltas.
- Workspace paths.

### Preflight only (spawn one trivial session, check visibility)

```sh
uv run python tools/agent_acceptance.py --preflight-only --data-root <your-data-root>
```

Spawns a single "Reply with the word ready." session and reports whether the fathom MCP server is visible.

### Run all scenarios

```sh
uv run python tools/agent_acceptance.py --data-root <your-data-root>
```

Spawns three agents, one per scenario. On completion:
- Prints workspace paths.
- Writes `verdict.json` per scenario.
- Writes `report.md` (summary table and details).
- Exit code: 0 if all scenarios passed, 1 if any failed, 2 if environment failure, 3 if usage error.

### Selective scenarios

```sh
uv run python tools/agent_acceptance.py --scenarios s1_existing_data,s2_from_scratch \
  --data-root <your-data-root>
```

### Custom model, plugin, budget

```sh
uv run python tools/agent_acceptance.py \
  --model haiku \
  --plugin-dir /path/to/dev/fathom \
  --budget-usd 5.0 \
  --data-root <your-data-root>
```

## Reading the verdict

Each scenario produces:

- **`transcript.jsonl`** — raw stream-json output from the agent.
- **`verdict.json`** — structured results: checks (pass/fail + evidence), surfaces used, cost, duration.
- **`stderr.txt`** — agent's stderr (timeouts, errors).
- **`report.md`** — summary table and per-scenario details.

### Verdict checks

Each scenario has scenario-specific checks:

**All scenarios:**
- `prompt_guard` — the prompt contains no forbidden terms (e.g., `/fathom:`, `--dry-run`, `fathom-eval`).
- `visibility` — the fathom MCP server is connected and the `fathom-eval` skill is listed.

**S1 (existing-data):**
- `no_spend` — no changes to ledger files (git status unchanged).

**S2 (from-scratch):**
- `bank_structure` — `fathom.toml` with `[data_root]`, a bank, ≥2 arms, and a ledger with ≥2 completed trials across ≥2 configs.
- `reconcile` — `fathom reconcile` exits 0.
- `scorecard` — a rendered scorecard exists in `report/`.

**S3 (unnamed-discovery):**
- `no_spend` — same as S1.
- `fathom_surface_used` — at least one fathom surface (skill, command, MCP, or CLI) was called.

### Understanding failure

If a scenario fails:
1. **Check `verdict.json`** for which checks failed and their evidence.
2. **Read `transcript.jsonl`** to see what the agent actually did (stream-json events).
3. **Check `stderr.txt`** for timeouts or permission errors.
4. **Read the agent's final result** in the `result` field of the last event in `transcript.jsonl`.

Common failures:
- **visibility failed** — the fathom MCP server did not start or the skill is not listed. Check the plugin is enabled and the `--plugin-dir` is correct.
- **bank_structure failed** — the agent did not author a valid bank. Check the agent's transcript to see what went wrong (missing tasks, arms, or verifier).
- **no_spend failed** — the agent ran a paid matrix (S1/S3 disallow this). The agent learned to spend despite the prompt saying not to.
- **prompt_guard failed** — the spec's prompt validation failed before spawn (the prompt contained a forbidden term).

## Implementation notes

The harness is implemented in `tools/agent_acceptance.py`:

- **Pure functions** (parsing, classification, checks) are unit-tested in `tests/test_agent_acceptance.py` with synthetic data (no real spawns).
- **Workspace management** handles both `clone` (local git clone of data root) and `empty` (fresh directory) modes.
- **Stream parsing** is tolerant of malformed lines and unknown event types.
- **Tool classification** distinguishes fathom surfaces: skill, slash command, MCP tool, CLI invocation, or documentation reads.
- **Ground-truth checks** validate bank structure, ledger contents, reconciliation, and scorecard rendering.

## Gates (all must pass before commit)

```sh
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
FATHOM_HOME= uv run fathom reconcile
python tools/changelog_currency.py [changed files]
```

## Data protection

- The real data root is never modified: workspaces are clones (for S1/S3) or empty directories (S2).
- Before and after S1/S3 runs, git status and HEAD are recorded and verified unchanged.
- The harness refuses to run if `--data-root` is an engine checkout (detected by `.claude-plugin/plugin.json`).

## Limitations and non-goals

- Does not test `fathom run` itself (no real paid matrix in the test).
- Does not test the series engine or gated-session strategies (only single-session, simple enough for an agent to author from scratch).
- Does not measure how much hand-holding a user needs to understand fathom's full feature set (only whether the installed surfaces work).
- Does not test user-facing CLI help text (covered by docs alone).

## Next steps

To extend the test:
1. Add more scenarios (e.g., test a gated-session or series strategy if agents can author them).
2. Increase trial budget and repeats for statistical confidence.
3. Add a stress variant (haiku model, tight timeouts) to test robustness.
