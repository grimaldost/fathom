# Fresh-agent acceptance test

`tools/agent_acceptance.py` answers one question with evidence: can a fresh Claude Code
agent, given only a user's goal and whatever the installed plugin exposes, use fathom end to
end? It is the acceptance test for the promise that an agent can build and run a bank from
the shipped skill, commands and MCP tools alone.

## What it measures

Each scenario starts one headless Claude Code session, the subject, in a workspace of its
own. The prompt is a user's goal in plain words. It names no fathom command, flag, path,
skill or MCP tool, and the harness appends no system prompt. The harness refuses to spawn a
prompt that contains `/fathom:`, `--dry-run`, `fathom-eval`, `mcp__`, `python -m`, `--home`,
`FATHOM_HOME`, `fathom init` or `fathom run`.

| Scenario | Workspace | The prompt asks the subject to |
|---|---|---|
| S1 existing-data | a clone of your data root; `FATHOM_HOME` names it | say which evaluations ran and what each concluded, whether the data is consistent, and what re-running the smallest would cost, spending nothing |
| S2 from-scratch | an empty directory; `FATHOM_HOME` unset | build a one-task, two-arm measurement with fathom, run each arm once for at most $1, and show the scorecard |
| S3 unnamed-discovery | a clone, as S1 | find whatever installed tool measures whether a skill helps, without being told its name, and show what a measurement would look like, spending nothing |

The prompts and each scenario's checks are data, in `tools/agent_acceptance_scenarios.toml`.

The harness judges each session three ways.

- **Visibility**, from the stream's init event: the plugin's MCP server
  (`plugin:fathom:fathom`) is connected, every command in the plugin's `commands/` is
  listed as `fathom:<name>`, and the `fathom:fathom-eval` skill is listed. A visibility
  failure is an environment failure, reported apart from the agent's behaviour.
