[experiment-rigor | measurement -> experiments/multiagent-composition-v2/record.yaml]

# Experiment: multiagent-composition-v2 (measurement tier)

_Derived from record.yaml by render.py -- do not hand-edit._

- Design: 8 cell(s) (control-haiku=16, placebo-haiku=16, perpr-haiku=16, final-haiku=16, control-sonnet=16, placebo-sonnet=16, perpr-sonnet=16, final-sonnet=16); shared_tasks=True
- Disposition: total=128, completed=128, excluded=0
- Outcomes:
  - held_out_clean (role=confirmatory): a trial passes iff all six held_out criteria in verify.py are true — type_bool_arith_heldout, type_compare_heldout, env_bool_typing, not_precedence_heldout, error_type_is_typemismatch, short_circuit_heldout — graded by the deterministic verifier on the executed workspace, blind to arm. None of the six is asserted by any gate check or by the probe (disjointness asserted by tests/test_multiagent_bank.py).
  - held_out_clean_independent (role=exploratory): sensitivity endpoint (pre-registration addendum no. 4) — the conjunction of the four held_out criteria the probes' type rule does not touch (env_bool_typing, not_precedence_heldout, error_type_is_typemismatch, short_circuit_heldout). Reported beside the primary with the same contrasts; not in the Holm family.
  - full15_clean (role=exploratory): a trial passes iff all fifteen original ablation-v2 criteria are true — the project-visible surface the implementer's own suite approximates.
- Results:
  - held_out_clean: verdict=confirmatory_supported, paired=False
  - held_out_clean / control-haiku: 4/16, wilson CI [0.1018, 0.495]
  - held_out_clean / placebo-haiku: 6/16, wilson CI [0.1848, 0.6136]
  - held_out_clean / perpr-haiku: 16/16, wilson CI [0.8064, 1.0]
  - held_out_clean / final-haiku: 12/16, wilson CI [0.505, 0.8982]
  - held_out_clean / control-sonnet: 2/16, wilson CI [0.035, 0.3602]
  - held_out_clean / placebo-sonnet: 5/16, wilson CI [0.1416, 0.556]
  - held_out_clean / perpr-sonnet: 14/16, wilson CI [0.6398, 0.965]
  - held_out_clean / final-sonnet: 9/16, wilson CI [0.3318, 0.769]
  - held_out_clean_independent: verdict=inconclusive, paired=False
  - held_out_clean_independent / control-haiku: 4/16, wilson CI [0.1018, 0.495]
  - held_out_clean_independent / placebo-haiku: 7/16, wilson CI [0.231, 0.6682]
  - held_out_clean_independent / perpr-haiku: 16/16, wilson CI [0.8064, 1.0]
  - held_out_clean_independent / final-haiku: 13/16, wilson CI [0.5699, 0.9341]
  - held_out_clean_independent / control-sonnet: 2/16, wilson CI [0.035, 0.3602]
  - held_out_clean_independent / placebo-sonnet: 5/16, wilson CI [0.1416, 0.556]
  - held_out_clean_independent / perpr-sonnet: 14/16, wilson CI [0.6398, 0.965]
  - held_out_clean_independent / final-sonnet: 10/16, wilson CI [0.3864, 0.8152]
  - full15_clean: verdict=exploratory_signal, paired=False
  - full15_clean / control-haiku: 4/16, wilson CI [0.1018, 0.495]
  - full15_clean / placebo-haiku: 6/16, wilson CI [0.1848, 0.6136]
  - full15_clean / perpr-haiku: 16/16, wilson CI [0.8064, 1.0]
  - full15_clean / final-haiku: 14/16, wilson CI [0.6398, 0.965]
  - full15_clean / control-sonnet: 2/16, wilson CI [0.035, 0.3602]
  - full15_clean / placebo-sonnet: 5/16, wilson CI [0.1416, 0.556]
  - full15_clean / perpr-sonnet: 14/16, wilson CI [0.6398, 0.965]
  - full15_clean / final-sonnet: 12/16, wilson CI [0.505, 0.8982]
