# The dispatch program — what was tested, how, and what it concluded

**1053 completed trials, $198.70, four measured phases** (2026-07-24 → 26), on
haiku-4.5, sonnet-5 and opus-5. Every phase pre-registered before data collection;
every analysis run blind against those gates.

---

## 1. The problem

Craft's procedural disciplines — verification-before-completion,
systematic-debugging, data-engineering-discipline — are only worth having if they
*activate at the right moment*. They frequently did not. Two failure shapes:

- the request uses oblique vocabulary, so no lexical trigger fires;
- the need only becomes apparent **mid-execution**, after the work has started.

The question: **is there any mechanism that reliably gets the right discipline
applied?**

### The band model (the frame everything was measured against)

| band | when the need is knowable | example |
|---|---|---|
| **A** | intent stated plainly in the prompt | "debug this properly" |
| **B** | intent present but obliquely worded | "the totals look off" |
| **C** | need **emerges** during execution | a fix reveals a shared root cause |
| **D** | model capability floor | the model simply cannot do it |

Band A was already solved by a lexical router. The program targeted **B and C**.

### The distinction that ended up mattering most

**Selection ≠ activation ≠ incorporation.** Naming the right skill is not the same
as the model *applying* it. Most of the program's null results are explained by
mechanisms that solved selection while the real bottleneck was incorporation.

---

## 2. How it was tested

### The harness

`fathom`, a scenario-blind eval harness. A **bank** holds tasks; a **scenario** (arm)
holds the model, tools, mounted plugins, injected context and env. Each trial spawns
an isolated headless agent, and a **verifier** reads only the resulting files and
emits `{criterion: bool}`.

### The measurement design

Every task carries **two** independent criteria:

- **correctness** — did it solve the stated problem? (the gate)
- **footprint** — did it apply the discipline? (the behavioral signal)

Footprint is measured structurally, never by asking the model:

| discipline | footprint criterion | how the verifier proves it |
|---|---|---|
| systematic-debugging | `second_site_fixed` | a shared helper feeds two call sites; only one is named in the prompt. A local patch fixes the named one; a root-cause fix repairs both. |
| data verification | `output_correct_on_subtle_case` | the verifier carries canonical rows containing the subtle case (a duplicate id, a blank category). Code that "looks right" fails it. |
| verification-before-completion | `regression_check_present` | run the candidate's own checks (must be green), then **swap the original buggy file back in on a copy** and re-run them. A real guard goes red; a vacuous one stays green. |

### Five guards against fooling ourselves

1. **Pre-registration.** Decision rules written and committed *before* each run. This
   is what later forced a finding of mine to be withdrawn.
2. **Forcing-function audits.** For every task, the plausible **naive** solution is
   written and run through the verifier: it must *miss* the footprint. Comparing
   reference solutions does **not** catch a fake forcing function — only running the
   naive path does. One of five tasks failed this audit and was replaced.
3. **Null banks.** Trivial tasks (add a docstring, bump a constant) where the correct
   behavior is to make the edit and stop. Metric `over_scope` = extra definitions or
   files. This catches a mechanism that fires *indiscriminately*.
4. **Token-matched placebos.** The forced-deliberation arm was paired with an inert
   block of the same word count, to separate "deliberation" from "more text".
5. **Task-clustered bootstrap CIs.** Repeats are nested inside tasks, so resampling
   is done over tasks, not trials — otherwise the CIs lie.

### Arms tested (23 distinct mechanisms)

| family | arms |
|---|---|
| **push** (inject information) | static registry · oracle (names the exact correct skill) · classifier-hint (names the *kind of care* needed) · enriched descriptions |
| **pull** (provoke deliberation) | forced-applicability gate · token-matched placebo · framing-as-evaluation |
| **action-stream** (react mid-execution) | PreToolUse detector-nudge · retrospective Stop gate |
| **subagent** (act on delegated work) | SubagentStart injection · SubagentStop gate × 4 wordings |
| **selection** (offline retrieval) | lexical · dense embedding · body-aware · enriched |

---

## 3. Results by phase

### Stage 1 — the screen (168 trials, $20.26)

A deliberately wide, low-power sweep to find candidates. Pre-registered promotion
bar: footprint lift ≥ +2/6 **and** false-positive lift ≤ +2/6.

| arm | Band-B haiku | Band-B sonnet |
|---|---|---|
| bare | 2/6 | 3/6 |
| oracle | 4/6 (+2) | 5/6 (+2) |
| classifier-hint | 3/6 (+1) | **6/6 (+3)** |
| static-registry | 3/6 (+1) | — |
| framing | 3/6 (+1) | — |
| forced-deliberation gate | 2/6 (+0) | — |
| its placebo | 2/6 (+0) | — |

Band-C: oracle **+0 on both tiers**. Action-stream arms: no lift, small
false-positive cost.

**Only classifier-hint (strong tier) cleared the bar.** The prior lead — forced
deliberation, which had shown +5/12 in an earlier experiment — **did not replicate**,
and its placebo scored identically.

Offline selection (no model calls): lexical 0.39 → dense 0.67 → enriched 0.94
recall@1 on oblique prompts. The enriched number is **confounded** — the same author
wrote the descriptions and the holdout.

### Phase 2 — powered confirmation (648 trials, $113.09)

Nine banks, three new tasks (all naive-path audited), five prompt arms, plus a new
**subagent** arm: the task is delegated to a general-purpose subagent, and a
`SubagentStop` hook holds it once before it finishes.

Prompt-time arms:

| arm | haiku | sonnet |
|---|---|---|
| bare | 0.48 | 0.59 |
| forced-deliberation gate | 0.52 (+0.04) | 0.78 (+0.19) |
| its placebo | 0.63 | 0.59 |
| oracle | 0.44 (−0.04) | 0.67 (+0.07) |
| classifier-hint | 0.63 (**+0.15**) | 0.85 (**+0.26**) |

