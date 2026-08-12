# verification-before-completion vNext — proof attempt, and what it could and could not decide

- **Date:** 2026-08-11. **Branch:** `eval/verification-lift`.
- **Banks:** `verif-lift-bug-v1`, `verif-lift-data-v1`, `verif-lift-trunc-v1`, `verif-lift-null-v1`,
  `verif-lift-bug-strong-v1`, `verif-lift-data-strong-v1`.
- **Arm added:** `skill-vnext` — built, armed, gated, dry-run. **Trials bought: 0.**
- **Headline:** the vNext arm was prepared and proved armed, and **not one decisive cell was
  measured**, because the paid-run serialization lock was held for the entire window by the
  sibling MAP matrix. Every vNext verdict below is therefore *not-proven* or *not-measurable*.
  Nothing here licenses shipping the vNext body, and — the more important half — **nothing here
  licenses stripping anything from the shipped skill either.**
- **Revised 2026-08-11 after referee review.** Six findings were wrong or missing and are corrected
  in place, each marked where it lands: the pre-registered non-inferiority margin **cannot pass at
  any funded n** (§3); the intervals were **unpaired beside a paired test** (§3); the n=6 power row
  was **overstated into an absolute** (§3); the TRUNC ceiling is an **authoring defect, not a
  property of the class** (§3, §5); the cost-to-finish table was **left in floor units while
  spend-to-date was corrected** (§7); and the reason given for forking a new arm — a longitudinal
  `config_hash` — **did not exist**, while the live hazard it masked did (§2). Two caveats that
  bound every number here were absent and are now stated: the body is **not mounted in the
  subagent**, and the `skill` arm is **not the skill as installed** (§8). The shipped
  `SubagentStop` gate's own proof obligation is **undischarged**, and this report now says so (§5).
- **Revised again 2026-08-11 after a second locked-out window.** A closing pass re-ran
  `analyse_vnext.py` against the ledgers and **bought nothing**: the serialization lock was held for
  that window too, so the per-cell table in §3 is byte-unchanged and every verdict in §4 stands
  exactly as written. Two things did change, both from free measurement. First, the full
  pre-registered decision tree is now walked branch by branch, **Branch G included** (§5) — and no
  branch fires, because every branch's precondition is an unbought cell. Second, and the reason
  this revision exists at all: the strong-tier gate arm behind the inherited **+0.44** was mounted
  and **never delivered its treatment** (§5a). That is a fact about delivery, not about effect, and
  it re-scopes what is worth buying rather than deciding anything. §7's stated mechanism for the
  ×3.81 economy bias is also **refuted as stated**, while the undercount itself survives by a
  different route.
- **Revised 2026-08-12 after a third window that also bought nothing — and this time the lock was
  not the reason.** The blocker moved: the paid block was never entered because `fathom smoke`
  failed its two authentication checks twice, ~30 s apart, on an expired OAuth session, and the
  stop rule is *auth failure = stop* (§6). The serialization lock was **acquired on the first poll**
  and released 57 s later holding zero trials — so this report's previous claim that *"the lock is
  now the binding constraint on the whole programme"* is **refuted by measurement**, and §9's first
  open decision is reclassified accordingly. Nothing was appended to any ledger, so **§3's table,
  §4's verdicts and §5's tree are byte-unchanged**; the tree was re-walked in full and still returns
  **UNRESOLVED**, with Branch G still not firing. Two free corrections did land, both in §7: the
  per-arm floor list **double-counted** weak/BUG's four runs inside weak/TRUNC's fourteen, because
  the analyzer grouped economy on `config_hash` alone and `bare` resolves to one hash in both banks
  — the instrument is fixed and the figures below are corrected. And the staged buy plan's paired
  contrast is now **verified rather than assumed** (§7).

---

## 1. What was asked, and what happened

The task was to add a `skill-vnext` arm carrying the shipped vNext body, verify its arming,
dry-run it, and buy the cells the plan marks decisive under the serialization lock, then report a
three-arm per-cell table with a verdict per claim and the DECISION-TREE outcome.

The free half completed. The paid half did not:

| step | outcome |
|---|---|
| build the arm from the craft body | done — provenance verified by hash, §2 |
| `fathom validate --strict` × 6 banks | **258 pass / 0 fail / 0 warn / 0 unverifiable** |
| `fathom verify-arming` × 3 new arms | **ALL VERIFIED** (`body_bytes=5192` reaching spawn argv) |
| `fathom run --dry-run` × 6 blocks | 80 trials planned, 0 already done |
| take the serialization lock | **never acquired** — held throughout, §6 |
| buy the decisive cells | **not done, $0 spent on the matrix** |

The lock was held by `holder=verification-lift MAP matrix (bare+skill)` from 20:19:48Z. Six
ten-minute retry cycles were run per the serialization rule. The lock was still held at the end.

## 2. The arm, and why it is a new one

`scenarios/verif-lift-assets/arm-skill-vnext.md` is the measured `skill` arm's head — the
delegation preamble and the 14-word framing line, asserted byte-identical in the build — followed
by the **shipped** vNext body:

```
source  craft-collection evals/arms/verification-vnext/verification-before-completion/SKILL.md
commit  609f6ef        file sha256 f3dbe66393a16606a4ea4929a8962c9097ba9a95cd3060706a8081cd4b48fc27
body    787 words, 4740 bytes, sha256 d25b2c7acce14ffc360ded74b0f1360e63a405e94973192bac79b8a1790f1cfc
```

The file hash matches the implementer's declared hash exactly. Because both arms carry the same
head, `skill-vnext − skill` is the body diff alone.

**A `vnext` arm already existed and was deliberately not used.**
`scenarios/verif-lift-{bug,data,trunc,null}/vnext.toml` injected the body the *plan projected*
(796 words, sha `7de774de…`). That is not what shipped: the two bodies differ in four places,
including two of the three table rows under test — the shipped body renames `Data output right`
to `Data output correct`, replaces `A cited file says X` with `Doc/report claim accurate`, and
adds a `references/non-vacuity.md` pointer to gate step 3 that the draft did not have. Measuring
that arm would have measured a draft nobody will ship. That reason is sufficient and it is the
only one that holds.