- Threats: 10 declared, 8 residual

## Record (canonical, machine-checked)

```yaml
analysis_plan:
  amendments:
  - commit: df645f1
    governs_first_run_at: '2026-09-02T17:17:42Z'
    scope: 'instrument exclusion after the fixture-contamination incident: sixteen trial rows voided by fixture mtime and stream facts (append-only kind: void rows written 17:09:42Z), every voided key re-bought; the frozen exclusion_rules (''none'') stands as frozen and this entry declares the deviation. The first resumed trial started 17:17:42Z, before this commit; the void rows it rests on were written before it.'
    timestamp: '2026-09-02T17:26:10Z'
  ci_method: wilson
  comparison: four pre-registered one-sided contrasts (treatment > control) per implementer tier-set, Holm-corrected within the tier-set's family of four at alpha 0.05 — (1) perpr vs control, (2) perpr vs placebo [decisive; separates independent information from the extra iteration], (3) final vs control, (4) final vs placebo — Fisher exact on held_out_clean counts; Wilson 95% on every cell; tier-sets never pooled.
  conditions_factors: arm x implementer tier. Arms — control (visible suite only), placebo (control + a ceremony gate that reddens exactly once per workspace with no information), perpr (control + `run_convoy_gate.py --phase <pr>` after each PR, fix subagent briefed with the envelope's repair_brief on blocked), final (control's brief; the harness runs the driver once after the session with a bounded fix loop). Tier — implementer subagents at claude-haiku-4-5 or claude-sonnet-5 via FATHOM_IMPL_MODEL; orchestrator Sonnet 5 effort high in every arm; tools, limits and env keys byte-identical across arms; briefs differ in one contiguous block (asserted by test). Convoy under test — 0.11.0, pinned by git tag via uvx, provenance echoed per call.
  decision_rule:
    comparison: gt
    direction: higher
    metric: rate_difference
    threshold: 0.0
  dv_operationalization: held_out_clean as above; secondary full15_clean; mechanism — first-gate red rate and fix-dispatch count per arm (from ledger detail and transcripts); cost per trial (sum of run rows per config_hash+repeat) and wall-clock.
  exclusion_rules: none. Every launched trial is dispositioned; an infrastructure stop (seat authentication failure) halts the matrix without writing the failing trial, which is resumed, not excluded. Reported as excluded if any row is dropped.
  n_and_rationale: 16 per cell. The exact power calculation (one-sided Fisher, alpha 0.0125 = Holm's strictest step, Laplace-shrunk pilot rates 0.875 vs 0.375 for perpr vs placebo) asks 20 for power 0.80; the remaining iteration budget ($286.52 of $400) buys 13 further repeat passes at $19.15/pass, so n=16 is budget-bound with exact power 0.69 on the decisive contrast and 0.99 on perpr vs control, declared before the first main trial. A non-significant decisive contrast at n=16 is reported as underpowered at the achieved n, not as a null.
  other: main-matrix trials run as repeat passes (--repeats k, k=4..16), each pass covering every arm once — arm-interleaved by pass (the run loop's order is scenario > task > repeat, so a plain run would block arms; the pilot's 24 were blocked and are disclosed as such). Caps $20 per spawn, $275 per run. Seat lifetime ~4h — the pass script stops on authentication failure and the same command resumes.
  prior_data_collected: yes — the v1 pilot (bank multiagent-composition, 24 trials, all cells at ceiling) and the v2 pilot (24 trials, the first 3 repeats of these 8 cells, block-ordered, pooled into n=16 as the run loop resumes them; declared in the 2026-09-02 addendum before the main matrix's first trial).
  question_hypothesis: does a Sonnet orchestrator dispatching one implementer subagent per PR produce more held-out-clean work when it runs convoy's standalone gate between PRs (fail-closed independent checks + repair_brief) than when it verifies with the project's own suite alone — and is the gain the independent information (perpr > placebo), not the extra iteration (placebo ≈ control)? Convoy's orchestration appears in no arm.
design:
  cells:
  - name: control-haiku
    planned_n: 16
  - name: placebo-haiku
    planned_n: 16
  - name: perpr-haiku
    planned_n: 16
  - name: final-haiku
    planned_n: 16
  - name: control-sonnet
    planned_n: 16
  - name: placebo-sonnet
    planned_n: 16
  - name: perpr-sonnet
    planned_n: 16
  - name: final-sonnet
    planned_n: 16
  shared_tasks: true
disposition:
  completed: 128
  excluded: 0
  total: 128
  voided_and_rebought: 16
experiment: multiagent-composition-v2
outcomes:
- name: held_out_clean
  operationalization: a trial passes iff all six held_out criteria in verify.py are true — type_bool_arith_heldout, type_compare_heldout, env_bool_typing, not_precedence_heldout, error_type_is_typemismatch, short_circuit_heldout — graded by the deterministic verifier on the executed workspace, blind to arm. None of the six is asserted by any gate check or by the probe (disjointness asserted by tests/test_multiagent_bank.py).
  role: confirmatory
  verifier:
    hash: 78d0e86ddeead4fa3da1188d9bd34550590a0fda892dc607891f7853cd8fe241
    path: tasks/multiagent-composition-v2/exprlang/verify.py
- name: held_out_clean_independent
  operationalization: sensitivity endpoint (pre-registration addendum no. 4) — the conjunction of the four held_out criteria the probes' type rule does not touch (env_bool_typing, not_precedence_heldout, error_type_is_typemismatch, short_circuit_heldout). Reported beside the primary with the same contrasts; not in the Holm family.
  role: exploratory
  verifier:
    hash: 78d0e86ddeead4fa3da1188d9bd34550590a0fda892dc607891f7853cd8fe241
    path: tasks/multiagent-composition-v2/exprlang/verify.py
- name: full15_clean
  operationalization: a trial passes iff all fifteen original ablation-v2 criteria are true — the project-visible surface the implementer's own suite approximates.
  role: exploratory
  verifier:
    hash: 78d0e86ddeead4fa3da1188d9bd34550590a0fda892dc607891f7853cd8fe241
    path: tasks/multiagent-composition-v2/exprlang/verify.py
plan_frozen_at:
  commit: 66c0982abae9a373d564853d478d4724afb83eb3
  path: experiments/multiagent-composition-v2/record.yaml
  timestamp: '2026-09-02T13:41:47Z'
results:
  full15_clean:
    arms:
      control-haiku:
        ci:
          alpha: 0.05
          high: 0.495
          low: 0.1018
          method: wilson
        denominator: 16
        numerator: 4
      control-sonnet:
        ci:
          alpha: 0.05
          high: 0.3602
          low: 0.035
          method: wilson
        denominator: 16
        numerator: 2
      final-haiku:
        ci:
          alpha: 0.05
          high: 0.965
          low: 0.6398
          method: wilson
        denominator: 16
        numerator: 14
      final-sonnet:
        ci:
          alpha: 0.05
          high: 0.8982
          low: 0.505
          method: wilson
        denominator: 16
        numerator: 12
      perpr-haiku:
        ci:
          alpha: 0.05
          high: 1.0
          low: 0.8064
          method: wilson
        denominator: 16
        numerator: 16
      perpr-sonnet:
        ci:
          alpha: 0.05
          high: 0.965
          low: 0.6398
          method: wilson
        denominator: 16
        numerator: 14
      placebo-haiku:
        ci:
          alpha: 0.05
          high: 0.6136
          low: 0.1848
          method: wilson
        denominator: 16
        numerator: 6
      placebo-sonnet:
        ci:
          alpha: 0.05
          high: 0.556
          low: 0.1416
          method: wilson
        denominator: 16
        numerator: 5
    paired: false
    unclustered_reason: 'one shared task and the trial is the randomization unit: every trial is an independent session in a fresh workspace with no prompt-cluster structure to pair on, so per-arm Wilson intervals over independent trials are the right unit and there is no clustered SE to state'
    verdict: exploratory_signal
  held_out_clean:
    arms:
      control-haiku:
        ci:
          alpha: 0.05
          high: 0.495
          low: 0.1018
          method: wilson
        denominator: 16
        numerator: 4
      control-sonnet:
        ci:
          alpha: 0.05
          high: 0.3602
          low: 0.035
          method: wilson
        denominator: 16
        numerator: 2
      final-haiku:
        ci:
          alpha: 0.05
          high: 0.8982
          low: 0.505
          method: wilson
        denominator: 16
        numerator: 12
      final-sonnet:
        ci:
          alpha: 0.05
          high: 0.769
          low: 0.3318
          method: wilson
        denominator: 16
        numerator: 9
      perpr-haiku:
        ci:
          alpha: 0.05
          high: 1.0
          low: 0.8064
          method: wilson
        denominator: 16
        numerator: 16
      perpr-sonnet:
        ci:
          alpha: 0.05
          high: 0.965
          low: 0.6398
          method: wilson
        denominator: 16
        numerator: 14
      placebo-haiku:
        ci:
          alpha: 0.05
          high: 0.6136
          low: 0.1848
          method: wilson
        denominator: 16
        numerator: 6
      placebo-sonnet:
        ci:
          alpha: 0.05
          high: 0.556
          low: 0.1416
          method: wilson
        denominator: 16
        numerator: 5
    paired: false
    unclustered_reason: 'one shared task and the trial is the randomization unit: every trial is an independent session in a fresh workspace with no prompt-cluster structure to pair on, so per-arm Wilson intervals over independent trials are the right unit and there is no clustered SE to state'
    verdict: confirmatory_supported
  held_out_clean_independent:
    arms:
      control-haiku:
        ci:
          alpha: 0.05
          high: 0.495
          low: 0.1018
          method: wilson
        denominator: 16
        numerator: 4
      control-sonnet:
        ci:
          alpha: 0.05
          high: 0.3602
          low: 0.035
          method: wilson
        denominator: 16
        numerator: 2
      final-haiku:
        ci:
          alpha: 0.05
          high: 0.9341
          low: 0.5699
          method: wilson
        denominator: 16
        numerator: 13
      final-sonnet:
        ci:
          alpha: 0.05
          high: 0.8152
          low: 0.3864
          method: wilson
        denominator: 16
        numerator: 10
      perpr-haiku:
        ci:
          alpha: 0.05
          high: 1.0
          low: 0.8064
          method: wilson
        denominator: 16
        numerator: 16
      perpr-sonnet:
        ci:
          alpha: 0.05
          high: 0.965
          low: 0.6398
          method: wilson
        denominator: 16
        numerator: 14
      placebo-haiku:
        ci:
          alpha: 0.05
          high: 0.6682
          low: 0.231
          method: wilson
        denominator: 16
        numerator: 7
      placebo-sonnet:
        ci:
          alpha: 0.05
          high: 0.556
          low: 0.1416
          method: wilson
        denominator: 16
        numerator: 5
    paired: false
    unclustered_reason: 'one shared task and the trial is the randomization unit: every trial is an independent session in a fresh workspace with no prompt-cluster structure to pair on, so per-arm Wilson intervals over independent trials are the right unit and there is no clustered SE to state'
    verdict: inconclusive
run:
  attestation: 'per-trial transcripts under streams-multiagent/2026-09-02-pilot-v2 and streams-multiagent/2026-09-02-main-v2 (FATHOM_STREAM_DIR); fixture_sha on the 103 rows written after the fixture-contamination incident (25 counted trials predate the guard); readout by tools/readout_multiagent.py over both stream directories (voids applied), mechanism and exposure by tools/stream_facts.py reading tool_use events on each counted trial''s surviving stream. Dose (addendum 5): gate reds per trial perpr 1.19 (Haiku) and 1.06 (Sonnet), placebo 0.94 and 1.06, control and final 0 at the orchestrator; Agent dispatches per trial perpr 7.19 and 7.12, control 6.00 and 6.06, placebo 5.75 (one aborted trial at 2) and 5.94, final 6.00; executed driver calls per perpr trial 6 in 27 and 7 in 5; placebo fired in every placebo trial but the aborted one; the final arm''s driver runs only inside its fix spawns. run.n counts every trial row in the ledger including the 16 voided ones; the disposition counts the frozen cells. Trial rows carry no timestamps: the exclusion boundary and the first-trial times below are derived from stream file names (end epoch) and run-row durations. Freeze chronology, disclosed: this typed record was committed at 66c0982 on 2026-09-02 13:41:47Z, after the pooled pilot''s first trial (05:51:34Z) and the main matrix''s first trial (12:47:29Z), so ER-ANCHOR fails on this record and is left failing rather than re-pointed; the amendment above is dated 8.5 minutes after the first trial of the wave it governs and fails the same chronology gate for the same reason. The prose pre-registration the record transcribes was committed before each wave it governs: 60ee721 (04:59:50Z; the eight cells, the endpoints, the four contrasts and Holm family, the pilot n) and ea2cd11 (12:45:49Z; n=16 per cell, the pass schedule, the caps). The frozen subset here reconciles against 66c0982 (ER-PREREG clean) and is left as frozen even where later evidence superseded its wording, because editing it fails ER-PREREG: held_out_clean''s ''none of the six is asserted by any gate check or by the probe'' holds for literal expressions only (threats.judge_bias states the semantic overlap); held_out_clean_independent''s ''the four criteria the probes'' type rule does not touch'' is false on two of the four and the endpoint reduced to env_bool_typing alone (verdict inconclusive); full15_clean''s ''the project-visible surface the implementer''s own suite approximates'' overstates it, the fifteen inherited criteria are not the visible suite; and n_and_rationale cites the incident addendum''s budget figure ($286.52 remaining) that the 22:46Z correction superseded ($152.58 spent, $247.42 remaining) without changing n.'
  cost_usd_est: 352.02
  first_run_at: '2026-09-02T05:51:34Z'
  ledger_path: ../../ledger/multiagent-composition-v2.jsonl
  n: 144
  source: fathom
schema_version: 1
threats:
  construct_validity_proxy:
    statement: 'held_out_clean stands for ''the work is correct on what the gate did not assert''. On this bank it is one defect class (see judge_bias): the result shows the gate restoring the one type rule bank v2 withheld from the PR prompts, not benefit on work independent of the rule the gate teaches, which needs a held-out group with a second defect class that has headroom (the off-rule pair here is at ceiling in every arm). One task shape (a 5-PR feature in a 4-module toy package); the claim is about convoy''s standalone gate under external orchestration, not about convoy''s runner. The tool allow-list the scenarios declare (Read, Write, Edit, Glob, Grep, Task, Bash(python:*)) was not the instrument that ran: every stream''s init lists the platform''s registered tools including unrestricted Bash and PowerShell (30 tools in every counted stream but one pilot final-haiku session listing 26, Bash present throughout), the same across arms, which is what made the task directory reachable.'
    status: residual
  contamination_familiarity:
    statement: 'exprlang is synthetic but the bool-subclasses-int trap is a well-known Python idiom the models may carry from pretraining. Isolation was directory adjacency plus a brief rule (''read nothing outside FATHOM_PROMPTS_DIR''), and before the 2026-09-02 harness repair FATHOM_PROMPTS_DIR sat inside the repository task directory, so an agent could walk up to verify.py, solution/ and the fixture tree. tools/stream_facts.py --exposure over every counted trial''s surviving stream finds four of 128 that did: perpr-sonnet r0 and r1 read verify.py inside an implementer subagent (both held_out_clean true); placebo-haiku r1 read verify.py, type_probe.py, run_convoy_gate.py and the whole reference solution, implemented PR01 in the task directory, declared its own measurement compromised and ended after 2 of 5 dispatches (held_out_clean false); final-haiku r3 (the re-bought trial) read the driver and type_probe.py through the final arm''s gate command. perpr-sonnet r0 also wrote a full implementation and a tests tree into the repository task directory (exprlang/exprlang/*.py, exprlang/tests/*.py; no such package is committed), and placebo-haiku r1, whose stream ends 48 minutes later (11:03:52Z and 11:51:44Z), read those five module files: one counted trial read another counted trial''s implementation out of the shared task directory, so per-trial isolation failed across trials as well as into the harness. They are retained: voiding them now would be an exclusion chosen after their outcomes entered the contrasts. Sensitivity, Holm within tier-set: dropping the first three leaves perpr>placebo at 0.0007 (Haiku) and 0.0106 (Sonnet; perpr-sonnet 12/14 vs 5/16) and moves final>placebo at Haiku from 0.0366 to 0.0531; dropping all four moves final>placebo at Haiku to 0.0697 and final>control to 0.0183. The per-PR conclusions survive every version; the final-vs-placebo Haiku contrast does not. The fixture''s visible test file names the oracle by filename in its docstring, identically in every arm, which is what sent agents in all four arms hunting for it.'
    status: residual
  custom_harness_containment:
    statement: 'final-haiku and final-sonnet only: their [gate].extra command is expanded by the gated-session strategy from the bank''s task.task_dir (the repository directory holding fixtures/, solution/ and verify.py), not from the staged $FATHOM_TASK_DIR, and the fix prompt hands that command to the fix spawn verbatim. It reached an agent only when the gate went red: 26 of the 32 counted final trials had at least one fix spawn (20 of the 26 after the repair). A scan of every post-repair final stream finds no read of solution/ or of the real verify.py; the one realised traversal is final-haiku r3''s fix spawn reading run_convoy_gate.py and type_probe.py. The streams do not capture every subagent tool call, so this bounds the residual without eliminating it; the exposed arm is a treatment arm, so an unseen leak would favour final-vs-control and final-vs-placebo. Fix for the next bank: expand the gate command from the staged directory.'
    status: residual
  generalization:
    statement: one bank, one task family, one defect class, two implementer tiers, one orchestrator model, one convoy version (0.11.0's standalone gate driven by a harness script). On bank v1, where the PR prompts spelled out the type rule, control was already 3/3 in both tiers at n=3 (ledger/multiagent-composition.jsonl), so that bank showed no headroom and could detect no effect; the restriction of the claim to briefs that leave the implementer something to infer is a design inference, not a measured null.
    status: residual
  judge_bias:
    statement: 'deterministic verifier on the executed workspace, blind to arm; no LLM judge. The primary criteria are disjoint from every gate assertion as literal strings and after stripping whitespace and parentheses (tests/test_multiagent_bank.py::TestProbeDeOverlap asserts string non-overlap only). Semantically they are not independent: four of the six held-out criteria grade the one rule the gate''s probes assert and its repair hint states (booleans are not numbers), reached by different literals and, for env_bool_typing, by a different mechanism (booleans routed through env; 8 of 128 trials pass the literal criteria and fail it, two of them perpr-sonnet trials whose probe ran green). The two criteria off that rule (not_precedence_heldout, short_circuit_heldout) are at 16/16 in seven cells and 15/16 in placebo-haiku and never flip either endpoint; the primary endpoint equals the conjunction of the four bool-rule criteria in every cell, so the experiment measures one defect class.'
    status: residual
  model_version_drift:
    statement: haiku implementer snapshot attested from every Haiku trial's transcript (claude-haiku-4-5-20251001); the Sonnet orchestrator and Sonnet implementers carry only the undated alias and the ledger records no cli_version or model snapshot; the matrix spans ~38h of wall-clock across three seat re-logins, and the pooled pilot's 24 (repeats 0-2, 19% of every cell) ran arm-blocked over ~2.5 h, so time is confounded with arm for that block; the main passes only (repeats 3-15) reproduce every contrast's direction.
    status: residual
  nondeterminism:
    statement: 16 independent trials per cell, temperature as the CLI default, Wilson intervals on every cell rate; the decisive contrast's exact power at n=16 is declared (0.69). The pooled pilot both set n (Laplace-shrunk rates) and sits in the analysed cells, an internal-pilot design with mildly inflated type-I error; n was re-declared twice at interim data (25 and 48 valid trials) for reasons unrelated to outcome, with no blinding mechanism between the operator and the readout script.
    status: controlled
  prompt_format_sensitivity:
    statement: one task statement and five PR prompts byte-identical across arms; the injected briefs differ in exactly one contiguous block (asserted by tests/test_multiagent_bank_v2.py); tools, limits and env keys identical.
    status: controlled
  selection_exclusion:
    statement: 'the frozen plan had no exclusion rule. After the 2026-09-02 fixture-contamination incident (agents inside two trials edited the bank fixture through a path the harness exposed; fourteen later trials staged from it) sixteen launched trial rows were voided by an instrument exclusion defined on fixture mtime and stream facts (3 control, 4 placebo, 5 perpr, 4 final), written to the ledger at 17:09:42Z before any resumed trial and declared in the pre-registration addendum committed at 17:26:10Z, eight minutes after the first resumed trial started (17:17:42Z) — see analysis_plan.amendments. Every voided key was re-bought, so the disposition counts 128 completed trials in the frozen cells and run.n counts all 144 rows. The voided rows were 12/16 held_out_clean against 68/128 among the kept, so the exclusion removed disproportionately clean (contaminated) trials from all four arms; the include-everything contrast keeps perpr>placebo significant at both tiers. The rule was under-inclusive relative to its own root cause: the same exposed path produced oracle reads at 11:03-11:51Z that fixture mtime does not reach (see contamination_familiarity). The harness repair (staged harness dir outside the repository, a fixture integrity guard, fixture_sha on every later row) covered every arm''s orchestrator and the whole of control, placebo and perpr from the first resumed trial; it did not cover the final arm''s gate command (see custom_harness_containment).'
    status: residual
  token_length_confound:
    statement: 'the treatment brief is longer than control''s by its gate block and the treatment arms spend more per trial (medians +20% to +25%) and more wall-clock (+14% to +18%); the placebo carries a comparable ceremony block and, measured from the streams (tools/stream_facts.py --dose), the same gate-red count: about one red and one repair round per trial in both perpr (1.19 and 1.06 reds) and placebo (0.94 and 1.06). The arms are matched on reds only: perpr still runs about 1.2 more Agent dispatches, spends about 10% more and takes 13-19% more wall-clock per trial than the placebo (medians), so the extra-work channel is bounded, not eliminated. Two asymmetries the placebo does not control remain: the repair actor (perpr dispatches a fresh implementer subagent with the repair_brief, 7.2 dispatches per trial against 6; placebo repairs inside the orchestrator) and the brief''s content (perpr''s block says the gate adds two type-contract checks the visible suite lacks; placebo''s says nothing of the kind), each a channel for the same rule. Control dispatches a fresh implementer for every PR and reads 4/16 and 2/16, so a fresh implementer without the brief does not find the defect; that is an argument, not a measurement. An equal-content placebo with a fresh-subagent repair is the next design.'
    status: residual
tier: measurement
```
