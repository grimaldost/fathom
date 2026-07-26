# Phase-4 findings — opus tier + the successor hypothesis (2026-07-25)

72/72 trials completed, **zero errors**, $28.53 (opus $21.31, sonnet $5.49, haiku
$1.73 — opus ran ~$0.35/trial, well under the $1 estimate). Blind analysis against
`docs/design/2026-07-25-phase4-opus-and-successor-prereg.md`, applied verbatim.

## 4a — the gate holds on opus: **CONFIRMED**

| tier | bare-sub | disc-sub | lift | 90% CI | FP-lift |
|---|---|---|---|---|---|
| opus-5 | 0.56 | **1.00** | **+0.44** | +0.11, +0.78 | **+0.00** |

The verification gate works on the tier the user actually runs, at zero
false-positive cost. The CI excludes zero. Across all three tiers now:

| tier | gate lift |
|---|---|
| haiku-4.5 (weak) | +0.56 |
| sonnet-5 (mid) | +0.56 |
| **opus-5 (strong)** | **+0.44** |

This was the pre-registered risk case — a strong model might have left no headroom.
It did not: `bare-sub` on opus is 0.56, meaning **an opus subagent still skips
verification on nearly half of delegated tasks**. Capability does not remove the
delegation gap. The shipped README (humblepowers 0.9.0) is updated to three tiers.

## 4b — the successor hypothesis (H3): **REFUTED**

| tier | bare-sub | presc-artifact-sub | FP-lift |
|---|---|---|---|
| haiku | 0.00 | **0.00** | +0.00 |
| sonnet | 0.00 | **0.00** | +0.00 |

A prescriptive gate whose artifact is *always producible* ("add a test that covers
the behavior you changed") over-triggered **zero times** on trivial edits. So
artifact-producibility does not explain the Phase-2 result either.

Per the pre-registration, this verdict is binding: **no authoring rule may be derived
from the Phase-2 contrast at all.** Two candidate explanations have now been tested
and both failed:

| explanation | tested in | verdict |
|---|---|---|
| the prescriptive *register* over-triggers | Phase 3 | refuted |
| an *always-producible artifact* over-triggers | Phase 4 | refuted |

### What is left standing — an unexplained observation, named as such

The Phase-2 measurement itself is not in doubt: the verification prescriptive gate
produced `over_scope` 0.58 on both tiers (7/12 per cell), against 0.00 for every other
arm ever measured. That is far too large and too consistent to be noise. But **we do
not know why**, and two plausible mechanisms are now excluded.

Remaining candidates, none tested — recorded so the next pass does not restart from
scratch:

- **Insistence / conditional framing.** The Phase-2 wording was long and pressing —
  *"If you have not added a regression check that exercises the specific edge this
  change addresses, add one now, confirm it passes on your fixed code, then stop."*
  The Phase-4 artifact wording was short and plain — *"add a test that covers the
  behavior you changed, confirm it passes, then stop."* Length, the conditional
  "if you have not", and "the specific edge this change addresses" are all
  uncontrolled differences.
- **Discipline-domain match.** The Phase-2 gate was a *verification* gate; adding a
  test **is** verification, so on a trivial edit the instruction still had a
  well-formed action. The Phase-4 gate was a *debugging* gate that happened to demand
  a test — a mismatch the model may have resolved by doing nothing.

The honest position: an always-on gate can over-trigger badly, we have one measured
instance, and we cannot yet predict which wordings do it. **The paired null bank is
therefore not optional for any future gate** — it is the only thing that catches this,
and it is cheap.

## 4c — the applicability hint keeps getting better with tier (descriptive)

| tier | bare | classifier-hint | lift |
|---|---|---|---|
| haiku | 0.48 | 0.63 | +0.15 |
| sonnet | 0.59 | 0.85 | +0.26 |
| **opus** | 0.50 | **1.00** | **+0.50** |

Monotonic and steepening. A short applicability hint — *"this situation calls for
X-type care"* — is the cheapest intervention in the program and the only prompt-time
arm that keeps paying as the model gets stronger. It also beat the oracle (naming the
exact skill) on every tier where both ran. This is a router finding: **emit the hint,
not the skill name.**

Note `bare` on opus (0.50, n=6) is not above sonnet's 0.59. Small cell; do not read a
capability regression into it.

## Standing summary after four phases

| claim | status |
|---|---|
| SubagentStop verification gate lifts discipline, no FP cost | **confirmed, 3 tiers** — shipped (humblepowers 0.9.0) |
| Delegation degrades verification | confirmed (bare-sub below main-agent on every tier) |
| Applicability hint > skill name, and scales with tier | confirmed, 3 tiers |
| Gate value is discipline-specific (verification >> debugging > data) | confirmed |
| Forced deliberation (4a) lifts discipline | refuted (3 runs) |
| Band-C emergent need is reachable by prompt-time dispatch | refuted (capability-bound) |
| Prescriptive *register* causes over-triggering | refuted |
| *Artifact-producibility* causes over-triggering | refuted |
| Why the Phase-2 gate over-triggered at 0.58 | **open** |

## Provenance
`ledger-phase4/*.jsonl` (72) + borrowed baselines from `ledger-phase3/e1-debug.jsonl`
(debug `bare-sub`/`presc-sub`) and `ledger-phase2/null-debug.jsonl` (null `bare-sub`)
× `scripts-phase2/analyze_phase4.py`. Model `claude-opus-5`.