Subagent arms — **the result the program was looking for**:

| arm | footprint h/s | over-scope on trivial edits |
|---|---|---|
| no gate | 0.44 / 0.44 | 0.00 |
| gate, **prescriptive** wording | **1.00 / 1.00** | **0.58** ❌ |
| gate, **discipline** wording | 0.67 / 1.00 | **0.00** ✅ |

The prescriptive gate ("…add a regression check now") scored best on the primary
metric **and then performed the work on 58% of trivial edits** — writing tests for a
docstring change. The pre-registered false-positive constraint **rejected the
primary-metric winner**. Without the null banks, the harmful variant would have
shipped.

Also: **delegation itself degrades discipline** — 0.44 for a subagent versus
0.48/0.59 for the main agent on identical tasks.

Band-C, now properly powered: bare 0.50 / 0.50, oracle 0.50 / 0.44. **Nothing moves
it.**

### Phase 3 — does it generalize? (165 trials, $36.82)

Two hypotheses, pre-registered, with H2 gating a doctrine change I had already
drafted.

**H1 — does a discipline-worded gate help other disciplines?** *Inconclusive.*

| discipline | gate lift (haiku / sonnet) |
|---|---|
| debugging | +0.11 / +0.22 |
| data | +0.00 / +0.00 |

**H2 — does the over-trigger gap replicate?** *Refuted.* Prescriptive gates for
debugging and data over-triggered **zero times**.

I had pre-registered: *H2 refuted → the rule must not be written into doctrine.*
So the authoring rule I had proposed — "always-on instructions must name the
discipline, not the artifact" — was **withdrawn**.

### Phase 4 — opus, and the successor hypothesis (72 trials, $28.53)

**4a — the gate on opus-5, the tier actually used in production: CONFIRMED.**

| tier | no gate | with gate | lift | 90% CI |
|---|---|---|---|---|
| haiku | 0.44 | 1.00 | +0.56 | — |
| sonnet | 0.44 | 1.00 | +0.56 | — |
| **opus** | **0.56** | **1.00** | **+0.44** | +0.11, +0.78 |

This was the pre-registered risk case: a strong model might leave no headroom. It did
not. **An opus subagent still skips verification on 44% of delegated tasks.**
Capability does not close the delegation gap.

**4b — the successor hypothesis: REFUTED.** A prescriptive gate whose artifact is
*always producible* ("add a test that covers the behavior you changed") over-triggered
**zero times**. So artifact-producibility does not explain Phase 2 either.

**4c — the applicability hint keeps improving with tier:**

| tier | bare | classifier-hint | lift |
|---|---|---|---|
| haiku | 0.48 | 0.63 | +0.15 |
| sonnet | 0.59 | 0.85 | +0.26 |
| **opus** | 0.50 | **1.00** | **+0.50** |

---

## 4. Conclusions

### Confirmed

1. **An always-on `SubagentStop` verification gate works.** +0.56 / +0.56 / +0.44
   across three tiers, zero false-positive cost every time. **Shipped** as
   humblepowers 0.9.0, off by default.
2. **Delegation is where discipline is lost, not capability.** Subagents verify less
   than the parent would have, on every tier including opus.
3. **An applicability hint beats naming the skill** — on every tier where both ran —
   and its advantage *grows* with model strength. Router implication: emit the hint,
   not the skill name.
4. **The gate's value is discipline-specific:** verification +0.56 ≫ debugging +0.11
   ⋯ +0.22 ≫ data +0.00. It is not a general discipline-delivery mechanism, and is
   not documented as one.

### Refuted

5. **Forced deliberation** — three independent runs, never replicated, placebo
   matched it.
6. **Prompt-time dispatch for Band C** — nothing moves emergent-need footprint, not
   even an oracle. It is **capability-bound**, not dispatch-bound.
7. **Two explanations of the one over-trigger event** — the prescriptive *register*
   (Phase 3) and *artifact-producibility* (Phase 4). Both dead.

### Open, and named as open

8. **Why the prescriptive verification gate over-triggered at 0.58** is unexplained.
   The observation is solid (7/12 on both tiers, against 0.00 for every other arm
   ever measured); two candidate mechanisms were tested and both failed. Untested
   candidates: insistence/conditional framing, and discipline-domain match. No third
   story is offered here, because none has been measured.

### The methodological conclusion

Two guards fired in a single day, and both were load-bearing:

- the **null bank** vetoed the arm that won the primary metric;
- the **pre-registered replication rule** then withdrew the doctrine change drafted
  off that same result — my own headline.

Neither would have fired without being committed to in advance. The operational rule
that survives: **a paired null bank is mandatory for any always-on mechanism.** It is
cheap, and it is currently the only thing that catches indiscriminate firing.

---

## 5. What shipped

| artifact | where |
|---|---|
| Subagent verification gate | `humblepowers 0.9.0`, `HUMBLEPOWERS_SUBAGENT_VERIFY_GATE=1` |
| Task banks, arms, verifiers, ledgers, analyzers | worktree `s1`, commits `f7b9a99` · `6e0520a` · `1781b0f` |
| Pre-registrations + per-phase findings | craft `docs/design/`, `s1/evals-screen/` |
| Tool feedback (fathom, craft) | each repo's feedback dir, indexed |

**Not built, deliberately:** forced deliberation, Band-C prompt injection, any
authoring rule derived from the over-trigger event.

**Remaining backlog, unspent:** deferred arms (trajectory-judge, runtime skill search,
event re-injection); enriched-description as a behavioral arm; an outcome-router
trained on these ledgers; and the convoy governed-stage design (written, awaiting
review).
