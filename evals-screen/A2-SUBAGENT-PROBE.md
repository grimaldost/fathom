# A2 -- subagent hook-delivery probe (2026-07-24)

Program-2 opener. Question: in the user's real workflow (opus main session + heavy
multi-agent, direct or convoy-orchestrated), **can a hook inject dispatch context
into every subagent, and does it reach the subagent?** This decides whether the
whole subagent path is worth any paid behavioral run.

Method: a throwaway plugin (`scratchpad/subagent-probe/testplugin`) mounted via
`--plugin-dir` into an isolated-credential `claude -p` headless spawn (haiku-4.5),
prompted to delegate once via the Task tool to a `general-purpose` subagent. The
plugin registers hooks on a superset of lifecycle events; each writes a firing
marker, and two inject a token that appears NOWHERE in the main prompt, so
surfacing it proves the channel reached the SUBAGENT (clean provenance). Same
isolated-config / env-stripped pattern as the PostToolUse/Stop probes.

## Results (both runs, haiku-4.5, exit 0)

| fact | result |
|---|---|
| Subagent spawnable in headless `-p`? | **Yes** -- `PreToolUse:Task` fired; stream carried `task_started` / `task_updated` / `task_notification` |
| `SubagentStart` fires (mounted `--plugin-dir`, not installed)? | **Yes** |
| `SubagentStart` payload fields | `session_id`, `agent_id`, **`agent_type`** (`general-purpose`), `transcript_path`, `cwd`, `prompt_id`, `hook_event_name` |
| `SubagentStart.additionalContext` reaches the subagent? | **Yes** -- token `ZZSUBHOOKZZ` echoed (5x, then 8x); subagent wrote "I will include the token ZZSUBHOOKZZ in my final report" |
| `SubagentStop` fires? | **Yes** |
| `SubagentStop` `decision:block` + `reason` re-prompts the subagent? | **Yes** -- fired 2x (blocked once, then allowed by the counter guard); token `ZZSTOPBLOCKZZ` echoed (7x); subagent wrote "I received a stop hook feedback requiring ZZSTOPBLOCKZZ ... before I finish" |

Corroborated by the Claude Code docs (via claude-code-guide): both events documented;
`SubagentStart` is informational (no block); `SubagentStop` supports
`decision:block`; **both channels' injected context lands in the subagent's own
transcript, isolated -- it does NOT flow to the main agent**; both fire in headless
and under `--plugin-dir`.

## What this establishes (and what it does NOT)

**Two reliable per-subagent delivery channels exist:**
1. **`SubagentStart`** -- inject dispatch context (a discipline nudge, a skill
   pointer, a registry) into *every* subagent at spawn. Routable by `agent_type`;
   the hook can also read the subagent's `transcript_path`. Informational only.
2. **`SubagentStop` `decision:block`** -- a real *per-subagent gate*: hold the
   subagent before it finishes and inject a reconsideration (e.g. "run
   verification / prove the fix / check the other sites"). Needs a bound (we used a
   block-once-per-`agent_id` counter) or it loops. This is the stronger lever --
   and unlike `PostToolUseFailure` (whose additionalContext does NOT reach the
   model, measured earlier), this one does.

**The honest limit -- DELIVERY, not INCORPORATION.** This proves the context
*arrives* in the subagent and is *acknowledged* (echo tokens). It does NOT prove
injected discipline *changes subagent behavior*. That is the same delivery != footprint
gap the Stage-1 screen exposed (oracle delivered the right skill name, +0 on
Band-C). Whether a `SubagentStart` nudge or a `SubagentStop` gate actually lifts a
subagent's discipline footprint is a paid behavioral question -- an A1 x subagent
arm -- and is expected to be tier-dependent (the one main-agent survivor,
classifier-hint, was strong-tier-only).

## Implication for the program

- The multi-agent path is **unblocked, not answered.** The channel the user asked
  about works into subagents; the behavioral payoff still has to be measured.
- The `SubagentStop` gate is the more promising subagent mechanism because it is a
  *gate* (mechanism), not a *nudge* -- consistent with "mechanism > nudge", the one
  thing that survived the whole line. It is also the subagent analog of convoy's
  always-on `[[checks]]` gate (see the E design track).
- Cheapest next paid step for the subagent path: a small behavioral arm delivering
  the verification-before-completion discipline via `SubagentStop` into subagents
  on a task where a naive subagent provably skips the check, across haiku / sonnet /
  opus. Fold into the A1 (opus) phase.

## Provenance
`scratchpad/subagent-probe/` (testplugin + run_sub.sh + MARKER.txt + run_out.jsonl,
gitignored / not committed). Docs cross-check: code.claude.com/docs/en/hooks.md
(SubagentStart / SubagentStop sections).
