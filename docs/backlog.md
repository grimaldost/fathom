# fathom — engine backlog

Open improvements to the engine: its code, gates, documentation and packaging. Analyses, banks
and their results are not tracked here; they belong to the data root that runs them.

Each item has a stable id (`FATH-Bnn`), a one-line claim, the cause and the proposed change, and
an effort estimate: **S** is one focused change, **M** a small series with tests, **L** a design
decision plus a multi-PR series. Items are grouped by area and ordered by leverage within each
group. Ids are never reused, so the numbering has gaps. A closed id that code or another document
still cites is listed under "Closed ids" at the end, so the reference resolves. A row that needs
confirmation names where to look first to validate it.

## Measurement correctness

These can put a wrong number on a scorecard without any visible error, so they come first.

**FATH-B51 — Economy on the delegated path is a floor.** *(M)*
A trial that delegates work through the Task tool records the parent session's usage; the
subagents' own consumption does not reach the ledger. Economy for a delegating arm is therefore a
lower bound of unknown depth, and the shortfall need not be the same across arms. Change: fold
subagent usage into the trial's economy at parse time, and record which stream events were
folded so the figure can be audited. Until then, report delegated economy as a floor and draw no
arm-to-arm economy conclusion from it. Building it needs a delegating-session stream fixture,
synthetic or captured from one small spawn, added under `tests/fixtures/`; after that the work
and its tests need no paid spawns.

**FATH-B49 — Economy views pool two configurations that share an arm name.** *(S)*
`report.py` maps each `config_hash` to its arm name and keys every view by the name. Pass rates
keep the latest trial per cell, but Economy, Efficiency and Arm Health sum the runs of every hash
that carries the name. Re-running an arm after changing its injected content (a new hash, the
same name) is the normal shape of a re-validation, and it averages the new trials' economy with
the old ones, which can make a healthy arm look truncated. Change: aggregate on `config_hash` and
render the name as a label beside it, with a hash prefix when one name carries more than one
hash; or warn when a scoped `dataset_version` holds two hashes under one name.

**FATH-B50 — A scenario that fails to load is dropped with a warning, and the matrix runs
without it.** *(S)*
`fathom run` prints `warning: skipping scenario …` and plans the arms that did load. A treatment
arm whose plugin tree is missing therefore drops out of a paid matrix, leaving a control-only
ledger and a scorecard with no treatment in it. The arming pre-flight cannot catch this, because
an arm that never loaded is not on the list it checks. Change: refuse the run with a dedicated
exit code when any scenario file fails to load, with an explicit flag to proceed anyway, and
print the resolved arm count beside the file count on the plan line.

**FATH-B52 — `verify-arming` can report a working MCP arm as unarmed, and its only escape is
the blanket override.** *(S)*
The probe reads each declared server's status from the CLI's init event, which is emitted at
session start. A stdio server that takes a few seconds to connect reads unhealthy in that
snapshot even when it connects and its tools are then called. The run refuses with
`EXIT_UNARMED`, and the documented way out is `--skip-arming-check`, which disables the check on
exactly the arms where an unarmed run is hardest to notice afterwards. Change: pass when the
server's last-seen status in the probe stream is healthy (or poll for a bounded time), keeping
the init sample as the fast path; better, corroborate with an observed `mcp__*` tool call that
was not denied (`arming.tools_served_by` already maps tools to servers). The refusal should name
the server and its last-seen status, and offer a scoped wait before the blanket flag.

**FATH-B56 — A relative `[tools] repo` resolves against the process working directory.** *(S)*
`resolve_repo_invocation_cmd` (`scenario.py`) resolves the path with `Path(repo).resolve()`,
against fathom's working directory rather than the scenario file that wrote it. It works only
when fathom runs from the directory the author had in mind. From a worktree, from a checkout laid
out differently, or with `--home` pointing at a data root from elsewhere, it names a directory
that does not exist and the series arm cannot start. `[context] inject` and `[settings] inject`
already resolve against the scenario file. Change: do the same for `[tools] repo`. The resolved
string enters `config_hash`, so if that would move committed hashes, take the smaller change
instead: refuse at resolution time when the resolved repo does not exist, naming the path.

