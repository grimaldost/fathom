# Spec — convoy-gate composition: the gate framework under external orchestration

- **Date:** 2026-09-01
- **Status:** draft
- **Audience:** the operator deciding whether to buy the matrix; the session that authors
  the scenario arms; the report reader deciding whether convoy's standalone gate earns
  composition with multiagent orchestration.
- **Output artifact(s):** `scenarios/gate-composition/*.toml`, one checks fixture per
  gated arm under `tasks/ablation-v2/exprlang/` (task content unchanged),
  `docs/reports/<date>-gate-composition-findings.md`, ledger rows in
  `ledger/ablation-v2.jsonl` (same bank id — the bank, not the directory, names it).

## Context

Convoy 0.10.0 (pending release) exposes the deterministic gate standalone: `convoy gate` /
`convoy_gate` run a series' `[[checks]]` against a workspace once — same runner, same
fail-closed independence guard, same verdict rules — with no spawn, no branch, no
telemetry. The engine repo's 2026-09-01 triage (T53, gated on T52a) records the mandate:
convoy has never been measured **composing** with an orchestrator that is not convoy, so a
partial-use decision is made blind. A production session chose direct multiagent dispatch,
rejected convoy's runner on its merits, and discarded the gate with it — 11 PRs verified
only by the agent that implemented each one.

What the corpus already establishes, and this design leans on:

- **The gate matters exactly when the implementer is blind and weak.** The 2026-07-24
  bakeoff's blind×weak arm: 3/3 reds caught and repaired with the gate, 3/3 "broken as
  done" without it. The strong tier self-gates to saturation (ablation-v2: bare Sonnet 5
  100%; every in-session feature +0).
- **Gate value tracks oracle independence, not gate presence.** ablation-v2 weak tier:
  the visible-suite gate went 8/8 green while 5/8 escaped to the blind oracle —
  self-authored tests inherit the implementer's blind spots.
- **The one arm that would have answered this is VOID.** `haiku-gate-sg2`'s probe never
  executed (placeholder gate path); it ran as its own control and its config_hash has no
  preimage. The strengthened-gate lift (38%→90%) is unattributable. The arming-verified
  check (FATH-B01) and the bank-validity triad (FATH-B02) shipped 2026-08-11, so the
  instrument defect that voided it is closed.

**Stance, declared:** this experiment is run by an advocate. The operator wants convoy to
win the comparison against the no-convoy arm — and the licensed way to get there is to
improve convoy until it wins honestly, never to bias the instrument. Concretely: arms are
symmetric in model, effort, prompts, budget and turn limits; the blind oracle is identical
for every arm; the only degrees of freedom are convoy's own surfaces (what the gate
refuses, what the failure `detail` carries, what the docs teach an agent to do). If the
composed arm loses, the next move is a convoy improvement and a re-run, recorded in the
report — not an arm asymmetry.

## Goal

Measure whether convoy's standalone gate, composed with orchestration that is NOT convoy,
(1) closes the defect-escape gap the visible-suite gate leaves at the weak tier, and
(2) does so at a cost/latency an operator would pay against the full engine. Redeem the
voided sg2 question through the real shipped surface with verified arming.

## The arms

Bank: `ablation-v2` (exprlang), unchanged — task content, fixtures, `verify.py` (blind
15-criterion oracle) and `type_probe.py` all exist. Tier: **weak (Haiku), effort high** —
the regime with measured headroom (bare 3/8, haiku-gate 3/8) and the causal precedent.
Comparators `haiku` (bare) and `haiku-gate` (visible-suite gated-session) are already in
the ledger at the same model+effort; resume reuses them for $0 where config is unchanged.

