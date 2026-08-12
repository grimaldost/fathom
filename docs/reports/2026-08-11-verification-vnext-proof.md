# verification-before-completion vNext — proof attempt, and what it could and could not decide

- **Date:** 2026-08-11, extended 2026-08-12. **Branches:** `eval/verification-lift`, then
  `eval/verif-lift-decisive`.
- **Banks:** `verif-lift-bug-v1`, `verif-lift-data-v1`, `verif-lift-trunc-v1`, `verif-lift-null-v1`,
  `verif-lift-bug-strong-v1`, `verif-lift-data-strong-v1`.
- **Arm added:** `skill-vnext` — built, armed, gated, dry-run, and at the fourth window **bought**.
- **Trials bought at the fourth window: 90 runs** (floor $11.79; ≈$44.92 in the conservative
  corrected unit). weak/BUG and weak/DATA at `bare` / `skill` / `skill-vnext`, n=10 per arm, plus
  the weak-tier gate trio `bare-gate` / `placebo-gate` / `skill-gate`, n=10 each.
- **Headline:** the decisive cells were measured at last, and they decide **against the vNext body
  and against the gate, and in favour of the shipped body — with one caveat that cuts the other
  way.** The shipped `skill` body lifts the footprint criterion **+50.0 pp** at weak/BUG (3/10 →
  8/10, paired interval excluding zero) — the programme's first positive result. The vNext body
  gives most of that back (**−40.0 pp**, 8/10 → 4/10) and improves nothing anywhere: **it does not
  ship.** The `SubagentStop` gate **ties its placebo exactly** (7/10 vs 7/10) with delivery
  confirmed at 80–90%, so **Branch G fires** and the gate is not promoted — though nothing licenses
  deleting it either. The caveat: the shipped body carries a measured **−30.0 pp** on weak/DATA's
  `output_correct_on_subtle_case`, which no previous window could see.
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
- **Revised 2026-08-12 after a fourth window — the first that bought anything.** Credentials were
  refreshed, `fathom smoke` returned 7/8 with only the permitted `engine-boundary` failure, the
  serialization lock was acquired on the first poll and **released 15 s after the last paid trial,
  before any analysis**, and 90 runs were bought. **The tree now resolves: Branches E and G fire**
  (§5), D2 and A2 move from unbought to measured (§4), and the `skill-vnext` column of §3 is
  populated. Three things here are corrected *against this report's own previous text* rather than
  merely extended. First, weak/BUG `bare` was quoted at **0/4** in three revisions and is **3/10**
  once its arm is complete — the six added trials scored 3/6, so a floor of zero was an artifact of
  n=4, and the prose had begun to lean on it (§3). Second, the instrument note claimed the paired
  interval is "materially narrower whenever the pairing is estimable"; on the first non-degenerate
  cell this programme has ever bought it is **wider**, because the arms are barely concordant, and
  the defensible claim is only that it *matches* the test beside it (§3). Third, §6's title — "why
  nothing was bought" — no longer describes this report and is re-scoped to the three windows it
  does describe. One finding is genuinely new and unwelcome: the **shipped** body costs
  `output_correct_on_subtle_case` −30.0 pp on weak/DATA, a class it had never been run against
  before this window.

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

**At the fourth window the paid half completed too:**

| step | outcome |
|---|---|
| `uv sync`, `ruff format --check`, `ruff check`, `pytest` | clean; 621 passed, 1 skipped, 160 subtests |
| `fathom smoke` | **7/8 — only `engine-boundary` red**, the one permitted failure; auth checks PASS |
| `fathom validate --strict` × 2 banks bought | **66 pass / 66 pass, 0 fail / 0 warn / 0 unverifiable** |
| `fathom verify-arming` × 3 arms bought | **ALL VERIFIED** (`bare` 371 B, `skill` 5227 B, `skill-vnext` 5192 B) |
| `fathom run --dry-run` × 6 blocks | 6 / 10 / 10 / 10 / 10 / 10 — matching the staged plan exactly |
| take the serialization lock | **acquired on the first poll**, 10:44:13Z |
| buy the decisive cells | **done — 90 runs, $11.79 floor, ≈$44.92 corrected** |
| release the lock | **13:15:17Z, 15 s after the last paid trial, before any analysis** |

One block failed mid-matrix and was repaired rather than abandoned: `b2` (weak/DATA `skill`) died at
workspace staging on a Windows `git init` failure and stopped at 2/10 while its dependent
`skill-vnext` block ran to completion behind it. The comparator was completed to n=10 **before**
any contrast was read, so no cell in this report contains a vNext arm without its `bare` and
`skill` comparators. The repair used `--limit`, which counts *new* trials rather than a target
total, so that arm finished at n=12; the analyzer intersects on the 10 tasks scored in every arm,
which is why the DATA rows below read n=10.

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
scored in every arm present.

> **Fourth window: the decisive cells were bought, and the `skill-vnext` column is no longer
> empty.** 90 runs were purchased — weak/BUG and weak/DATA at `bare` / `skill` / `skill-vnext`,
> n=10 per arm, plus the weak-tier gate trio (§5b). Both classes the vNext body was authored to
> move are now measured against their comparators, in the pre-registered order, so no vNext trial
> in this report lacks the `bare` and `skill` arms of its own cell. weak/TRUNC and weak/NULL are
> unchanged and were deliberately not re-bought: both are ceilinged in `skill` (10/10, 6/6), where
> no body change can show a lift. strong/BUG and strong/DATA remain **NO TRIALS IN LEDGER** — still
> unmeasured, still not nulls.