- **Behaviour**, from the tool calls in the stream. Each call is classified by the fathom
  surface it used: `skill` (the Skill tool on `fathom-eval`), `command` (a `fathom:` command
  through the Skill or SlashCommand tool), `mcp` (a tool of the plugin's server), `cli`
  (a Bash command that runs fathom, with its subcommand read from the argv), or `docs` (a
  Read of a file in the plugin's tree). Results are paired with their calls, and errors on
  a fathom surface are kept, 300 characters each.
- **Ground truth**, read by the harness after the subject exits: files in the workspace, the
  real data root's git state, and for S2 a `fathom reconcile` the harness runs itself.

## Checks

Every scenario gets `session_finished`: the stream has a result event that is not an error,
and the session was not killed at the wall-clock limit. Every clone scenario also gets
`data_root_untouched`: the real data root's `git status --porcelain` and HEAD are the same
after the subject as just before it.

| Check | Kind | Passes when |
|---|---|---|
| `no_ledger_change` | ground truth | nothing under the clone's `ledger*/` is new or modified (`report/` and `.fathom/` are ignored) |
| `no_paid_run` | ground truth | no `fathom run` without `--dry-run` was executed |
| `reconcile_ran` | behaviour | a reconcile ran through the CLI and returned, either clean or reporting a disagreement |
| `plan_ran` | behaviour | a dry-run plan succeeded, through the CLI or the MCP `plan` tool |
| `answer_names_banks` | answer | the final answer names at least half of the banks that have a `ledger/<bank>.jsonl` in the clone |
| `fathom_used` | behaviour | any fathom surface was used |
| `data_root_created` | ground truth | a `fathom.toml` with a `[data_root]` table exists under the workspace |
| `bank_authored` | ground truth | that data root has a bank with at least one task whose `[verify] entry` file exists |
| `arms_authored` | ground truth | at least two scenario files that declare a `strategy` |
| `trials_completed` | ground truth | at least two `completed` trial rows across at least two `config_hash` values |
| `measurement_within_budget` | ground truth | the ledger's summed `cost_usd_est` is at most 1.5 times the budget the prompt states |
| `reconcile_passes` | ground truth | `fathom reconcile`, run by the harness in that data root, exits 0 |
| `scorecard_rendered` | ground truth | a non-empty `report/scorecard-<bank>.md` exists |

A command call (`/fathom:reconcile` through the Skill tool) only expands the command's text;
the engine runs in the Bash call that follows it. That is why `reconcile_ran`, `plan_ran` and
`no_paid_run` count CLI and MCP calls only.

The verdict also records, without passing or failing on them: the surfaces used in order,
how many tool calls came before the first fathom use, every fathom operation, and for a
paid run whether a budget rail (`--max-run-usd`, `--max-spawn-usd`) was passed and whether
smoke and a dry-run plan came first.

## Cost

Each subject session is capped with `--max-budget-usd` (`--budget-usd`, default $3), so the
three sessions cost at most $9. S1 and S3 spend nothing on fathom. S2's own fathom spawns
(its smoke check, the arming check and the two trials) are separate processes outside that
cap: the prompt allows $1, and `measurement_within_budget` fails above $1.50. The preflight
is one session capped at $0.20. `--dry-run` prints the ceiling for the scenarios selected.

## Safety rails

- **The real data root is never handed to a subject.** S1 and S3 get
  `git clone --local --no-hardlinks <data root> <workspace>/data`, with the clone's
  `origin` remote removed, and the session starts in the clone's parent so it finds the data
  through `FATHOM_HOME`. The harness reads the real data root's git state just before each
  subject and again after it, with `--no-optional-locks`, so even that read writes nothing.
  Work of your own in the data root while a subject runs fails that subject's check.
- **It refuses** an engine checkout or plugin tree (a `.claude-plugin/plugin.json` or a
  `src/fathom/` in it), a plugin cache directory, a directory without a `[data_root]` table,
  and a directory that is not the top of a git work tree.
- **Environment.** A subject starts from the environment the engine gives its own trial
  spawns (`env_for_agent_code`): every `FATHOM_*` variable, `PWD`, `OLDPWD` and the billing
  and routing variables are removed, along with any variable whose value names the real
  data root. The variables a running Claude Code session sets for its children are removed
  too (`CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, the parent session's identity and host
  channel, `MCP_CONNECTION_NONBLOCKING` and others; the full list is
  `PARENT_SESSION_VARS`). `FATHOM_HOME` is then set per scenario or left unset, never
  inherited. `--dry-run` prints every name it removes.
- **Permissions.** `--permission-mode acceptEdits`, allowed tools `Bash`, `Read`, `Write`,
  `Edit`, `Glob`, `Grep`, `Skill`, `SlashCommand`, `ToolSearch` (which loads a deferred MCP
  tool's schema) and the plugin's MCP server; disallowed `Bash(git push:*)`, `Bash(gh:*)`,
  `WebFetch` and `WebSearch`. The subject never sees these lists. A call to any other tool
  is refused and shows in the verdict's `permission_denials`.
- **Wall clock.** Each subject is killed with its whole process tree at `--timeout-s`
  (default 1800 s), with the engine adapter's `taskkill /T /F` on Windows.

A subject runs with your own Claude Code configuration, since that is where the installed
plugin lives: your user settings, permissions, hooks and `CLAUDE.md` apply as they would to a
session you started. A user-scope `CLAUDE.md` that mentions fathom makes S3 easier, and a
`settings.json` `env` table applies after the harness's environment.

## How to run

From an engine checkout, with your data root as an argument (it defaults to `FATHOM_HOME`):

```sh
# Prepare the workspaces and print each subject's command, env changes and prompt.
uv run python tools/agent_acceptance.py --dry-run --data-root DIR

# One trivial session: is the plugin visible at all? Cents.
uv run python tools/agent_acceptance.py --preflight-only --data-root DIR

# The scenarios, in the order given.
uv run python tools/agent_acceptance.py --data-root DIR --scenarios S1,S3,S2
```

Other options: `--model` (default `sonnet`; `haiku` is the stress variant), `--out DIR` and
`--run-id ID` (the default output is `<temp>/fathom-agent-acceptance/<run id>/`, and a
directory that is not empty is refused), `--budget-usd`, `--timeout-s`, and `--plugin-dir DIR`
to test a development tree. With `--plugin-dir`, the installed plugin may load as well, and
the verdict lists every fathom plugin the init event reported.

A scenario that finds a visibility failure stops the run: the remaining scenarios are marked
skipped, since their behaviour would say nothing about the plugin.

## Reading the verdict

The output directory holds `report.md` and one directory per scenario,
`<id>-<name>/`, with:

- `workspace/`, the subject's working directory, kept for inspection;
- `transcript.jsonl`, the raw stream;
- `stderr.txt`, the CLI's stderr;
- `verdict.json`: the status, each check with its evidence, visibility, behaviour, the
  fathom-surface errors, cost, turns, duration, the command and the removed environment
  names, and the final answer.

`report.md` starts with a table of scenario, verdict, cost and duration, then the visibility
of each scenario, then each scenario's checks, behaviour and final answer.

| Exit | Meaning |
|---|---|
| 0 | every scenario passed |
| 1 | a check failed |
| 2 | an environment or preflight failure: the plugin was not visible, the stream had no init event (for example, `claude` could not start), `claude` is not on `PATH`, or a workspace could not be prepared |
| 3 | a usage error: a bad option, an unusable data root, a used output directory, or a scenario file or prompt the harness refuses |

Start with the visibility row. If the MCP server is `failed` or `pending`, or a command is
missing, fix the installation (`/plugin`, `/mcp`) and run `--preflight-only` again before
reading any behaviour. A failed check names its evidence, and `#N` in it is the tool call's
position in the stream, counting from 0.
