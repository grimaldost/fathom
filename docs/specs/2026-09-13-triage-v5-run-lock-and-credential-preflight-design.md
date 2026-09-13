# Spec — the run lock, the credential pre-flight, and the gate-output decode

- **Date:** 2026-09-13
- **Status:** ready
- **Audience:** the implementer of this change and its reviewer
- **Output artifact(s):** `src/fathom/runlock.py`, `src/fathom/smoke.py`, `src/fathom/cli.py`,
  `src/fathom/strategies/gated_session.py`, `tests/test_runlock.py`,
  `tests/test_smoke_logic.py`, `tests/test_gated_session.py`

## Context

Source of scope: the 2026-09-13 feedback triage (v5, 14 reports). It separates the rows that
affect **what fathom measures** from the ergonomic ones, and grounds every row against the
tree at `ee56cdf` (0.5.0). Four clusters were handed to this change: T24, T25, T26, T34.
This spec covers **T24, T25 and T34a**; §7 records why T26 is not in it.

Relevant prior decisions: ADR-0002 (append-only ledger; a config change must not silently
fork a resume key), ADR-0004 (credential-only isolated config — the credential is copied,
never read), and `docs/backlog.md` FATH-B53, which designed the lock, deferred it to 0.5.0
behind a named trigger, and was missed.

## Goal

Give fathom a lock of its own with a heartbeat and a `stop` verb, so mutual exclusion on one
authenticated seat stops being a convention each caller re-invents; make `smoke` prove the
credential is live *before* it asserts anything that depends on a live spawn; and stop a
gate subprocess's undecodable output from turning into a silent empty re-brief.

## Gate commands

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- `uv lock --check` (CI runs it **before** `uv sync`; no test can replace it)

## Non-goals

- No paid run, no spawn, no matrix. Every assertion here is exercisable at $0.
- No change to any committed ledger row, and no change to any scenario's `config_hash`.
  Nothing in this spec enters `_resolved_to_dict`.
