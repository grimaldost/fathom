# research-fusion-v1: the MCP mount integrated, arming proven, matrix not bought

- **Date:** 2026-08-11. Branch `eval/research-fusion`. Bank `research-fusion-v1`, arms
  `bare` / `fusion` in `scenarios/research-fusion/`.
- **Gate:** mantis-research's **MANT-B36**, via the precondition bank authored in the previous
  wave (`2026-08-11-research-fusion-v1-bank-and-precondition-probe.md`).
- **Verdict on the gate: still unmeasured. No trials ran; `ledger/research-fusion-v1.jsonl`
  does not exist.** This report exists because the run's blocking work — the one the previous
  wave named "the unbought half" — is now done and should not be re-derived. What remains is
  wall-clock under a contended lock, not engineering.

**Nothing here supports any conclusion about the research tool's value, in either direction.**

## What this wave delivered

### 1. The MCP-serving mount, vendored (the previously blocking item)

`fusion.toml` mounts `tasks/research-fusion-v1/plugins/mantis-research@0.2.0`, which did not
exist. Every other mounted plugin in this repo is prose-only; this one serves an MCP server that
self-installs with `uv run --project ${CLAUDE_PLUGIN_ROOT}`, so the mounted copy carries the build
inputs (`pyproject.toml`, `uv.lock`, `README.md`, `.python-version`) beside the package and the
manifest, with an environment materialised in-tree at `.venv` (gitignored, and already in the
mount hash's skiplist). Sourced from the repo at `main` (0.2.0), not the installed plugin cache
(0.1.2) — the staleness the previous wave kept hitting. Mounted **as shipped**, reference skill
included, so the arm measures the plugin a user would install.

*Confound to carry:* the shipped skill is part of the treatment. A gain would be "plugin as
installed", not "fan-out alone".

### 2. The silent arm-drop is closed

With the mount absent, `--dry-run` printed `scenarios=1` and planned the matrix anyway — it
dropped the treatment arm and would have bought a control-only matrix, rendered a scorecard with
no treatment in it, and reported it as an A/B (FATH-B50). It now prints **`scenarios=2`**. The
run script also refuses to spend unless the plan says `scenarios=2`, so the failure cannot recur
silently.

### 3. Arming proven — and the built-in gate is a false negative here

`fathom verify-arming` reports **NOT ARMED** for this arm: the plugin registers, but its MCP
server is `pending` and no `mcp__*` tools appear. That is the FATH-B01 shape the gate exists to
catch, so it was treated as a hard stop and diagnosed rather than skipped. It is a false negative:

| evidence | result |
|---|---|
| direct stdio handshake with the mounted server | healthy — `initialize` in **2.4 s**, `tools/list` returns `research` |
| live spawn, exact arm config, model asked to call the tool (`dry_run=true`, no substrate spend) | **4/4 ARMED**, each returning a real `outputs_dir` |
| mantis run dirs left behind by those calls | **exactly one per call** |
| server startup measured again under concurrent load | **6–11 s** (was 1.1 s on a quiet machine) |
| the same probe's *ambient* MCP tool list | populated once, `[]` minutes later under identical config |

The gate reads the **init-event snapshot**, which is sampled before a slow-starting stdio MCP
server finishes connecting. Under load it is a race, not a signal — the ambient-tools flip proves
the snapshot is nondeterministic independent of this mount. `MCP_TIMEOUT` does not change it.

**Filed as a fathom defect:** `verify-arming` cannot see MCP-served tools that connect
asynchronously. The false-negative direction is the safe one, but it blocks a legitimate run and
pressures an operator toward `--skip-arming-check`, which is the unsafe direction — so it is worth
fixing rather than documenting. A sound fix samples tool availability *during* the turn (or waits
for server readiness) instead of reading the init snapshot.

**Validity consequence, which is not merely cosmetic:** if the server needs 6–11 s and the CLI
does not wait, a trial could begin before its tool exists. Arming must therefore be checked
**per trial, after the fact**, not once before the run. The tool writes one timestamped run
directory per invocation, so the run script harvests those directories before each restore; the
count is an independent per-trial witness, and any fusion trial without one is an unarmed trial
that must be excluded rather than averaged in.

### 4. A resume hazard that would have re-bought the matrix

The mounted package installs **editable**, so mantis's `core/paths.py::project_root()` walks up
from `__file__` and resolves to *the mount directory itself*. Every armed trial writes
`outputs/`, `state/`, `logs/`, `transcripts/` **inside the mount**. Those names are not in
fathom's tree-hash skiplist (only `__pycache__`, `.venv`, `.git`, `.in_use`, `.orphaned_at` are),
so the mount's `tree_sha` — which feeds `config_hash`, which is in the resume key — changes after
the first armed trial. A chunked re-invocation would have treated every completed trial as
not-done, re-bought all of them, and split the ledger across two `config_hash` values.

Confirmed empirically: one tool call added 8 files and forked the hash.

Mitigation, without touching the instrument's hashing: the mount is committed, and the tree is
restored to its committed bytes before every invocation, with the hash verified against a
baseline. Two traps inside that:

- **`git clean` cannot do it on Windows.** The tool's transcript filenames exceed `MAX_PATH` and
  git refuses (`Filename too long`). The restore deletes untracked paths through extended-length
  (`\\?\`) paths instead.
- **The baseline must be taken after a git round-trip.** `.gitattributes` normalises `md/py/json/
  toml` to `eol=lf`, so a raw filesystem copy hashes differently from the checked-out bytes
  (`5ef22dd8…` vs the canonical `f33ae12f…`). Using the pre-commit value would have failed on the
  very first restore.

### 5. The rail was being set 18× too high

`--max-budget-usd` is a **per-spawn** cap, not a total; `_CEILING_PER_TRIAL_USD = 2.00` is only a
display constant. Passing the program's `$90` rail would have given each of 18 trials a `$90`
ceiling — a `$1,620` worst case, i.e. no rail at all. The correct expression of a `$90` total over
18 trials is **`--max-budget-usd 5`**.

## Gates, as run

| gate | result |
|---|---|
| `fathom smoke --no-engine-boundary` | **ALL PASS (7/7)** |
| `fathom validate research-fusion-v1` | **8 pass, 0 fail, 0 warn, 4 unverifiable** |
| `--dry-run` (repeats 3) | `scenarios=2  tasks=3  repeats=3` → **18 trials, ceiling $36.00** |
| `fathom verify-arming` | FAIL — false negative, see above |

The one smoke check excluded, `engine-boundary`, fails for a reason proven unrelated to this bank:
`scenarios/series.toml` sets `repo = "../convoy"`, which from this worktree resolves to
`.wt-closeout/convoy` and does not exist, so the engine subprocess dies before spawning `claude`.
It exercises the `series` strategy; **both arms of this bank are `single-session`**. Worth noting
as a worktree-layout fragility: a relative `[tools].repo` silently means something different
inside a worktree than in the main checkout.

## Why the matrix was not bought

Serialization, not budget or readiness. The shared paid-run lock was held continuously by sibling
programs: `verification-lift` from 19:47 to 22:42, then — after this program's one 6-minute window,
in which `fathom run`'s own arming pre-flight refused (rc=11, the false negative above) —
`keel-kit-ablation-v1`. A 5-minute poll starves against peers running back-to-back segments: the
lock was released and re-taken within ~17 s of this program's wait beginning. Tightening the poll
to 5 s won the lock once, at 55 minutes of waiting.

The lock was never taken from another holder, and this program released its own lock on the
refusal path (the release trap is registered only after acquisition, so a kill while waiting can
never delete a peer's lock).

**Budget position:** the plan is `$36.00` against a `$90` rail, a `~$70` estimate and `$350`
remaining — the stop rule was not close to triggering. Roughly **$1** was spent, all on
pre-flight probes (2 smoke runs, 3 `verify-arming` probes, 4 live arming probes). No trial spend.

## Power, stated before anyone reads a future number

Even fully run, this matrix is small and must not be over-read:

- **3 dev questions**, not the 10 the skeleton costed — the sealed holdout (`cost-per-outcome`)
  is excluded by default. At 3 repeats that is **9 armed and 9 control trials**, and the
  question set, not the repeat count, is the binding limit on power. Repeats sharpen the estimate
  for three questions; they do not broaden it.
- With n=9 per arm, only gross outcomes are resolvable — near-0 or near-1 well-formedness rates.
  Anything intermediate will not be distinguishable from noise, and no confidence interval on a
  9-trial proportion will separate, say, 55% from 75%.
- Two criteria (`multi_substrate`, `divergences_present`) are **availability** criteria: the bare
  arm scores 0 on them by construction. That is a floor, not a finding, and reporting it as a
  fusion "win" would be an artifact of the bank's design.
- The bank measures the **precondition** — whether a well-formed sidecar with joinable
  cross-substrate divergences is produced at all. It does **not** measure decision value, which
  is what MANT-B36 actually asks, and it cannot: no verifier observes a counterfactual.
- The armed arm's second-provider (OpenRouter) spend is invisible to `cost_usd_est`, so the
  landscape brief's 8.8×-cost comparison **cannot** be settled from this ledger.

**Therefore: no retirement or retention decision for the research tool is supportable from this
bank, and none is offered here.** A null from 9 trials over 3 questions would be a statement about
this bank's power, not about the tool.

## Ledger

None. No fathom trials were run; `ledger/research-fusion-v1.jsonl` does not exist. What this
commits is the vendored mount tree and this report.

## To run it (state is ready; nothing needs re-deriving)

```sh
cd C:/Users/grima/Documents/.wt-closeout/fathom-fusion
uv run fathom smoke --no-engine-boundary          # expect ALL PASS (7/7)
python <scratch>/restore_mount.py                 # MUST print MATCH before spending
uv run fathom run research-fusion-v1 --scenarios-dir scenarios/research-fusion \
    --repeats 3 --max-budget-usd 5 --skip-arming-check
```

`--scenarios-dir` is load-bearing and its glob is non-recursive. `--skip-arming-check` is used in
its documented sense — "re-run a matrix whose arming was already verified this session" — and is
only honest while the four-probe evidence above is re-established in the session that spends.
Restore the mount before **every** invocation, harvest the tool's run dirs before each restore,
and confirm one run dir per fusion trial before reading any scorecard.