> **The `bare` arm's headline number moved when its n moved, and that is the finding to read
> first.** The three previous revisions recorded weak/BUG `bare` at **0/4** on
> `regression_check_present` and reasoned from a floor of zero. Completing that arm to n=10 gives
> **3/10**: the four original trials are 0/4 and the six added are **3/6**. Nothing changed but the
> sample. A rate quoted from n=4 was not a small measurement of a real zero, it was an artifact,
> and the program's own prose had begun to lean on it. This is the owner's rule about underpowered
> reads demonstrated against this report's own text rather than asserted.

> **Instrument correction.** The intervals in the table below were computed with the Newcombe
> *hybrid* interval for two **independent** proportions — printed beside an exact McNemar p, on
> arms that run the same tasks. The test was paired and the interval was not. `analyse_vnext.py`
> now computes **Newcombe's correlated-proportions interval** (`newcombe_paired`), which is the
> matching instrument and is materially narrower whenever the pairing is estimable.
>
> **In the previously-bought rows the printed numbers did not change**, because in all four of them
> one margin is degenerate (an arm at 100%), so the correlation is not estimable, φ̂ falls back to
> 0, and the paired interval coincides with the unpaired one. **The cells bought this window are
> the first non-degenerate ones — and there the paired interval comes out *wider*, not narrower.**
> weak/BUG `skill`−`bare` splits 2 both / 1 bare-only / 6 skill-only / 1 neither: seven of ten pairs
> are discordant, so the arms are barely concordant at all, φ̂ is not the healthy positive
> correlation the narrowing assumes, and the paired interval [+2.2, +76.4] is wider than the
> unpaired [+6.6, +74.0] on the same counts. The earlier revision's phrasing — "materially narrower
> whenever the pairing is estimable" — described the common case as if it were the rule. The
> defensible claim is only that the paired interval is the one that **matches** the exact McNemar
> printed beside it; whether matching costs or buys width is a property of the data, and here it
> costs. The pooled row at the foot of the table is the one place the unpaired interval is still
> printed, because per-task pairing is not reconstructable across pooled cells, and it is labelled.

| tier | class | criterion | n | bare | skill | **skill-vnext** | skill−bare | 95% paired | McNemar |
|---|---|---|---|---|---|---|---|---|---|
| weak | BUG | **`regression_check_present`** | 10 | 3/10 (30%) | 8/10 (80%) | **4/10 (40%)** | **+50.0** | [+2.2, +76.4] | 0.1250 |
| weak | BUG | `spec_met` | 10 | 10/10 (100%) | 10/10 (100%) | **10/10 (100%)** | +0.0 | [−27.8, +27.8] | 1.0000 |
| weak | BUG | `proxy_instrument_ok` | 10 | 10/10 (100%) | 10/10 (100%) | **10/10 (100%)** | +0.0 | [−27.8, +27.8] | 1.0000 |
| weak | DATA | **`regression_check_present`** | 10 | 2/10 (20%) | 3/10 (30%) | **5/10 (50%)** | +10.0 | [−22.7, +40.6] | 1.0000 |
| weak | DATA | `output_correct_on_subtle_case` | 10 | 7/10 (70%) | 4/10 (40%) | **6/10 (60%)** | **−30.0** | [−50.7, −1.5] | 0.2500 |
| weak | DATA | `spec_met` | 10 | 8/10 (80%) | 7/10 (70%) | **6/10 (60%)** | −10.0 | [−31.5, +10.5] | 1.0000 |
| weak | DATA | `proxy_instrument_ok` | 10 | 10/10 (100%) | 10/10 (100%) | **10/10 (100%)** | +0.0 | [−27.8, +27.8] | 1.0000 |
| weak | TRUNC | **`defect_past_slice_handled`** | 10 | 9/10 (90%) | 10/10 (100%) | **not run** | +10.0 | [−18.9, +40.4] | 1.0000 |
| weak | TRUNC | `spec_met` | 10 | 10/10 (100%) | 10/10 (100%) | **not run** | +0.0 | [−27.8, +27.8] | 1.0000 |
| weak | NULL | **`scope_respected`** | 6 | 6/6 (100%) | 6/6 (100%) | **not run** | +0.0 | [−39.0, +39.0] | 1.0000 |
| weak | NULL | `spec_met` | 6 | 6/6 (100%) | 6/6 (100%) | **not run** | +0.0 | [−39.0, +39.0] | 1.0000 |
| strong | BUG | **`regression_check_present`** | — | **not run** | **not run** | **not run** | — | — | — |
| strong | DATA | **`regression_check_present`** | — | **not run** | **not run** | **not run** | — | — | — |

**The body diff on its own — `skill-vnext` − `skill`, the contrast this window was bought to get:**

