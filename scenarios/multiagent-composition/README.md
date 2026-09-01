# Arms for `multiagent-composition` — operator note

Run them with `--scenarios-dir scenarios/multiagent-composition` — `fathom run`
globs a scenarios dir non-recursively, and omitting the flag silently runs the
wrong arms. The design, the endpoints and the contrasts live in
[`docs/specs/2026-09-01-multiagent-composition-preregistration.md`](../../docs/specs/2026-09-01-multiagent-composition-preregistration.md);
this file is the run procedure only.

| Arm | Brief | After each PR the orchestrator… | Harness adds |
|---|---|---|---|
| `control-*` | `brief-control.md` | runs the project's visible suite | — |
| `placebo-*` | `brief-placebo.md` | runs `placebo_gate.py`, then re-verifies | — |
| `perpr-*` | `brief-treatment-perpr.md` | runs `run_convoy_gate.py --phase <tag>` | — |
| `final-*` | `brief-control.md` (control's, byte for byte) | runs the project's visible suite | `gated-session` + `[gate].extra` runs the driver once after the session |

`-haiku` and `-sonnet` differ only in `FATHOM_IMPL_MODEL`.

## The two exports

Both are required for **every** arm, control included, and neither is recoverable
after the spend:

| Variable | Value | Why it is not optional |
|---|---|---|
| `FATHOM_TASK_DIR` | absolute path to `tasks/multiagent-composition/exprlang` | Every arm's `[env]` block resolves `${FATHOM_TASK_DIR}` at spawn time. Unset, the briefs point at nothing and the arm degrades silently. |
| `FATHOM_STREAM_DIR` | a run-scoped directory, e.g. `streams-multiagent/<date>` | The transcripts are the **only** record of what the agent invoked. The `perpr-*` arming criterion (every transcript shows at least one driver invocation) and the arm's adoption rate are derived from them; there is no ledger-side invocation counter. |

```sh
export FATHOM_TASK_DIR="$PWD/tasks/multiagent-composition/exprlang"
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

## Where a `final-*` gate's output lands

The `gated-session` executor writes the extra gate's own output into the trial
row's `detail`, bounded and whitespace-condensed, as `extra-gate first: …` (and
`extra-gate final: …` when a fix round ran). A `final-*` row therefore records
which convoy ran and what it reported, not only `red`/`green`; a row reading
`extra-gate first: <not run: the task's own gate was red>` says the visible suite
short-circuited before convoy was reached, which is a different fact from a
convoy red.
