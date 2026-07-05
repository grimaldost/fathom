# Scorecard — test-bank

## Dev Tasks

### Pass Rates

| Scenario | Pass | N | Pass Rate | Wilson 95% CI | Infra Errors |
|---|---|---|---|---|---|
| bare | 1 | 2 | 50.0% | [9.5%, 90.5%] | 0 |
| series | 2 | 2 | 100.0% | [34.2%, 100.0%] | 0 |
| single-long-session | 1 | 1 | 100.0% | [20.7%, 100.0%] | 1 |

> **CI caveat:** N pools every task×repeat cell; repeats within a task and the different (heterogeneous) tasks are correlated repeats, so the Wilson 95% CI is a **heuristic width** (an under-estimate of true uncertainty), not exact 95% coverage — cf. ADR-0007 D3. Each verdict shows K = distinct tasks.

### Verdicts

- **bare** — 1/2 (50.0%), Wilson 95% CI [9.5%, 90.5%], n=2 across K=2 task(s) — directional, not final
- **series** — 2/2 (100.0%), Wilson 95% CI [34.2%, 100.0%], n=2 across K=2 task(s) — directional, not final; arm deltas vs bare: human decomposition, per-PR gates, review/fix subagents, engine settings
- **single-long-session** — 1/1 (100.0%), Wilson 95% CI [20.7%, 100.0%], n=1 across K=1 task(s) — directional, not final; 1 infra error(s) excluded

### Per-Criterion Pass Rates

| Criterion | bare | series | single-long-session |
|---|---|---|---|
| criterion_1 | 50.0% (1/2) | 100.0% (2/2) | 100.0% (1/1) |

### Pairwise vs Bare Anchor

| Scenario | Win | Tie | Loss | N Pairs |
|---|---|---|---|---|
| series | 1 | 1 | 0 | 2 |

### Economy

| Scenario | Tokens | Turns | Wall-clock (s) | Sessions/Trial | Est. USD |
|---|---|---|---|---|---|
| bare | 430 | 7 | 22.0 | 1.00 | 0.0130 |
| series | 740 | 13 | 53.0 | 1.50 | 0.0210 |
| single-long-session | 700 | 10 | 30.0 | 1.00 | 0.0200 |

### Efficiency

| Scenario | Mean In-Tok | Mean Out-Tok | Mean Cache-Tok | Mean Turns | Mean Wall (s) | Quality / 100k Tok | Pareto |
|---|---|---|---|---|---|---|---|
| bare | 150 | 65 | 0 | 3.5 | 11.0 | 232.56 | ★ |
| series | 265 | 105 | 0 | 6.5 | 26.5 | 270.27 | ★ |
| single-long-session | 500 | 200 | 0 | 10.0 | 30.0 | 142.86 |  |

## Holdout Tasks

### Pass Rates

| Scenario | Pass | N | Pass Rate | Wilson 95% CI | Infra Errors |
|---|---|---|---|---|---|
| bare | 1 | 1 | 100.0% | [20.7%, 100.0%] | 0 |
| series | 1 | 1 | 100.0% | [20.7%, 100.0%] | 0 |
| single-long-session | 1 | 1 | 100.0% | [20.7%, 100.0%] | 0 |

> **CI caveat:** N pools every task×repeat cell; repeats within a task and the different (heterogeneous) tasks are correlated repeats, so the Wilson 95% CI is a **heuristic width** (an under-estimate of true uncertainty), not exact 95% coverage — cf. ADR-0007 D3. Each verdict shows K = distinct tasks.

### Verdicts

- **bare** — 1/1 (100.0%), Wilson 95% CI [20.7%, 100.0%], n=1 across K=1 task(s) — directional, not final
- **series** — 1/1 (100.0%), Wilson 95% CI [20.7%, 100.0%], n=1 across K=1 task(s) — directional, not final; arm deltas vs bare: human decomposition, per-PR gates, review/fix subagents, engine settings
- **single-long-session** — 1/1 (100.0%), Wilson 95% CI [20.7%, 100.0%], n=1 across K=1 task(s) — directional, not final

### Per-Criterion Pass Rates

| Criterion | bare | series | single-long-session |
|---|---|---|---|
| criterion_1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |

### Economy

| Scenario | Tokens | Turns | Wall-clock (s) | Sessions/Trial | Est. USD |
|---|---|---|---|---|---|
| bare | 180 | 3 | 8.0 | 1.00 | 0.0060 |
| series | 225 | 4 | 12.0 | 1.00 | 0.0070 |
| single-long-session | 550 | 8 | 25.0 | 1.00 | 0.0160 |

### Efficiency

| Scenario | Mean In-Tok | Mean Out-Tok | Mean Cache-Tok | Mean Turns | Mean Wall (s) | Quality / 100k Tok | Pareto |
|---|---|---|---|---|---|---|---|
| bare | 120 | 60 | 0 | 3.0 | 8.0 | 555.56 | ★ |
| series | 160 | 65 | 0 | 4.0 | 12.0 | 444.44 |  |
| single-long-session | 400 | 150 | 0 | 8.0 | 25.0 | 181.82 |  |
