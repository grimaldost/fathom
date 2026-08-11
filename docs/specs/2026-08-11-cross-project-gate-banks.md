# Bank skeletons and cost plans for the two unmeasured cross-project gates

- **Date:** 2026-08-11. **Status:** skeletons and cost plans only — **neither bank is authored and
  neither has been run.** Both gates are recorded as **still-unmeasured**.
- **Why now:** two sibling backlog rows gate a retirement on a measurement this harness would
  execute, and both name fathom's own FATH-B01 (arming verified, not asserted) and FATH-B02 (the
  bank-validity triad) as preconditions. Both closed on 2026-08-11, so the gates are unblocked and
  the next question is what the banks cost. This document answers that and nothing more.
- **Deliberately not done in this wave:** authoring the task content. A bank is the expensive,
  judgement-heavy artifact — the discrimination ratio, the turn budget and the discriminate-by-scale
  call are all authoring judgement that `fathom validate` explicitly cannot check. Writing two
  speculative banks in the same pass that fixed the instrument would reproduce the failure the
  instrument work exists to prevent: a measurement whose defects are discovered after the spend.

---

## Gate A — the pre-mortem directive ablation (keel's KEEL-B09)

### What is being measured

The directive body dispatched on every pre-mortem is ~2,600 words. The question is its **marginal**
effect: how much of the finding-rate it produces survives cutting it to a ~500-word core, and how
much survives cutting it entirely.

Three arms, blind-scored:

| Arm | Treatment |
|---|---|
| A | the full directive body |
| B | a ~500-word core: blind non-author, cite `file:line`, severity + `smallest_fix` + `disconfirming_test` + verdict token |
| C | a bare adversarial spec review, no directive |

The decision rule the sibling row states: **retire every directive arm B matches.**

### Shape as a fathom bank

```
tasks/premortem-ablation-v1/
  bank.toml                  # dataset_version, holdout = ["<2 of the 10 specs>"]
  <spec-id>/                 # one task per historical spec, ~10 of them
    task.toml                # instruction = "review this spec adversarially and report findings"
    fixtures/                # the spec + its PR manifest AT THE TREE STATE IT WAS REVIEWED AGAINST
    truth.json               # the materialized failure modes for this spec (the scoring key)
    verify.py                # reads argv[1] only; emits {criterion: bool}
```

Arms are `[context] inject` over one shared task set — the same axis `skill-pyeng-v1` already uses,
which means the arming axis is `context` and is **verified** by the check shipped this wave:

```
scenarios/premortem-ablation/
  arm-a-full.toml            # [context] inject = "assets/directive-full.md"
  arm-b-core.toml            # [context] inject = "assets/directive-core.md"
  arm-c-bare.toml            # no [context] block — the control
```

### The scoring key, and the reason this bank is harder than it looks

The key is the predicted→materialized ledger (keel ADR-0015 §3): for each historical spec, which
failure modes actually materialized. `verify.py` can check two very different things, and the bank's
credibility depends on keeping them apart:

**Mechanically checkable (a deterministic verifier, no judge):** the structural contract — one
`file:line` citation per claim, a severity tag, a `smallest_fix`, a `disconfirming_test`, a verdict
token. This is the half that is cheap and reliable, and it is a real measurement of whether the
directive's *form* survives compression.

**Not mechanically checkable:** whether an emitted finding *is* an adjudicated real BLOCKER/MAJOR,
and the false-positive rate. Matching free-text findings against a truth list is a judge, and this
repo's pairwise judge has shipped dark since 2026-06-10 precisely because fuzzy-rubric agreement is
weak evidence without human adjudication. **Do not fake this with string matching against
`truth.json`** — a paraphrased finding scores as a miss and the ablation manufactures a null in
arm B's favour, which is the direction the decision is already leaning.

Honest resolution: score the structural contract in `verify.py` (deterministic, blind), and hold the
hit/false-positive adjudication as a separate human pass over the blinded outputs. The bank measures
what a verifier can measure; the adjudication is recorded as a manual step with its own cost.

### Bank-validity pre-check (FATH-B02), which this bank will find awkward

`fathom validate` requires that the unmodified fixture leave the arm something to do. For a review
task the fixture is a spec, and "unmodified" means "no findings emitted yet" — so the criteria start
false trivially and property 1 passes without saying anything useful. **The discriminating question
here is not property 1 but the one the triad explicitly cannot answer:** does arm C actually fail?
The prior says it may not.

### The prior this must be powered against

