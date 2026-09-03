# Findings — multiagent dispatch with convoy's gate versus multiagent dispatch alone (iteration 1)

[experiment-rigor | measurement -> experiments/multiagent-composition-v2/record.yaml]

**Status: closed 2026-09-03; revised the same day after a blind review** (two reviewers,
methodology and decision relevance, with no access to the authors; ten of their fourteen
serious findings adversarially verified by a third pass, then a closeout pass over the
revision; all thirty-eight are answered below, in the record, or in the 2026-09-03 correction
addendum — some in part, with the reason given where it arises: a frozen field, or a change
that belongs upstream in the report renderer). The derived report
[`experiments/multiagent-composition-v2/report.md`](../../experiments/multiagent-composition-v2/report.md)
(rendered from `record.yaml`, gated for drift) is the source of the cell counts, intervals
and verdicts; the contrasts come from `tools/readout_multiagent.py`, the dose and exposure
figures from `tools/stream_facts.py`, and the cost figures from the ledger's run rows. This
document explains, points, and records what the numbers cannot say.

## The question

Does a Sonnet orchestrator dispatching one implementer subagent per PR produce more
held-out-clean work when convoy's standalone gate — fail-closed independent checks and a
repair brief — runs between PRs than when it verifies with the project's own suite alone?
And is the gain the independent information (gate arm > placebo arm), not the extra
iteration a ceremony gate also buys? Convoy's orchestration appears in no arm.

## Method, in one paragraph

Bank `multiagent-composition-v2`: one five-PR feature (comparison and boolean operators for
a small expression language) whose PR prompts state *what* to build but not the type rule
the held-out oracle checks. Eight cells: four arms (control, placebo, perpr, final) × two
implementer tier-sets (Haiku, Sonnet). The manipulation is one contiguous block appended to
step 3 of the control brief — the placebo's says "run the quality gate; if it exits
non-zero, re-verify and fix" against a gate that reddens exactly once per workspace and
carries no information; perpr's says "run the convoy gate driver after each PR and, on
`blocked`, dispatch a fix subagent with the envelope's `repair_brief` verbatim until
`completed`" — while the final arm keeps control's brief byte for byte and the harness runs
the gate once after the session with a two-fix repair loop. The orchestrator is Sonnet 5 at
effort high in every arm; limits and env keys are identical across arms; the tool surface
that actually ran was the platform's registered set (30 tools, including unrestricted Bash
and PowerShell, in every counted stream but one pilot final-haiku session listing 26, Bash
present throughout), the same across arms — the scenarios' declared allow-list
(`Bash(python:*)`) was not enforced. Primary endpoint `held_out_clean`: all six held-out
criteria in `verify.py` pass on the executed workspace, none of them an expression any gate
check or probe evaluates. Four pre-registered one-sided Fisher contrasts per tier-set,
Holm-corrected within the tier-set; Wilson 95% intervals on every cell; tier-sets never
pooled. n = 16 per cell: the first three repeats are the pooled pilot (24 trials, run
arm-blocked), thirteen arm-interleaved repeat passes follow. Pre-registration:
`docs/specs/2026-09-01-multiagent-composition-preregistration.md` and its dated addenda,
including the 2026-09-03 post-review correction; frozen record:
`experiments/multiagent-composition-v2/record.yaml`.

## Results

`held_out_clean`, numerator/denominator and Wilson 95%, Haiku implementers then Sonnet:

| arm | Haiku | Sonnet |
|---|---|---|
| control (own suite only) | 4/16 [0.10, 0.49] | 2/16 [0.03, 0.36] |
| placebo (ceremony gate, no information) | 6/16 [0.18, 0.61] | 5/16 [0.14, 0.56] |
| perpr (convoy gate after each PR) | 16/16 [0.81, 1.00] | 14/16 [0.64, 0.97] |
| final (harness gate loop once, after the session) | 12/16 [0.51, 0.90] | 9/16 [0.33, 0.77] |

Pre-registered contrasts (one-sided Fisher, Holm-adjusted within the tier-set's family of
four, alpha 0.05):

| contrast | Haiku | Sonnet |
|---|---|---|
| perpr > control | < 0.0001 | 0.0001 |
| **perpr > placebo (decisive)** | **0.0004** | **0.0048** |
| final > control | 0.0121 | 0.0233 |
| final > placebo | 0.0366 | 0.1426 |

