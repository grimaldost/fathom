# ADR-0006 — Mount whole plugins via --plugin-dir; preserve triggering fidelity

> **Note (0.8.0):** particulars were removed from this record for the standalone engine.

- **Status:** Accepted
- **Date:** 2026-06-14

## Context

A plugin-level evaluation measures whether a plugin improves coding outcomes **as actually
shipped**. For a process-discipline plugin, much of the value is that the right skill fires at
the right moment; the dispatch and triggering signal is the main difference between such a
plugin and a bare skill body.

Force-loading individual skill bodies via `--append-system-prompt-file` (the `[context] inject`
path) injects their content directly into the system prompt. That discards the plugin's
dispatch machinery: skills do not trigger conditionally, and the model has no way to decide
whether a skill is worth loading for the task at hand. Such an evaluation measures "skill body
content injected into every prompt", not "the plugin deciding when to load itself".

A spike confirmed that plugins can be mounted with the claude CLI's `--plugin-dir` flag in a
credential-only isolated spawn: every skill of each mounted plugin appeared in the init event,
with no credential leak and no setup overhead beyond fetching the plugin.

## Decision

Mount whole plugins via the claude CLI's `--plugin-dir` flag (repeatable, one flag
per directory) rather than force-loading individual skill bodies. The mounted
plugin set becomes part of the scenario configuration, which enters the config
hash deterministically so that ledger resumption and longitudinal comparison
remain stable.

An experiment that contrasts two plugins may mount an identical held-constant set of
further plugins in both arms, to keep the arms at parity on a broader toolkit. Because
`--plugin-dir` mounts only what is explicitly named, the exact versions of the
held-constant set cannot bias the contrast; the contrast stays on the one plugin that
differs.

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
  identically to their prior versions, preserving ledger continuity for existing
  arms. A change to any mounted plugin's content (its `tree_sha`) changes the hash
  and forks the ledger, ensuring longitudinal integrity across reruns.

- **Adapter wiring:** `ClaudeCliRunner.build_command()` accepts a sequence of
  plugin directories and appends `--plugin-dir <dir>` for each in order. Empty
  sequence produces no `--plugin-dir` tokens, preserving backward compatibility.
  (0.8.0) In a trial the directories passed are per-spawn copies of the declared
  mounts (`stage_arm_files`), without the names `tree_sha` skips, so the argv names
  no path in the data root. The mounted plugin is still the whole plugin as hashed,
  but it must work from a copy without a `.venv` or `.git` of its own.

- **CLI factory warning:** When a scenario declares a mount directory that does
  not exist or is empty, a loud `WARNING` is printed and the arm is marked
  unarmed in the run log, mirroring the inject-file warning. (Later strengthened:
  `fathom run` refuses to spend on an arm it cannot prove armed; backlog FATH-B01.)

- **Smoke gate:** A new check group mounts a tiny canary plugin and asserts, from
  the spawn's init event (before any model turn), that its skill is available.
  A control spawn without the mount verifies the skill is absent, proving the
  mount mechanism itself. This proves mounting, not auto-fire — real
  triggering is validated by a cheap pilot before the full matrix spend.

- **Isolation preserved:** Plugin directories are passed to the claude CLI only;
  the credential-only `CLAUDE_CONFIG_DIR` remains unchanged. Default-deny
  permissions are never bypassed; plugin mounts add no new credential or
  isolation risk beyond what the prior adapter already manages.

- **External validity caveat:** A held-constant set is deliberately narrow. A verdict
  speaks to the plugin set the arms actually mounted, not to every toolkit the plugin
  might be used with, and an analysis states that boundary.