An in-session structured review pass at the strong tier scored **+0** against the same strategy
without it (this repo's FATH-B35). Arm C is the closest analogue. **If the ablation returns +0
across all three arms that is a reproduction, not a surprise** — and at 10 specs × 3 arms × 3
repeats it is also the most likely outcome. Record the prior in the plan before spending.

### Cost plan

| | |
|---|---|
| Matrix | 3 arms × 8 dev specs (2 held out) × 3 repeats = **72 trials** |
| Per-trial | a spec review is a read-and-reason task, not a build: expect the low end of the observed range, ~$0.15–0.60/trial at the strong tier |
| **Estimated** | **$11 – $43**, most likely ~$20 |
| Dry-run ceiling as printed today | 72 × $2.00 = $144 (the flat ceiling FATH-B04 notes over-warns by 4–25×) |
| Free preconditions | `fathom validate`, `fathom verify-arming`, `--dry-run` |
| Not included | the human adjudication pass over 72 blinded finding-lists — the real cost of this gate is operator time, not tokens |

**Recommendation:** pilot at 3 arms × 3 specs × 1 repeat (9 trials, ~$3) to measure the real
per-trial cost and — more importantly — to check whether arm C fails at all before buying the
other 63.

---

## Gate B — multi-substrate research vs a single-provider run (mantis-research's MANT-B36)

### What is being measured

Two quantities, on the same held-out questions:

1. **how often a surfaced divergence changed a decision**, and
2. **cost per decision changed**,

against the counter-claim the landscape brief raises: that one good model dominates fusion on
quality-per-token at **8.8× the cost**. That multiple is the bar. A fusion run that changes a
decision one time in ten at 8.8× cost is losing.

### Shape as a fathom bank

This gate does **not** fit the harness's default shape, and saying so is part of the deliverable.

fathom's unit is a coding task in a staged git workspace, scored by a verifier that sees only the
final workspace. A research question produces a *brief*, not a workspace. Two adaptations are
needed, and only one of them is cheap:

**Cheap and sound — the sidecar as the result view.** The tool emits a machine-readable epistemic
sidecar per run (`claims`, `divergences`, `verification_queue`, `sources`, with each
`SourceCitations.substrate` joining back to a `sources[].label`). A task can require the arm to
write its brief plus sidecar into the workspace, and `verify.py` can then check, deterministically
and blind:

- sidecar schema conformance and the gating fields (`question`, `generated_at`, non-empty `sources`);
- `divergences` present, each with non-empty `sides` and `substrates`;
- substrate↔source join integrity;
- **and the load-bearing one:** whether the decision extracted from the brief matches the known
  post-hoc answer for that question.

That last criterion is what makes the bank discriminate, and it requires questions whose answer is
**known post-hoc and was not obvious at the time** — the scarce ingredient.

**Expensive and unsound if faked — "did a divergence change a decision".** This is a
counterfactual: it compares the decision a consumer would have made from the single-provider brief
alone against the decision they made with the divergence surfaced. A verifier cannot observe a
counterfactual. Options, in decreasing order of honesty: (a) a blind human adjudication pass over
paired briefs; (b) a two-arm decision-extraction where the metric is simply *decision correctness*
per arm, and "divergence changed the decision" is inferred only where the arms disagree AND the
fusion arm is right; (c) an LLM judge — **not recommended**, for the same reason as Gate A.

Option (b) is the one to build: it is deterministic, it is blind, and it is a strictly weaker claim
than the row asks for. **State the weakening in the report** rather than letting a decision-change
number be read as directly measured.

```
tasks/research-fusion-v1/
  bank.toml                  # holdout = [...] — this bank feeds a retirement decision, so seal one
  <question-id>/
    task.toml                # instruction = the question + "write brief.md and sidecar.json here"
    truth.json               # the known post-hoc answer, beside verify.py and NOT under fixtures/
    fixtures/                # empty scaffold — only fixtures/ is staged, so truth.json is unreachable
    verify.py
```

Arms: the armed arm mounts the research plugin (`[plugins] mount`), the bare arm is a
single-provider deep-research run with the same tool budget and no mount. **The armed arm's mount is
MCP-served**, which is exactly the configuration that produced the recorded 100%-on-an-unarmed-arm
result — so `fathom verify-arming` is not optional here, and its allow-list must permit
`mcp__plugin_<plugin>_<server>` (not `mcp__<server>`).

### Cost plan

| | |
|---|---|
| Matrix | 2 arms × 10 questions × 3 repeats = **60 trials** |
| Per-trial | a fan-out research run is the most expensive trial shape in the corpus — the armed arm makes several provider calls per trial. Expect **$1–4/trial armed**, $0.30–1 bare |
| **Estimated** | **$40 – $150**, most likely ~$70 |
| Dry-run ceiling as printed today | 60 × $2.00 = $120 (which, unusually, **under**-states the armed arm) |
| Additional | the armed arm bills a second provider account, which fathom's `cost_usd_est` does not see at all — the USD column will understate the armed arm by construction. Record provider-side cost separately or the 8.8× comparison is unmeasurable |
| Free preconditions | `fathom validate`, `fathom verify-arming` (mandatory here), `--dry-run` |

**This is the most expensive item across the four gates and it exceeds a single wave's budget.** It
also needs a question set with known post-hoc answers, which does not exist and is the real
long-pole. **Recommendation:** author the question set first as a separate, unpaid deliverable; the
bank and the run follow only once ten questions with defensible post-hoc answers exist.

---

## What both skeletons share, and what to copy from this wave

1. **Run the free gates first.** `fathom validate <bank>` and `fathom verify-arming` cost nothing
   and a fraction of a cent respectively, and both caught real defects this wave — including two in
   the checks themselves.
2. **Pilot before the matrix.** `--limit` is scenario-major, so a small `--limit` pilot spends its
   whole budget on the first arm; use a low `--repeats` instead to get one trial per arm.
3. **Set `--max-budget-usd` from an observed figure, not a guess.** This wave lost $2.04 to a
   per-spawn cap set below the arm's actual need: the trial errored at the cap, scored nothing, and
   the money was spent anyway. Measure one trial at the default cap, then set the rail.
4. **Neither gate is settled by a null.** Both decisions are retirements, so the outcome the
   decision wants and the outcome a broken instrument produces are the same outcome. Report the
   interval, not the point.