**FATH-B67 — `validate` proves a bank can discriminate on its fixture, not that it does against
a live bare arm.** *(M)*
The fixture check shows every task leaves the arm something to do; it cannot show that a bare
arm actually fails. A bank whose tasks are easy enough for every arm passes validation and then
measures nothing, which is found only after the spend. Change: an optional pre-spend screen, a
few bare-arm trials per task, that warns when the bare arm already passes, phrased as "bare and
armed are predicted to tie". FATH-B08 is the post-hoc half of the same problem.

**FATH-B63 — A ledger's cost is never reconciled against a recomputation.** *(S)*
`cost_usd_est` is the CLI's reported figure (with `cost_source` saying whether one was
reported), and nothing in the engine recomputes it. The reported figure folds every token
bucket into one number, and cached input can dominate a trial whose system prompt carries an
injected treatment, so an error in it would scale with the quantity under test. Change: a
`fathom reconcile` check that recomputes each run row's cost from its recorded usage buckets
and a dated price table (FATH-B16), reports the recomputed-to-reported ratio per ledger, and
flags rows outside a stated band. It is only exact for rows that carry `config_preimage`, and
it needs a decision on whether subagent spend belongs in the parent's usage (FATH-B51) before
its band can be set.

**FATH-B79 — The scorecard counts a run with no reported cost as free.** *(S)*
A run row whose spawn consumed tokens but reported no cost is written with `cost_source = "none"`
and `cost_usd_est = 0.0`. The adapter warns when it writes such a row, but `report.py` sums
`cost_usd_est` without reading `cost_source`. An arm's USD, and any comparison built on it, then
reads low with nothing on the page saying so. `calibration.py` (`_arm_cost`) sums the same field the
same way, so the calibration views count the row as free too. Change: count the `cost_source =
"none"` rows per arm, render that arm's USD as a floor with the count (or as unknown), and show the
count in Arm Health, in `report.py` and `calibration.py` alike. This is a report-rendering change
that ships independently of FATH-B63, which is a reconcile check; the two pair well.

**FATH-B11 — Environment identity is declared, not fingerprinted at execution time.** *(M)*
A plugin mounted from a path dependency can serve stale code (a cached wheel, say) under an
unchanged `config_hash`, and new server code behind a `file://` mount forks neither the hash nor
the resume key, so a re-run can resume-skip and report old scores as if they measured the new
code. The mirror case is task content (instruction, `verify.py`, fixtures) changing without a
`dataset_version` bump. A related cause: a mount or inject that resolves outside the data root,
or to an untracked path, makes `config_hash` depend on bytes the data root's history does not
hold. Change: record the resolved package version or source hash of a path-dependency server at
run start and warn or refuse when it changed while `config_hash` and `dataset_version` did not;
warn in `validate` when task content changed without a bump, and when a mount or inject resolves
outside the data root or is untracked.

## Operations

**FATH-B55 — A matrix longer than the credential's life only survives if it is chunked.** *(M)*
Each spawn copies the shared OAuth credential into a throwaway `CLAUDE_CONFIG_DIR` (ADR-0004),
the CLI refreshes it inside that spawn, and the refreshed credential is discarded with the
directory. Two consequences: concurrent spawns can redeem the same refresh token and invalidate
each other, and a matrix that runs longer than the credential lives fails part-way however good
the launch-time check was. Change: document the chunked, resumable run shape in the cost
section operators read (resume is free, so re-invoking per block costs nothing); add a `--chunk
N` that stops cleanly on a stated boundary and prints the resume command; and either copy the
config once per run or write the refreshed credential back, so spawns stop racing each other's
refresh.