- Not FATH-B58 (a buy script's exit-code seam) or FATH-B59 (orphan-process preflight).
  T24a is their named blocker; unblocking them is not building them.

## Invariants touched

| Invariant | ADR | How this change treats it |
|---|---|---|
| The ledger is append-only and is the resume checkpoint | ADR-0002 | A stop halts **between** trials, so nothing already bought is lost and no row is rewritten. |
| `config_hash` identity must not move | ADR-0002 | Nothing added here is hashed. |
| The isolated config carries the credential and nothing else | ADR-0004 | The pre-flight reads **only** `expiresAt` / `refreshTokenExpiresAt` from the credential file. It never reads, logs, copies or reports a token. |
| A gate's verdict is the gate's own exit code | — | Unchanged. T34a changes what is *recorded about* the output, never the red/green. |

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| Ledger append-only / stop between trials | enforced | `tests/test_cli.py` — a stop request halts with the ledger intact |
| `config_hash` unmoved | enforced | `tests/test_scenario.py` + `fathom reconcile` (`preimage`/`version-sites`) |
| Credential values never read | enforced | `tests/test_smoke_logic.py` — the parser is fed a file whose token fields are sentinels and asserted not to surface them |
| Gate output never silently empty | enforced | `tests/test_gated_session.py` — a real subprocess emitting byte `0x97` |

## Concept → module map

| Concept | Module |
|---|---|
| Ticket, ticket ordering, staleness horizon (pure) | `src/fathom/runlock.py` |
| Lock directory I/O, heartbeat thread, stop request | `src/fathom/runlock.py` |
| `fathom stop` verb, run-loop stop check | `src/fathom/cli.py` |
| Credential TTL reading (metadata only) | `src/fathom/smoke.py` |
| Liveness gating of smoke checks | `src/fathom/smoke.py` |
| Gate-subprocess decode posture | `src/fathom/strategies/gated_session.py` |

## Numbered sections

### §1 T24a — a native run lock with a heartbeat and a FIFO ticket directory

FATH-B53's trigger was explicit: *a decision on the heartbeat seam plus a lock path outside
`ledger/` with its `.gitignore` rule in the same change*. Both decisions are made here.

**Lock path.** `.fathom/locks/<bank>/` at the repo root, with `/.fathom/` added to
`.gitignore` in this change. Not `ledger/`: `ledger/` is tracked, so a lock under it becomes
a committed artifact the first time anyone runs `git add ledger/`.

**Heartbeat seam.** A daemon thread owned by the lock, ticking every `HEARTBEAT_INTERVAL_S`
(15s) by rewriting its own ticket's `heartbeat` field. Not per-trial: a series trial can run
for an hour, so a per-trial beat gives a staleness horizon no shorter than the longest trial,
which is the horizon that made the three observed deadlocks undecidable. Staleness horizon
`STALE_AFTER_S` = 120s — eight missed beats, so a stalled writer is not mistaken for a dead
one.

**FIFO tickets.** Each acquirer creates one ticket file `<created_ns>-<pid>-<uuid>.json`
with `O_EXCL`, so creation never contends. The holder is the **lowest-ordered live** ticket;
a waiter polls and prunes tickets whose heartbeat is older than the horizon. This is what
makes the release-to-relock window stop being a race the politest poller loses.

**Testability — the objection that deferred this row.** FATH-B53 said the failure mode is
multi-process on one authenticated seat, which this repo's gate cannot exercise. That is true
of the *seat* and false of the *lock*: the lock is a directory, and its decision is a pure
function of the ticket files. So the module splits the way `smoke` and `arming` already do —
pure ordering/staleness over ticket records, unit-tested against handwritten tickets, plus
the I/O that produces them, exercised by a real multi-process contention test that spends
nothing.

**Acceptance criterion:** `fathom run` acquires the lock before the first spawn and releases
it in a `finally`; a second `fathom run` on the same bank waits, and reports which PID holds
and how old its heartbeat is; a ticket whose heartbeat is past the horizon is pruned by the
waiter rather than blocking it forever; the multi-process test observes no overlapping
critical sections.

### §2 T24b — `fathom stop <bank>`

`fathom stop <bank>` writes a stop request into the bank's lock directory. The holding run
reads it at its next **trial boundary** and returns `EXIT_STOPPED` (15). This is the primitive
`pause_matrix.py` and `guard_cap.py` each re-implemented by hand in one day.

Default is at-boundary, because the ledger is the checkpoint: halting between trials loses
nothing already bought, while killing a tree mid-trial discards a spawn that was already paid
for. `--at-boundary` is accepted as the explicit spelling of that default. `--now` escalates:
it also terminates the holder's recorded process tree, for the case a run is wedged inside a
spawn (the `TaskStop` incident, where `uv → fathom → claude` survived its wrapper). `--now`
names, in its own output, the in-flight trial's spend as the cost.

`fathom stop` on a bank nobody holds prints that and exits 0 — a stop that finds nothing to
stop is not an error.

**Acceptance criterion:** a stop request placed while a matrix runs halts it before the next
trial with `EXIT_STOPPED`, the ledger holding exactly the trials that completed; the request
is consumed, so a later run is not stopped by a stale one.

### §3 T24c — the operational check that ships with its mechanism

FATH-B64's own corrected trigger: *each check ships in the same change as its mechanism, so
this row dissolves into B53 and its siblings.* Accordingly `smoke` gains one operational
check now — **concurrency exclusion** — asserting that while one ticket holds, a second
acquirer does not, and that a ticket past the staleness horizon is pruned rather than
honoured. It costs nothing and spawns nothing, and it is exercisable on CI, which is what
FATH-B59 and the rest of B64 were waiting for.

Not built here: FATH-B58's exit-code seam and FATH-B59's orphan preflight. They are unblocked,
not shipped.

**Acceptance criterion:** `fathom smoke` reports a concurrency-exclusion check, and
`--no-engine-boundary` still runs it (it needs no engine and no spawn).

### §4 T25a — a credential-TTL pre-flight, check 0

A zero-cost check reading `~/.claude/.credentials.json` and extracting **only**
`claudeAiOauth.expiresAt` and `claudeAiOauth.refreshTokenExpiresAt` (epoch milliseconds).
Never the token, never any other field, never anything under `mcpOAuth`. It runs **first**, so
its verdict is available to the checks that depend on a live spawn (§5).

A credential already expired is a FAIL with "re-authenticate, then re-run". A credential whose
access token expires within `CREDENTIAL_MIN_TTL_S` but whose refresh token is still good is a
PASS carrying the remaining life in its detail, because a refreshable credential is not a dead
one. An unreadable or shapeless file is a FAIL, not a silent pass — absence of evidence is the
failure mode this whole cluster is about.

**Acceptance criterion:** with an expired `expiresAt` and an expired `refreshTokenExpiresAt`,
`run_smoke` returns nonzero and the check's detail names re-authentication; the assertion is a
pure function over a parsed status, unit-tested without touching the real credential file.

### §5 T25b — the two hollow checks

`2026-09-01-multiagent-composition-pilot-blocked` recorded both:
*"stream parsing detects activity" passed with `turns=1 tokens_in=0 tokens_out=0`*, and
*"disallowed tool refused" passed with no tool call to refuse*. Both are true by vacuity: the
first passes on `num_turns > 0` regardless of whether the spawn authenticated, and the second
passes on an empty leak list, which is exactly what a spawn that never ran produces.

The fix is not a stronger predicate — it is an ordering. A liveness-dependent assertion is
**gated on the spawn having been live**, and reports `SKIPPED (spawn not live)` otherwise:

- `assert_activity_detected` requires `status == OK` **and** observed token flow
  (`tokens_in > 0 or tokens_out > 0`), not turns alone: a turn count is emitted by the
  harness's own accounting, tokens only by a spawn that reached the model.
- `assert_tool_denied` requires `status == OK`: with no live spawn there was no tool call to
  refuse, so there is nothing to conclude.

A SKIPPED check is **not a pass**, and the gate does not go green with one outstanding.
`smoke` is a go/no-go before paid spend; "could not be proven" must not read as "go". That is
the structural removal of the vacuity rather than a relabelling of it.

**Acceptance criterion:** fed a record with `status=INFRASTRUCTURE, turns=1, tokens_in=0,
tokens_out=0` and an empty leak list — the observed numbers, verbatim — both checks report
SKIPPED, neither reports PASS, and `run_smoke` returns nonzero.

### §6 T25c — name the failing and skipped checks on the summary line

The `7/8` headline read as "mostly fine". The summary now names which checks were not proven,
so the one line an operator reads carries the same information as the fold above it.

**Acceptance criterion:** the `SMOKE RESULT:` line lists the failed and skipped check names.

### §7 T34a — read gate-subprocess output with `errors="replace"`

`gated_session._run_gate` reads with `encoding="utf-8"` and no `errors=`. Reproduced on this
machine against a real subprocess emitting byte `0x97`: the reader thread raises,
`subprocess.run` returns with the exit code intact and `stdout=None`, and `_run_gate` builds
`(None or "") + (None or "") == ""`. The verdict stays correct; the fix-loop re-brief goes out
empty.

Two changes, and the second is the one that keeps the first honest:

1. `errors="replace"`, matching the posture already applied to the harness's own stdout.
2. A stream that came back `None` is a **named condition**, not an empty string. The
   triage scoped this as "`proc.stdout is None and proc.stderr is None`"; the reproduction
   shows only the stream carrying the bad byte comes back `None` (the other was `''`), so the
   guard is `stdout is None or stderr is None`. Recording it is what stops a future decode
   failure from re-entering the same silence.

**Acceptance criterion:** a gate command emitting an invalid UTF-8 byte yields non-empty
output carrying the replacement character; a `subprocess.run` returning `stdout=None` yields
the named condition rather than `""`; the red/green verdict is unchanged in both cases.

### §8 Release

`0.5.0 → 0.6.0` across every site `fathom reconcile`'s `version-sites` check holds equal:
`pyproject.toml`, `.claude-plugin/plugin.json`, and the newest `## [X.Y.Z]` heading in
`CHANGELOG.md`. Minor, not patch: `fathom stop` is a new verb and `fathom run` acquires a lock
it did not before — a caller's behaviour changes. No tag.

## Out of scope, and why — T26 (harness staging outside the bank)

T26 was in this change's brief and is **not** in it. Two findings, both from reading source:

**T26b's premise does not hold.** The row proposes asserting a spawn's init-event tool list
against the scenario's declared allow-list, failing the arm on mismatch. Read against a real
init event from `streams-multiagent/2026-09-01-pilot`: the `tools` array is the platform's
full 30-tool registry (`Task, Artifact, Bash, … Write`) and is emitted before any permission
decision. It is a registry listing, not the effective allow-list, so the proposed assertion
would fail every arm always — including correctly-armed ones. The underlying concern (the
allow-list is documented, not shown to be enforced) is real and stands; the mechanism named
for it is not the observable it needs. The row needs re-scoping onto an observable that does
reflect enforcement (`permission_denied_tools`, which requires a denied call to exist), and
that re-scoping is a design decision, not an implementation of this one.

**T26a moves committed arm identity.** Resolving the harness from a staged directory means the
multiagent scenarios' `[env]` templates stop reading `${FATHOM_TASK_DIR}` and start reading
`${harness_dir}`. `[env]` vars enter `config_hash` (`scenario.py:_resolved_to_dict`), so that
edit forks the resume key of every arm in a bank with ~3,000 committed rows. Whether to fork
longitudinal history, or to carry a compatibility path, is precisely the class of decision
ADR-0002 exists to make deliberately. Building it inside a release whose other three clusters
are additive would decide it by side effect.

T26c (promote `stream_facts.py --exposure --fail-on-exposure` from an operator tool to a
default close gate) is buildable independently of both and is left with them so the cluster
lands as one coherent change rather than a third of one.