| Arm | Strategy | What changes | Reads as |
|---|---|---|---|
| A0 `haiku` (ledger) | single-session | — | floor |
| A1 `haiku-gate` (ledger) | gated-session, gate = visible suite | — | orchestration + self-oracle gate |
| **A2 `haiku-gate-sg2r`** | gated-session; `[gate].extra` = the type probe invoked directly (`python "${task_dir}/type_probe.py" "${workspace}"`) | the voided sg2 cell re-armed, with FATH-B01 arming verification | probe-direct: what an operator wires by hand |
| **A3 `haiku-convoy-gate`** | gated-session; `[gate].extra` = one driver (`python "${task_dir}/run_convoy_gate.py" "${task_dir}" "${workspace}"`) that materializes a gate spec into a temp file — visible suite as a blocking check plus `type_probe.py` as a blocking `independent = true` check with an out-of-tree `asset` — and execs `uvx --from git+<convoy>@<tag> convoy gate <spec> -w ${workspace} --json`, exiting with convoy's exit code | probe-through-convoy: the same oracle content, carried by the framework's fail-closed surface |
| **A4 `haiku-convoy-gate-self`** | single-session; a context inject hands the agent a ready checks file (visible suite ONLY — no probe, the agent stays blind) and instructs it to iterate `uvx ... convoy gate checks.toml -w .` until exit 0 | the AGENT drives the framework, no harness loop, at A1's oracle | adoption: "agents actively use the framework without the orchestration" |
| `haiku-series` (authored, unrun) | series | full engine, decomposed 5-PR series | the whole-engine reference — priced in the same dry-run, bought only if the composed arms warrant it |

The attribution chain, three single-factor contrasts:

- **A2 vs A1** — the independent probe's own value (the sg2 question, finally validly
  measured). Everything convoy claims routes through this being nonzero at the weak tier.
- **A3 vs A2** — the framework's marginal contribution at EQUAL oracle content:
  fail-closed isolation, the envelope, and the failure `detail` the fix loop re-briefs
  with, against a hand-wired probe. The advocate's honest win conditions: quality ≥
  probe-direct with better repair economy, or equal at ≈0 overhead — safety and
  ergonomics for free. If A3 < A2, something in convoy's surface is in the way; improve
  convoy, re-tag, re-run.
- **A4 vs A1** — agent-driven convoy-gate loop vs harness-driven naive loop at equal
  oracle: does the surface survive contact with a weak-tier agent (discoverability,
  usability, loop discipline)?