All four contrasts clear Holm at the Haiku tier; three of four at the Sonnet tier, the
exception being final vs placebo. No power was declared for the final-arm contrasts (the
n = 16 calculation was made on the per-PR gap alone), so final vs placebo at Sonnet is
reported as underpowered at the achieved n, not as a null. perpr-haiku at 16/16 sits at the
instrument's ceiling: the effect there has no estimable upper bound, only the clamped
interval.

**Sensitivity to four counted trials that reached the task directory** (see deviation 8;
`tools/stream_facts.py --exposure`). Dropping the three that read the oracle or the
reference solution (perpr-sonnet r0 and r1, both held-out-clean; placebo-haiku r1, not)
gives perpr-sonnet 12/14 and placebo-haiku 6/15: perpr > placebo Holm 0.0007 (Haiku) and
0.0106 (Sonnet), final > placebo at Haiku 0.0531. Dropping the fourth as well (final-haiku
r3, which read harness internals; 11/15) gives final > placebo at Haiku 0.0697 and
final > control 0.0183. Scoring the two perpr-sonnet successes as failures gives
perpr > placebo 0.0350 at Sonnet. Ignoring the sixteen voids (144 rows) or leaving the pooled
pilot out (main passes only, n = 13) keeps both perpr contrasts significant at both tiers;
on the main passes alone neither final-arm contrast is (final > control 0.1152 and 0.0968).
So: the per-PR conclusions survive every version; the final-vs-placebo Haiku contrast does
not survive the disposition of one trial, and final > control loses significance when the
pooled pilot is left out, to which the arm-blocked pilot block and the smaller n both
contribute.

**What the endpoint measures.** Per criterion, the four that separate the arms —
`type_bool_arith_heldout`, `type_compare_heldout`, `env_bool_typing`,
`error_type_is_typemismatch` — all grade one rule, booleans are not numbers, which is the
rule the gate's two probes assert and its repair hint states; the two genuinely off that
rule (`not_precedence_heldout`, `short_circuit_heldout`) are at 16/16 in seven cells and
15/16 in placebo-haiku and never flip either endpoint in any trial. The primary endpoint
equals the conjunction of the four bool-rule criteria in every cell. The pre-registered
sensitivity endpoint, defined as the four criteria the probes and the hint do not touch, is
numerically identical to `env_bool_typing` alone in every cell (control 4/16 and 2/16,
placebo 7/16 and 5/16, perpr 16/16 and 14/16, final 13/16 and 10/16) and cannot do the job
it was registered for; its verdict is `inconclusive`. What "held out" still means here is
reachability: no gate check or probe evaluates an expression the oracle grades, and
`env_bool_typing` routes booleans through the environment rather than literals, so an
implementation that special-cases literals greens the probe and reds the oracle — 8 of 128
trials did exactly that, two of them perpr-sonnet trials whose probe ran green.

**The fifteen inherited criteria** (`full15_clean`, exploratory; not the implementer's
visible suite, which was green in every arm by construction): control 4/16 and 2/16,
placebo 6/16 and 5/16, perpr 16/16 and 14/16, final 14/16 and 12/16. They reproduce the
effect at equal or greater strength (final > placebo reaches 0.0160 at Sonnet), with the
caveat that their separation comes from `type_bool_in_arith` and `type_compare_bool`, which
overlap the manipulated rule. The final arm reads higher on the fifteen (14/16 and 12/16)
than on the held-out six (12/16 and 9/16) mainly because the fifteen do not grade
`env_bool_typing`, on which the final arm is 13/16 and 10/16; per criterion the inherited
and held-out type checks are repaired about equally often. The conjunction of the criteria the visible suite does
assert is 16/16 in every cell but placebo-haiku (15/16): a green own-suite is flat across
arms.