**FATH-B12 — `smoke` takes no model or effort.** *(S)*
`smoke` does not accept `--model` / `--effort`, which blocks a cheap acceptance probe before a
paid run at a non-default model or effort. The row's other gap, output not forced to UTF-8, is
closed: `fathom` and `fathom smoke` write stdout and stderr as UTF-8 at their entry points.

**FATH-B64 — `smoke` checks isolation and blindness but most of the operational surface not at
all.** *(M)*
The concurrency-exclusion check shipped with the run lock (0.6.0). Still missing: a rail
actually refuses at a trivially low cap; a gate naming an unresolvable path refuses at validate
time (FATH-B54); an MCP-served arm arms after a bounded wait (FATH-B52). Each check ships in the
same change as the mechanism it checks; a check written after its mechanism tends to be written
to pass.

**FATH-B59 — Nothing checks for an orphaned process holding the virtual environment.** *(S)*
On Windows a stale `fathom.exe` or `python` process can hold files in the venv, and the failure
surfaces as an unrelated `uv sync` error. Change: an orphan-process pre-flight in `fathom smoke`,
as part of FATH-B64's group.

## Reporting

**FATH-B09 — Truncated trials drop out of the per-criterion table.** *(S)*
A trial cut off by `max_turns` or its timeout is `errored`, so its criteria never reach the
per-criterion table, and partial compliance is visible only in the ledger. Separately,
`infra_error` is a field that `report.py` guards against and nothing writes. Change: give budget
exhaustion its own `TrialStatus` (`strategies/base.py`) and show those trials in the
per-criterion table; delete `infra_error` and its guards, accepting the change to the "Infra
Errors" column and the golden file.

**FATH-B27 — Economy is reported per trial, not per successful outcome.** *(S)*
A cheaper arm with a lower pass rate can cost more per passing trial, and the scorecard leaves the
division to the reader. Add a cost-per-passing-trial column to the Economy table.

**FATH-B19 — `fathom report` takes none of the directory flags `fathom run` accepts.** *(S)*
`report` reads `tasks/<bank>/` and `ledger/<bank>.jsonl` under the data root, while `run` also
accepts `--tasks-dir`, `--scenarios-dir` and `--ledger-dir`. A bank run from an alternate tasks
directory renders a scorecard with its calibration section silently missing. Thread the same
flags through `report`, or warn on the asymmetry.

## Ledger and schema

**FATH-B18 — The schema has no notion of a factor.** *(S)*
Task tags (`[tags]` in `task.toml`) and per-tag grouping in the scorecard are built
(CHANGELOG, 0.9.0). Remaining: a tag that carries a per-task inject override, so a per-task
hint no longer needs one bank per value.

**FATH-B47 — Every trial gets exactly one user prompt.** *(M)*
The adapter runs one headless session per trial and removes its config directory afterwards, so a
scenario cannot send a second prompt, and any question about what happens on a later turn cannot
be asked. Change: a per-trial config-directory lifecycle that survives more than one spawn, a
continue-session mode on the adapter, and a strategy that sends `prompts = [...]` in order. Scope
it to the smallest change that makes a two-prompt arm possible; FATH-B18's tags can carry a
per-task prompt sequence.

**FATH-B22 — The sealed-holdout invariant is easy to satisfy vacuously.** *(S)*
`holdout` is a required key that an empty list satisfies, and nothing exercises the
`--include-holdout` path end to end. Change: either make a non-empty `holdout` a validation
error for banks that feed a tuning loop (a bank-level flag would say which), or state in
ADR-0005 that the invariant covers promotion-decision banks only; and add an end-to-end test that
runs a holdout task into a ledger and shows it reported separately.