| tier | class | criterion | n | skill | vnext | diff (pp) | 95% paired | McNemar | NI@−10pp |
|---|---|---|---|---|---|---|---|---|---|
| weak | BUG | **`regression_check_present`** | 10 | 8/10 (80%) | 4/10 (40%) | **−40.0** | [−68.5, +4.4] | 0.2188 | undecidable at n=10 |
| weak | BUG | `spec_met` | 10 | 10/10 | 10/10 | +0.0 | [−27.8, +27.8] | 1.0000 | undecidable at n=10 |
| weak | DATA | **`regression_check_present`** | 10 | 3/10 (30%) | 5/10 (50%) | +20.0 | [−3.8, +40.0] | 0.5000 | undecidable at n=10 |
| weak | DATA | `output_correct_on_subtle_case` | 10 | 4/10 (40%) | 6/10 (60%) | +20.0 | [−3.5, +38.9] | 0.5000 | undecidable at n=10 |
| weak | DATA | `spec_met` | 10 | 7/10 (70%) | 6/10 (60%) | −10.0 | [−27.6, +8.2] | 1.0000 | undecidable at n=10 |

**Pooled footprint criterion, weak tier, BUG + DATA** (unpaired interval, labelled — pairing is not
reconstructable across pooled cells): `bare` 5/20 (25%), `skill` 11/20 (55%), `skill-vnext` 9/20
(45%). `skill`−`bare` **+30.0 pp**; `skill-vnext`−`skill` **−10.0 pp**, 95% unpaired
[−37.1, +19.4].

Four facts in those tables matter, and they do not all point the same way.

**1. The shipped `skill` body does lift the footprint criterion — this is the program's first
positive result.** weak/BUG `regression_check_present` goes 3/10 → 8/10, **+50.0 pp**, and the
paired 95% interval **[+2.2, +76.4] excludes zero**. The exact McNemar is 0.1250, which is *not*
below 0.05 — at n=10 with 1 vs 6 discordant pairs the exact test cannot get there, and the floor is
a property of the design (see the power note below). So the honest reading is: the interval
excludes zero, the test does not reach conventional significance, and the two disagree because the
exact test is conservative at this n. It is evidence, not proof, and it is the strongest evidence
this program has produced about anything.

**2. The vNext body does not reproduce that lift — it points sharply the other way where the lift
exists.** On the same cell `skill-vnext` scores 4/10 against `skill`'s 8/10: **−40.0 pp**, paired
[−68.5, +4.4]. The interval crosses zero, so vNext is not *proven* worse; but there is no reading
of this cell in which vNext is better, and the point estimate is most of the shipped body's lift
given back. weak/DATA moves the other way (+20.0 pp, [−3.8, +40.0]), and the pooled result is
**−10.0 pp**. Two cells of n=10 disagreeing in sign, pooling to a small negative, is what "no
demonstrated improvement" looks like when it is measured rather than assumed.

**3. The shipped body costs correctness on the DATA class.** `output_correct_on_subtle_case` falls
7/10 → 4/10 under `skill`, **−30.0 pp**, paired **[−50.7, −1.5]** — an interval excluding zero in
the *unwanted* direction, on the criterion that asks whether the subtle case actually came out
right. `spec_met` drifts the same way (8/10 → 7/10). This was invisible while weak/DATA had no
trials, and it is the single most consequential thing this window bought: the arm the program was
trying to *promote* a successor to has a measured cost, on a class it was never previously run
against. It is one cell at n=10 with McNemar 0.2500, so it is a flag and not a verdict — but it is
a flag on the shipped artifact, not on the candidate.

**4. Non-inferiority remains undecidable everywhere, exactly as predicted before the spend.** At
the pre-declared −10 pp margin a *perfect tie* needs n ≥ 35. Every cell here is n=10. So no cell
passes or fails the pre-registered gate, and none is written as if it had.

**The two cells bought in earlier windows are still ceilinged in the `skill` arm, and were
deliberately left unbought this window.** TRUNC is 10/10 and NULL is 6/6 on their primary criteria.
A criterion already at 100% cannot show a lift for *any* body change; it can only show a loss. A
vNext arm there could not have produced a positive result **as this bank is currently authored**,
so buying one would have spent real money on a foregone conclusion. That is why this window's
budget went to BUG and DATA instead — the two classes with headroom — and why A1 and A3 below
remain unresolved rather than resolved cheaply and wrongly.

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