**Correction to this report's first revision.** It also claimed that "editing it would have forked
a longitudinal `config_hash` the ledger keys on". **There was no longitudinal history to fork.**
Every trial in every verif-lift ledger is scenario `bare` or `skill` — 37 runs, zero `vnext` — so
that arm's `config_hash` had never appeared in a ledger line. The claim dressed a free choice as a
constrained one.

**And it left a live hazard unflagged, which this revision removes.** Those four `vnext.toml` files
sat in the very directories a full 5-arm matrix passes to `--scenarios-dir`, so the next run would
have silently bought the 796-word draft. With zero trials behind them there was nothing to
preserve: **the four scenario files and the `arm-vnext.md` asset are deleted**, and `skill-vnext`
— carrying the shipped body — replaces them. Git history holds the draft. The three `skill-vnext`
scenario directories are new and **no other existing scenario file was touched.**

## 3. The three-arm per-cell table

Arms run the same tasks, so every contrast is paired and read with exact McNemar. `n` is tasks
scored in every arm present. The `skill-vnext` column is empty in every row for the reason in §1.

> **Re-run at the close of the second window and again at the close of the third — unchanged both
> times.** `analyse_vnext.py` was executed against the ledgers after each blocked window. The
> ledgers still hold **37 runs, all `bare` or `skill`** — 4 in weak/BUG, 20 in weak/TRUNC, 13 in
> weak/NULL — so every figure below is the same figure, and the analyzer still reports weak/DATA,
> strong/BUG and strong/DATA as **NO TRIALS IN LEDGER** rather than as nulls. Neither pass appended
> a line; the distinction between *unmeasured* and *measured null* is preserved in the instrument,
> not just in the prose. The third pass verified the ledgers byte-unchanged before reading them
> (74 lines: 37 `run` records and 37 `trial` records) rather than inferring it from the analyzer's
> own output.

> **Instrument correction.** The intervals in the table below were computed with the Newcombe
> *hybrid* interval for two **independent** proportions — printed beside an exact McNemar p, on
> arms that run the same tasks. The test was paired and the interval was not. `analyse_vnext.py`
> now computes **Newcombe's correlated-proportions interval** (`newcombe_paired`), which is the
> matching instrument and is materially narrower whenever the pairing is estimable.
>
> **The printed numbers below do not change**, and the reason is worth stating rather than hiding:
> in all four of these rows one margin is degenerate (an arm at 100%), so the correlation is not
> estimable, φ̂ falls back to 0, and the paired interval coincides with the unpaired one. The
> correction bites on every non-ceilinged cell this program has yet to buy — on mid-rate cells with
> realistic positive correlation it removes roughly a fifth to a third of the width — and it
> matters most for the one-sided non-inferiority read, which is where an interval of the wrong
> width turns into a wrong verdict.

| tier | class | criterion | n | bare | skill | **skill-vnext** | skill−bare | 95% CI | McNemar |
|---|---|---|---|---|---|---|---|---|---|
| weak | TRUNC | **`defect_past_slice_handled`** | 10 | 9/10 (90%) | 10/10 (100%) | **not run** | +10.0 | [−18.9, +40.4] | 1.0000 |
| weak | TRUNC | `spec_met` | 10 | 10/10 (100%) | 10/10 (100%) | **not run** | +0.0 | [−27.8, +27.8] | 1.0000 |
| weak | NULL | **`scope_respected`** | 6 | 6/6 (100%) | 6/6 (100%) | **not run** | +0.0 | [−39.0, +39.0] | 1.0000 |
| weak | NULL | `spec_met` | 6 | 6/6 (100%) | 6/6 (100%) | **not run** | +0.0 | [−39.0, +39.0] | 1.0000 |
| weak | BUG | **`regression_check_present`** | — | 0/4 (0%) | **not run** | **not run** | — | — | — |
| weak | BUG | `spec_met` | — | 4/4 (100%) | **not run** | **not run** | — | — | — |
| weak | DATA | **`regression_check_present`** | — | **not run** | **not run** | **not run** | — | — | — |
| weak | DATA | `output_correct_on_subtle_case` | — | **not run** | **not run** | **not run** | — | — | — |
| strong | BUG | **`regression_check_present`** | — | **not run** | **not run** | **not run** | — | — | — |
| strong | DATA | **`regression_check_present`** | — | **not run** | **not run** | **not run** | — | — | — |

Two facts in that table matter more than the empty column.

**The two cells that finished are ceilinged in the `skill` arm.** TRUNC is 10/10 and NULL is 6/6
on their primary criteria. A criterion already at 100% cannot show a lift for *any* body change;
it can only show a loss. So even a fully-bought vNext arm could not have produced a positive
result in either cell **as this bank is currently authored**.

**But the TRUNC ceiling is an authoring defect, not a property of the class** — and the first
revision of this report called those cells "downside checks, permanently", which generalised a
fixable wording bug into an impossibility. All 11 TRUNC instructions end:

> *"The package README states the rule this module is meant to follow. Bring the module into line
> with it."*

The README covers **both** functions. `tasks/verif-lift-trunc-v1/trunc-bounds/fixtures/README.md`
states the closed-interval rule for `lower_bound` **and** `upper_bound` — and `upper_bound` is the
planted twin, at line 29 of the module. So the instruction hands the agent a document describing
the twin's correct behaviour and then directs whole-module conformance, which is precisely what
`defect_past_slice_handled` scores. **`bare` at 9/10 is the expected result of obeying the
instruction, not a capability ceiling.** The repair is to scope the instruction to the cited
symptom and the named function; it is recorded in the bank README and not applied here, because
changing task text requires a `dataset_version` bump that would orphan the 20 bought trials.

NULL's 6/6 is a different matter: `scope_respected` is a false-positive guard, and 100% is the
*desired* reading, not a ceiling on an effect. It is a downside check by construction.

**The one cell with real headroom is the one whose comparator is missing.** On weak/BUG the bare
arm is 4/4 on `spec_met` and **0/4** on `regression_check_present` — fixing the bug and leaving no
regression check, which is exactly the fix-without-check contrast the program was built to
measure. The `skill` arm was never run there, so the headroom is visible and unexploited.

### Power, computed before the spend

Exact McNemar reaches p<0.05 only at six discordant pairs all in one direction:

