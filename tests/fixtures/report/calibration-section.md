## Model-Tier Calibration

### Calibration: predicted tier vs empirically-right tier

| predicted ↓ / empirical → | weak | mid | strong | indeterminate |
|---|---|---|---|---|
| **weak** | 1 | 0 | 0 | 0 |
| **mid** | 0 | 0 | 0 | 0 |
| **strong** | 0 | 0 | 0 | 1 |

On-diagonal (well-tuned): **1/2**.

### Per-task (per-trial pass rate by arm: all hard criteria true)

| task | score | predicted | empirical | haiku | sonnet | opus | note |
|---|---|---|---|---|---|---|---|
| t1 | 10 | weak | weak | 100% | 100% | 100% | ✓ |
| t2 | 80 | strong | ? | 0% | 0% | 100% | indeterminate |

Mixed-hard trials: **0/12** (a trial where some hard criteria passed and others failed). The per-trial estimator treats a cell as one draw; at 0 that is exact, above 0 it is conservative — see ADR-0009.

### Dose-response (first-attempt pass rate × cost per upgrade, by band)

| band | arm | mean first-attempt pass | mean $/trial | Δ first-attempt vs prev arm |
|---|---|---|---|---|
| weak | haiku | 1.00 | $0.010 | — |
| weak | sonnet | 1.00 | $0.010 | +0.00 |
| weak | opus | 1.00 | $0.010 | +0.00 |
| strong | haiku | 0.00 | $0.010 | — |
| strong | sonnet | 0.00 | $0.010 | +0.00 |
| strong | opus | 1.00 | $0.010 | +1.00 |

### Cost vs first-attempt pass: Pareto frontier (★ = non-dominated)

| arm | mean first-attempt pass | mean $/trial | frontier |
|---|---|---|---|
| haiku | 0.50 | $0.010 |  |
| opus | 1.00 | $0.010 | ★ |
| sonnet | 0.50 | $0.010 |  |
