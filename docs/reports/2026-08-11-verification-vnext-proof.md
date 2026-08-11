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
`scenarios/verif-lift-{bug,data,trunc,null}/vnext.toml` injects the body the *plan projected*
(796 words, sha `7de774de…`). That is not what shipped: the two bodies differ in four places,
including two of the three table rows under test — the shipped body renames `Data output right`
to `Data output correct`, replaces `A cited file says X` with `Doc/report claim accurate`, and
adds a `references/non-vacuity.md` pointer to gate step 3 that the draft did not have. Measuring
that arm would have measured a draft nobody will ship; editing it would have forked a
longitudinal `config_hash` the ledger keys on. The new arm lives in three new scenario
directories and **no existing scenario file was touched.**

## 3. The three-arm per-cell table

Arms run the same tasks, so every contrast is paired and read with exact McNemar. `n` is tasks
scored in every arm present. The `skill-vnext` column is empty in every row for the reason in §1.

| tier | class | criterion | n | bare | skill | **skill-vnext** | skill−bare | 95% Newcombe | McNemar |
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
result in either cell — those two cells are downside checks, permanently.

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
| 6 | **not detectable at any effect size** |

At n=1 repeat this design resolves only large effects. The `+10.0` on TRUNC and the `+0.0` on
NULL are **not** evidence of no effect; they are intervals so wide they exclude almost nothing.

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
| A1 | new row *A check ran → the count of units it saw, non-zero* | `defect_past_slice_handled` (TRUNC) | **not-proven** — and unprovable in this cell, §5 |
| A2 | new row *Data output correct → a hard case named and its value written before the fix* | `output_correct_on_subtle_case` (DATA) | **not-proven** — cell never bought |
| A3 | new row *Doc/report claim accurate → the cited span read whole* | `defect_past_slice_handled` (TRUNC) | **not-proven** — and unprovable in this cell, §5 |
| A4 | finishing: "or a jumped runtime" | none exists | **not-measurable** |
| — | the three additions as a group (false-positive risk) | `scope_respected` (NULL) | **not-proven** — and undetectable at n=6 |
| X1 | "the vNext body is smaller" (the plan's 790 → ~720) | direct measurement, no trial needed | **refuted** — see below |

**X1 is the one claim this run settles, and it settles it against the plan.** Measured with the
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
3. **Two of the four weak classes can never supply that evidence.** TRUNC and NULL are ceilinged
   in the `skill` arm. Any future attempt to establish "the skill does / does not help" must buy
   BUG and DATA, where headroom is demonstrated (weak/BUG bare 0/4), and must not read a ceiling
   as a null.

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

## 7. What is banked, and what it costs to finish

Banked, free, and reusable the moment the lock clears:

- the arm (`scenarios/verif-lift-assets/arm-skill-vnext.md` + three scenario dirs), armed and
  verified on real spawns;
- `tasks/verif-lift-authoring/analyse_vnext.py`, the three-arm analysis, which reads whatever is
  in the ledger and reports empty cells as empty rather than as nulls;
- the pre-declared verdict rules, the −10 pp non-inferiority margin, the power table, and the buy
  rule: **no vNext trial is bought in a cell that lacks a `bare`+`skill` comparator** — a vNext
  trial with no comparator is not a contrast, it is spend.

Cost to finish, at the ledger-floor per-trial rates observed here:

| block | trials | ledger-floor cost | note |
|---|---|---|---|
| weak BUG + DATA (vNext) | 40 | ~$4 | the decisive cells; needs the MAP's `skill` arm too |
| weak NULL + TRUNC (vNext) | 16 | ~$1.5 | downside checks only — both ceilinged |
| strong BUG + DATA (vNext) | 24 | ~$18 | needs the MAP's strong arms, which do not exist |

**These are floors, not estimates.** Every arm delegates through the `Task` tool, so each trial's
stream carries two `result` events — parent and subagent sidechain — and `parse_stream` keeps the
last; a saved stream measured the undercount at 3.81×. The bias is not guaranteed common-mode
across arms, so no arm-to-arm economy claim is made from these figures at all. Recorded spend
across the verif-lift ledgers stands at a **$3.34 ledger floor** (≈$12.7 corrected), all of it the
MAP's; this run added $0 of matrix spend and three sub-cent arming probes.

## 8. Limits that bound every future verdict from this arm

- **`references/non-vacuity.md` is not injected.** This is a system-prompt arm with no file behind
  the three pointers the vNext body adds. D1/D2/D3 are therefore tested under the pessimistic
  assumption that the displaced procedure is never recovered — and an agent that follows a
  pointer pays for a failed read. Non-inferiority measured this way would imply non-inferiority
  with the file present; the converse does not hold, and no result from this arm is evidence
  about the packaged skill's reference file.
- **The strong tier is unmeasured**, so the tier × class map the program is named for does not
  exist.
- **n=1 repeat.** Nothing here separates a real effect from a single lucky trial below the
  minimum detectable differences tabulated in §3.