**Dose and mechanism**, from tool_use events on the surviving stream of each counted trial
(`tools/stream_facts.py`; the pre-registration's addendum 5 obligation):

| cell (Haiku / Sonnet) | gate reds per trial | `Agent` dispatches per trial | executed driver calls |
|---|---|---|---|
| control | 0 / 0 | 6.00 / 6.06 | 0 |
| placebo | 0.94 / 1.06 (the gate reddens once per workspace; one Sonnet trial recorded two reds, one Haiku trial none) | 5.75 / 5.94 | 0 |
| perpr | 1.19 / 1.06 (13 trials at 1, 3 at 2 / 15 at 1, 1 at 2) | 7.19 / 7.12 | 6 in 27 trials, 7 in 5 |
| final | 0 / 0 at the orchestrator; 13/16 first-round reds per tier in the harness | 6.00 / 6.00 | only inside the fix spawns |

The reds do not diverge materially, so the decisive contrast is matched on gate-red count,
not dose-confounded; on the other dose measures perpr still does more work than the placebo
(about 1.2 more dispatches, about 10% more spend and 13–19% more wall-clock per trial on
medians), so the extra-work channel is bounded, not eliminated. What the placebo does not
match is the repair actor — perpr dispatches a fresh implementer subagent carrying the
`repair_brief` (one extra dispatch per trial), the placebo repairs inside the orchestrator —
and the brief's content: perpr's block states that the gate adds two type-contract checks
the visible suite lacks, the placebo's says nothing of the kind. Both are declared residual
threats. The placebo fired in every placebo trial but placebo-haiku r1, which ended after
two dispatches. The post-session gate's loop fired on 26 of 32 trials, every time on
convoy's red with the task's own suite green on the first round (32 of 32); in four of the
five trials that ended red the fix spawns then broke the visible suite, which is why convoy
did not re-run on the last round. The loop itself is the harness's and would fire on either
verdict, so the final arm's contrasts compare a harness loop with no loop, not convoy's gate
with nothing. The convoy provenance line
appears in 27 of 32 final rows because it is recorded only when the last round completed
green; it attests the verdict's logging, not which binary ran. Implementer snapshots:
`claude-haiku-4-5-20251001` in every Haiku transcript; the Sonnet transcripts carry only the
undated alias.

**Cost and time** (per trial, medians from the run rows; wall-clock is a median because six
run rows carry a truncated duration; cost per held-out-clean trial is the cell's total
spend divided by its clean trials):

| arm | Haiku median $ / s | Sonnet median $ / s | $ per held-out-clean trial, Haiku / Sonnet |
|---|---|---|---|
| control | 1.93 / 826 | 2.28 / 669 | 7.79 / 19.50 |
| placebo | 2.11 / 821 | 2.58 / 675 | 5.54 / 8.60 |
| perpr | 2.31 / 974 | 2.85 / 763 | 2.39 / 3.31 |
| final | 2.39 / 1002 | 2.66 / 740 | 3.25 / 5.00 |

On medians the per-PR gate costs 20% (Haiku) and 25% (Sonnet) more per trial than control
and 18% and 14% more wall-clock; per held-out-clean trial it costs 31% (Haiku) and 17%
(Sonnet) of control — a third to a sixth.

## Conclusion

**Supported for the per-PR gate, at both implementer tiers, with a narrower mechanism than
the question hoped for.** With a Sonnet orchestrator dispatching one implementer per PR,
running convoy's standalone gate after each PR raised the held-out-clean rate from 4/16 to
16/16 (Haiku) and from 2/16 to 14/16 (Sonnet); the ceremony placebo reached 6/16 and 5/16.
The decisive perpr > placebo contrast clears Holm at both tiers under every sensitivity run
(exposed trials dropped or scored as failures, voids ignored, pilot left out), and the arms
are matched on gate-red count, so the gain is not the extra repair round a gate forces —
though perpr still does about one dispatch, 10% of spend and 13–19% of wall-clock more per
trial than the placebo, so the extra-work channel is bounded rather than closed.

What the design does not separate is *why* the perpr leg wins: a runtime red with a
repair brief, a fresh implementer subagent for the repair, and a brief that tells the
orchestrator type contracts are checked all travel together, and the endpoint they move is
one defect class — the type rule bank v2 withheld from the PR prompts, which the gate's
probes assert with different literals. The honest statement is that the gate restored a
withheld rule the implementers were not finding on their own; that its checks are not
reachable by satisfying the probe (the environment criterion caught 8 trials that passed
the three literal criteria, two of them perpr-sonnet trials whose gate had run the probe
green); and that benefit on work *independent* of the rule the gate teaches is not
shown here, because the two criteria off that rule are at ceiling in every arm.

The post-session gate is weaker on every count: 12/16 and 9/16; it beats control at both
tiers on the pre-registered analysis but not on the main passes alone, and it beats the
placebo at neither tier once the disposition of one exposed Haiku trial is allowed to vary.
Every firing of its loop was on convoy's red (the visible suite was green on the first round
of all 32 trials), but the loop is the harness's and its gate command carried the
repository path the harness repair was meant to remove.