**FATH-B16 — Model data the engine mirrors from upstream is undated and untested.** *(M)*
`calibration.py` carries `FAMILY_TIERS` and `THRESHOLDS`, a copy of a model-routing policy's tier
map, with no date and no test that fails when it goes stale. The cost audit (FATH-B63) needs a
per-model price table, which would go stale the same way. Change: one dated data file holding
the tier map and, with FATH-B63, the prices; a test that fails once its review date passes; and
an unknown model id recorded as `null` with a warning rather than priced at a default rate,
which would give a plausible but wrong figure for a new model. Keep tokens and turns as the
primary economy currency; the price table exists for auditing reported cost, not for producing
it.

## Documentation and surface

**FATH-B10 — Authoring knowledge that is not written down has to be rediscovered by each
author.** *(S)*
The authoring guide is split into `skills/fathom-eval/reference/authoring.md` (the data root,
the bank and task schemas, the verifier, running and reading the scorecard), `arming.md` (arms,
their tools and treatments, `config_hash`, series arms) and `bank-design.md` (making a bank
discriminate, the checklist), each with a line budget in its header, so an addition past the
budget must displace something. Plugin hooks in headless `-p`, discrimination by scale and turn
budget, the order `--limit N` cuts in, how a mounted plugin's MCP tools are named, and an answer
key kept beside the verifier are written there. Still not written anywhere: the arm can be
given the interpreter a verifier shells out to through `[env] PATH`. Change: write it into
`arming.md`, within that file's budget.

**FATH-B48 — The skill's trigger description overlaps with skill-evaluation tools that do a
different job.** *(S)*
`fathom-eval` triggers on "A/B this skill". Measuring whether a skill description fires on the
right prompts (trigger recall and specificity) is a different measurement that other tools own;
fathom measures outcomes on a task bank, scored by verifiers. Add a negative trigger that says
so, and state which side owns the with/without comparison.

**FATH-B29 — Two CLI naming and ergonomics fixes.** *(S)*
`--no-engine-boundary` reads as disabling a safety control when it only skips a check group;
rename it `--skip-engine-check` (moot if FATH-B36 retires the group). Consider `--limit-per-arm
N` beside `--limit`, so a pilot cannot spend its whole budget on the first arm; document the
scenario-major behaviour first (FATH-B10).

**FATH-B26 — A second runner adapter would make the vendor-neutrality claim true.** *(L)*
The `Runner` protocol is in place, but `claude-cli` is the only adapter, so the claim that the
framework is not coupled to the subscription CLI (ADR-0001) is a design intent that nothing
exercises. State it as "designed for, not yet exercised" now (S), and build a second adapter for
another agent CLI when a question needs a non-Claude arm.

**FATH-B81 — ADR-0008 has stayed Proposed with nothing built on it.** *(S)*
ADR-0008 adds oracle quality as a third calibration factor crossed against model tier, and states
that its Proposed status is the build gate; ADR-0009 refers to a slicer gated behind it. A
proposal left open indefinitely reads as a live plan. Change: decide it. Either accept it with
the slicer it gates (a factor slicer in the calibration views), or withdraw it, with the reason
recorded. Then update the references in ADR-0009 and in the authoring guide's calibration
section (`bank-design.md`, section 9).

## Retire or fold

Each candidate names its replacement.

**FATH-B34 — Wire or remove the pairwise judge.** *(S)*
`grading/judge.py` ships dark: no strategy, `cli.py` or `report.py` path calls it, yet it costs
a `GradingRecord` kind in the ledger schema, a `report.py` path that renders a "Pairwise vs
Bare Anchor" section when the ledger holds grading rows (no fathom command writes them), and
caveats repeated across the docs. Either wire it behind a validation against human
adjudication, or delete the module, its test, `GradingRecord`, the scorecard section and the
caveats. Verifier-expressible criteria carry every verdict today. The code stays recoverable
from history.

**FATH-B35 — Fold `gated-review` into `gated-session`.** *(S)*
`gated-review` is `gated-session` plus one review pass, implemented as a `with_review` flag on the
same executor, yet it is a distinct strategy name in the docs and the parser. Replacement: a
`review = true` key on `gated-session`, with the old name accepted for one release so committed
`config_hash`es stay interpretable.