**The cell with real headroom now has its comparator, and the headroom was real.** On weak/BUG the
`bare` arm is 10/10 on `spec_met` and 3/10 on `regression_check_present` — fixing the bug and
leaving no regression check, which is exactly the fix-without-check contrast the program was built
to measure. Completing the comparator turned that visible headroom into the +50.0 pp of fact 1
above. Two prior revisions described this cell as the one worth buying; it was, and it is the cell
that carried this report from "nothing decided" to a decision.

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
| D2 | seen-red section: failure examples + inverse-edit rationale → pointer, bright line kept | `regression_check_present` (BUG, DATA) | **MEASURED — not supported.** BUG −40.0 pp [−68.5, +4.4]; DATA +20.0 pp [−3.8, +40.0]; pooled −10.0 pp. No improvement anywhere, and a large negative point estimate in the cell that has the lift |
| D3 | finishing: baseline-capture procedure → pointer | none exists | **not-measurable** |
| A1 | new row *A check ran → the count of units it saw, non-zero* | `defect_past_slice_handled` (TRUNC) | **unmeasured** — cell ceilinged as authored and deliberately not bought; the ceiling is repairable, §3 |
| A2 | new row *Data output correct → a hard case named and its value written before the fix* | `output_correct_on_subtle_case` (DATA) | **MEASURED — suggestive, not established.** 4/10 → 6/10, +20.0 pp [−3.5, +38.9], McNemar 0.5000; below the 60 pp detectable at n=10 |
| A3 | new row *Doc/report claim accurate → the cited span read whole* | `defect_past_slice_handled` (TRUNC) | **unmeasured** — same cell and same reason as A1 |
| A4 | finishing: "or a jumped runtime" | none exists | **not-measurable** |
| — | the three additions as a group (false-positive risk) | `scope_respected` (NULL) | **unmeasured** — still n=6, where only a total flip is detectable |
| X1 | "the vNext body is smaller" (the plan's 790 → ~720) | direct measurement, no trial needed | **refuted** — see below |

**Two verdicts moved this window, and both moved because their cells were bought.** D2 is the claim
the whole vNext exercise rested on — that turning the seen-red section into a pointer would not cost
the footprint behaviour — and it is now **measured and not supported**: no cell shows an
improvement, and the cell where the shipped body demonstrably lifts is the cell where vNext gives
most of that lift back. A2 is the one addition whose criterion exists and whose cell is now bought;
it shows a **positive point estimate that its own interval cannot separate from zero**, so it is
recorded as suggestive and explicitly not as support. The rest did not move, and the reason is
unchanged: A1 and A3 need weak/TRUNC, whose `skill` arm is ceilinged as authored, so buying them
would have purchased a foregone conclusion; the over-scope read needs weak/NULL at an n that can
resolve it, where the minimum detectable difference is still 100 pp at n=6; D1, D3 and A4 have no
criterion in any verifier and no n would change that. **Those four are written as `unmeasured`, not
as `null` and not as `not-proven` with a number attached.** X1 was settled by direct measurement of
the two bodies and needed no trial. Measured with the
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
| **Gate 0** | is the cell interpretable? | **yes, for weak BUG and DATA** | both now carry `bare` + `skill` + `skill-vnext` at n=10 with real headroom (`bare` 3/10 and 2/10 on the footprint criterion) and **zero errored trials**. weak/TRUNC and weak/NULL remain ceilinged in `skill` ⇒ still no lift claimable from either. strong/BUG and strong/DATA remain unbought. |
| **A** | H2 holds: strong-tier `skill+gate` − `skill` ≥ +0.15, FP clean, beats placebo | **no** | no strong-tier trial exists. Stronger than before: §5a shows this cell cannot deliver its treatment on this mechanism at all, so H2 is not merely unbought, it is **unbuyable as designed**. |
| **B** | H2 fails **and** strong-tier bare is genuinely failing (A0 fail ≥ 0.25) | **no** | the strong-tier bare arm was never run, so its fail rate is unknown. |
| **C** | H2 fails **and** strong-tier bare is ceilinged | **no** | same — neither conjunct is measured. |
| **D** | H4 ~0 (body does nothing) **and** H1/H2 hold (gate does) | **no — now for a measured reason** | **both conjuncts are now refuted, not absent.** H4 is not ~0: `skill`−`bare` pools to **+30.0 pp**. And H1 does not hold: at weak tier the gate adds **+0.0 pp** on `bare` and **−10.0 pp** on `skill` (§5b). |
| **E** | H4 ≥ +0.15 (the body itself moves the footprint) | **FIRES (weak tier)** | `skill`−`bare` on the footprint criterion is **+50.0 pp** at weak/BUG with a paired interval excluding zero, **+10.0 pp** at weak/DATA, **+30.0 pp pooled** — above the +0.15 threshold. This is the first branch in the programme to fire on bought data. Read with fact 3 of §3, which is the counterweight and is *not* optional. |
| **F** | H6 fails: FP > +0.15 on the null bank | **no** | NULL is still 6/6 vs 6/6 and still n=6, where the minimum detectable difference is 100 pp. Undetectable, not clean — unchanged, and not re-bought. |
| **G** | **H3 fails: the gate ties the placebo** | **FIRES** | `skill-gate` **7/10** vs `placebo-gate` **7/10** — an exact tie, +0.0 pp, McNemar 1.0000 — with gate **delivery confirmed at 80–90%** in the same streams. For the first time this is a *measured* equality and not an absent comparison. See below. |
| **H** | per-obligation nulls (D2, P1, N1, X1) | **partly** | **X1 fails** (displacement refuted by direct measurement, −3 words not −70) and **D2 is now measured and not supported** (§4). P1 and N1 remain untested. |
| **I** | nothing beats bare anywhere, with failing bare arms throughout | **no — now for a measured reason** | something *does* beat bare: `skill` beats `bare` by +50.0 pp at weak/BUG. The precondition is refuted rather than unevaluated. |

**The tree no longer returns UNRESOLVED. Two branches fire on bought data — E and G — and they are
the two that answer the two different questions this programme kept conflating.** Branch E says the
**body** moves the footprint criterion. Branch G says the **gate** does not beat a content-free
gate that costs the same extra turn. Taken together they locate the mechanism in the body and not
in the always-on hook, which is the opposite of the inherited `+0.22 / +0.56 / +0.44` reading, and
it is the first time either statement rests on trials rather than on inheritance.

**What fired is not a licence to change everything.** Both firing branches sit at n=10, where the
minimum detectable paired difference is 60 pp. Branch E's +50.0 pp clears its +0.15 threshold on
the point estimate and its paired interval excludes zero, so it is the strongest reading available
— but it is one class, and the same body carries a measured **−30.0 pp** on weak/DATA's
`output_correct_on_subtle_case`. A tree walk that reports E firing and omits that is the same
error, in the same direction, as the inherited ladder it replaces.

### Branch G, stated precisely, because it is the one most likely to be misread

Branch G's consequence is severe and worth quoting: *if the gate ties the placebo, the lift is an
extra turn and not a mechanism; V2 does not ship as a discipline gate, and what ships instead is
nothing.* It is the branch that would retire the mechanism.

**Fourth window: it fires, and it fires on a measured tie rather than on an absent comparison.**
The trio was bought at weak tier, n=10 each, in the pre-registered order (`bare-gate`, then
`placebo-gate`, then `skill-gate`, so the treatment never landed before its control). On the
primary criterion `skill-gate` scores **7/10** and `placebo-gate` scores **7/10**: +0.0 pp, paired
[−35.1, +35.1], McNemar 1.0000. Three earlier revisions said a tie would be a *measured equality*
and that what existed then was an *absent comparison*. The comparison now exists, and it is a tie.

**The tie is only readable because delivery was checked first, and delivery held.** The gate's own
verbatim marker appears in **9/10** `bare-gate` streams, **9/11** `skill-gate` streams and **8/10**
`placebo-gate` streams, and in **0** streams of the two ungated arms — the negative control that
proves this counts the mount rather than the filename. At strong tier the identical hook delivered
**0/15** (§5a). Had this window bought the strong-tier gate cell the plan funds, it would have
produced a tie made of an untreated treatment arm and would have looked exactly like this one.
That distinction is the whole reason the trio was bought at weak tier and the strong block was not.

**What Branch G licenses, stated exactly.** The gate does **not** ship as a discipline gate: the
extra blocked turn buys the same 7/10 whether the injected sentence carries the discipline or
carries nothing. Two further readings from the same trio point the same way — the gate on top of
the skill body moves `regression_check_present` **8/10 → 7/10** (−10.0 pp), and the gate without
any body moves it **3/10 → 3/10** (+0.0 pp, an exact tie against ungated `bare`). In no
configuration at this tier does the mechanism add anything.

**What Branch G does not license is deleting it.** The tie sits at n=10 with a paired interval of
[−35.1, +35.1]; an effect of up to a third of the scale is still compatible with it. Declining to
*promote* a mechanism on such a read is the conservative direction and costs nothing — the gate is
already default-off and opt-in, so firing Branch G changes no shipped default. *Removing* the gate
would be taking a structural cut from an underpowered read, which is the owner's rule in the other
direction, and this report does not take it. So: **the gate stays default-off and opt-in, and the
reason on the record now changes** — from "G1 is undischarged in all three conjuncts" to "H3 was
bought and returned a tie at n=10 with delivery confirmed, and H1 measured +0.0 / −10.0 pp at the
same tier." G1's remaining conjuncts, H2 (strong tier) and H6 for the gate arms (the NULL bank),
stay **unmeasured** — and H2 is unbuyable on this mechanism until the strong-tier delivery failure
is itself explained.

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

### 5b. The gate trio, bought — delivery, then contrast, in that order

Three arms on `verif-lift-bug-v1` at weak tier, n=10 each, 31 runs, ordered so the treatment arm
never preceded its control. Streams were persisted (`FATHOM_STREAM_DIR`) specifically so delivery
could be counted before any contrast was read; `tasks/verif-lift-authoring/analyse_gate.py`
reproduces both tables and refuses to certify a contrast when the streams are absent.

**Delivery — did the treatment arrive?**

| arm | gate marker in stream | rate | 95% Wilson |
|---|---|---|---|
| `bare-gate` | 9/10 | 90% | [60%, 98%] |
| `skill-gate` | 9/11 | 82% | [52%, 95%] |
| `placebo-gate` | 8/10 | 80% | [49%, 94%] |
| `bare` (ungated control) | 0 | — | negative control |
| `skill` (ungated control) | 0 | — | negative control |

**Contrasts, n=10, paired, all three criteria** (`spec_met` and `proxy_instrument_ok` are 10/10 in
every arm and move nowhere, so only the footprint criterion is reproduced here):

| contrast | control | treatment | diff (pp) | 95% paired | McNemar | what it means |
|---|---|---|---|---|---|---|
| **H3 — the placebo contrast** | `placebo-gate` 7/10 | `skill-gate` 7/10 | **+0.0** | [−35.1, +35.1] | 1.0000 | the gate's *content* buys nothing over an equal-cost empty gate |
| gate on top of the body | `skill` 8/10 | `skill-gate` 7/10 | −10.0 | [−47.5, +31.5] | 1.0000 | adding the gate to the body does not help |
| gate without the body | `bare` 3/10 | `bare-gate` 3/10 | **+0.0** | [−35.1, +35.1] | 1.0000 | the gate alone does nothing |

The three rows are mutually consistent and all null-to-negative. The mechanism arrives, and having
arrived, does not move the criterion it was built to move — at this tier, at this n. The honest
bound is the interval: ±35 pp is still compatible with these ties, so this retires the gate as a
*candidate for promotion*, not as a possibility.

### The strong-tier branch as originally asked

The instruction's branch was: *if strong-tier lift is ~0 with power, state what the skill's
trigger/guidance must say.*

**That branch is not reachable on this evidence, and the reason is not subtle: no strong-tier
trial has ever been run.** `verif-lift-bug-strong-v1` and `verif-lift-data-strong-v1` have no
ledger lines at all. There is no strong-tier lift estimate — not a null one, not a small one,
none. The precondition "~0 **with power**" is doubly unmet: the estimate is absent, and the
design's power at n=12 per strong cell would have been a 50 pp minimum detectable difference even
had it run.

So the **strong-tier branch specifically** remains unreachable — the tree's resolution at the
fourth window (Branches E and G, §5) is entirely a weak-tier resolution — and the consequential
instruction for the strong tier is still a prohibition rather than a rewrite:

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
   demonstrated, and must not read a ceiling as a null. **That is what the fourth window did**, and
   the headroom was real: weak/BUG `bare` finished at 3/10 and `skill` at 8/10 (§3). The figure this
   sentence originally cited — `bare` 0/4 — was itself the underpowered read the same sentence
   warned against.

### The question this report did not answer: is the shipped gate allowed to ship?

The first revision answered only "should a repair pass delete this?" — correctly, *strip nothing*.
It never answered the other question, and the plan's answer to that one is **no**.

`craft` branch `feat/verification-vnext` already carries `5b2eb1a` (V1, the router rows),
`3ac471d` (V2, the `SubagentStop` gate) and `609f6ef` (0.10.0). The plan makes **V2 a full gate on
G1**: H1 or H2 at ≥ +0.15, **and** H6 (FP ≤ +0.05), **and** H3 (beats placebo by ≥ +0.10).

**Fourth window: two of the three conjuncts are now measured, and both fail.** H3 — "beats placebo
by ≥ +0.10" — is a **+0.0 pp exact tie** (7/10 vs 7/10, §5b). The H1 leg of the first conjunct is
**+0.0 pp** on `bare` and **−10.0 pp** on `skill` at the same tier, nowhere near ≥ +0.15. The third
conjunct H6 (FP ≤ +0.05) is still **unmeasured for the gate arms**, since no gate arm was run on the
NULL bank, and H2 remains unmeasured and unbuyable as designed (§5a).

So G1's status changes from *undischarged in every conjunct* to **failed in the two conjuncts that
were bought, unmeasured in the rest**. That is a stronger statement and it is the one the data
supports. The distinction that governed three revisions — unmeasured is not unmet — still governs
H2 and H6; it no longer governs H1 and H3.

The facts are not in tension, and all belong in the record:

- **Nothing licenses deleting the gate.** A tie at n=10 with a [−35.1, +35.1] paired interval is
  not a refutation of the mechanism; it is a refutation of the *case for promoting* it. Deleting on
  this evidence would take a structural cut from an underpowered read.
- **Nothing licenses shipping it on as measured — and now the reason is evidence, not absence.**
  Previously the gate sat in the tree ahead of its own gate. It now sits behind a bought contrast
  that it tied. Default-off remains a safety property rather than evidence, but the obligation is
  no longer merely undischarged: where it was tested, it was not met.

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

**Updated at the fourth window — "strip nothing" stands, and one thing is now decided.**

- **The vNext body does not ship.** D2 is measured and unsupported, the one addition with a
  reachable criterion (A2) cannot be separated from zero, and the body gives back most of the
  shipped body's lift in the only cell where a lift exists (−40.0 pp). This is a decision *not to
  promote a candidate*, which the data supports; it is **not** a finding that the vNext additions
  are harmful, which it does not.
- **The `SubagentStop` gate is not promoted.** Branch G fired on a measured tie (§5b). It stays
  default-off and opt-in. Still: **do not delete it** — see the interval.
- **Still strip nothing from the shipped body**, and note that the shipped body is now the one
  carrying a measured cost (`output_correct_on_subtle_case`, −30.0 pp on weak/DATA). That is a
  reason to *investigate* the shipped body on the DATA class, not to edit it on one n=10 cell.
- **A1, A3 and the over-scope read remain unmeasured**, and their repair path is unchanged: fix
  TRUNC's instruction scope (a `dataset_version` bump) before buying, or the ceiling repeats.

## 6. Why the first three windows bought nothing, stated plainly

> **Scope note added at the fourth window.** This section describes windows one to three and is
> kept as the record of them. It no longer describes the report: the fourth window bought 90 runs.
> The blocker was different in each of the three — the lock (window one), the lock again (window
> two), and an expired OAuth session (window three) — and none of the three was a design fault in
> the matrix, which is why the fourth window needed no redesign to spend, only a working
> credential and a free lock.

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

| block | trials | ledger floor | **corrected (×3.81)** | status |
|---|---|---|---|---|
| weak BUG + DATA, all three arms | 59 runs | $8.72 | **~$33** | **BOUGHT** at the fourth window — the decisive cells |
| weak gate trio (`bare`/`skill`/`placebo` ×gate) | 31 runs | $3.07 | **~$12** | **BOUGHT** at the fourth window — discharges H3 (§5b) |
| weak NULL + TRUNC (vNext) | 16 | ~$1.5 | **~$6** | **unbought by choice** — both ceilinged in `skill`, so a vNext arm there cannot show a lift; TRUNC's ceiling is repairable (§3) and buying it before the repair wastes the spend |
| strong BUG + DATA (vNext) | 24 | ~$18 | **~$69** | **unbought** — needs strong-tier `bare`/`skill` arms, which do not exist |
| strong gate cell | — | — | — | **must not be bought as designed** — delivery is 0/15 at that tier (§5a) |

The two bought rows came in at **$11.79 floor / ≈$44.92 corrected** against a $60 soft target and a
$100 hard stop; the strong block was left unbought deliberately, not for want of budget.

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

Recorded spend across the verif-lift ledgers now stands at **127 paid runs, a $15.13 ledger floor,
≈$57.6 corrected**, of which the fourth window bought **90 runs / $11.79 floor / ≈$44.92
corrected**. The remaining 37 runs are the MAP's, unchanged.

**Economy, aggregated by `config_hash` as the rule requires — a floor, not a measurement:**

| tier | class | arm | `config_hash` | runs | $ total | $/run | turns | dur s |
|---|---|---|---|---|---|---|---|---|
| weak | BUG | `bare` | `3214c0e6bbbb` | 10 | $1.07 | $0.107 | 1.1 | 6 |
| weak | BUG | `skill` | `52ffcd608665` | 10 | $1.44 | $0.144 | 2.7 | 22 |
| weak | BUG | `skill-vnext` | `046e6deada19` | 10 | $1.42 | $0.142 | 5.1 | 21 |
| weak | BUG | `bare-gate` | `c6c95f7080e8` | 10 | $1.69 | $0.169 | 2.6 | 22 |
| weak | BUG | `placebo-gate` | `3a665058f27a` | 10 | $1.52 | $0.152 | 4.6 | 31 |
| weak | BUG | `skill-gate` | `609dea0d69b1` | 11 | $1.99 | $0.181 | 4.5 | 44 |
| weak | DATA | `bare` | `3214c0e6bbbb` | 10 | $0.90 | $0.090 | 1.0 | 6 |
| weak | DATA | `skill` | `52ffcd608665` | 13 | $1.22 | $0.093 | 1.9 | 17 |
| weak | DATA | `skill-vnext` | `046e6deada19` | 10 | $0.96 | $0.096 | 3.0 | 33 |

Two properties of that table are load-bearing. **The hash is the identity, not the arm name:**
`bare` resolves to `3214c0e6bbbb` in *both* banks and `skill` to `52ffcd608665` in both, because
only the injected file's sha256 enters `config_hash` and never its path — which is what let the six
staged scenario directories be reused without forking a hash. The rows are therefore keyed on
**(bank, `config_hash`)**; keying on the hash alone is the double-count defect corrected at the
third window. **And the $/run column must not be read as an arm-to-arm economy claim**: it is a
floor whose bias is not guaranteed common-mode across arms, and the delegated-path undercount
below applies unevenly to arms that delegate more.

The ×3.81 figure used above is the **conservative budgeting unit, not a measured multiplier.** Its
originally-proposed mechanism — two `result` events per delegated stream — is **refuted** by the
stream corpus below, where the observed `sum ÷ last` ratio never approaches 3.81 on any stream that
has two events at all, and no replacement mechanism has been derived. It is used here because it
over-reserves rather than overspends, and for no other reason. Every "corrected" figure in this
report, including this window's ≈$44.92, inherits that caveat and is a budgeting figure rather than
a measurement.

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
- **`skill-gate` − `skill` is not a replication of anything — but `bare-gate` − `bare` is, and it
  was bought this window.** The prior program's `bare-sub` arms mounted **no plugins**, and their
  injected preamble is byte-identical (sha256 `b044b0bf…`) to this bank's `arm-bare.md`. Phase 2/4's
  headline lift is therefore `bare+gate` − `bare`, which is exactly the `bare-gate` − `bare`
  contrast in §5b. **It returns +0.0 pp — 3/10 versus 3/10, an exact tie — against an inherited
  +0.22 at the same tier.** That is a failed replication on a different bank, with the treatment
  confirmed delivered in 9 of 10 streams, at n=10 where the minimum detectable difference is 60 pp.
  So it does not refute +0.22; it declines to reproduce it under the most directly comparable
  conditions this programme can construct, and it is the second independent reason (after §5a) that
  the published ladder should not be cited as the gate's measured effect.
- **The strong tier is unmeasured**, so the tier × class map the program is named for does not
  exist.
- **n=1 repeat.** Nothing here separates a real effect from a single lucky trial below the
  minimum detectable differences tabulated in §3.
- **A strong-tier gate arm does not deliver its treatment** (§5a), so the `bare-gate` arm that makes
  `skill-gate` a replication is only meaningful at weak tier until that is understood. It was
  bought at weak tier (`c6c95f7080e8`, 10 runs); its strong-tier cell was **not** bought and should
  not be.
- **The gate results are weak-tier only, and delivery is the reason they are readable.** 80–90% of
  gate-mounted streams carry the marker here against 0/15 at strong. Nothing in §5b transfers to
  the strong tier in either direction — not the tie, not the +0.0 replication.

## 9. Open decisions this report hands to the operator

None of these is settled by the evidence above; each is recorded because the evidence changed what
the decision costs.

1. **Credentials and the lock — both cleared at the fourth window, and neither was the real
   lesson.** ~~The lock is the precondition for every other item.~~ ~~Superseded at the third
   window: an expired OAuth session is.~~ **Both resolved:** the session was refreshed, smoke
   returned 7/8 with only the permitted failure, the lock came free on the first poll and was held
   2 h 31 m and released 15 s after the last paid trial. The item that survives is the one the
   third window predicted — *expect a new blocker each window rather than assume the path is
   clear* — and the fourth window duly produced one that had nothing to do with either: a block
   died mid-matrix on a Windows `git init` failure (exit `0xC0000142`, DLL-init under process
   pressure) while staging a workspace, leaving that arm at 2/10 while its dependent vNext arm ran
   on to completion. The buy order alone did not prevent an orphan, because the order assumes a
   block either completes or halts the script; this one failed and the script continued. **Carry
   forward: the runner should stop the dependent arm when its comparator block exits non-zero**, or
   the repair has to be done by hand as it was here (the comparator was completed before analysis,
   so no orphan reached the report).
2. **Re-scope the grid before the next block.** In corrected units the plan's 368-trial grid is
   ≈$223 against a $120 ceiling, and `--max-budget-usd` is per-spawn so nothing rails the total
   (§7). The strong block alone exceeds the ceiling — and §5a now removes part of its motivation.
3. **The gate trio was bought at weak tier and H3 is discharged — what remains is H6 and the
   strong-tier delivery failure.** ~~The only thing standing between G1/H3 and a verdict.~~
   **Done (§5b):** 31 runs, delivery 80–90%, H3 an exact tie, Branch G fired. Two follow-ons are
   now the open part. **(a)** H6 for the gate arms is still unmeasured — no gate arm has run on the
   NULL bank, so the false-positive conjunct of G1 has no reading; at weak-tier prices that is a
   small block if anyone wants G1 closed rather than merely failed. **(b)** The strong-tier
   zero-delivery is still unexplained, and it — not the gate's effect — is the precondition for any
   strong-tier gate work. Buying the strong cell before explaining it repeats §5a.
4. **The published `+0.22 / +0.56 / +0.44` ladder needs a decision, not a silent edit.** The opus
   figure's arm shows zero gate activations, and at n=9 that contrast could not have reached
   significance in any case (best-case exact McNemar p = 0.125). The plugin's README and CHANGELOG
   currently present it as the gate's measured effect at that tier. **This pass deliberately made no
   craft edit** — no pre-registered branch licensed one, and a delivery measurement is not a branch
   outcome — but the citation is now known to attribute an effect to a mechanism that left no trace
   in the trials producing it. **Sharpened at the fourth window, and now a branch *has* fired.** The
   gate was bought at the tier where it demonstrably *does* deliver (80–90%), and there it produced
   **+0.0 pp against its placebo, +0.0 pp against ungated `bare`, and −10.0 pp on top of the skill
   body**. So the ladder is now doubly unsupported: at strong tier the mechanism left no trace in
   the trials, and at weak tier, where it leaves a trace in 8–9 streams out of 10, it moves nothing.
   Branch G licenses not promoting the gate; whether that obliges a correction to the published
   README and CHANGELOG numbers is still an operator call, but it is no longer a call made in the
   absence of data.
5. **Re-derive or retire the ×3.81 multiplier.** Its stated mechanism is refuted (§7); the
   undercount it stands for is real and probably larger. Keep it as a conservative budget unit,
   stop quoting it as measured.
6. **The non-inferiority margin cannot pass at any funded n** (§3). Re-register the margin,
   re-register n, or withdraw the displacement — an operator decision, and explicitly *not* one to
   be fixed by dropping the margin after seeing data. **Unchanged by the fourth window, and now
   demonstrated rather than projected:** every bought cell is n=10, needs n ≥ 35, and the analyzer
   printed **undecidable** on all seven rows rather than scoring them failures. Note this did not
   end up mattering for the ship decision — vNext is declined on the *point estimates and paired
   intervals*, not on a failed non-inferiority test, so the undecidable margin blocked nothing this
   window. It would bind immediately on any future attempt to argue a body is *equivalent*.
7. **New: investigate the shipped body's cost on the DATA class** (§3, fact 3).
   `output_correct_on_subtle_case` 7/10 → 4/10 under `skill`, paired [−50.7, −1.5]. One cell, n=10,
   McNemar 0.2500 — a flag, not a verdict, and explicitly not a licence to edit the shipped body.
   The cheap next step is more n on weak/DATA `bare` vs `skill` alone, which needs no new arm.
