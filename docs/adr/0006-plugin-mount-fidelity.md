# ADR-0006 — Mount whole plugins via --plugin-dir; preserve triggering fidelity

- **Status:** Accepted
- **Date:** 2026-06-14

## Context

fathom's plugin-level evaluations (humblepowers vs superpowers) measure whether a
process-discipline plugin improves coding outcomes **as actually shipped**. A
plugin's value is that the right skill auto-fires at the right moment — the
dispatch/triggering signal is the main differentiator between a process-discipline
plugin and a bare skill body.

The prior `skill-pyeng-v1` bank force-loaded individual skill bodies via
`--append-system-prompt-file`, injecting their content directly into the system
prompt. This approach discarded the plugin's dispatch machinery: skills did not
trigger conditionally; the model had no mechanism to decide whether a skill was
worth loading for the task at hand. The evaluation measured "skill body content
injected into every prompt" rather than "the plugin deciding when to load itself."

For humblepowers vs superpowers, we must measure the full stack: both
process-discipline dispatch and the skill bodies themselves.

Spike validation on 2026-06-14 confirmed both plugins can be mounted via the
claude CLI `--plugin-dir` flag in a credential-only isolated spawn:
- humblepowers @ inline mounted; all eight skills available in the init event.
- superpowers (obra/superpowers @ 6fd4507, v5.1.0) fetched from GitHub, mounted
  via `--plugin-dir`; all fourteen skills available in the init event.

Both mounts incurred no credential leak and no setup overhead beyond fetch time.

## Decision

Mount whole plugins via the claude CLI's `--plugin-dir` flag (repeatable, one flag
per directory) rather than force-loading individual skill bodies. The mounted
plugin set becomes part of the scenario configuration, which enters the config
hash deterministically so that ledger resumption and longitudinal comparison
remain stable.

The five-arm scenario set includes two held-constant arms (`stack-humble` and
`stack-super`) that mount an identical set of process-discipline plugins
(`engineering-discipline` and `session-workflow` from craft-collection) in
addition to the contrasting humble or super mount. Because `--plugin-dir` mounts
only what is explicitly named, the exact versions of the held-constant stack
cannot bias the humble ↔ super contrast — its role is to keep the experiment at
parity on a broader process toolkit while isolating the humble/super dimension.

## Alternatives considered

**Force-load the union of skill bodies via `--append-system-prompt-file`.** This
is weaker and loses the triggering signal entirely. It would measure "body content
alone" rather than "the plugin deciding to load and fire." Since the evaluator's
goal is to measure the plugin as shipped (including its dispatch logic), this
alternative does not serve the question.

## Consequences

- **Plugin set in config_hash:** Each scenario's `[plugins] mount` list is
  resolved to `(name, version, tree_sha)` tuples and included in the hashable
  dict **only when the mount list is non-empty**. Scenarios without mounts hash
  identically to their prior versions, preserving ledger continuity for
  the series-engine bank and `skill-pyeng-v1`. A change to any mounted plugin's pinned
  commit (its `tree_sha`) changes the hash and forks the ledger, ensuring
  longitudinal integrity across reruns.

- **Adapter wiring:** `ClaudeCliRunner.build_command()` accepts a sequence of
  plugin directories and appends `--plugin-dir <dir>` for each in order. Empty
  sequence produces no `--plugin-dir` tokens, preserving backward compatibility.

- **CLI factory warning:** When a scenario declares a mount directory that does
  not exist or is empty, a loud `WARNING` is printed and the arm is marked
  unarmed in the run log, mirroring the prior inject-file warning (ADR-0002 § K7).

- **Smoke gate:** A new check group mounts a tiny canary plugin and asserts, from
  the spawn's init event (before any model turn), that its skill is available.
  A control spawn without the mount verifies the skill is absent, proving the
  mount mechanism itself. This proves mounting, not auto-fire — real
  triggering is validated by the cost-probe pilot before the full matrix spend.

- **Isolation preserved:** Plugin directories are passed to the claude CLI only;
  the credential-only `CLAUDE_CONFIG_DIR` remains unchanged. Default-deny
  permissions are never bypassed; plugin mounts add no new credential or
  isolation risk beyond what the prior adapter already manages.

- **External validity caveat:** The `stack-*` arms mount a deliberately narrow
  held-constant set (engineering-discipline and session-workflow only), not a
  fuller craft-collection. The verdict speaks to that stack specifically, not to
  all possible process toolkits. This is reflected in the analysis scope and
  reported as a boundary of the finding.
