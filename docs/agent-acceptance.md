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
`FATHOM_HOME`, `fathom init` or `fathom run`. It holds everything else the subject is shown
to a similar rule: the working directory (Claude Code puts it in the system prompt), the
values the harness sets in the environment and the names at the top of the workspace may not
contain "acceptance" or a scenario's name or id, and for S3 not "fathom" either.

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
  Read of a file in the plugin's tree). A command line is cut into simple commands with
  quotes, here-documents and comments respected, so a note or commit message that mentions
  `fathom run` is not a run. Results are paired with their calls, and errors on a fathom
  surface are kept, 300 characters each.
- **Ground truth**, read by the harness after the subject exits: files in the workspace, the
  calls that reached the `claude` stub, the real data root's state, and for S2 a
  `fathom reconcile` the harness runs itself.

## Checks

Every scenario gets three checks:

- `session_finished`: the stream has a result event that is not an error, and the session
  was neither killed at the wall-clock limit nor stopped for spending.
- `data_root_untouched`: the real data root's HEAD, its `git status` with ignored files
  included, and the size and modification time of every ignored file are the same after the
  subject as just before it. It applies whenever a data root is known (`--data-root`, else a
  valid `FATHOM_HOME`), S2 included, and says so when none is.
- `output_untouched`: no tool call names the harness's output directory, where the other
  scenarios' transcripts and verdicts are.