The placebo's rate is higher than control's by 12.5 and 18.8 points; that comparison is
unregistered, its one-sided p is 0.35 and 0.20 with 95% intervals on the difference
(Newcombe, Wilson-based) of [−19, +41] and [−10, +45] points, and it is not a null. The independent-information reading rests on the
registered perpr > placebo contrast alone.

The gate makes each trial dearer and each correct trial much cheaper.

What the result does *not* say: it is one bank, one task family, one orchestrator model,
two implementer tiers, convoy 0.11.0's standalone gate driven by a script the harness placed
in the brief, and one defect class. On bank v1, where the prompts spelled out the type rule,
control was 3/3 in both tiers at n = 3 (`ledger/multiagent-composition.jsonl`), so that bank
showed no headroom; the scope restriction to briefs that leave the implementer something to
infer is a design inference, not a measured null.

## What happened to the plan (deviations, chronological)

1. **2026-09-02 ~05:00Z — the v1 bank showed no headroom** (24 trials in total, 3 per cell,
   every cell clean in both tiers; `ledger/multiagent-composition.jsonl`). Bank v2 withholds
   the type rule from the prompts; its pilot showed headroom.
2. **05:51Z — the v2 pilot ran arm-blocked**, not interleaved, over ~2.5 h; its 24 trials
   are the first three repeats of every cell, 19% of the analysed n, so time is confounded
   with arm for that block. The main passes alone reproduce every contrast's direction.
3. **12:45Z — n declared 16 per cell, budget-bound**, exact power 0.69 on the decisive
   contrast at Holm's strictest step, none declared for the final-arm contrasts. The same
   pilot set n (Laplace-shrunk rates) and sits in the analysed cells: an internal-pilot
   design whose type-I error is mildly inflated.
4. **13:41Z — the typed record was frozen after both waves began.** The prose
   pre-registration was committed before each wave (04:59:50Z for the cells, endpoints,
   contrasts and pilot n; 12:45:49Z for n = 16 and the pass schedule) but the typed record
   that transcribes it at 13:41:47Z, after the pilot's first trial (05:51:34Z) and the main
   matrix's (12:47:29Z). The gate's chronology check (`ER-ANCHOR`) reads the record's commit,
   fails, and is left failing; the record's `plan_frozen_at.timestamp` now carries the
   commit's real time and `run.attestation` the sequence with hashes.
5. **17:10Z — the fixture-contamination incident.** At 41 trial rows agents inside two trials
   had edited the bank fixture through a path the harness exposed and fourteen later trials
   had staged from it. Sixteen rows were voided (3 control, 4 placebo, 5 perpr, 4 final;
   append-only `kind: void` rows with the evidence, written 17:09:42Z), the fixture restored,
   the harness repaired (a staged harness directory outside the repository for the briefs
   and drivers, a fixture integrity guard, `fixture_sha` on every later row), n re-declared 13
   and every voided key re-bought. The addendum's commit (17:26:10Z) postdates the first
   resumed trial (17:17:42Z) by eight and a half minutes; the record declares the exclusion
   as an `analysis_plan` amendment with those times, which fails the same chronology gate for
   the same reason. Twenty-five counted trials predate the guard and carry no `fixture_sha`.
   The voided rows were 12/16 held-out-clean against 68/128 kept, so the exclusion removed
   disproportionately clean trials from every arm; including them changes no verdict.
6. **22:46Z — the incident addendum's budget arithmetic was wrong** (the v2 pilot counted
   twice); the correction, declared at 48 valid trials, returned n to the frozen 16. n was
   thus re-declared twice at interim data for reasons unrelated to outcome, with no blinding
   mechanism between the operator and the readout script.
