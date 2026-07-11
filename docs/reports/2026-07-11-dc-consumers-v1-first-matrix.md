# Can consumer personas answer over the metadata surface? — dc-consumers-v1 findings

- **Date:** 2026-07-11. Bank: `dc-consumers-v1` (5 persona tasks over the GENERATED
  39-entity mock-payments corpus; 42 blind criteria; oracle frozen from executed
  server drives; freshness questions run-time-relative). Companion to
  `2026-07-11-dc-granularity-v1-first-matrix.md` — phase 1 of the data-context
  mock-consumers campaign (its spec §6).
- **Question (operator):** does the data-context twelve-tool surface carry an agent
  through realistic consumer scenarios — analyst report-building, manager number
  distrust, incident triage, onboarding serving, governance audit — on a corpus
  complex enough to have 7-hop chains, a diamond, conflicting artifacts, and honest
  freshness gaps? And does it carry a WEAK-tier model?

## What was run

2 arms (product-sonnet / product-haiku — identical plugin-mounted server + frozen
corpus, only `model` differs) × 5 personas × 3 repeats = 30 trials, single-session,
effort medium, headless default-deny. Zero infra errors; `answers_valid` 30/30
(even haiku always produced parseable, complete answers).

## Result

| Arm | Pass | Per-criterion | Mean turns | Est. USD | Pareto |
|---|---|---|---|---|---|
| product-sonnet | **15/15 (100%)** | **42/42 criteria at 100%** | 16.4 | $5.48 | ★ |
| product-haiku | 9/15 (60%) | 30/35 at 100%; 5 criteria degraded | 23.5 | $2.53 | |

Haiku's failures concentrate in four criteria (all sonnet-perfect):

- `count_2hop_correct` 1/3 — multi-hop distinct-upstream counting on the diamond.
  **Same discriminator as the granularity A/B** (where even sonnet dropped to 2/3
  on the treasury corpus). Third independent signal for the v4 lineage payload fix.
- `error_code_correct` 1/3 — reporting the machine-readable `unresolved_locator`
  code when serving a dashboard fails (haiku paraphrased instead of quoting the
  structured code).
- `platforms_exact` 1/3 — cross-platform name disambiguation (exact-leaf
  `transactions` on postgres + bigquery; haiku over-included prefixed variants).
- `scd2_marker_correct` 2/3 — quoting the SCD-2 current-version marker.

Everything else — including the honest-freshness family (no-assertion unknown,
MONTH-unit unsupported_schedule, run-time-relative fresh/stale), deprecation
conflict resolution, alias serving, fan-in counting, owner teams, snapshot
provenance — passed at 100% on BOTH tiers.

Economy: haiku costs half per trial (~$0.17 vs ~$0.37) but spends 1.4× the turns
and 1.6× the wall-clock for 60% of the quality; sonnet is the sole Pareto arm.
Matrix total **$8.01 vs $60.00 advisory ceiling**, ~30 min wall.

## Interpretation

1. **Phase-1 verdict: the surface is sufficient for real consumer personas at the
   mid tier.** A sonnet-class agent answered every analyst / manager / incident /
   onboarding / governance question over a realistically messy corpus, through
   the tools alone, at ~$0.02 per answered question.
2. **The weak tier degrades exactly where the payloads make the agent do work**:
   counting distinct multi-hop sets, quoting structured codes verbatim, and
   exact-set disambiguation. These are contract-shape issues, not knowledge
   issues — the same v4 remedies (lineage sets with counts + hop labels +
   locator-joined rows; error codes surfaced as first-class fields) directly
   target haiku's failure modes. Re-running this bank after v4 lands gives a
   before/after read on whether contract hardening lifts the weak tier.
3. The mock corpus's designed probes all fired as authored (executed-oracle
   parity held through the paid matrix) — the generated-corpus + persona-bank
   pattern is reusable for phase 2 (treasuryutils association) as-is.
