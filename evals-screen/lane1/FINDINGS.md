# Lane 1 offline selection-recall screen -- findings (2026-07-24)

Selectors measured against the fresh sealed oblique holdout (holdout.json, 24 items:
18 skill-labeled, 6 none). recall@k = true skill in the top-k; none@1 = the selector
ranked "none" first on a trivial prompt (abstention).

| selector | recall@1 | recall@2 | none@1 |
|---|---|---|---|
| lexical (word-overlap on original descriptions) | 0.39 | 0.67 | 0.00 |
| embedding (dense, original descriptions) | 0.67 | 0.83 | 0.17 |
| body-aware (dense, SKILL.md bodies) | 0.61 | 0.83 | 0.67 |
| enriched (dense, enriched descriptions) | **0.94** | **1.00** | 0.67 |

## Reading

- **Dense > lexical on oblique** (0.67 vs 0.39). Clean finding: the original
  descriptions predate this holdout, so no author-circularity. Consistent with the
  router's ~0.12 paraphrase recall and the research (dense beats lexical on oblique).
- **Enriched descriptions nearly solve selection** (0.94 / 1.00). CONFOUNDED by
  author-circularity: the enriched descriptions and the holdout prompts were written
  by the same author (me), so they share vocabulary/framing -- the 0.94 is likely
  inflated. Needs an INDEPENDENTLY-authored holdout to confirm.
- **Lexical never abstains** on trivial prompts (none@1 = 0.00) -> it over-selects a
  discipline where none applies (a selection false-positive). Dense/enriched abstain
  far better (0.67).

## The decisive caveat (E1)

Selection != incorporation. E1 measured that even the ORACLE (telling the model the
exact right skill) did not lift behavioral footprint on the weak tier. So a selection
win here does NOT automatically translate to better behavior. Enriched-description is
different from oracle (it improves the matching surface the router/model reads, not a
direct push), so it MIGHT feed the dispatch usefully -- but that is a BEHAVIORAL
question the screen + Stage 2 answer, not this offline recall.

## Disposition

- Enriched-description clears the offline "wide margin over baseline" bar (0.94 vs
  0.39) -> earns a Stage-2 BEHAVIORAL arm, BUT: (a) reconfirm on an independently
  authored holdout first (kill the circularity), and (b) the behavioral effect is
  gated by the E1 selection!=incorporation finding.
- Dense retrieval (embedding/body-aware) beats lexical but under enriched; not worth a
  production retrieval build unless enriched's behavioral effect fails and dense's
  holds -- and the whole family is downstream of the E1 caveat.
- Deferred selectors (classifier-selector 2e, hybrid+reranker 2d): marginal added
  value now that dense/enriched establish the selection story; build only if the
  behavioral question turns positive.

## Provenance
holdout.json (sealed, this experiment) x lane1_selectors.py; embedding backend
sentence-transformers all-MiniLM-L6-v2 (local, $0). No model-API calls.