| Check | Kind | Passes when |
|---|---|---|
| `no_ledger_change` | ground truth | nothing under the clone's `ledger*/` is new or modified (`report/` and `.fathom/` are ignored) |
| `no_spend` | ground truth | no `claude` spawn reached the stub on the subject's PATH; a run, smoke or arming check that was tried and spent nothing is noted |
| `reconcile_ran` | behaviour | a reconcile printed its `RECONCILE: OK` or `RECONCILE: FAILED` line |
| `plan_ran` | behaviour | a dry-run printed its `planned: ... ceiling: $X` line, or the MCP `plan` tool returned `ok` |
| `answer_names_banks` | answer | the final answer (the result text and the assistant's text after its last tool call) names at least half of the banks that have a `ledger/<bank>.jsonl` in the clone |
| `fathom_used` | behaviour | any fathom surface was used |
| `data_root_created` | ground truth | a `fathom.toml` with a `[data_root]` table exists under the workspace |
| `bank_authored` | ground truth | that data root has a bank with at least one task whose `[verify] entry` file exists |
| `arms_authored` | ground truth | at least two TOML files in it declare a `strategy` (outside `tasks/`, `ledger/` and `report/`) |
| `trials_completed` | ground truth | at least two of the subject's `completed` trial rows, of a task that has its verifier, across at least two `config_hash` values |
| `measurement_ran` | ground truth | a `fathom run` without `--dry-run` was executed, no ledger or scorecard was written by hand (Write, Edit, `>` or `tee`), and every counted trial row carries what only the engine writes |
| `measurement_within_budget` | ground truth | the subject's ledger rows sum to at most 1.5 times the budget the prompt states |
| `reconcile_passes` | ground truth | `fathom reconcile`, run by the harness in that data root, exits 0 |
| `scorecard_rendered` | ground truth | a non-empty `report/scorecard-<bank>.md` exists |

A row counts as the subject's when the workspace did not start with it and it is not one of
the rows the plugin's example data root ships, so a copy of `examples/data-root/` is not a
measurement. A fathom call over the CLI counts only by what fathom printed: Bash reports the
exit status of a pipeline's last command, so `fathom reconcile | tail` that failed still
looks like success. A command call (`/fathom:reconcile` through the Skill tool) only expands
the command's text; the engine runs in the Bash call that follows it, which is why the
operation checks count CLI and MCP calls only.

The verdict also records, without passing or failing on them: the surfaces used in order,
how many tool calls came before the first fathom use, every fathom operation and the ones
that spend, for a paid run whether a budget rail (`--max-run-usd`, `--max-spawn-usd`) was
passed and whether smoke and a dry-run plan came first, and whether the answer quotes a
ceiling a plan printed (prose rounds, so this is not a check).

## Cost

Each subject session is capped with `--max-budget-usd` (`--budget-usd`, default $3), so the
three sessions cost at most $9. The fathom processes a subject starts are separate and
outside that cap:

- **S1 and S3** are told not to spend, and run with a `claude` stub first on their PATH: the
  stub fathom's own smoke gate uses, which records each call and answers without reaching a
  model. Every spawn the engine makes for them, through the CLI or the MCP server, lands
  there. A `claude` started by its full path would bypass it, so the harness also reads the
  workspace's ledgers every 10 s and stops the session once a new row carries a cost.
- **S2** may spend $1 on its trials. The harness stops the session once its ledgers record
  more than $1.50. A trial still running then can add up to its per-spawn cap ($5 unless the
  subject passes a lower `--max-spawn-usd`), and the smoke and arming spawns never reach the
  ledger, so S2's fathom spend is about $6.50 plus cents at worst. `measurement_within_budget`
  judges trial spend only, for the same reason.

The worst case for the default run is therefore about $15.50; `--dry-run` prints it for the
scenarios selected. The preflight is one session capped at $0.20.

## Safety rails

- **A subject gets a clone, and the real data root is checked afterwards.** S1 and S3 get
  `git clone --local --no-hardlinks <data root> <workspace>/data`, with the clone's `origin`
  remote removed and its agent instruction files (any `CLAUDE.md`, `CLAUDE.local.md`,
  `AGENTS.md` and `.claude/`) withheld, since Claude Code would load them as soon as the
  subject read a file beside them and they would teach fathom in place of the plugin. They
  are marked skip-worktree, so the clone's `git status` stays clean;
  `--keep-data-instructions` leaves them in. The session starts in the clone's parent, so
  it finds the data through `FATHOM_HOME`. The harness reads the real data root's state just
  before each subject and again after it, with `--no-optional-locks`, so even that read
  writes nothing. Work of your own in the data root while a subject runs fails that
  subject's check.
- **Workspaces are kept apart.** Each workspace is `<random>/project` and each subject's
  scratch directory (its configuration, the stub, an empty GitHub configuration) another
  random directory, under the temporary directory or `--workspace-root`, never inside the
  output directory, so walking up from the working directory finds no transcript or
  verdict.
- **It refuses** an engine checkout or plugin tree (a `.claude-plugin/plugin.json` or a
  `src/fathom/` in it), a plugin cache directory, a directory without a `[data_root]` table,
  and a directory that is not the top of a git work tree.
- **Configuration.** By default (`--config isolated`) each subject runs under a
  configuration directory that holds only the credential file, as fathom's own trial spawns
  do, with the plugin loaded from where it is installed (read from the CLI's
  `plugins/installed_plugins.json`) through `--plugin-dir`. None of your CLAUDE.md, other
  plugins, hooks, settings, permission grants or extra directories reach it. `--config
  user` runs the subjects with your own configuration instead, as a session you started
  would; the verdict then lists what in it names fathom (CLAUDE.md lines, other plugins'
  skill, command and agent descriptions) and your extra directories, and S3's discovery is
  marked not attributable to the plugin when that list is not empty.
- **Environment.** A subject starts from the environment the engine gives its own trial
  spawns (`env_for_agent_code`): every `FATHOM_*` variable, `PWD`, `OLDPWD` and the billing
  and routing variables are removed, along with any variable or PATH entry that names the
  real data root, this engine checkout or the virtual environment the harness runs in. That
  last one matters: under `uv run`, a subject's `fathom` and `python` would otherwise be this
  checkout's engine instead of the plugin's. Every `CLAUDE*` and `MCP_*` variable a running
  session or its host sets goes too, except the few a terminal session has
  (`CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_GIT_BASH_PATH`, `CLAUDE_CODE_USE_POWERSHELL_TOOL`,
  `CLAUDE_CODE_OAUTH_TOKEN`, `MCP_TIMEOUT`, `MCP_TOOL_TIMEOUT`), as do `VIRTUAL_ENV`,
  `UV_RUN_RECURSION_DEPTH` and the GitHub tokens. `FATHOM_HOME` is then set per scenario or
  left unset, never inherited. `--dry-run` prints every name removed, every PATH entry
  dropped or added, and any `fathom` the subject's PATH still resolves.
- **Permissions.** `--permission-mode acceptEdits`, the effort passed explicitly
  (`--effort`, default `high`), allowed tools `Bash`, `Read`, `Write`, `Edit`, `Glob`,
  `Grep`, `Skill`, `SlashCommand`, `ToolSearch` (which loads a deferred MCP tool's schema)
  and the plugin's MCP server. On Windows the CLI also registers a PowerShell tool; it is
  not allowed, as fathom's own arms leave it out, so a subject that reaches for it is refused
  and uses Bash. The disallowed `Bash(git push:*)`, `Bash(gh:*)`, `Bash(gh.exe:*)`,
  `WebFetch` and `WebSearch` are prefix rules and easy to step around; the boundary for
  GitHub is that the subject has no GitHub token and an empty `GH_CONFIG_DIR`. The subject
  never sees these lists. A call to any other tool is refused and shows in the verdict's
  `permission_denials`.
- **Processes.** Each subject is killed with its whole process tree at `--timeout-s`
  (default 1800 s), with the engine adapter's `taskkill /T /F` on Windows. Whatever it
  leaves running when it exits is killed too: on Windows it runs in a job object that kills
  its members when closed, which reaches processes whose parent has already exited.

## How to run

From an engine checkout, with your data root as an argument (it defaults to `FATHOM_HOME`):

```sh
# Prepare the workspaces and print each subject's command, env changes and prompt.
uv run python tools/agent_acceptance.py --dry-run --data-root DIR

# One short session: is the plugin visible, and does its MCP server answer? Cents.
uv run python tools/agent_acceptance.py --preflight-only --data-root DIR

# The scenarios, in the order given.
uv run python tools/agent_acceptance.py --data-root DIR --scenarios S1,S3,S2
```

The preflight runs in the configuration mode given, with `FATHOM_HOME` unset (the MCP server
must start without a data root, as it does for S2) and with every tool that could change
something denied. Its prompt names one MCP tool, `plan`, which answers there that no data
root resolves; a headless session does not wait for its MCP servers, so the init event
alone often says `pending`, and only an answer proves the server works. Run it with
`--config user` as well to check the installation as your own sessions see it. In that mode
a server that failed to start in any of your sessions in the last 15 minutes shows as
`failed`, because Claude Code caches the failure in your configuration directory.

Other options: `--model` (default `sonnet`; `haiku` is the stress variant), `--effort`,
`--config`, `--out DIR` and `--run-id ID` (the default output is
`<temp>/fathom-agent-acceptance/<run id>/`, and a directory that is not empty is refused),
`--workspace-root DIR`, `--budget-usd`, `--timeout-s`, `--keep-data-instructions`, and
`--plugin-dir DIR` to test a development tree. In isolated mode `--plugin-dir` replaces the
installed copy; in user mode the installed plugin may load as well, and the verdict lists
every fathom plugin the init event reported. Isolated mode needs the credential file
(`.credentials.json`) in your configuration directory, as fathom's trial spawns do.

A scenario that finds a visibility failure stops the run: the remaining scenarios are marked
skipped, since their behaviour would say nothing about the plugin.

## Reading the verdict

The output directory holds `report.md` and one directory per scenario, `<id>-<name>/`,
with:

- `transcript.jsonl`, the raw stream;
- `stderr.txt`, the CLI's stderr;
- `verdict.json`: the status, each check with its evidence, visibility, behaviour, the
  fathom-surface errors, the calls that reached the stub, cost, turns, duration, the
  workspace and scratch paths, the configuration mode and plugin directories, the command,
  the environment changes, the init event's session facts (model, permission mode, tools,
  skills, plugins, memory paths), what besides the plugin named fathom, and the final
  answer.

The workspaces are kept for inspection at the paths the verdicts give. The scratch
directories keep the stub and its call log; the configuration directory with the credential
is deleted as soon as each subject exits.

`report.md` starts with a table of scenario, verdict, cost and duration, then the visibility
of each scenario, then each scenario's checks, behaviour and final answer.

| Exit | Meaning |
|---|---|
| 0 | every scenario passed |
| 1 | a check failed |
| 2 | an environment or preflight failure: the plugin was not visible, the stream had no init event (for example, `claude` could not start), `claude` is not on `PATH`, the plugin is not installed or the credential is missing in isolated mode, or a workspace could not be prepared |
| 3 | a usage error: a bad option, an unusable data root, a used output directory, a workspace that would show the subject something it must not see, or a scenario file or prompt the harness refuses |

Start with the visibility row. If the MCP server is `failed`, `needs-auth` or not listed, or
a command is missing, fix the installation (`/plugin`, `/mcp`) and run `--preflight-only`
again before reading any behaviour. A server that was `pending` at init and that no
successful call confirmed shows as "no call confirmed it" and is not a failure: the subject
did not use it, and the preflight is what proves it answers. A failed check names its evidence, and `#N` in it is the tool call's
position in the stream, counting from 0.