**FATH-B36 — Keep or retire the `series` strategy on the strength of a measurement.** *(M)*
It is the largest strategy, the one sanctioned non-adapter model call, a smoke check group and
an engine contract spec. Its remaining claim is dependency-ordered execution under per-phase
budgets with gates that can reject "done". Retire it, with the contract spec and the smoke
group, only if a measurement in a data root shows that claim adds nothing over a gated
single-session arm; if it goes, the smoke check count drops by one and `--no-engine-boundary`
goes with it.

**FATH-B33 — Fold `/fathom:plan` into `/fathom:run`.** *(S)*
`/fathom:plan` is `fathom run <bank> --dry-run`, and much of `/fathom:report` repeats the skill's
scorecard-reading section. Replacement: `/fathom:run` dry-runs first and asks for confirmation
before spending; `/fathom:report` points at the skill for interpretation.

**FATH-B32 — Retire the MCP server, or state what it adds.** *(S)*
Its tools shell out to the CLI and return its output, which an agent with a shell can do
directly, and `smoke` is the one of them that spends money. The server's own logic is resolving
and vetting the data root before it runs the engine. Replacement: the CLI plus the slash
commands, with `fathom report` printing the scorecard path on its last line. Removing the server
also removes the plugin's only third-party runtime dependency.

**FATH-B37 — Fold the generic `docs/method/` files to pointers at the method kit.** *(S)*
`definition-of-ready.md`, `definition-of-done.md`, `pre-mortem-prompt.md`, `reflection-triage.md`
and the generic half of `review-checklist.md` are copies of keel's portable method kit, and each
copy can drift from its source. Replacement: short pointers to keel's originals, each kept at its
current path so links into it still resolve. Keep what is specific to this repository:
`method-bindings.md`, the project items in `review-checklist.md`, `measured-terms.md`, and the
notes in `series-toml-skeleton.md` on what fathom pins and strips.

## Later

Deferred work with a known shape. Each narrows a route that the authoring guide describes
and leaves to the bank author until it lands (`authoring.md` section 7, `arming.md` sections 10
and 12), so none of them blocks a correct run.

**FATH-B70 — A gate that times out is stopped only as far as its process tree reaches.** *(M)*
`run_shell_bounded` stops the tree it can find: on Windows, `taskkill /T` from the shell, which
misses a process whose parent has already exited; on POSIX, the process group the shell leads,
which a process that moves to a group of its own leaves. Such a process runs on while the fix
spawn works in the same workspace, and can still write there when the verifier copies it;
the drain after the stop gives up waiting for it after 10 seconds. Change: start each gate
command in a container that holds every descendant (a job object on Windows, a session or
cgroup check on POSIX), and stop the container, and confirm it is empty, before the fix spawn
starts. A unit test with a gate that detaches a child shows the gap and the fix.

**FATH-B71 — The verifier runs under fathom's interpreter, which can lie in the data root.**
*(S)*
The verifier's environment names no withheld directory, but it runs under fathom's own
`sys.executable`. When fathom runs from a virtual environment inside the data root, that path
is on the verifier's command line and is `sys.executable` inside it, so a child the verifier
starts with `sys.executable`, as the authoring guide's example does, runs from the data root
too. Section 7 of the guide documents the route and asks for fathom to be installed outside
the data root. Change: run the verifier under the interpreter the virtual environment was
created from (the verifier contract allows the standard library only, so it needs nothing
from the environment), or have `fathom validate` warn when the interpreter lies in a withheld
directory.

**FATH-B72 — Hook scripts named by `[settings] inject` are not staged.** *(M)*
Each trial spawn gets its own copies of the arm's `[context]` file and `[plugins]` directories,
so its command line names no path in the data root. A `[settings]` file is copied into the
spawn's config directory as written, and its hook commands run as written, so a hook script
kept in the data root puts that path in the process table and in the settings file the agent
can read. The guide asks authors to keep such scripts elsewhere or inline. Change: let an arm
declare the scripts its hooks run, copy them per spawn beside the settings file, and
substitute the copies' paths into the hook commands; hash the scripts' content into
`config_hash`, which gives only those arms a new hash.