7. **2026-09-03 18:08Z — the last pass overran the iteration cap by about $8** ($352.02 on the
   bank, $408.04 program against $400); the user authorized it with three of the pass's
   eight trials done.
8. **2026-09-03, the blind review.** (a) Three counted trials reached the task directory
   before the repair through the exposed prompts path — the exclusion rule keyed on fixture
   writes and did not reach oracle reads — and a fourth (final-haiku r3) after the repair
   through the final arm's gate command (b); all four are retained with the sensitivity
   above. One of the three, perpr-sonnet r0, also wrote a full implementation and a tests
   tree into the repository task directory, and placebo-haiku r1 read those files 48 minutes
   later: isolation failed across trials as well as into the harness. A scan of every
   counted trial's surviving stream is now a tool (`tools/stream_facts.py --exposure`). (b) The harness
   repair did not cover the final arm's gate command, which the gated-session strategy
   expands from the repository task directory and hands to the fix spawn; no post-repair
   final stream reads the oracle or the solution, and the one traversal is final-haiku r3's
   fix spawn reading the driver and the probe (threat `custom_harness_containment`). (c) The
   sensitivity endpoint is degenerate (verdict `inconclusive`). (d) The dose table required by
   addendum 5 was missing and is produced above; the first readout's mechanism figures were
   substring counts over concatenated stream files and are withdrawn. (e) The cost table was
   medians labelled means. (f) The declared tool allow-list was not enforced. (g)
   `full15_clean` is not the visible suite and is no longer described as such. (h) The
   fixture's visible test file names the oracle by filename in its docstring, identically in
   every arm, which is what sent agents in all four arms hunting for it. All of these are in
   the 2026-09-03 correction addendum of the pre-registration.

## Threats the record carries (statements in `record.yaml`)

Contamination/familiarity (**residual**: four retained trials, one of them primed by
another's writes, the pre-repair path, the docstring that names the oracle), prompt-format sensitivity (controlled), judge bias
(**residual** on endpoint independence: string-disjoint, semantically one rule), model
version drift (residual: Sonnet snapshots undated; the arm-blocked pilot block),
nondeterminism (controlled, with the internal-pilot and interim re-declaration caveats),
construct validity (residual: one defect class, one task shape, an unenforced allow-list),
token-length confound (residual: gate-red count matched, dispatches, spend and wall-clock
not; repair actor and brief content not),
selection and exclusion (residual: an under-inclusive instrument exclusion declared after its
first governed trial), generalization (residual), and harness containment (custom,
residual: the final arm's gate command).

## What this updates

- **Convoy's gate as a feature under external orchestration** (convoy backlog CONV-B53):
  supported at measurement tier for the per-PR standalone gate on one bank, as a package —
  runtime red, repair brief, a fresh repair subagent and the brief's gate claim travelling
  together, not separated by this design — that restores a rule the briefs withheld, at
  about one extra dispatch and +20–25% cost per trial and a third (Haiku) to a sixth
  (Sonnet) of control's cost per correct trial. The post-session form is not the feature to
  sell: it loses significance against control on the main passes alone, does not beat the
  placebo once one exposed trial's disposition varies, and ran with an uncontained gate
  command.
- **What iteration 2 must change before it can claim more:** a held-out group with a
  second defect class that has headroom; an equal-content placebo (a brief that makes the
  same claim about its gate, a fresh-subagent repair on its uninformative red); the tool
  allow-list enforced and verified before the first paid trial; the gated-session gate
  command expanded from the staged directory; the oracle's name stripped from the fixture;
  timestamps on ledger rows; the stream exposure scan run as a close gate; a per-trial
  arming criterion that flags a trial with fewer implementer dispatches than the task's PR
  count and voids it when the decomposition was not executed.
- **The mechanism to measure next** is convoy 0.12.0's hook (`convoy hook`: `SubagentStop`
  as the judge, `PostToolUse` on `Agent` as the messenger), pre-registered on this bank as
  `hook-haiku` and `hook-sonnet` with control's brief plus one phase-marker instruction and
  the prediction `held_out_clean` ≈ perpr at control's orchestrator dose. It is the per-PR
  shape with no gate instruction in the orchestrator's brief beyond a phase marker, which
  removes the gate-claim channel this design could not separate, though not the whole
  brief-content channel.
