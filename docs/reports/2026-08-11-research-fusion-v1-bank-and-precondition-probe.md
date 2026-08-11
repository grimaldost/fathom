# The multi-substrate research gate — a bank, the free gates, and a precondition probe

- **Date:** 2026-08-11 (wave 2, branch `eval/wave-2`). Bank: `research-fusion-v1`; arms
  `bare` / `fusion` in `scenarios/research-fusion/`.
- **Gate:** mantis-research's **MANT-B36** — blind A/B the multi-substrate research tool against a
  single-provider run, on *how often a divergence changed a decision* and *cost per decision
  changed*, against the landscape brief's counter-claim that one good model dominates fusion on
  quality-per-token at **8.8× the cost**.
- **Verdict on the gate: still-unmeasured.** What this wave adds is a validated bank, the two arms,
  the free gates run, and a direct probe of the moat's *precondition*. What it does not add is the
  decision-value measurement, and the reason is recorded below rather than deferred silently.

## Why the bank measures a weaker thing than the row asks, deliberately

The row's two quantities are both outside a verifier's reach. "A divergence changed a decision" is a
counterfactual: it compares the decision a consumer *would* have made from the single-provider brief
against the one they made with the divergence surfaced, and no verifier observes a counterfactual.
The honest substitute the gate-banks spec prescribes is two-arm **decision correctness**, with
"changed the decision" inferred only where the arms disagree and the fusion arm is right — and that
needs questions whose answers are **known post-hoc and were not obvious at the time**.

That question set does not exist, and it is the long pole the spec already named. It could not be
authored honestly inside this wave either: the tempting shortcut is a set of crisp technical
questions with one right answer, and that set would **ceiling** — both arms score 100%, the bank
measures nothing, and the null it manufactures is precisely the outcome the retirement decision is
leaning toward. Writing it would reproduce the exact failure FATH-B02 exists to prevent.

So `research-fusion-v1` measures the **precondition** of the moat claim: given contested questions,
does a real fan-out produce a well-formed epistemic sidecar whose cross-substrate divergences join
back to their sources? That is deterministic, blind, and — the property that makes it worth
building — **able to reject the claim on its own terms**. If a fan-out over genuinely contested
questions returns no divergences, or divergences with one side, or substrate labels joining to
nothing, then the surface the moat rests on is not being produced and no decision-value study is
worth buying yet.

**A structurally perfect sidecar is not evidence that fusion beats one good model.** It is evidence
that the thing fusion is supposed to produce exists. The bank says so in its own `bank.toml`.

## The bank

```
tasks/research-fusion-v1/
  bank.toml            dataset_version = 1, holdout = ["cost-per-outcome"]
  fusion_verify.py     the shared verifier — 11 criteria, stdlib only
  <question-id>/       task.toml · fixtures/question.txt · verify.py · solution/
```

Four questions, three dev and one sealed holdout (ADR-0005 — this bank feeds a retirement
decision). All four are **contested by construction**, not factual: universal vs per-platform
lockfiles, `typing.Protocol` vs ABCs as the default seam, one long session vs a governed series for
a ten-PR feature, and price-per-token vs cost-per-successful-outcome. A question with one right
answer gives a fan-out nothing to disagree about.

The eleven criteria split into two classes the report must keep apart:

| class | criteria | how to read it |
|---|---|---|
| **availability** | `multi_substrate`, `divergences_present` | only an armed arm can produce a cross-substrate divergence at all — the bare arm scores 0 **by construction**, which is a floor, not a result |
| **well-formedness** | `sidecar_required_fields`, `sidecar_question_matches`, `divergences_well_formed`, `substrate_source_join`, `claims_present`, `verification_queue_present` | given a sidecar, is it internally consistent? this is where the claim can fail on its own terms, and it is the load-bearing class |

Gate (verifier exit 0): `brief_written AND sidecar_written AND sidecar_parses`.

### The free gates, run

| Gate | Result |
|---|---|
| `uv run fathom validate research-fusion-v1` | **8 pass, 0 fail, 0 warn, 4 unverifiable** — 11/11 criteria start false on every unmodified fixture, and the reference solution satisfies the verifier on all four (so a null cannot be an unsatisfiable-verifier artifact) |
| `uv run fathom smoke` | ALL PASS (8/8), earlier this wave |
| `--dry-run` | see the blocker below |

## The blocker the cost plan did not have: this mount is not like the others

The armed arm mounts the research plugin, and its tools are **MCP-served** — the exact configuration
that produced the recorded unarmed-arm result (23 tools denied across 9 armed trials, scorecard 9/9,
`Infra Errors: 0`). The arm therefore allow-lists the long spelling,
`mcp__plugin_mantis-research_mantis-research__research`, and `fathom verify-arming` is a hard
precondition rather than a nicety.

It could not be verified this wave, for a reason worth writing down: **every other mounted plugin in
this repo is prose-only.** This one ships an MCP server whose command is
`uv run --project ${CLAUDE_PLUGIN_ROOT} python -m mantis_research.interface.mcp`, so a vendored mount
tree needs a resolvable Python environment materialised **inside the committed bank tree** at spawn
time. No bank here has needed that, ADR-0006 requires a real tree for mount fidelity, and creating a
virtualenv under `tasks/` on first spawn is a git-hygiene problem as much as a latency one. That
integration is the unbought half of this gate, and it is engineering, not budget.

### An instrument defect this walked into

With the mount tree absent, `fathom run --dry-run` printed

```
warning: skipping scenario fusion.toml: [Errno 2] ... plugin.json
fathom run: bank=research-fusion-v1  scenarios=1  tasks=3  repeats=1
planned:  3 trials (0 already done)  ceiling: $6.00
```

