# Arms for `multiagent-composition-v2` — operator note

Run them with `--scenarios-dir scenarios/multiagent-composition-v2` — `fathom run`
globs a scenarios dir non-recursively, and omitting the flag silently runs the
wrong arms. The design, the endpoints and the contrasts live in
[`docs/specs/2026-09-01-multiagent-composition-preregistration.md`](../../docs/specs/2026-09-01-multiagent-composition-preregistration.md),
section "Pre-registration — bank v2"; this file is the run procedure only.

The eight arms carry the v1 names and the v1 definitions. The bank name is the
identity: `multiagent-composition-v2` gives every arm a new `config_hash` and a
separate ledger (`ledger/multiagent-composition-v2.jsonl`), so nothing here can
resume or overwrite a v1 row.

| Arm | Brief | After each PR the orchestrator… | Harness adds |
|---|---|---|---|
| `control-*` | `brief-control.md` | runs the project's visible suite | — |
| `placebo-*` | `brief-placebo.md` | runs `placebo_gate.py`, then re-verifies | — |
| `perpr-*` | `brief-treatment-perpr.md` | runs `run_convoy_gate.py --phase <tag>` | — |
| `final-*` | `brief-control.md` (control's, byte for byte) | runs the project's visible suite | `gated-session` + `[gate].extra` runs the driver once after the session |

`-haiku` and `-sonnet` differ only in `FATHOM_IMPL_MODEL`.

## The three exports

All three are required for **every** arm, control included, and none is recoverable
after the spend:

| Variable | Value | Why it is not optional |
|---|---|---|
| `FATHOM_TASK_DIR` | absolute path to `tasks/multiagent-composition-v2/exprlang` | Every arm's `[env]` block resolves `${FATHOM_TASK_DIR}` at spawn time for the driver and placebo paths. Unset, the `perpr-*` and `final-*` gate calls point at nothing and the arm degrades silently. |
| `FATHOM_PROMPTS_DIR` | absolute path to `$FATHOM_TASK_DIR/prompts` | New in v2, and the only path the briefs give the orchestrator. It holds the five PR prompts and nothing else. In v1 the briefs sent the orchestrator to the task dir for the prompts, so a directory listing — and `series.toml`'s header comment — exposed the driver's filename; two non-treatment orchestrators saw it in the pilot (neither executed it). Unset, every arm's Step 1 reads nothing and the trial is void. |
| `FATHOM_STREAM_DIR` | a run-scoped directory, e.g. `streams-multiagent/<date>` | The transcripts are the **only** record of what the agent invoked. The `perpr-*` arming criterion (every transcript shows at least one driver invocation) and the arm's adoption rate are derived from them; there is no ledger-side invocation counter. |

```sh
export FATHOM_TASK_DIR="$PWD/tasks/multiagent-composition-v2/exprlang"
export FATHOM_PROMPTS_DIR="$FATHOM_TASK_DIR/prompts"
export FATHOM_STREAM_DIR="$PWD/streams-multiagent/$(date +%Y-%m-%d)"
```

## Before the first paid trial

1. **The pinned convoy tag must exist.** `run_convoy_gate.py` pins
   `git+https://github.com/grimaldost/convoy@v0.11.0`. Until that tag is cut and
   pushed, `uvx --from …@v0.11.0` cannot resolve and every `perpr-*` and
   `final-*` gate call fails before reaching convoy. The arming runs to date used
   the `FATHOM_CONVOY_GATE_LOCAL` override against a local 0.10.0 checkout, so the
   pinned path has never executed.
2. **Observe the pin, once, without the override.** With `FATHOM_CONVOY_GATE_LOCAL`
   unset, run the driver over a throwaway workspace and confirm two things: the
   stderr echo reads `convoy gate via: git+https://github.com/grimaldost/convoy@v0.11.0`,
   and the envelope's `convoy_version` reads `0.11.0`. Do not start the matrix
   until both are seen.
3. **Warm the uv cache, and time a warm call.** A cold `uvx --from git+…` is a
   clone plus a build plus an install. The harness gate timeout
   (`_GATE_TIMEOUT_S`, `src/fathom/strategies/gated_session.py`) is 120s, and a
   timeout is scored as a genuine gate red — it would burn fix spawns and write
   `gate first=red` into `final-*` rows that never saw a real defect. Run
   `uvx --from git+https://github.com/grimaldost/convoy@v0.11.0 convoy --version`
   once, then time one full `run_convoy_gate.py` call warm and record both in the
   run log. If the warm call is not comfortably under the timeout, raise
   `_GATE_TIMEOUT_S` for this run and note the change in the pre-registration
   addendum: it is harness config, not an arm field, so it forks no `config_hash`.
4. **`fathom smoke`** is the go/no-go for spawn isolation, then `fathom run …
   --dry-run` for the trial count and the ceiling.
5. **Run the matrix as repeat passes** (`--repeats k` for k = 1..n, each pass
   covering every arm once). The v1 pilot ran arm-blocked and confounded time
   drift with arm; the run loop is scenario → task → repeat, so a single
   `--repeats 3` invocation blocks by arm.

## Where a `final-*` gate's output lands

The `gated-session` executor writes the extra gate's own output into the trial
row's `detail`, bounded and whitespace-condensed, as `extra-gate first: …` (and
`extra-gate final: …` when a fix round ran). A `final-*` row therefore records
which convoy ran and what it reported, not only `red`/`green`; a row reading
`extra-gate first: <not run: the task's own gate was red>` says the visible suite
short-circuited before convoy was reached, which is a different fact from a
convoy red.
