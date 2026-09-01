# Gate composition — does convoy's standalone gate earn its place under external orchestration?

- **Date:** 2026-09-01 (matrix); **revised 2026-09-01** after a blind two-reviewer validity pass — see "Retractions" first
- **Design:** [`docs/specs/2026-09-01-convoy-gate-composition-design.md`](../specs/2026-09-01-convoy-gate-composition-design.md)
- **Bank:** `ablation-v2` / `exprlang`, weak tier (Haiku 4.5, effort high), 15-criterion held-out oracle unchanged
- **Spend:** $9.11 est. across the three new arms (24 trials), against a $120 configured ceiling and a ~$6.51 ledger-derived expectation (40% overrun, unexplained; smoke cost sits outside this figure — it wrote no ledger rows)
- **Convoy under test:** the published `v0.10.0` release, resolved through `uvx --from git+…@v0.10.0`

## Retractions

The first version of this report headlined "composing convoy's gate with external
orchestration beats naive gating, p = 0.0385". Two blind reviewers and the operator's own
re-analysis found that claim unsupported on three independent grounds, any one of which
is sufficient. It is withdrawn, and the corrected reading is below.

1. **The significant contrast is an implementation draw, not gate action.** The ledger's
   `detail` records the first gate verdict before any fix. In A3, **7 of 8** implementations
   were already criterion-clean when the gate first ran; the gate went red once. The
   counterfactual "A3 without its gate" is 7/8 — against A1's 4/8 that is p = 0.141, not
   significant. The arm with the *larger* measured gate action (A2: 4 first-reds, 3
   repaired) is the *non-significant* one. Significance tracked the batch, in the
   opposite direction to what the gate did. It is also not knowable from the ledger
   whether A3's one red came from the probe or from the visible suite that runs first;
   if the latter, convoy's probe blocked in zero A3 trials.
2. **The headline criterion is not blind to the gate.** `verify.py` grades
   `type_bool_in_arith` on four expressions; `type_probe.py` asserts three of them
   string-identically (`"true + 1"`, `"1 - true"`, `"-true"`) and the fourth by shape. Two of
   the three `type_compare_bool` items are likewise identical to probe cases. An arm whose
   gate runs the probe to green is *definitionally* passing what it is graded on. The 13
   criteria that would have measured generalization are at 8/8 in every arm — zero
   variance. The bank cannot answer "does the gate improve quality"; it can answer "does
   asserting X make X true".
3. **No endpoint, test, direction or correction was pre-registered, and the headline does
   not survive any of them.** Two-sided p = 0.077; Holm over the four contrasts the report
   itself declares, p = 0.154. The spec quoted A1 at 3/8 (the all-15-criteria metric the
   prior report used); this report switched to 4/8 (single criterion) without saying so.
   On the spec's own metric A3 vs A1 is 8/8 vs 3/8, one-sided p = 0.0128, Bonferroni
   0.051 — still subject to (1) and (2).

Also withdrawn: the cost claim ("A3 ~26% dearer") was computed per **spawn**, not per
trial, and rewards the arm that needed more repairs; per trial A3 is +4% on the median,
**−15% on the mean and on total spend ($2.97 vs $3.51 per 8 trials), and faster (173 s
vs 187 s median wall-clock)**. The "A3 vs A2 null, p = 0.50" was presented as evidence of
absence; 0.50 is the *minimum attainable* one-sided p for 8/8 vs 7/8 and carries no
information. And the A4 reading ("ceremony without oracle independence buys nothing —
and may cost") rested on 2/8 vs 4/8 (two-sided p = 0.61; vs bare, p = 1.0) for an arm
with **no per-trial evidence the agent ever invoked the gate** — no transcripts were
persisted, `detail` is empty on all eight rows, and turn counts are indistinguishable from
the non-convoy arm. By the harness's own FATH-B01 rule (execution asserted in the ledger,
never assumed), A4 is void, and its 2/8 is the signature an inert arm produces.

## Arms

| | Arm | What it is |
|---|---|---|
| A0 | `haiku` | bare single session, no gate (July cell, resume-reused) |
| A1 | `haiku-gate` | harness-driven loop, gate = the project's own visible suite (July cell) |
| A2 | `haiku-gate-sg2` | same loop, plus an independent type-contract probe wired by hand |
| A3 | `haiku-convoy-gate` | same loop, same oracle content, carried by `convoy gate` — plus a `repair_hint` A2 has no equivalent for |
| A4 | `haiku-convoy-gate-self` | single session; an injected brief tells the agent to drive `convoy gate` itself at A1's oracle; `Bash(uvx:*)` added to the allow-list — **four factors from A1, not one; void per above** |

None of these arms is multi-agent. The "external orchestrator" is the harness's own
`while red: re-prompt` loop. The one multi-agent arm in the design (`haiku-series`) is
authored and unrun. **The operator's question as framed — "convoy with multiagents" — was
not tested here.**

## Data (correct, and kept)