— it **dropped the treatment arm and planned the matrix anyway**. On a paid run that buys a full
control arm, appends a ledger and renders a scorecard with no treatment in it, and the
`verify-arming` pre-flight cannot catch it because a scenario that failed to load never reaches the
list of arms to verify. This is FATH-B01's class, not a papercut: an arm that is *absent* produces a
confident number just as an arm that is *unarmed* does. Filed as **FATH-B49's sibling, FATH-B50**.

## The precondition probe

Rather than leave the precondition unexamined, the tool was called directly on one of the bank's own
contested questions, and its output measured against the bank's verifier.

**Caveat stated first: this is not a blind A/B and settles nothing about MANT-B36.** It has no
control arm, n = 1, and it exercised the **installed plugin cache (0.1.2)**, not the merged 0.2.0
worktree — the same staleness that runs through this whole wave.

### What the probe found: the fan-out is fast, the synthesis stage did not finish

| step | outcome |
|---|---|
| `dry_run=true` (free, `cost_usd = 0`) | **orchestration is wired**: three OpenRouter substrates + synthesis, both stages exit 0, and the manifest returns the paths it will write |
| real run, `assurance="fast"`, substrates `openai` / `deepseek` / `google` | **fan-out completed in ~3 minutes** — all three substrate briefs written (20,096 / 8,640 / 5,556 bytes) |
| synthesis stage | **did not complete.** The MCP call aborted at the client's 1800 s idle timeout with no progress; the server's synthesis child (a local `claude -p`) was still alive **49 minutes** later with no synthesis and no `sidecar.json` on disk, and was terminated |

So the precondition is **unverified, not refuted**: the bank's six well-formedness criteria never got a
sidecar to score. What the probe does establish, and what the cost plan did not have, is where the
latency lives — the multi-provider fan-out this tool exists for is the *cheap, fast* part, and the
single-seat synthesis that follows it is the long pole.

**Two things this makes concrete:**

1. **The 60-trial matrix is not wall-clock feasible as designed.** At one observed run failing to
   finish inside 50 minutes, 60 armed trials is well over a day of sequential wall-clock before any
   repeat, and `trial_timeout_s` would have to exceed anything in this corpus (the current bank sets
   2400 s, which this run would already have blown). Cost was never the binding constraint here.
2. **The silent-run defect is real and is exactly what the merged version fixes.** The installed 0.1.2
   reports nothing between call and return, so a client cannot distinguish a long run from a hang and
   answers by giving up — which is precisely what happened. The merged 0.2.0 adds progress reporting
   over the MCP context for this reason. **The probe therefore also demonstrates the wave's running
   theme: the installed cache is not the merged tool**, and a measurement pointed at the cache would
   have recorded a defect its subject had already fixed.

One incidental observation worth a line: the run's outputs are written **inside the installed plugin
cache** (`~/.claude/plugins/cache/mantis-research/mantis-research/0.1.2/outputs/…`). A plugin cache is
a throwaway tree — this repo's own `_resolve.py` refuses `FATHOM_HOME` inside one precisely so a
longitudinal record cannot be lost to a re-install — so research artifacts accumulating there are one
`plugin update` away from disappearing.

## A confound the bank must carry into any future run

The tool's MCP result is a **bounded projection** of its sidecar (`core/sidecar.py`
`project_for_agent`). It carries `claims`, `divergences`, `source_overlaps`, `verification_queue`,
`agreements_worth_verifying` and `coverage_notes`; it does **not** carry `question`, `generated_at`,
`sources` or `source_citations`, which stay in the on-disk artifact whose path the manifest returns.

So `divergences_present`, `divergences_well_formed`, `claims_present` and
`verification_queue_present` are satisfiable from the tool result alone, while
`sidecar_required_fields`, `multi_substrate` and `substrate_source_join` require the arm to **read
the on-disk sidecar**. That is a genuine property worth measuring — can a consumer reconstruct the
epistemic record from what the tool hands it? — but it is a property of the agent-facing projection,
not of the fan-out, and a report that scores the two together will misattribute the result. The task
instruction was made arm-neutral about it ("if any tool returns a path to a machine-readable record
of its own run, read that file") so the bare arm is not advantaged by a trap the armed arm walks
into.

## Cost plan, restated against what this wave learned

| | skeleton (2026-08-11) | after this wave |
|---|---|---|
| Matrix | 2 arms × 10 questions × 3 repeats = 60 trials | unchanged in shape; the bank ships 3 dev + 1 holdout question and needs the other six |
| Estimated | $40–150, most likely ~$70 | unchanged, and still the most expensive item across the four gates |
| Blocking work | a question set with defensible post-hoc answers | **that, plus** vendoring an MCP-serving plugin tree with a materialisable environment, plus a `verify-arming` pass on the long tool spelling |
| Wall-clock | not costed | **the binding constraint, newly measured**: one `fast` run did not finish inside 50 minutes (fan-out ~3 min, synthesis the remainder), so 60 armed trials is over a day sequential and needs a `trial_timeout_s` beyond anything in this corpus |
| Unmeasurable without extra accounting | the armed arm's second-provider spend | confirmed: `OPENROUTER_API_KEY` is present so the arm *would* run, and `cost_usd_est` cannot see a cent of it — the 8.8× comparison needs provider-side cost recorded separately |

**Recommendation, unchanged from the skeleton and now with evidence behind it:** author the question
set as its own unpaid deliverable and have it reviewed before any spend. The bank, the arms and the
verifier now exist and validate, so that is the only remaining long pole besides the mount
integration.

## Ledger

No fathom trials were run for this report; `ledger/research-fusion-v1.jsonl` does not exist. What
this commits is the bank, its verifier and reference solutions, the two arms, and this report.
