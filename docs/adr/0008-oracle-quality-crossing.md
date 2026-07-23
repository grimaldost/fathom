# ADR-0008 — Oracle-quality as a third calibration factor (model × oracle crossing)

- **Status:** Proposed
- **Date:** 2026-07-15

## Context

ADR-0007 framed model-tier calibration on **two knobs** — model (capacity) and
effort (thinking) — and deliberately **staged** them rather than crossing (D5
rejected a full model×effort factorial as a 5× blow-up). The `model-tier-v2` design
(`docs/specs/2026-07-14-tier-separating-bank-design.md`) introduces a **third,
orthogonal experimental factor: oracle quality** — three `verify.py` variants
(thin ⊂ standard ⊂ strong) crossed against model tier, a full 3×3 (≈405 spawns).

That factor carries its own load-bearing decision: `humblepowers:choosing-models`
ships an **oracle-coverage discount** (a weaker model is licensed when the oracle's
coverage/independence is high) as a *labeled hypothesis*, and this crossing is the
experiment that keeps or retires it. Adding a new factor and a full crossing on a
spec alone — against ADR-0007's explicit stage-don't-cross precedent — is the kind
of decision the ADR log exists to record. This ADR records it before any build or
spend.

## Decision

We **add oracle quality as a third calibration factor and cross it against model
tier** (3×3), under these constraints:

- **D1 — Cross here, unlike ADR-0007's effort staging.** The crossing is justified
  *only* because the model×oracle **interaction** is the whole question (does oracle
  quality *differentially* license the weak tier). Effort was staged because its main
  effect sufficed; oracle quality's main effect is a set-inclusion tautology, so only
  the interaction is informative. The blow-up is bounded by the weak-model-fails
  screen, which admits ~2 arms/task before the 9-cell matrix runs.
- **D2 — Screen-gated build and spend.** No task enters the 3×3 matrix until it
  passes the two-arm admission screen (weak fails / strong passes, unanimous over 5
  repeats). The paid matrix stays behind a separate `--max-budget-usd` approval
  (ADR-0007 cost rails).
- **D3 — Oracle axis is new code, scoped not assumed.** `calibration.py`'s
  family-token arm resolution lands arms on the *tier* ladder but has no oracle axis
  (`_tier_arm` keeps one arm per tier). Crossing requires an explicit arm → (tier,
  oracle) resolver and a model×oracle interaction/slope estimator, built before the
  matrix.
- **D4 — Retirement is a null interaction, not a flat curve.** The discount is
  retired iff the weak and strong tiers' oracle-quality slopes are
  indistinguishable. "Flat pass-rates" cannot be the test: the screen selects tasks
  where weak already fails the `standard` oracle, so the weak leg is non-flat by
  construction.

## Alternatives considered

- **Stage oracle quality (ADR-0007 style), don't cross.** Rejected: the licensing
  claim is inherently an interaction (weak-vs-strong response to oracle sharpening);
  a staged main-effect view cannot express it. The screen makes the crossing
  affordable, removing the cost objection that justified staging effort.
- **Fold oracle quality into the existing effort knob.** Rejected: they are
  orthogonal — effort is test-time compute on the *model*; oracle quality is the
  *verifier's* coverage. Conflating them would confound the very interaction under
  test.
- **Leave the choosing-models discount as a permanent labeled hypothesis.**
  Rejected: it actively shapes routing (a real downshift), so "untested indefinitely"
  is a standing risk; this crossing is the cheapest experiment that can settle it.

## Consequences

- **New invariant:** a calibration factor added beyond ADR-0007's two knobs must be
  recorded in its own ADR before build — this one sets that precedent.
- Easier: a keep/retire decision on the choosing-models oracle-coverage discount
  becomes evidence-backed rather than asserted.
- Harder: `calibration.py` gains a second crossed factor (D3) — more analysis
  surface, and the open-loop design measures oracle *detection*, not model
  *licensing* under a fix loop (a limitation the spec states explicitly).
- The crossing does not proceed to spend until D2's screen passes and budget is
  approved; this ADR being **Proposed** (not Accepted) is itself the build gate.

---
*Number ADRs sequentially. Never edit an Accepted ADR's decision; supersede it with a
new ADR. This ADR extends ADR-0007 (it does not supersede it — the two-knob framing
stands; oracle quality is an added factor).*