`type_bool_in_arith`: A0 3/8 · A1 4/8 · A2 7/8 · A3 8/8 · A4 2/8. All-15-criteria clean:
A1 3/8 · A2 7/8 · A3 8/8. First-gate state: A1 green **8/8** (its loop never executed one
iteration — operationally A1 is bare plus a redundant `unittest` run) · A2 green 4/8 · A3
green 7/8. Free comparator never mentioned in the first version: `haiku-reprompt`
(iteration-matched, no gate) 5/8; A3 vs it, p = 0.10. The void `haiku-gate-sg` arm — unattributable,
its probe never ran — reads 10/10 against A1's 4/8, one-sided p = 0.023: this bank
produces "significant" contrasts from arms with no mechanism.

Config integrity **does** hold: recomputing `config_hash` from the committed TOMLs
reproduces the July comparators' ledger hashes exactly, and A1 vs A3 differ in exactly one
preimage key (`gate.extra`). What does not hold is the environment pin: `cli_version` and
`tool_git_sha` are empty on every row, no row carries a timestamp, and the model is an
undated alias — the two-month gap between comparators and treatment arms, run as
contiguous blocks rather than interleaved, is unfalsifiable from the ledger.

## What this dataset does establish

**Within-arm, needing no cross-arm comparator:** in A2, a harness-side deterministic
probe turned the criterion from 4/8 pre-gate to 7/8 post-gate, with perfect concordance
between first-gate verdict and pre-fix defect state (every first-green trial passed,
every first-red failed pre-fix; three of four reds repaired, one stayed red and failed).
**An implementer-unreachable oracle plus a bounded fix loop repairs the class it
asserts** — with the caveat from Retraction 2 that "the class it asserts" overlaps what
was graded, so this is repair-of-the-tested, not generalization.

**Across three batches, a self-oracle gate goes green while the held-out oracle fails:**
A1 8/8 green gates → 4/8 criterion escapes; A4 → 6/8 escapes; the July round 8/8 green →
5/8 escapes. Roughly fifteen escapes under twenty-six green self-authored gates. This is
the robust finding in the corpus and it is a *mechanism* observation, not a fragile
between-arm contrast.

**As engineering:** `convoy gate` v0.10.0 composes with a non-convoy harness — all 16
invocations across A2/A3-style calls returned well-formed envelopes, the fail-closed
isolation guard passed an out-of-tree asset rather than skipping it, and per completed
task the composed arm cost no more than a hand-wired probe and ran faster. That is what
the round was *entitled* to claim.

## Defects in this round, disclosed

- **Driver stream encoding.** The A3 driver wrote convoy's em-dash narration through a
  cp1252 stream; the harness reads strict UTF-8; a dead reader thread yields `None`
  streams and an **empty fix re-brief**. Traced: exit codes survive, so no red was read as
  green — but the destroyed text is convoy's advertised differentiator (`detail` +
  `repair_hint`), so A3's single repair ran with convoy's edge disabled. A stalled pipe
  could also have flipped a green to a timeout-red under `_GATE_TIMEOUT_S = 120` (not
  observed). Fixed in the driver; the harness-side read remains strict.
- **The A3 arm was edited after its trials without re-versioning** — the encoding fix
  landed in the driver in the same commit as the first version of this report, against the
  scenario's own rule. Repaired: the fixed driver runs under `haiku-convoy-gate-v2`; the
  eight trials stay attributed to `haiku-convoy-gate` and the pre-fix driver.
- **The pinned build's red-detection was verified but not recorded** in the spec's arming
  table (all three table rows ran under the local-checkout override). Repaired: the
  un-overridden run is now the table's fourth row.
- **The persona leaked into experiment selection, not wording.** The first version's
  "next moves" had no branch that could return "the lift was the batch". That branch is
  now the first one.

## What comes next — and the branch that can say convoy lost

1. **Batch-randomized replication with a placebo gate.** Re-buy A1 *interleaved* with A3
   in one batch, and add a placebo arm — an extra check that reddens once without
   carrying independent information — to separate "one more repair iteration" from "an
   independent oracle". The ledger already hints the former matters (`haiku-reprompt`
   5/8). This is the branch that can return "the observed lift was drift plus an extra
   turn", and it is bought first.
2. **Grade on held-out items the gate does not assert.** Until the bank's oracle has
   discriminating criteria outside the probe's assertions, no arm on this bank can show
   generalization. This is bank work, priced before any further arm.
3. **Persist per-trial attestation** — gate exit code, gate stdout, and the provenance line
   the driver already prints — in the ledger `detail`, so "which convoy ran" and "did the
   probe block" are facts, not inferences. Also required to un-void an A4-shaped arm.
4. **The doctrine change convoy should make** is supported — but by the within-arm
   mechanism observation, not by A4: *adopting the gate surface without an
   implementer-unreachable check leaves you exactly where you started.* One sentence, no
   "may cost".
5. **The operator's actual question** needs a different experiment: subagent dispatch
   self-verified (the production status quo) vs. + hand-wired oracle vs. + `convoy gate`,
   over ≥10 PR-sized tasks reconstructed from real merged PRs with post-merge tests
   withheld, at the tier actually dispatched, n ≥ 30, interleaved. `haiku-series` and the
   A3-vs-A2 n≈30 question are deferred behind it; the latter needs n ≈ 80 near ceiling and
   the decision does not turn on it.