**FATH-B73 — A series engine's checks can leave files in the scored workspace.** *(M)*
The gated strategies remove whatever a gate command creates in the workspace once it exits.
A series engine runs its own `[[checks]]` in the trial workspace, and fathom removes nothing
after them, so a test runner's cache or compiled bytecode can reach the result view and tell
a series trial apart from the others. Change: have the engine run its checks against a
snapshot of the workspace (a copy, or a worktree of the commit under test) that it discards
afterwards, as a clause of the series-engine contract
(`docs/specs/2026-07-03-series-engine-contract.md`). Until then the authoring guide
(`arming.md`, section 12) asks for checks that write nothing into the workspace.

**FATH-B74 — A series arm whose engine checkout lies inside the data root names the data root.** *(S)*
The engine command carries `[tools].repo` as an absolute path, and running the engine from a
virtual environment in that checkout puts the data root on `VIRTUAL_ENV` and `PATH`. Change:
refuse, or warn, when a series arm's repo resolves inside the data root, and say in the
authoring guide (`arming.md`, section 12) that the engine checkout lives outside it.

**FATH-B75 — fathom's own process holds the arm name during a trial.** *(S)*
`FATHOM_STREAM_TAG` and `FATHOM_STREAM_DIR` are set in fathom's environment for the whole
trial. Children never receive them, but a process that can read another process's
environment could. Change: pass the tag and directory to the adapter as arguments instead of
environment variables.

**FATH-B76 — A plugin's content hash and its staged copy can disagree on symbolic links.** *(S)*
The mount's tree hash does not descend into symlinked directories, while the staged copy
follows them, so two mounts that differ only below a symlink share a `config_hash`. Change:
hash what the copy contains, or refuse symlinked directories in a mount.

**FATH-B77 — `fathom validate` decodes gate output in the locale, trials in UTF-8.** *(S)*
Change: decode both as UTF-8 so validate runs the gate exactly as a trial does.

## Watch list

Rows with one occurrence and a concrete shape. Each needs a second occurrence, or a first one
with a real cost, before it is promoted. This list is FATH-B31.

- A gated-strategy arm on a bank whose tasks declare no `[gate]` degrades silently to a single
  spawn.
- Infrastructure halts are not classified further (expired credential, usage limit, stall).
- `trial_timeout_s` is enforced in-process; a hung child that no in-process deadline reaches
  needs an out-of-band wall-clock timer. The likeliest of this list to be promoted.
- Gate telemetry lives in a free-text `detail` rather than in ledger columns.
- `max_fix_attempts` is not threaded through, so repair depth cannot be swept.
- The result view is not kept when a trial fails (revisit if persisted verifier output proves
  insufficient).
- No warning when a vendored plugin tree's `@version` does not match what it claims.
- A design-effect-inflated Wilson interval as a mechanical guard, if stating the clustering
  caveat beside K proves insufficient (see FATH-B46).
- A reference checker for the docs.

## Declined

Recorded so they are not reopened without new evidence.

- **FATH-B40 — A flag to emit a record fragment for downstream consumers.** Readers can use the
  ledger directly, and FATH-B07 serves them at lower cost. Reopen if a consumer appears that
  cannot read the ledger.
- **FATH-B41 — `arm_tier` substring resolution misclassifying a mixed-family arm name.** Harmless
  while such arms live only in banks without `scores.toml`, and the per-bank `[arms]` override is
  the escape. Reopen if such a bank ships.
