# Gate composition — does convoy's standalone gate earn its place under external orchestration?

- **Date:** 2026-09-01
- **Design:** [`docs/specs/2026-09-01-convoy-gate-composition-design.md`](../specs/2026-09-01-convoy-gate-composition-design.md)
- **Bank:** `ablation-v2` / `exprlang`, weak tier (Haiku 4.5, effort high), blind 15-criterion oracle unchanged
- **Spend:** $9.11 est. across the three new arms (24 trials), against a $120 configured ceiling and a ~$6.51 ledger-derived expectation
- **Convoy under test:** the published `v0.10.0` release, resolved through `uvx --from git+…@v0.10.0` — not a working tree

## The question, and the stance it was run under

Convoy 0.10.0 made the deterministic gate usable without the orchestration around it. The
question this matrix answers is whether that composition — convoy's gate under an
orchestrator that is *not* convoy — is worth paying for, and it was run by a declared
advocate: the operator wants convoy to win, and the only licensed route to that is
improving convoy until it does. Arms are symmetric in model, effort, prompts and budget;
the blind oracle is identical across all of them; nothing about the instrument was tuned
to produce a result. Where convoy does not win below, it says so.

## Arms

| | Arm | What it is |
|---|---|---|
| A0 | `haiku` | bare single session, no gate |
| A1 | `haiku-gate` | harness-driven loop, gate = the project's **own visible suite** |
| A2 | `haiku-gate-sg2` | same loop, plus an **independent type-contract probe** wired by hand |
| A3 | `haiku-convoy-gate` | same loop, same oracle content, carried by **`convoy gate`** (fail-closed isolation, declarative spec, `repair_hint`) |
| A4 | `haiku-convoy-gate-self` | the **agent itself** drives `convoy gate` in a loop, at A1's oracle (visible suite only) |

A0 and A1 are pre-existing ledger cells at the same model and effort; A2–A4 are the 24
trials bought here. A2 re-arms the cell that was voided in 2026-08 when its probe silently
never executed.

## Result — the criterion the probe targets (`type_bool_in_arith`)

| Arm | passes | Wilson 95% |
|---|---|---|
| A0 bare | 3/8 | [0.14, 0.69] |
| A1 visible-suite gate | 4/8 | [0.22, 0.78] |
| A2 probe, hand-wired | 7/8 | [0.53, 0.98] |
| **A3 probe via `convoy gate`** | **8/8** | [0.68, 1.00] |
| A4 agent-driven, naive oracle | 2/8 | [0.07, 0.59] |

Overall blind pass-fraction: A0 0.950 · A1 0.958 · A2 0.992 · **A3 1.000** · A4 0.950.

| Contrast | Reading | One-sided Fisher |
|---|---|---|
| **A3 vs A1** — convoy's gate carrying an independent oracle, against naive gating | 8/8 vs 4/8 | **p = 0.0385** |
| A2 vs A1 — the independent oracle's own value | 7/8 vs 4/8 | p = 0.141 |
| A3 vs A2 — the framework's marginal contribution at equal oracle | 8/8 vs 7/8 | **p = 0.50 (null)** |
| A4 vs A1 — adoption: the agent driving the gate itself | 2/8 vs 4/8 | p = 0.94 |

## What this establishes

**1. Composing convoy's gate with external orchestration beats naive gating — the only
contrast that clears conventional significance here.** A3 vs A1 is 8/8 against 4/8,
p = 0.0385. An orchestrator that is not convoy, calling `convoy gate` once per iteration,
closed the defect class the project's own test suite passes. That is the question the
round was bought to answer, and the answer is yes.

**2. The lift is the oracle, not convoy's plumbing.** A3 vs A2 — the same oracle content,
hand-wired versus carried by the framework — is **null** (8/8 vs 7/8, p = 0.50), and A3
costs **~26% more per trial** ($0.370 vs $0.285 median). On this bank at this n, convoy's
gate does not buy quality over a probe an operator wires themselves. What it buys is that
wiring an implementer-unreachable oracle is *declarative and fail-closed* rather than an
act of discipline — real value, and not value this measurement can see.

**3. Ceremony without oracle independence buys nothing — and may cost.** A4 gave the
agent the gate to drive itself, at the visible suite only: 2/8, below both bare (3/8) and
the harness-driven naive loop (4/8), though at n=8 those differences are noise. The
mechanism was verified working (the injected brief reached the spawn's argv; the arming
check passed), so this is not an unarmed arm. The reading is that a weak agent running a
gate against its own visible suite remains judge and defendant on the class that matters.
**Adoption of the surface is not the same as adoption of an independent oracle**, and
convoy's own doctrine should say so where it currently only says the gate is separable.

## Confounds and defects, disclosed

- **A3 vs A2 is not the single-factor contrast the design claimed.** A3's gate spec carries
  a `repair_hint` — a convoy feature with no equivalent in A2's raw probe invocation. The
  repair economy differs in A3's favour (A2: 4 fix rounds across 8 trials with one trial
  still red after two attempts; A3: 1 fix round, none left red), and that difference may be
  the hint rather than the framework. This is an arm asymmetry I introduced and did not
  notice until analysis. It does not touch the A3-vs-A1 headline; it means the framework's
  marginal value is **unresolved**, not null-with-confidence.
- **A decode defect in the A3 driver, which could only have hurt A3.** The driver wrote
  convoy's em-dash narration through Windows-codepage streams; the harness reads with
  strict UTF-8, so at least one reader thread raised `UnicodeDecodeError` and lost that
  call's captured output. Exit codes survive, so gate verdicts were correct — what is lost
  is the text a red gate's fix re-brief quotes. A3 won anyway. Fixed (the driver now forces
  UTF-8 on its own streams, verified against the harness's exact read path).
- **n = 8 per arm.** Only the largest contrast clears; every Wilson interval is wide. Read
  directions, not point estimates.
- **One bank, one task shape, one tier.** The strong tier self-gates to saturation on this
  bank, so nothing here transfers to it.

## What the advocate does next — and what it will not do

The honest next move is **not** to promote "convoy's gate lifts quality" from a null
contrast. It is:

1. **De-confound `repair_hint`.** Run A2′ with an equivalent hint injected by hand, or A3′
   without it. If the hint is the repair-economy lift, that is a convoy feature earning its
   keep, nameable and defensible — and currently hidden inside "the framework".
2. **Resolve A3 vs A2 at usable n.** At 8/8 vs 7/8 the question needs n ≈ 30+ per arm.
   Worth buying only after (1), since the hint may be the whole effect.
3. **Route the A4 finding into convoy's doctrine.** `docs/authoring-series.md` says the gate
   is separable; it does not say that pointing the gate at the implementer's own suite
   reproduces the failure the gate exists to break. That is a documentation change convoy
   should make on this evidence.

None of these is a change to the instrument. If a future arm shows convoy losing, the same
rule applies: improve convoy, ship it through convoy's own process, tag it, and measure it
as a **new arm**.
