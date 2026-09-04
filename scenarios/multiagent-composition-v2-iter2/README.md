# Arms for `multiagent-composition-v2-iter2` — operator note

Run them with `--scenarios-dir scenarios/multiagent-composition-v2-iter2` — `fathom run`
globs a scenarios dir non-recursively, and omitting the flag silently runs the
wrong arms. The design, the endpoints and the contrasts live in
[`docs/specs/2026-09-01-multiagent-composition-preregistration.md`](../../docs/specs/2026-09-01-multiagent-composition-preregistration.md),
section "Pre-registration — iteration 2 on bank v2"; this file is the run
procedure only. Iteration 1's own precondition checklist is
[`scenarios/multiagent-composition-v2/README.md`](../multiagent-composition-v2/README.md) —
the 2026-09-01 addendum made a written checklist mandatory after a forgotten
export lost part of a paid pass; this file repeats it for iteration 2's own
eight new cells, harness staging and caps.

Eight NEW contemporaneous cells on the SAME bank and fixture iteration 1
measured: `{control2, placebo2, perpr2, hook2}` x `{haiku, sonnet}`.

## Run this with `local/run-iter2.sh`, not by hand

`local/run-iter2.sh <n_per_cell> <max_run_usd> <stream_dir> [START] [ITER_SPEND_CAP]`
stages the harness directory, sets the three exports below, and enforces the
per-pass gates (exposure scan, arming check, spend cap). Do not invoke
`fathom run` directly against this scenarios dir for a paid pass — the harness
staging and the caps are the runner's job, and skipping them reproduces
exactly the failure modes the 2026-09-03 blind review found in iteration 1.

## The three exports the attestation depends on

`local/run-iter2.sh` sets these; if running anything by hand (a smoke test, a
single probe trial), set them the same way:

| Variable | Value | Why it is not optional |
|---|---|---|
| `FATHOM_TASK_DIR` | the staged harness dir, e.g. `$LOCALAPPDATA/Temp/fathom-harness-multiagent-composition-v2-iter2` | Every arm's `[env]` block resolves `${FATHOM_TASK_DIR}` at spawn time for the driver, probe and gate-spec paths. |
| `FATHOM_PROMPTS_DIR` | `$FATHOM_TASK_DIR/prompts` | The only path the briefs give the orchestrator for the five PR prompts. |
| `FATHOM_STREAM_DIR` | a run-scoped absolute directory | The transcripts are the only record of what the agent invoked; the hook arms' Stop hook also resolves this to know where to copy `.convoy/hook.log`. |

```sh
unset FATHOM_CONVOY_GATE_LOCAL
```

`FATHOM_CONVOY_GATE_LOCAL` must stay unset for the whole matrix: it is the
arming-verification escape hatch, and a matrix run under it never touches the
pinned convoy release the record attests.

## Before the first paid pass

1. **`fathom verify-arming` PASS on all eight arms**, with the observed
   registered-tool set recorded in the run log — the registry restriction is
   iteration 2's answer to the blind review's first threat (30 tools
   registered in iteration 1's init event), and it is worth nothing unarmed.
2. **Observe the pinned convoy tag, once, without the override.** With
   `FATHOM_CONVOY_GATE_LOCAL` unset, run the driver over a throwaway workspace
   and confirm the stderr echo reads
   `convoy gate via: git+https://github.com/grimaldost/convoy@v0.12.0` (or
   whatever `FATHOM_CONVOY_PIN` names, for the arms that override it).
3. **Warm the uv cache and time a warm call**, against the hook arms' 900s
   `SubagentStop` / `PostToolUse` hook timeout:
   `uvx --from git+https://github.com/grimaldost/convoy@v0.12.0 convoy --version`.
   A cold resolution eating a meaningful fraction of that budget is worth
   knowing before the spend starts, not after a hook2 trial times out.
4. **`fathom smoke` on the bank** before pass 1.
5. **Caps**: `--max-spawn-usd 20` (per spawn), and the runner's own
   `ITER_SPEND_CAP` — pre-registered at $385, refused above that by the
   runner itself. Do not pass a larger override to "just get through the
   matrix"; a cap that can be silently raised is not a cap.