| n | minimum detectable paired difference |
|---|---|
| 40 (BUG+DATA pooled) | 15 pp |
| 20 | 30 pp |
| 12 | 50 pp |
| 10 | 60 pp |
| 6 | **100 pp — only a total flip** |
| ≤5 | not detectable at any effect size |

**The n=6 row is corrected.** The first revision printed "not detectable at any effect size",
which is false. The generator, `mdd_pp()`, returns **100 pp** at n=6 — a real, if brutal,
detectable difference: six discordant pairs all one way gives exact-McNemar p = 0.031. Confirmed by
enumeration: at n=6 against a lift of 0.99 the exact power is **0.941**. The script's honest "100
pp" had been editorialised into an absolute. The function was itself conflating two cases — it
returned `100.0` both for "detectable only by a total flip" and for "not detectable at all" (which
begins at n≤5) — and now returns `None` for the latter so the two stay distinguishable.

At n=1 repeat this design resolves only large effects. The `+10.0` on TRUNC and the `+0.0` on
NULL are **not** evidence of no effect; they are intervals so wide they exclude almost nothing.

### The pre-registered non-inferiority gate cannot pass at any funded n

Independently of whether any trial is bought: the vNext body's non-inferiority margin is **−10 pp**,
read one-sided off the interval's lower bound. Recomputed with the analyzer's own interval, at a
**perfect tie** — the most favourable data the test can ever see:

| n | lower bound at 100% vs 100% | clears −10 pp? |
|---|---|---|
| 6 | −39.0 pp | no |
| 10 | −27.8 pp | no |
| 12 | −24.3 pp | no |
| 18 | −17.6 pp | no |
| 20 | −16.1 pp | no |
| 24 | −13.8 pp | no |
| **35** | **−9.9 pp** | **first n that clears** |

The plan funds weak BUG at K=18; the bank holds 20 non-holdout BUG tasks; the finish plan in §7
buys n=20 per class. **The obligation therefore fails regardless of the data** — a gate that
cannot pass, which is the mirror image of the vacuous gate this discipline exists to refuse. This
report's own table proves it: *weak TRUNC `spec_met` 10/10 vs 10/10 → +0.0 [−27.8, +27.8]* — a
perfect tie scored as a failure.

The feasibility bound above is read at the **all-pass tie**, which is the configuration this bank's
ceilinged cells actually occupy and the one where φ̂ is not estimable, so the paired and unpaired
intervals coincide and the number does not depend on which instrument is used. That matters,
because Newcombe's method 10 **degenerates at φ̂ = 1** — a perfectly concordant tie at a mid rate
returns a zero-width interval, which would trivially "pass" any margin. No feasibility or
non-inferiority claim in this report is read off that configuration, and none should be.

`analyse_vnext.py` now checks feasibility before reading the bound and reports such cells as
**undecidable**, never as a non-inferiority failure. Fixing this is a pre-registration decision —
re-register the margin, re-register n, or withdraw the displacement — and it belongs to the
operator, not to an analysis pass. It must not be fixed by dropping the margin after seeing data.

## 4. Verdict per claim

The body diff is seven changes. Each is mapped to the criterion that could move it, and the
mapping is grounded in the verifiers' source (`tasks/verif-lift-*/_lib/proxy.py`), which emits
exactly `spec_met`, `regression_check_present`, `proxy_instrument_ok`,
`output_correct_on_subtle_case`, `defect_past_slice_handled`, `scope_respected` — and nothing else.