- **FATH-B45 — Replacing the harness with a hosted eval platform.** Those platforms vary prompts
  and models over a fixed scaffold; fathom's unit of variation is the scaffold itself (skill armed
  or bare, strategy, effort), and blind scoring is part of its construction rather than an option.
  Reopen if a comparison UI or factorial statistics come to cost more to lack than to adopt.
- **FATH-B46 — Replacing the pooled Wilson interval on per-criterion pass rates with cluster-t
  or a bootstrap.** Both collapse at K=1 banks and on all-0 or all-100 tasks, which is worse than
  Wilson. The report keeps the pooled interval, states the clustering caveat and shows K beside
  n. This does not cover the tier decision statistic, which ADR-0009 made one draw per trial.

## Closed ids

Closed items that code, tests or other documents still cite, one line each, with the version
that closed them. The changelog starts at 0.8.0 and has the detail for the rows closed there.
Earlier versions are not part of this repository, so for a row closed before 0.8.0 this line
is the whole record.

| Id | What closed it | Version |
|---|---|---|
| FATH-B01 | Arming verification: `fathom verify-arming` and the pre-flight in `fathom run` (exit 11). | 0.2.0 |
| FATH-B02 | `fathom validate` and the pre-flight that refuses a bank that cannot discriminate (exit 12). | 0.2.0 |
| FATH-B03 | A trial that did not complete carries `valid=false` and no criteria. | 0.2.0 |
| FATH-B04 | `--max-run-usd` (exit 14), `--max-spawn-usd`, a dry-run ceiling from the cap in force; the credential pre-flight (exit 15). | 0.4.0, 0.6.0 |
| FATH-B05 | Per-cell N, per-trial spreads, a contested Pareto mark and the Arm Health table. | 0.2.0 |
| FATH-B06 | A committed ledger needs a written verdict: `fathom report` warns when no `docs/reports/` entry or `docs/STATUS.md` row names the bank; a data root that wants the rule to bind holds its own test. | 0.2.0 |
| FATH-B14 | The verifier's stdout and stderr are kept on the trial row, bounded. | 0.2.0 |
| FATH-B38 | The engine repository ships no build briefs or campaign data. | 0.8.0 |
| FATH-B53 | The run lock with a heartbeat, and `fathom stop` (exit 16). | 0.6.0 |
| FATH-B57 | The adapter's token-times-price cost fallback removed; rows carry `cost_source`. | 0.5.0 |
| FATH-B61 | The ledger index digest is taken over canonical LF bytes. | 0.4.0 |
| FATH-B62 | `fathom reconcile` (exit 13) and the forward-only `config_preimage` field. | 0.4.0 |
| FATH-B65 | The silent-failure items in `docs/method/review-checklist.md`. | 0.4.0 |
| FATH-B66 | `docs/method/measured-terms.md`. | 0.4.0 |
| FATH-B69 | New ledger rows record `engine_version`, outside `config_hash` and the resume key. | 0.8.0 |
| FATH-B07 | `docs/ledger-contract.md`, the ledger row format, and the public `report.is_pass()`. | 0.9.0 |
| FATH-B08 | The Hard-Criteria Fraction table in every scorecard section, and the saturation banner. | 0.9.0 |
| FATH-B54 | `fathom validate` and the pre-flight in `fathom run` refuse a gate command that names a missing path (exit 12). | 0.9.0 |
| FATH-B58 | An arm's `comparator` key: a dependent arm's cell runs only after its comparator completed the same task and repeat. | 0.9.0 |
| FATH-B80 | The plan's `expected:` line, the median cost per trial from the bank's own completed trials. | 0.9.0 |
| FATH-B82 | A finished plan prices one more repeat and counts the completed trials for its arms. | 0.9.0 |
| FATH-B83 | Each spawn's `--settings` layer excludes the instruction files above its workspace (`claudeMdExcludes`), the claude.ai connectors are off, and `fathom smoke` checks it on a live spawn. | 0.9.0 |
| FATH-B85 | A study declares repeats per cell; one-repeat studies are marked directional. | Unreleased |