The probe stays harness-side in A2/A3 (it must strengthen the gate, not become the
oracle, and must not leak into the implementer's context); A4 deliberately gets no probe
— handing the agent the probe file would teach to the test and break blindness.

## Mechanism notes (what makes this cheap)

- No fathom engine change. `gated-session` already runs `[gate].extra` commands after the
  task gate with `${task_dir}` / `${workspace}` substituted at run time (the template,
  not a machine path, enters `config_hash`).
- Convoy is pinned by release tag via `uvx --from git+https://github.com/grimaldost/convoy@v0.10.0`
  — portable across checkouts, no sibling-path coupling, and the measured artifact is the
  *shipped* surface, honoring the engine repo's own release discipline. First invocation
  per machine pays the uvx build; subsequent ones are cached.
- A gate spec's `[[checks]].run` strings are read by convoy, not by fathom, so they
  cannot carry fathom's `${task_dir}` placeholder. A3 therefore ships a small driver
  (`run_convoy_gate.py`, task-dir-side, stdlib-only) that receives the two substituted
  paths, writes the gate spec with absolute paths to a per-trial temp file (nothing
  lands in the workspace; the task dir is shared by parallel trials and stays
  read-only), invokes `convoy gate`, and propagates the exit code. A4's checks file has
  no such paths (visible suite only) and ships as a static fixture the inject brief
  points at.
- Arming verification: the FATH-B01 check plus one paid smoke trial per new arm before
  the matrix; the sg2 lesson says the probe's own execution is asserted in the ledger
  `detail`, not assumed.

## Arming verification (done, 2026-09-01, $0 — no spawns)

The sg2 cell was voided because its probe never executed and nothing said so until the
spend was gone. So the A3 and A4 mechanics were proven to **fire** before any trial is
bought, by running the driver against hand-built workspaces with the convoy under test
pointed at the local checkout (`FATHOM_CONVOY_GATE_LOCAL`, which the driver echoes to
stderr on every call — a trial that ran under an override says so in its own ledger
detail instead of being indistinguishable from a pinned one).

| Probe | Workspace | Result |
|---|---|---|
| A3 driver, correct implementation | fixtures + reference `solution/` | both checks green, driver exit 0; the independent check's out-of-tree asset passed convoy's isolation guard rather than being skipped |
| A3 driver, injected escape | same, with `_is_number`'s `and not isinstance(v, bool)` removed — the exact bool-is-int class the probe exists for | **visible suite 20/20 green** while `type-contract-probe` goes RED with the full 7-case diagnostic in `detail`; driver exit 1, which is what `gated-session` reads as a red gate and re-briefs the fix loop with |
| A4 command shape | agent-authored `convoy-checks.toml` (visible suite only) + `convoy gate <file> -w .` | runs, exits 0, prints `completed` |
| A3 driver, **un-overridden**, against the published release | the injected-escape workspace, `FATHOM_CONVOY_GATE_LOCAL` unset | provenance line reads `git+https://github.com/grimaldost/convoy@v0.10.0`; visible suite green, probe RED, driver exit 1 — the pinned build detects the escape (run after the tag existed; recorded here late, after a reviewer noted the table showed only override rows) |

The second row is the whole bank's premise reproduced on demand: a defect that is
invisible to the project's own suite and visible to an implementer-unreachable oracle.
The third row confirms A4's brief is executable as written — and that A4, by design,
does **not** catch that escape (its gate is the visible suite only; A4 vs A1 is a
loop-discipline contrast at equal oracle, not an oracle contrast).

What this does not establish: that the weak-tier agent produces the escape at a useful
rate, or that the fix loop repairs it — those are the measurement, not the arming.

## Gate commands

fathom's own: `uv run fathom validate <bank>`, `uv run fathom smoke`, `uv run fathom run
ablation-v2 --scenarios-dir scenarios/gate-composition --dry-run` (plan + USD ceiling)
before any paid trial. The engine repo's gate is not this spec's concern.

## Cost plan (to be priced by --dry-run before any spend)

n=8 per new arm (matching the existing haiku cells), 3 new arms (A2, A3, A4) ⇒ 24 paid
trials plus one smoke trial per arm. Weak-tier exprlang trials observed ~130s/spawn;
gated-session ≤ 1 impl + 2 fix spawns. Ballpark $10–15; the dry-run number is the one
that licenses the spend, and the operator confirms the ceiling before `fathom run`.
`haiku-series` (5-PR engine trials, ~20× wall clock) is NOT in the default buy: price it
in the same dry-run, decide after the composed arms read out.

## Non-goals

- No strong-tier arms (measured saturation; nothing to learn per dollar).
- No new task bank (the bank-validity triad makes authoring the expensive artifact;
  exprlang already discriminates at the weak tier).
- No declared-red-window or adjudication-halt modeling (convoy triage T54 — watch).
- Not a general "convoy vs the field" verdict — one bank, one tier, one task shape; the
  report states the regime.

## Invariants touched

- Ledger append-only; same bank id ⇒ rows join `ledger/ablation-v2.jsonl` (ADR-0003
  blind scoring unchanged).
- `config_hash` discipline: new arms are new hashes; nothing resumes under an old arm's
  identity. The `uvx --from ...@<tag>` string is part of the arm config on purpose — a
  convoy improvement and re-run (the advocate loop) lands as a NEW tag and therefore a
  new, comparable arm, never a silent mutation of an existing one.
- The advocate loop's evidence rule: a convoy change made to win the comparison ships
  through convoy's own repo process first (PR, CHANGELOG, tag), then re-measures here.

## DoR gaps (why status = draft)

- **Convoy 0.10.0 is not yet tagged** (PRs in flight). `CONVOY_PIN` names it in advance;
  the arm cannot run for real until the tag exists, and the first paid trial must be
  preceded by one un-overridden invocation confirming the pinned release resolves.
- **The dry-run ceiling is unpriced** at `--repeats 8` (the `--repeats 2` plan came back
  at a $30 ceiling for 6 trials; the real number gates the spend and needs the operator's
  explicit confirmation).
- ~~The driver and the `-self` brief are unauthored~~ — authored and arming-verified
  above.
