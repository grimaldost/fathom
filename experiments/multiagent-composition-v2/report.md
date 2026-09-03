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
  - held_out_clean_independent: verdict=exploratory_signal, paired=False
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
- Threats: 9 declared, 6 residual

## Record (canonical, machine-checked)

```yaml
analysis_plan:
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
  timestamp: 2026-09-02 13:00:00+00:00
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
    verdict: exploratory_signal
run:
  attestation: 'per-trial transcripts under streams-multiagent/2026-09-02-pilot-v2 and streams-multiagent/2026-09-02-main-v2 (FATHOM_STREAM_DIR); fixture_sha on every row written after the fixture-contamination incident; readout by tools/readout_multiagent.py (voids applied). run.n counts every trial row in the ledger including the 16 voided ones; the disposition counts the frozen cells. Freeze chronology, disclosed: this typed record was committed at 66c0982 on 2026-09-02 13:41:47Z, after the pooled pilot''s first trial (05:51:34Z) and the main matrix''s first trial (12:47:29Z), so ER-ANCHOR fails on this record and is left failing rather than re-pointed. The prose pre-registration the record transcribes was committed before each wave it governs: 60ee721 (04:59:50Z; the eight cells, the endpoints, the four contrasts and Holm family, the pilot n) and ea2cd11 (12:45:49Z; n=16 per cell, the pass schedule, the caps). The frozen subset here reconciles against 66c0982 (ER-PREREG clean).'
  cost_usd_est: 352.02
  first_run_at: '2026-09-02T05:51:34Z'
  ledger_path: ../../ledger/multiagent-composition-v2.jsonl
  n: 144
  source: fathom
schema_version: 1
threats:
  construct_validity_proxy:
    statement: held_out_clean stands for "the work is correct on what the gate did not assert"; it is one task shape (a 5-PR feature in a 4-module toy package) and the claim is about convoy's gate under external orchestration, not about convoy's runner.
    status: residual
  contamination_familiarity:
    statement: exprlang is a synthetic package but the bool-subclasses-int trap is a well-known Python idiom the models may carry from pretraining; no arm primes another (fresh workspace per trial, prompts-only visibility via FATHOM_PROMPTS_DIR).
    status: residual
  generalization:
    statement: one bank, one task family, two implementer tiers, one orchestrator model, one convoy version; the v1 pilot showed the effect vanishes when the PR prompts spell out the rule, so the claim is scoped to briefs that leave the implementer something to infer.
    status: residual
  judge_bias:
    statement: deterministic verifier on the executed workspace, blind to arm; no LLM judge; the primary criteria are disjoint from every gate assertion as literal strings and after stripping whitespace/parentheses.
    status: controlled
  model_version_drift:
    statement: haiku implementer snapshot attested from transcripts (claude-haiku-4-5-20251001); the Sonnet orchestrator and Sonnet implementers carry only the undated alias in transcripts and the ledger records no cli_version or model snapshot; the matrix spans ~20h of wall-clock across seat re-logins, and the pilot's 24 were arm-blocked.
    status: residual
  nondeterminism:
    statement: 16 independent trials per cell, temperature as the CLI default, Wilson intervals on every cell rate; the decisive contrast's exact power at n=16 is declared (0.69).
    status: controlled
  prompt_format_sensitivity:
    statement: one task statement and five PR prompts byte-identical across arms; the injected briefs differ in exactly one contiguous block (asserted by tests/test_multiagent_bank_v2.py); tools, limits and env keys identical.
    status: controlled
  selection_exclusion:
    statement: the frozen plan had no exclusion rule. After the 2026-09-02 fixture-contamination incident (agents inside two trials edited the bank fixture through a path the harness exposed; thirteen later trials staged from it) sixteen launched trial rows were voided by an instrument exclusion defined on timestamp and stream facts and declared in the pre-registration addendum before any resumed trial; the fixture was restored, the harness repaired (staged harness dir outside the repository, a fixture integrity guard, fixture_sha on every later row) and every voided key re-bought, so the disposition counts 128 completed trials in the frozen cells and run.n counts all 144 rows. The exclusion is blind to outcome (it removed 2 control, 4 placebo, 5 perpr, 5 final rows by the clock, not by result) but it is an exclusion the plan did not foresee, so this threat is residual, not controlled.
    status: residual
  token_length_confound:
    statement: the treatment brief is longer than control's by its gate block and the treatment arms spend more turns (per-trial cost +20% to +48%, wall-clock +25% to +50% in the pilot); the placebo arm carries a comparable ceremony block and is the length/iteration control, but no equal-length no-information brief beyond it was run.
    status: residual
tier: measurement
```