| id | change | criterion that could move it | verdict |
|---|---|---|---|
| D1 | gate step 3: the `$?`-after-a-pipe procedure → `references/non-vacuity.md` | none exists | **not-measurable** |
| D2 | seen-red section: failure examples + inverse-edit rationale → pointer, bright line kept | `regression_check_present` (BUG, DATA) | **not-proven** — cell never bought |
| D3 | finishing: baseline-capture procedure → pointer | none exists | **not-measurable** |
| A1 | new row *A check ran → the count of units it saw, non-zero* | `defect_past_slice_handled` (TRUNC) | **not-proven** — cell ceilinged as authored; the ceiling is repairable, §3 |
| A2 | new row *Data output correct → a hard case named and its value written before the fix* | `output_correct_on_subtle_case` (DATA) | **not-proven** — cell never bought |
| A3 | new row *Doc/report claim accurate → the cited span read whole* | `defect_past_slice_handled` (TRUNC) | **not-proven** — cell ceilinged as authored; the ceiling is repairable, §3 |
| A4 | finishing: "or a jumped runtime" | none exists | **not-measurable** |
| — | the three additions as a group (false-positive risk) | `scope_respected` (NULL) | **not-proven** — and undetectable at n=6 |
| X1 | "the vNext body is smaller" (the plan's 790 → ~720) | direct measurement, no trial needed | **refuted** — see below |

**Not one verdict in that table moved at the third window, and the reason is the table's own
subject matter.** Every verdict except X1 is keyed to a trial in a cell, and no trial was bought:
D2 needs weak/BUG or weak/DATA `skill`+`skill-vnext`, which remain unbought; A2 needs weak/DATA,
which has **no trials at all**; A1 and A3 need weak/TRUNC, whose `skill` arm is ceilinged as
authored; and the over-scope read — the three additions as a group against `scope_respected` —
needs weak/NULL at an n that can resolve it, where the minimum detectable difference is still
100 pp at n=6. X1 was settled by direct measurement of the two bodies and needed no trial, which is
exactly why it is the only one settled. **A verdict that cannot be reached is left unreached
here.** Restating "not-proven" is not the same as narrowing it, and the temptation at a third
blocked window is to let the repetition read as convergence. Measured with the
same instrument for both bodies: shipped 790 words / 4775 bytes, vNext 787 words / 4740 bytes.
The body shrinks by **3 words and 35 bytes, 0.7%**. The plan projected ~720 words. The
displacement pays for the additions almost exactly and buys no headroom, which independently
confirms the implementer's arithmetic and the bank README's recorded deviation. Any
non-inferiority test of this body is a test of a body *the same size* as the one it replaces —
so "we made it smaller" is not a claim the skill or its changelog may carry.

### A1 and A3 cannot be separated by this program even if bought

A TRUNC task hands the agent a symptom citing `ranges/bounds.py:1-23` and plants the twin defect
at line 29 — a `file:lo-hi` citation ending mid-structure, which is verbatim the "not sufficient"
cell of the A3 row, while an incomplete scan is what A1 addresses. One criterion is moved by two
of the additions. A movement on TRUNC would have been evidence for {A1, A3} jointly and for
neither alone. Recorded here because it is a property of the bank, not of this run.

## 5. The DECISION-TREE outcome

### The pre-registered tree, walked branch by branch

The plan's tree is read **Gate 0 first, then the branch that matches**. Walked in full, so that the
absence of a firing branch is on the record as a reasoned outcome rather than an omission:

| step | precondition | fires? | why |
|---|---|---|---|
| **Gate 0** | is the cell interpretable? | **partly** | weak/TRUNC `skill` 10/10 and weak/NULL `skill` 6/6 are ceilinged ⇒ no lift claimed from either, in either direction. weak/BUG has headroom (`bare` 0/4) but no comparator. Every other cell is unbought. |
| **A** | H2 holds: strong-tier `skill+gate` − `skill` ≥ +0.15, FP clean, beats placebo | **no** | no strong-tier trial exists; no gate trial exists; no placebo trial exists. |
| **B** | H2 fails **and** strong-tier bare is genuinely failing (A0 fail ≥ 0.25) | **no** | H2 unmeasured, and the strong-tier bare arm was never run, so its fail rate is unknown. |
| **C** | H2 fails **and** strong-tier bare is ceilinged | **no** | same — neither conjunct is measured. |
| **D** | H4 ~0 (body does nothing) **and** H1/H2 hold (gate does) | **no** | H4's decisive cells (BUG, DATA) are unbought; H1/H2 have no gate trials. |
| **E** | H4 ≥ +0.15 (the body itself moves the footprint) | **no** | the two bought cells are ceilinged in `skill`; the one cell with headroom has no `skill` arm. |
| **F** | H6 fails: FP > +0.15 on the null bank | **no** | NULL is 6/6 vs 6/6 — no false-positive signal — but at n=6 the minimum detectable difference is 100 pp, so this is *not* a pass either. Undetectable, not clean. |
| **G** | **H3 fails: the gate ties the placebo** | **no** | **zero gate trials and zero placebo trials have ever been bought.** See below. |
| **H** | per-obligation nulls (D2, P1, N1, X1) | **partly** | **X1 fails** — the displacement is refuted by direct measurement (−3 words, not −70). D2 and P1 are unbought; N1 is untested. |
| **I** | nothing beats bare anywhere, with failing bare arms throughout | **no** | requires measured nulls across the grid; this grid is 4 cells short of one arm and 2 classes short of any arm. |

**The tree returns UNRESOLVED.** Exactly one pre-registered consequence fires anywhere in it — the
X1 leg of Branch H — and its repair is textual, not structural (§5, *Instruction to the repair pass*).

**Re-walked in full at the third window, row by row, against re-read ledgers: every cell above is
the same cell and no branch changed state.** The walk is repeated rather than assumed because a
tree whose preconditions are all unbought cells has exactly one way to change — a purchase — and
none was made. The one thing worth saying about a third identical walk is that it is *not*
accumulating evidence: nine branches that did not fire three times over are nine branches that
never had data, not nine findings of no effect.

### Branch G, stated precisely, because it is the one most likely to be misread

Branch G's consequence is severe and worth quoting: *if the gate ties the placebo, the lift is an
extra turn and not a mechanism; V2 does not ship as a discipline gate, and what ships instead is
nothing.* It is the branch that would retire the mechanism.

**It does not fire, and it does not fail to fire because the gate won.** It does not fire because
**H3 was never measured**: the verif-lift ledgers contain `bare` and `skill` scenarios only — not one
`skill-gate` trial, not one `placebo-gate` trial, not one `bare-gate` trial. A tie is a *measured
equality*; what exists here is an *absent comparison*. Reading Branch G as satisfied would convert
an unrun experiment into a refutation, which is the same error in the opposite direction from
reading a ceiling as a null.

So the disposition for the `SubagentStop` gate is unchanged and is **not** Branch G's disposition:
the gate stays **default-off and opt-in**, as it already ships, and the reason on the record is that
**G1 is undischarged in all three conjuncts** — not that it tied a placebo. Nothing ships it on.
Nothing deletes it either. Both halves are load-bearing.

**Third window: the trio that would decide G is staged, priced and still unbought.** The three arms
that discharge H3 — `bare-gate`, `skill-gate`, `placebo-gate` — are staged at **weak tier only**
(≈$3.48 corrected, per §5a's finding that a strong-tier gate cell buys an untreated treatment arm),
and they sit behind the BUG and DATA comparator blocks in the buy order. That order is deliberate
and it is the reason G is still undecided: a gate arm bought before its comparators is spend without
a contrast. So the gate's disposition **stays exactly where it is — off by default, opt-in, and
explicitly unmeasured** — and the arithmetic that would change it is $3.48 and one working
credential away, not a redesign. Recording that the decisive cell is cheap matters: it removes the
last excuse for leaving G undischarged indefinitely, and it keeps "we never bought it" from
hardening into "it must not be worth buying."

### 5a. The strong-tier gate arm was mounted and never delivered its treatment

This is the one new measurement in this revision. It is free — it reads 250 saved streams from the
prior program plus their scenario definitions, and spawns nothing — and it was re-derived
independently for this report rather than carried over.

The prior program's gate is a `SubagentStop` hook that blocks a subagent once and injects a fixed
reconsideration sentence. Its **only** delivery route is that injected text; when it fires, the
stream carries the verbatim marker `Stop hook feedback:` and the sentence itself. Counting that
marker across every gate-mounted arm, split by the plugin that was mounted so that a plugin
difference cannot be mistaken for a tier difference:

| plugin | haiku | sonnet | opus |
|---|---|---|---|
| `subagent-verify-gate` | 19/21 (90%) | 14/21 (67%) | — |
| `subagent-gate-multi` | 67/76 (88%) | 38/75 (51%) | — |
| **`subagent-generic-gate`** | **16/21 (76%)** | **10/21 (48%)** | **0/15 (0%)** |

The bottom row is a **within-plugin** contrast: the same hook, the same wording, the same repo.
Firing collapses to zero at opus — Fisher exact, opus 0/15 against haiku+sonnet 26/42 on that
plugin, **p = 0.000014**; the 95% Wilson interval on the opus rate is **[0.0%, 20.4%]**.

Three alternative explanations were checked and each is excluded by the streams themselves:

- **"The subagent never ran."** It ran. All **15/15** opus streams contain an `Agent` tool call and
  13–55 subsequent messages of subagent activity.
- **"The plugin was not mounted."** It was. The string `subagent-generic-gate` appears in **15/15**
  opus streams; the mount is visible in every one.
- **"The marker is just formatted differently at opus."** It is not there in any form. The gate's own
  sentence — *"are you actually confident this is correct"* — appears in **0/15** opus streams and in
  **16/21** haiku streams on the same plugin, alongside the marker in every haiku case.

**What this licenses, and what it does not.** It is a measurement of whether a treatment *arrived*,
not of whether it *works*. It says nothing about the gate's effect in either direction, and it is
not evidence for Branch G. Two consequences follow, and both are about design rather than verdict:

1. **A strong-tier gate cell cannot deliver its treatment on this mechanism, so buying one buys
   nothing.** The plan funds strong-tier gate arms; on this evidence that spend would purchase a
   contrast in which the treated arm is untreated. The gate trio is worth buying at **weak** tier,
   where delivery runs 76–90%, and must not be bought at strong tier as designed. Whether the
   zero-delivery is a harness property, a permission interaction, or something in how that CLI
   handled `SubagentStop` is itself unmeasured and is the precondition for any strong-tier gate work.
2. **The inherited +0.44 can no longer be cited as the gate's effect at strong tier.** That figure is
   `phase4-e1-verif-disc-sub-opus` at 9/9 on `regression_check_present` minus
   `phase4-e1-verif-bare-sub-opus` at 5/9 — two arms whose *only* declared difference is the gate
   mount, in trials where the gate never activated. The difference is real in the ledger and its
   **cause is now unexplained**; it is not refuted, and it is not the gate firing. Two further
   properties of that number belong beside it whenever it is quoted: at n=9 the exact McNemar
   floor is **p = 0.125 two-sided even in the best case** of four discordant pairs all one way, so
   it never reached significance on its own bank; and the arm mounts no skill body, so it was
   already a different contrast from the one this program measures.

**No craft edit is taken from this.** The pre-registered tree licenses changes on branch outcomes,
and no branch fired; a delivery measurement is not a branch outcome. It is recorded here, and the
citation question it raises for the published `+0.22 / +0.56 / +0.44` ladder is flagged in §9 as an
operator decision rather than settled by this pass.

### The strong-tier branch as originally asked

The instruction's branch was: *if strong-tier lift is ~0 with power, state what the skill's
trigger/guidance must say.*

**That branch is not reachable on this evidence, and the reason is not subtle: no strong-tier
trial has ever been run.** `verif-lift-bug-strong-v1` and `verif-lift-data-strong-v1` have no
ledger lines at all. There is no strong-tier lift estimate — not a null one, not a small one,
none. The precondition "~0 **with power**" is doubly unmet: the estimate is absent, and the
design's power at n=12 per strong cell would have been a 50 pp minimum detectable difference even
had it run.

So the DECISION-TREE returns **UNRESOLVED**, and the consequential instruction is a prohibition
rather than a rewrite:

1. **The skill's trigger and guidance change on the strength of this run: nothing.** No sentence
   may be added scoping `verification-before-completion` to a tier or a task class, because the
   tier × class map that would justify such scoping does not exist yet. Writing "this skill helps
   weak models more than strong ones" today would be asserting the very result the program was
   commissioned to measure and did not.
2. **If the strong cells are later bought and the lift is ~0 with power**, the correct edit is to
   the *trigger surface*, not the body: the description would need to say plainly where the skill
   earns its context — naming the tier/class where the lift is real — and drop any implication of
   uniform benefit. That edit is licensed by a measured null with a stated interval, and by
   nothing else.
3. **Two of the four weak classes cannot supply that evidence as authored — and one of them is
   repairable.** TRUNC and NULL are ceilinged in the `skill` arm. The first revision said they
   "can never supply that evidence"; that is wrong for TRUNC, whose ceiling comes from an
   instruction that points at a README describing the planted twin (§3). Repair the wording and
   TRUNC has headroom again — which matters, because TRUNC is the only class the plan built to
   test H5, P1 and V5, and retiring it would retire those obligations by accident. NULL's 6/6 is
   a false-positive guard reading its desired value, not a ceiling on an effect. Any attempt to
   establish "the skill does / does not help" should buy BUG and DATA, where headroom is
   demonstrated (weak/BUG bare 0/4), and must not read a ceiling as a null.

### The question this report did not answer: is the shipped gate allowed to ship?

The first revision answered only "should a repair pass delete this?" — correctly, *strip nothing*.
It never answered the other question, and the plan's answer to that one is **no**.

`craft` branch `feat/verification-vnext` already carries `5b2eb1a` (V1, the router rows),
`3ac471d` (V2, the `SubagentStop` gate) and `609f6ef` (0.10.0). The plan makes **V2 a full gate on
G1**: H1 or H2 at ≥ +0.15, **and** H6 (FP ≤ +0.05), **and** H3 (beats placebo by ≥ +0.10).

**None of the three was measured. Not one gate trial and not one placebo trial has ever been
bought** — the ledgers carry `bare` and `skill` only. So G1 is undischarged in every conjunct, and
undischarged here means *unmeasured*, not *unmet*.

The two facts are not in tension, and both belong in the record:

- **Nothing licenses deleting the gate.** An unmeasured mechanism is not a refuted one.
- **Nothing licenses shipping it as measured either.** The gate is in the tree ahead of its own
  gate. It is default-off and fails open, which bounds the blast radius to whoever opts in — but
  default-off is a safety property, not evidence, and the plan's obligation was not written to be
  discharged by being cautious.

The honest disposition is the one the craft CHANGELOG now carries: the gate ships **opt-in and
explicitly unmeasured in this codebase**, with the prior program's numbers named for what they are
— a different contrast (`bare+gate` − `bare`) on a different bank at n=9. V1 is unaffected: its
obligation was the offline trigger check, and that ran.

### Instruction to the repair pass

**Strip nothing.** The repair pass was to remove any provisional block the map refuted. The map
refuted no provisional block, because the map never measured the cells those blocks depend on.
The only refuted claim in this whole wave is X1 — the *size* claim — and its repair is textual,
not structural:

- **Do** remove any wording that presents the vNext body as smaller, leaner, or as buying context
  headroom, wherever it appears (plan text, changelog, commit narrative). Measured: −3 words.
- **Do not** remove the displaced procedures, the `references/non-vacuity.md` pointers, the three
  added table rows, the `SubagentStop` gate, or the router row. Each is *unmeasured*, and an
  unmeasured mechanism is not a refuted one. Deleting them on this evidence would convert an
  unrun experiment into a false negative.
- **Do not** treat the ceilinged TRUNC and NULL cells as evidence the discipline does not work.

## 6. Why nothing was bought, stated plainly

The serialization lock — one paid matrix at a time against these append-only ledgers, $120
program ceiling — was held by the MAP matrix for the whole window and never released. Six
ten-minute retry cycles were run, as the rule requires.

Partway through, the evidence said the holder was no longer spending: the MAP's `fathom.exe` and
its two python children (started 17:28) had exited, and no ledger had been written for ~57
minutes while the lock file remained. **The lock was not taken anyway.** The rule is
unconditional and carries no staleness clause, and the failure it guards against — a second
process appending to a paid ledger, or a second draw against a shared $120 ceiling — is precisely
the failure that a "the lock looks stale to me" override produces. An operator can clear a stale
lock; a subagent inferring staleness from process tables should not.

**This is the finding to act on first:** the lock file at
`…/scratchpad/fathom-run.lock` names a holder whose run has exited. It needs an operator decision
— release it and re-run this arm, or confirm the MAP is resuming.

**A second window closed the same way, and the lock is now the binding constraint on the whole
programme rather than an inconvenience.** The closing pass polled from 22:58Z to 00:52Z (~115
minutes) and never acquired: the lock was held from 22:47Z, released somewhere in a
three-minute gap after 00:11Z, and re-taken at 00:14Z under the same holder string. A third
agent queued on the same lock since ~20:20Z had also never acquired. No ledger line has been
written since 17:56Z, and **37 runs is the whole programme's spend to date.**

Two mechanical notes, because the polling discipline itself is part of the failure. A holder's
recorded `pid` is the shell subprocess that *wrote* the file and exits immediately, so a dead pid
in the lock is expected and is **not** evidence of staleness — the earlier revision's inference from
the process table was reading the wrong signal. And a 5–10 minute poll cadence is precisely the
cadence that loses a three-minute release-to-relock gap, so the politest poller starves. The
cheapest fixes, in order: a **heartbeat** (touch the lock each block) so staleness becomes decidable
rather than guessed; a **FIFO ticket directory** instead of one file, so the gap stops being a race;
and failing both, an atomic `noclobber` acquire loop at ~30 s.

### The third window: the lock was not the blocker, and this section's headline was wrong

The 30 s atomic-acquire fix was adopted for the third window, and the lock was **free on the first
poll** — acquired 08:38:40Z, released 08:39:37Z, 57 seconds, zero trials. The paid block was never
entered for an unrelated reason: `uv run fathom smoke` failed **two of its three authentication
checks**, twice, ~30 s apart —

```
[FAIL] credential-only spawn authenticates & completes
        status=infrastructure turns=1
        result='Failed to authenticate: OAuth session expired and could not be refreshed'
[FAIL] system-prompt injection reaches the model   (canary_present=False, status=infrastructure)
[FAIL] engine-boundary                             <- the one PERMITTED failure (convoy not importable)
SMOKE RESULT: SOME FAILED (5/8 checks)
```

The go/no-go rule admits ALL PASS, or 7/8 with **only** `engine-boundary` failing. This was neither,
so the stop rule fired and nothing was spent. The credential file behind the isolated spawn config
had expired; refreshing it is an operator action in the user's own session and not something an
agent may perform.

**Two corrections to what this section previously asserted.** First, *"the lock is now the binding
constraint on the whole programme"* is **refuted**: the one window that tested it acquired
immediately. Second, and the sharper lesson — the two starved windows made the lock the obvious
suspect, and it was the wrong one. Contention was real but it was never the *only* thing standing
between this programme and a purchase; a second, independent blocker sat behind it the whole time
and only became visible once the first cleared. The programme has now spent nothing across three
windows for **two different reasons**, which is worth more than either reason alone: it says the
zero is not one fixable obstacle but a thin operational path with several single points of failure,
and clearing them one at a time will keep producing windows that buy nothing.

## 7. What is banked, and what it costs to finish

Banked, free, and reusable the moment the lock clears:

- the arm (`scenarios/verif-lift-assets/arm-skill-vnext.md` + three scenario dirs), armed and
  verified on real spawns;
- `tasks/verif-lift-authoring/analyse_vnext.py`, the three-arm analysis, which reads whatever is
  in the ledger and reports empty cells as empty rather than as nulls;
- the pre-declared verdict rules, the −10 pp non-inferiority margin, the power table, and the buy
  rule: **no vNext trial is bought in a cell that lacks a `bare`+`skill` comparator** — a vNext
  trial with no comparator is not a contrast, it is spend.

Cost to finish. **The correction is applied to this table too** — the first revision corrected
spend-to-date ($3.34 floor ≈ $12.7 corrected) but left the cost-to-finish rows in floor units,
labelled "floors, not estimates" rather than multiplied. That asymmetry ran in exactly one
direction: the uncorrected column is the one that makes finishing look affordable.

| block | trials | ledger floor | **corrected (×3.81)** | note |
|---|---|---|---|---|
| weak BUG + DATA (vNext) | 40 | ~$4 | **~$15** | the decisive cells; needs the MAP's `skill` arm too |
| weak NULL + TRUNC (vNext) | 16 | ~$1.5 | **~$6** | downside checks; TRUNC's ceiling is repairable (§3) |
| strong BUG + DATA (vNext) | 24 | ~$18 | **~$69** | needs the MAP's strong arms, which do not exist |

Why the floors are floors — **and the stated mechanism is now refuted, while the undercount
survives.** This report previously explained the ×3.81 bias as: every arm delegates, so each stream
carries two `result` events (parent and subagent sidechain), and `parse_stream` keeps the last.
Measured against the **1,072** saved streams, that mechanism does not hold:

- **Delegation alone does not produce a second `result` event.** All 15 opus streams delegate
  (`Agent` tool, 15/15) and every one carries **exactly one** `result` event.
- **The second event tracks the stop hook, not the subagent.** Across the 959 plugin-mounted
  streams the coupling is near-perfect: hook fired **and** a second `result` event, 164; hook silent
  **and** a single event, 794; hook silent with a second event, 1; hook fired with a single
  event, **0**.
- **Where two events do exist, the ratio never approaches 3.81.** Across the whole corpus, 232
  streams carry more than one `result` event and all 232 carry costs on both; `sum ÷ last` runs
  **1.16 to 2.02, median 1.49** — **0 of 232 reach 3.81**.

So ×3.81 cannot have come from this mechanism on any stream in the corpus. **The undercount is
nonetheless real, by a different and probably larger route:** the ledger's per-run usage on the
delegated path records the parent's final iteration and omits the subagent's consumption outright.
The weak/TRUNC `bare` runs average **1.0 turns, 331 output tokens and 5.7 s** while scoring 10/10 on
`spec_met` for a code-fix task — work that cannot have been done in 331 parent tokens.

The practical disposition: **keep ×3.81 as the budgeting unit**, because it is conservative in the
safe direction (it over-reserves rather than overspends), and **stop publishing it as a measured
multiplier** until it is re-derived from the true mechanism. The bias is not guaranteed common-mode
across arms, so no arm-to-arm economy claim is made from these figures at all.

Recorded spend across the verif-lift ledgers stands at **37 paid runs, a $3.34 ledger floor,
≈$12.74 corrected** — $0.344/trial true against the plan's assumed $0.145. All of it is the MAP's;
this run added $0 of matrix spend and three sub-cent arming probes, and both the second and third
closing passes added **$0.00 with no paid spawn of any kind.**

**Per-arm floors, corrected — the previous list double-counted four runs.** It read: `bare`-TRUNC
`3214c0e6bbbb` **14 / $1.341** *and* `bare`-BUG `3214c0e6bbbb` **4 / $0.417**. Those are not two
arms. `bare` injects the same file in both banks, so it resolves to the **same `config_hash` in
both**, and the 14 already contained the BUG 4. The five entries summed to 41 runs and $3.76 against
a ledger holding 37 runs and $3.343 — the very total stated in the paragraph directly above, which
is how a reader could have caught it without opening a file. Recomputed per `(bank, config_hash)`:

| tier | class | arm | config_hash | runs | $ floor | $/run |
|---|---|---|---|---|---|---|
| weak | BUG | `bare` | `3214c0e6bbbb` | 4 | $0.417 | $0.104 |
| weak | NULL | `bare` | `4aa4b7da5965` | 7 | $0.443 | $0.063 |
| weak | NULL | `skill` | `5fe55a4e55d6` | 6 | $0.360 | $0.060 |
| weak | TRUNC | `bare` | `3214c0e6bbbb` | 10 | $0.920 | $0.092 |
| weak | TRUNC | `skill` | `52ffcd608665` | 10 | $1.204 | $0.120 |

Five rows, **37 runs, $3.343** — reconciling to the ledger exactly.

**The instrument, not the arithmetic, produced that error, and it is fixed.**
`analyse_vnext.py` grouped its economy table on `config_hash` **alone** and labelled each group with
a single `(tier, class)` taken from a dict that the last bank in `BLOCKS` overwrote. A hash shared
across two banks therefore merged their runs into one row and attributed the whole of it to
whichever bank came last — so **weak/BUG disappeared from the economy table entirely** while
weak/TRUNC reported 14 runs it had not bought. The key is now `(bank, config_hash)`.

Two things are worth keeping from this. The defect was **visible in this very section all along**:
the prose above reports the weak/TRUNC `bare` runs at "1.0 turns, 331 output tokens and 5.7 s",
computed on the TRUNC-only subset, while the superseded table said **1.1 turns** for the same arm on
the pooled 14 — prose and table disagreed inside one section, and the table was the wrong one. The
mismatch was there to be found at every earlier revision and no reader, this one included, followed
it up until the numbers were reconciled against the ledger deliberately. And the sharing that caused it is
not a bug to be designed away: an identical arm file resolving to an identical hash across banks is
`config_hash` **working as specified**, which is what makes the cross-bank reuse in the staged block
sound. The hash identifies a *configuration*; it was never a key for a *cell*, and using it as one
is what merged two cells. No verdict in this report moves — the economy table feeds no contrast —
but the corrected per-cell figures are the ones any future budgeting should read.

**The staged block's paired contrast is verified, not assumed.** The buy script gives the `bare` arm
`--limit 6` (it has 4 done) and the `skill` and `skill-vnext` arms `--limit 10`, which pairs
correctly only if those slices land on the *same* tasks. They do: BUG `bare`'s four completed trials
are exactly the **first four non-holdout tasks in plan order** — `bug-base-convert`,
`bug-checksum-mod`, `bug-csv-quote`, `bug-even-split` — so `--limit 6` puts `bare` on tasks 1–10,
the identical set `--limit 10` gives the other two arms. Had the done-set been scattered through the
bank instead, `--limit` would have produced a **mismatched pairing in silence**, and every paired
interval and McNemar p downstream would have been computed on arms that ran different tasks. The
analyzer intersects on task id and would have reported a smaller honest `n` rather than a wrong
number — but it would not have told anyone the block had bought half a contrast.

**The next block is staged and its reuse of the longitudinal hashes is proven, not asserted.**
Single-arm scenario directories with absolute inject paths reproduce the existing `config_hash`
values exactly — only the injected file's sha256 enters the hash, never its path — confirmed
end-to-end by `fathom run verif-lift-bug-v1 --dry-run` reporting *"16 trials (4 already done)"*
against the staged `bare` directory. Resolved: `bare` `3214c0e6bbbb`, `skill` `52ffcd608665`,
`skill-vnext` `046e6deada19`, `skill-gate` `609dea0d69b1`, `placebo-gate` `3a665058f27a`, and a new
`bare-gate` `c6c95f7080e8` — the `bare+gate` replication arm §8 records as missing. Single-arm
directories are **required**, not tidiness: `fathom run` plans scenario-major and `--limit` slices
that flat list, so a multi-arm directory with `--limit` buys one arm's entire sweep before touching
the next. The buy order is itself the buy rule — comparators land before the vNext arm, so an
interrupted block never leaves an orphan vNext cell with nothing to contrast against.

**The program's budget is denominated in a unit its own ledger understates ~3.8× on the only path
it uses.** In corrected units the plan's 368-trial grid is ≈$99 weak + ≈$124 strong ≈ **$223
against a $120 ceiling — the strong block alone exceeds the ceiling.** And the
`--max-budget-usd` rails ($10/$35/$56) are **per-spawn caps**, so nothing rails the program total;
the cumulative-cap check is the only thing that can, and it must sum ledgers ×3.81 or it will
report green throughout. Re-scoping the grid is an operator decision and it is a precondition for
the next block, not a footnote to it.

## 8. Limits that bound every future verdict from this arm

- **`references/non-vacuity.md` is not injected.** This is a system-prompt arm with no file behind
  the three pointers the vNext body adds. D1/D2/D3 are therefore tested under the pessimistic
  assumption that the displaced procedure is never recovered — and an agent that follows a
  pointer pays for a failed read. Non-inferiority measured this way would imply non-inferiority
  with the file present; the converse does not hold, and no result from this arm is evidence
  about the packaged skill's reference file.
- **The body is NOT mounted in the subagent.** `arm-skill.md` (and `arm-skill-vnext.md`) is
  appended to the **parent's** system prompt via `--append-system-prompt-file`
  (`src/fathom/adapters/claude_cli.py`), and `verify-arming`'s `body_bytes=5192` proves injection
  into the **top-level spawn only**. Delivery to the worker rests on one preamble sentence — *"The
  following working discipline applies to you and to any subagent you spawn"* — plus the parent
  choosing to relay it, while the same preamble instructs the parent to hand the subagent "the full
  task instruction verbatim" and says nothing about forwarding the discipline. So `skill` − `bare`
  measures **a parent told to relay a discipline**, not a subagent carrying the skill. That is the
  difference between this arm and the prior program's `SubagentStop` mechanism, which fires on the
  worker regardless of what the parent forwarded — and it means these two arms are not two
  deliveries of the same thing.
- **The `skill` arm is not the skill as installed.** Shipped,
  `verification-before-completion` is a plugin skill an agent must *choose* to load, and the audit
  records **zero** dispatch-router rows for it — in practice it may never load at all. This arm
  forces 4775 bytes of body into the system prompt unconditionally. A1 is therefore an **upper
  bound**: a positive on `skill` − `bare` overstates what installing the plugin delivers by
  however often the real dispatch surface fails to load it. A null on this arm is the stronger
  result of the two, because it is a null under the most favourable delivery available.
- **`skill-gate` − `skill` is not a replication of anything.** The prior program's `bare-sub` arms
  mounted **no plugins**, and their injected preamble is byte-identical (sha256 `b044b0bf…`) to
  this bank's `arm-bare.md`. Phase 2/4's headline lift is therefore `bare+gate` − `bare` — a
  contrast this bank does not contain, because every gate scenario here also injects `arm-skill.md`.
  Replicating +0.22/+0.44 needs a `bare+gate` arm that does not yet exist.
- **The strong tier is unmeasured**, so the tier × class map the program is named for does not
  exist.
- **n=1 repeat.** Nothing here separates a real effect from a single lucky trial below the
  minimum detectable differences tabulated in §3.
- **A strong-tier gate arm does not deliver its treatment** (§5a), so the `bare-gate` arm that would
  make `skill-gate` a replication is only meaningful at weak tier until that is understood. The
  arm is now staged (`c6c95f7080e8`) but its strong-tier cell should not be bought.

## 9. Open decisions this report hands to the operator

None of these is settled by the evidence above; each is recorded because the evidence changed what
the decision costs.

1. **Credentials, and the lock demoted.** ~~The lock is the precondition for every other item.~~
   **Superseded at the third window (§6).** The 30 s atomic acquire was adopted and the lock came
   free on the first poll, so contention is no longer the binding constraint — an **expired OAuth
   session** is. `fathom smoke` fails its two auth checks and the stop rule forbids entering a paid
   block on a failed smoke; only an operator can refresh the session. **This is now the precondition
   for every other item**, and the lock reforms in §6 stay worth doing on their own merits rather
   than as the unblocker they were billed as. The general form is the item to carry forward: three
   windows have bought nothing for two unrelated reasons, so the next one should expect a third
   rather than assume the path is now clear.
2. **Re-scope the grid before the next block.** In corrected units the plan's 368-trial grid is
   ≈$223 against a $120 ceiling, and `--max-budget-usd` is per-spawn so nothing rails the total
   (§7). The strong block alone exceeds the ceiling — and §5a now removes part of its motivation.
3. **The gate trio moves to weak tier — and it is the cheapest undischarged obligation on the
   board.** Delivery is 76–90% at haiku and 0/15 at opus on the same plugin (§5a), so buying the
   strong-tier gate cells as designed purchases an untreated treatment arm. Staged at weak tier the
   trio costs **≈$3.48 corrected** and is the only thing standing between G1/H3 and a verdict
   (§5, Branch G). The shipped gate has now been default-off and unmeasured across three windows;
   at that price the gap is a scheduling fact, not a funding one.
4. **The published `+0.22 / +0.56 / +0.44` ladder needs a decision, not a silent edit.** The opus
   figure's arm shows zero gate activations, and at n=9 that contrast could not have reached
   significance in any case (best-case exact McNemar p = 0.125). The plugin's README and CHANGELOG
   currently present it as the gate's measured effect at that tier. **This pass deliberately made no
   craft edit** — no pre-registered branch licensed one, and a delivery measurement is not a branch
   outcome — but the citation is now known to attribute an effect to a mechanism that left no trace
   in the trials producing it.
5. **Re-derive or retire the ×3.81 multiplier.** Its stated mechanism is refuted (§7); the
   undercount it stands for is real and probably larger. Keep it as a conservative budget unit,
   stop quoting it as measured.
6. **The non-inferiority margin cannot pass at any funded n** (§3). Re-register the margin,
   re-register n, or withdraw the displacement — an operator decision, and explicitly *not* one to
   be fixed by dropping the margin after seeing data.
