# routing-decision-v1 — what a routing decision costs, and what it decides

Four blocks whose task is **the routing decision itself**: briefs in, one model tier
per brief out. The arms are routing mechanisms crossed with the tier the decision is
taken at.

Design of record:
[`docs/specs/2026-08-12-routing-mechanism-eval-design.md`](../../docs/specs/2026-08-12-routing-mechanism-eval-design.md).

**Authored, not run.** No ledger exists for this bank. Everything below is offline
evidence produced by the verifiers and tests themselves, at zero spend.

> **Blocked at the smoke gate, $0 spent.** `fathom smoke` cannot pass while the host's
> OAuth session is expired — the same block the sibling `model-tier-v2` bank records.
> The unblock is a host re-authentication, which is a human step. Nothing here is
> buyable until `fathom smoke` passes.

## Why this bank exists

`choosing-models` scores every task on a rubric before dispatching it. Scoring is not
free: the policy is ~3.8k words, it is loaded into the session that is *making* the
decision, and that session is frequently an expensive one. So the skill can be paying
strong-tier prices to decide that some downstream task deserves a weak-tier model.

If the decision costs more than the routing saves, the rubric is net-negative however
well it routes. No existing evidence prices the decision at all — the three
model-tier calibration runs measured what tiers *do*, never what deciding costs. This
bank measures the decision.

## The blocks

| block | briefs | why |
|---|--:|---|
| `route-1-mechanical` | 1 | the bottom of the score range (20) — a single-function fix |
| `route-1-review` | 1 | a review-shaped brief, a shape the fix-ladder does not cover |
| `route-1-ledger` | 1 | the top of the score range (71) — a ledger parity fault |
| `route-9-mixed` | 9 | every brief at once — the batch shape a series-authoring decision takes |

The K=1 / K=9 contrast is the point, not redundancy. A mechanism carrying a large
policy pays for it **once per decision episode**, so its per-task decision cost
collapses as the batch grows. Two block sizes give a two-point fit that separates the
fixed cost (loading the policy) from the marginal cost (deciding one more task).
Measuring only one size would produce a number that does not generalise to the other.
Every single-brief block also appears in the batch, so the fit compares different K on
the *same* work rather than different work.

## The briefs

Copied from `model-tier-v2` so the join to that bank's per-tier outcome table is exact.
Nine briefs, six dispatch shapes, rubric scores 20 to 71. Full provenance, per-brief
scores and the recorded coverage shortfall: [`provenance.toml`](provenance.toml).

The copy is deliberate. Reading the sibling bank's `task.toml` at run time would make
this bank depend on another agent's uncommitted worktree; a committed copy plus
recorded provenance is auditable and self-contained. The drift risk that creates is
covered by `tests/test_bank_routing_decision_v1.py`, which checks every brief against
its provenance entry in both directions.

**Known shortfall, inherited:** the weak band holds exactly one brief. Once a task is
substantial enough to plant a displaced cause in, the rubric's cross-shape floor lifts
it to at least 26 — the same structural finding the sibling bank records. A bank
concentrated in the mid band **flatters `fixed-mid`**, which is why no headline is
reported on the bank's own uniform mix alone.

## What the verifier scores

**Well-formedness only**, and that is the whole of the hard criteria:

| criterion | meaning |
|---|---|
| `answer_present` | `routing.json` exists and parses |
| `covers_every_brief` | exactly the expected brief ids, none missing, none extra |
| `tiers_are_legal` | every value is `weak`, `mid` or `strong` |

Routing **accuracy is deliberately not scored here.** Its ground truth —
`cheapest_adequate_tier`, per task, from `model-tier-v2`'s run — does not exist yet.
A verifier that graded accuracy today would have to invent the answer key, which is the
one thing this study must not do.

Instead the verifier **records** the emitted routing as `chose__<brief>__<tier>`
booleans, exactly one true per brief. Those are records, not grades: they never gate
the exit code, and a test asserts none is ever promoted to a hard criterion. They
travel into the ledger and `fathom.routing.routes_from_criteria` reconstructs the
routing from them, so accuracy is computed at analysis time by joining evidence to
evidence.

The `solution/` overlay exists only to satisfy fathom's "the verifier is satisfiable"
property. Its values are the rubric's own predictions, which is a defensible
well-formed answer and **not** an answer key — the hard criteria do not inspect values
at all, so the choice is immaterial to grading.

## The arms

`scenarios/routing-decision/` — three mechanisms crossed with three deciding tiers.

|  | `weak` (Haiku 4.5) | `mid` (Sonnet 5) | `strong` (Opus 5) |
|---|---|---|---|
| **`none`** | no policy injected — the true baseline | | |
| **`shortcuts`** | ~0.44k tokens: a floor plus a shape lookup | | |
| **`rubric`** | ~6.1k tokens: `choosing-models` as shipped | | |

Arms differ **only** by `model` and by the injected policy; a test asserts every other
axis (adapter, strategy, effort, tool allow-list, limits) is identical across all nine,
so nothing confounds the mechanism axis with a configuration axis. The 14x size gap
between the two policies is itself asserted, because that gap is the hypothesis.

## Running it

```sh
uv run fathom smoke                                              # must pass first
uv run fathom run routing-decision-v1 --scenarios-dir scenarios/routing-decision \
    --repeats 3 --max-budget-usd 2 --dry-run
```

`--scenarios-dir` is load-bearing: without it the run globs the default `scenarios/`
and silently uses the wrong arms.
