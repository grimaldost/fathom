# Arms

<!-- Line budget: 450 lines. The guide is three files; an addition that would take this
file past its budget displaces something first (tests/test_authoring_guide.py). -->

Part of the authoring guide, which starts at [`authoring.md`](authoring.md). That file maps
the guide's three files, defines its terms (`authoring.md`, section 1) and lists the parsers
everything here is written against. Sections are numbered across the three files: a bare
section number here is a section of this file, and a section in another file is cited with
that file's name.

This file covers the arms that attempt a bank: what an arm file holds, the tools and the
isolation every spawn gets, the strategies, the treatments, the MCP servers a mounted plugin
serves and the check that proves them armed (section 10); `config_hash` and the resume key
(section 11); and series arms (section 12).

## 10. Arms (scenario TOML)

An arm is one flat TOML file (no `[scenario]` table around it). `fathom run` reads every
`*.toml` in the scenarios directory, **non-recursively**: `scenarios/` by default, or the
directory given with `--scenarios-dir`. Every arm in that directory runs against every task.
A data root with one bank can keep its arms directly in `scenarios/`, as the example data root
does. To keep one bank's arms apart from another's, give each bank its own subdirectory and
always pass it:

```sh
fathom run example --scenarios-dir scenarios/example
```

Without the flag the run silently uses whatever arms sit in `scenarios/`. The plan prints the
arm names before anything spawns; read them.

Name the control arm `bare`. The report treats `bare` as the anchor for pairwise comparisons
and for the deltas it prints beside series arms.

```toml
name = "nudge"                 # required; the arm's name in the ledger and the scorecard
adapter = "claude-cli"         # required; the only adapter
model = "claude-haiku-4-5"     # required; passed to `claude --model`
strategy = "single-session"    # required; see the strategy table
effort = "low"                 # required; passed to `claude --effort` unchanged
# comparator = "bare"          # optional; buy a cell only after bare completed it ("Comparator")

[tools]
source = "none"                # "none" (default) or "repo" (series arms)
allowed = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]
# disallowed = ["WebFetch"]    # optional; refused even when allowed would permit it
# repo = "/abs/path/to/engine" # series arms only (section 12)

[context]                      # optional treatment: text appended to the system prompt
inject = "assets/nudge.md"     # relative to this file

# [settings]                   # optional treatment: a settings.json for the spawn
# inject = "assets/hooks.json"

# [plugins]                    # optional treatment: plugin directories to mount
# mount = ["assets/some-plugin"]

# [env]                        # optional: non-secret environment variables for the spawn
# SOME_MODE = "strict"

# [gate]                       # optional: extra gate commands for the gated strategies
# extra = ["python ${task_dir}/probe.py ${workspace}"]
#                              # a fix spawn is shown this command as written, placeholders
#                              # and all (see "Tools and default-deny")

[limits]
trial_timeout_s = 300          # optional; wall-clock seconds per spawn (default 1800)
```

Only the five keys commented `required` must be set; `comparator` and every table are
optional. The top-level keys sit at the top of the file, before any table. A file that wraps
them in a table has no top-level keys at all:

```toml
# Wrong: under [scenario], `name` is scenario.name, and the file has no top-level `name`.
[scenario]
name = "nudge"
```

What `fathom run` does with a faulty arm file:

- A file that is not valid TOML, or lacks one of the five keys, is skipped with a warning,
  and the run goes on with the other arms. For a missing key the warning quotes only the
  key: `warning: skipping scenario nudge.toml: 'name'`. With no arm left the run stops with
  `no scenarios found`.
- Tables and keys the parser does not know are ignored without a warning. A misspelled
  treatment table (`[contxt]` for `[context]`) leaves the arm without its treatment, so it
  runs as the control would, under its own name. Check the spelling of every table.
- An unknown `strategy` stops the run (including `--dry-run`) before anything spawns.
- So does a `comparator` that names no loaded arm, names the arm itself, or forms a cycle
  ("Comparator", below).

### Tools and default-deny

Every spawn runs `claude -p` headless with no permission mode: tools not on the allowlist are
refused, and fathom never passes `bypassPermissions` or `--dangerously-skip-permissions`
(ADR-0004). So:

- **An empty `allowed` list means the agent has no tools.** It cannot read or write the
  workspace; the arm is unarmed and measures nothing. `fathom run` warns about it.
- Entries are Claude Code permission rules: a tool name (`Read`), a tool with a specifier
  (`Bash(python:*)`, `Bash(git diff:*)`), or an MCP server prefix (`mcp__<server>`; a mounted
  plugin's servers take a longer one, see "MCP servers in a mounted plugin", below).
- Give the control and treatment arms the same allowlist unless the tools are the treatment.
- The order of `allowed` enters `config_hash`; reordering it forks the arm's history.

Each spawn also gets a temporary `CLAUDE_CONFIG_DIR` holding only a copy of the credential
file. Claude Code also reads `CLAUDE.md`, `CLAUDE.local.md` and `.claude/CLAUDE.md` in every
directory above its working directory, whatever that directory says, so each spawn gets a
settings layer (`--settings`) whose `claudeMdExcludes` lists those files, and the account's
claude.ai connectors are turned off. No personal instructions, settings, history, plugins or
connectors reach any arm. A `CLAUDE.md` inside the task's fixture still does: it is part of
the task. The spawn's environment is the host's with these removed:

- the variables that would send it to another account or backend;
- every `FATHOM_*` variable, and `PWD` and `OLDPWD`, which name the directory fathom was
  started in;
- every variable whose value names a withheld directory. While a command runs, fathom
  withholds the data root, and the directories given with `--tasks-dir`, `--scenarios-dir`
  and `--ledger-dir`, from every child it starts. A variable that names one of them anywhere
  in its value is dropped (`VIRTUAL_ENV`, when fathom runs from a virtual environment inside
  the data root), and `PATH` keeps its other entries but loses those inside one. A directory
  that is, or holds, the home or the temporary directory is not withheld, because every
  process needs those; a data root placed there is not withheld at all.

Those are what would otherwise tell the agent where the data root is (the directory that
holds every task's reference solution and verifier) and which arm it is running: during a
run, `FATHOM_STREAM_TAG` names the bank, the arm, the task and the repeat. The series
engine's process gets the same environment. Nor does the spawn's command line name a file
in the data root: each spawn of a trial gets its own copies of the arm's `[context]` file
and `[plugins]` directories ("Treatments", below). Whatever an arm receives beyond the task,
it declares in its own file.

A gated arm's gate commands run in the workspace with the spawn's environment, less its config
directory: everything listed above is removed from it too, the API credentials included. A gate
that finds its tools only through a virtual environment inside the data root therefore fails;
install the tools a gate needs outside the data root. A gate that runs past its time limit is
stopped together with every process still under it; a process that detached itself from the
gate's process tree can outlive the stop, so a gate should not start background processes.
Each gate command runs on its own, and whatever it creates in the workspace is removed when it
exits, because the workspace is what the verifier scores and a test runner's cache or compiled
bytecode would mark the trial as one a gate ran in. Files that existed before the command stay
as it left them, and so does whatever the agent writes between gates. One gate command
therefore cannot use another's output: an arm's `[gate] extra` probe cannot import something
the task's `[gate] run` built. A gate that needs a build step does it in the same command.

A fix spawn is shown each gate command as written, with `${task_dir}` and `${workspace}` left
as placeholders, and the tail of the failing command's output. In both, every spelling of
the task directory's path is replaced by `${task_dir}`, and then every spelling of a withheld
directory's path, the data root's included, by `<withheld>`. The spellings include a path
relative to the workspace that climbs out of it (`../../…`, which a test runner prints when
it is shorter) and, on Windows, the short (8.3) form. The same masking applies to the
`[gate] extra` output that the trial row records.

That is the extent of what fathom enforces. What remains is up to the bank and arm author:

- **Other paths in gate output.** Masking replaces a withheld directory's own path, not what
  follows it: a gate that prints a file's path in the data root shows it as
  `<withheld>/ledger/example.jsonl`, so the layout below the data root still reaches the fix
  spawn. A relative path is masked only when it is relative to the workspace; one relative
  to another directory (a probe that prints paths relative to its own file, say) passes as
  printed. Write gates that print test results and nothing else.
- **Hook commands and `[env]` values.** A `[settings]` file is copied into the spawn's
  config directory as written, and its hook commands run as written; `[env]` values are set
  as written. fathom rewrites no path in either and masks nothing. The agent can read both:
  its environment names the config directory that holds the settings file, and a running
  hook's command line is in the process table. So keep a hook's script outside the data
  root, or write the hook inline in its command, and write no path in the data root into an
  `[env]` value. `${NAME}` in an `[env]` template reads the reduced environment, so it
  cannot pass on a withheld value.
- **Agent code that a gate runs.** A gate that runs tests or a probe runs code the agent
  wrote, with the gate's whole view: the expanded `${task_dir}` in the command line and in a
  probe's `sys.argv` and `__file__`, and read and write access to everything in the task
  directory, the verifier and `solution/` included (fathom checks only `fixtures/` for changes
  between trials). Masking covers only the output fathom captures. A file that code writes
  into the workspace reaches the next fix or review spawn unmasked. So keep the agent's code
  out of a probe's own process: a probe that has to exercise that code can run it in a child
  process started in the workspace, for example
  `subprocess.run([sys.executable, "-c", code], cwd=workspace)`, so that it does not share
  the probe's `sys.argv`, `__file__` or variables. The task's own `[gate] run` takes no
  placeholder, so its command line names no task directory.
- **The process tree.** A process can read the command lines of other processes that run as
  the same user, and on most systems their working directories and starting environments.
  While a command runs, fathom's working directory is the data root; its command line
  carries the data root's path when `--home` is given (the plugin always gives it), and its
  interpreter's path when fathom runs from a virtual environment inside the data root; and
  its starting environment holds `FATHOM_HOME` if that was set. A gate's command line holds
  the expanded `${task_dir}`. An agent with a tool that runs arbitrary code
  (`Bash(python:*)` is one), and any agent code a gate runs, can read all of these. fathom
  keeps them out of the environment it passes down, not out of the process table.
- **What an agent can reach on disk.** The environment does not name the data root, but an
  agent whose tools can read outside the workspace can still look for it. The allowlist is
  what bounds that: keep file tools and shell commands scoped to the work.

The last three routes need an agent, or its code, that goes looking. fathom closes the routes
that would hand the arm or the data root to an agent that does not ask; it does not contain an
agent that searches for them. The kept streams ("Streams", below) record each spawn's tool
calls, so read them when a result looks better than the arm should manage.

### Strategies

| `strategy` | Spawns per trial | What it does |
|---|---|---|
| `single-session` | 1 | The instruction, once. The usual control. |
| `gated-session` | 1 + up to 2 fixes | After the implementation spawn, runs the task's `[gate] run` and then the arm's `[gate] extra` commands in the workspace (each stopped after a fixed 120 seconds and then counted red; the first red stops the list). What each command creates in the workspace is removed when it exits. On red, a fix spawn receives the gate commands (all of them, joined with `&&`, as written, placeholders not filled in) and the last 3000 characters of the failing command's output, with the task directory's and the data root's paths masked; up to 2 fix rounds. The trial detail records the first and final gate colour. |
| `gated-review` | as gated-session, + 1 or 2 | As gated-session; once the gate is green, a review spawn replies `VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES`, and a request gets one more fix spawn. |
| `reprompt-session` | 2 | The instruction, then one generic "re-examine and fix" prompt, always. It matches the gated arms' extra spawn without any gate information, so it separates the value of the gate from the value of a second attempt. |
| `series` | many | Drives an external multi-PR engine (section 12). |

The gated strategies need a gate. With neither a task `[gate] run` nor an arm `[gate] extra`,
`gated-session` is a single spawn and `gated-review` is the implementation plus its review
pass. The verifier scores every trial the same way whatever the gate said; a red gate is a
measured result, not an error.

### Treatments

Each treatment table adds one thing to an arm's spawns. Paths are relative to the scenario
file. A declared file or directory that is missing or empty makes `fathom run` warn, because
the arm would run as the control.

During a trial, each spawn is given its own copies of the `[context]` file and of each
`[plugins]` directory, made in a temporary directory just before the spawn and removed after
it, and the command line names the copies, so it names no path in the data root.
`config_hash` is taken over their content, so the copies change no hash. A copy that fails
stops the matrix as an infrastructure error (exit 10) and records nothing for that trial. The
arming check (below) and `fathom smoke` spawn from copies made the same way.

- **`[context] inject`** — a text file appended to the spawn's system prompt with
  `--append-system-prompt-file`. The usual way to measure a skill body, a guideline or a short
  instruction. Its content's sha256 enters `config_hash`.
- **`[settings] inject`** — a JSON file copied as `settings.json` into the spawn's temporary
  config directory, so user-scope hooks (a `PreToolUse` hook, say) are active for the arm.
  Hooks shipped inside a plugin do not fire in headless `claude -p`; user-scope hooks do. Its
  content's sha256 enters `config_hash`. The file is copied as written, and its hook commands
  run as written, so keep the scripts they run outside the data root (see "Tools and
  default-deny" above).
- **`[plugins] mount`** — plugin directories mounted with `--plugin-dir`. Each needs a
  `.claude-plugin/plugin.json` with `name` and `version`. Each mount's `tree_sha`, a hash over
  every file under the directory (tracked by git or not, skipping `.git`, `.venv`,
  `__pycache__`, `.in_use` and `.orphaned_at`), enters `config_hash`, so keep a mounted
  directory free of scratch files. A trial's spawn mounts a copy of the directory without those
  same names, in a directory named `plugin` rather than the mount's own name, which is often
  the arm's; the plugin keeps the name its manifest gives it. A mounted plugin must be
  self-contained: it cannot rely on a `.venv` or `.git` of its own, or on a path that leads out
  of its own directory. Symbolic links are copied as what they point to, and a link that points
  nowhere is left out. What the plugin writes into its own tree is gone when the spawn ends,
  and a large directory is copied again for every spawn. The arming check (below) mounts a
  copy too, so a plugin that does not load from its copy, or whose MCP server does not start
  from it, fails there before any trial is bought.
- **`[env]`** — name/value pairs set in the spawn's environment. Values may use
  `${workspace}` (the trial workspace) and `${NAME}` (the value of `NAME` in the reduced
  environment, empty when unset, so `"/extra/bin:${PATH}"` prepends). The templates, not the
  substituted values, enter `config_hash`. They are applied after the environment is reduced
  (see "Tools and default-deny" above): an arm may set a `FATHOM_*` name of its own as a
  declared treatment, but `${FATHOM_HOME}`, `${PWD}` and any variable withheld because it
  named the data root substitute as empty, so no template can forward the host's value. A
  value is set as written, so write no path in the data root into one. Never put a
  credential here.
- **`[gate] extra`** — shell commands the gated strategies run after the task's own gate, with
  the same red/green meaning. Each command is a template: `${task_dir}` (the task's
  directory, so a probe script can live there) and `${workspace}` (the trial workspace) are
  filled in at run time, each as one quoted shell word with forward slashes. A placeholder
  outside quotes gets double quotes of its own, and one inside quotes is escaped for them, so
  `python ${task_dir}/probe.py` and `python "${task_dir}/probe.py"` run the same probe, and a
  path with a space in it does not split the command. Only the command that runs is
  expanded, and the agent sees it unexpanded: on a red gate the fix spawn is shown the
  command as written, placeholders and all, and the gate's output with every spelling of the
  task directory replaced by `${task_dir}` and of the data root by `<withheld>` (see "Tools
  and default-deny" above). Agent code that the probe runs does see the expanded path. Each
  command runs on its own, and what it creates in the workspace is removed when it exits. The
  template text enters `config_hash`; the content of a script it runs does not, so rename the
  arm when you change such a script. The task's own `[gate] run` takes no placeholders. Other
  strategies ignore `[gate]`.

**MCP servers in a mounted plugin.** A plugin declares its MCP servers under `mcpServers` in
`.claude-plugin/plugin.json`, in a `.mcp.json` at its own root, or in both. Claude Code 2.1.291
reads both from a mount, and when both name the same server, the manifest's entry runs. Write
the paths in a server's command with `${CLAUDE_PLUGIN_ROOT}`, which names the copy the spawn
mounts. The init event spells each server `plugin:<plugin>:<server>`, with the manifest's
`name` and the server's key as written, and names its tools
`mcp__plugin_<plugin>_<server>__<tool>`, with every character other than a letter, a digit,
`_` or `-` replaced by `_`. The allowlist matches the tool names, so `mcp__<server>`,
`mcp__<plugin>` and the init event's spelling each permit none of them. Allow
`mcp__plugin_<plugin>_<server>` for all of a server's tools, or a tool's full name: a server
keyed `docs.v2` in a plugin named `codenav` shows as `plugin:codenav:docs.v2` and serves
`mcp__plugin_codenav_docs_v2__find`. An entry that fails Claude Code's schema (one without a
`command`, say) is dropped with no error in the init event, and the arming check (below) sees
only the servers the init event lists. So run `claude plugin validate <plugin directory>`
(Claude Code 2.1.281 and later check `.mcp.json`), and find each declared server in the
`servers=` line the check prints. A `.mcp.json` at the root of the task's fixture is another
file: the workspace's own, loaded for the control arm as for any other, with its tools named
`mcp__<server>__<tool>`. It is part of the task, not a treatment.

**Proving a treatment reached the spawn.** Before it spends, `fathom run` makes one cheap real
spawn per arm that declares `[context]`, `[settings]`, `[plugins]` or `[env]`, and checks each
declared treatment live, spawning from per-spawn copies of the `[context]` file and the
`[plugins]` directories as a trial does: the command line passes a context file whose content
matches the declared, non-empty one; the settings file is in the spawn's config with the right
hash, and a `SessionStart` or `UserPromptSubmit` hook it declares actually fired; each mounted
plugin appears in the session's plugin list, and any MCP server it provides is healthy and
permitted by the allowlist; each `[env]` variable is set with no unsubstituted `${…}`. An arm
that cannot be proven armed stops the run with exit 11.
`fathom verify-arming [--scenarios-dir DIR]` runs the same check on its own; it costs a
little. `--skip-arming-check` turns it off for arms verified in the same session.

**Streams.** For any arm with a `[context]` inject or a tool grant, `fathom run` keeps each
spawn's raw stream-json output under the data root's `.fathom/streams/<bank>/`, named after the
trial. They are the only record of what the agent did (which tools it called, whether a skill
activated). A series arm's agents are spawned by its engine, not by fathom (section 12), so
none of their streams is kept. Set `FATHOM_STREAM_DIR` to keep them somewhere else (a relative value is taken
from the directory the command starts in). Streams are written only by `fathom run`.
When `FATHOM_STREAM_DIR` is unset, `fathom validate` prints a `note:` line naming such arms
and the directory `fathom run` will use; it needs no action.

### `[limits]`

`trial_timeout_s` is the wall-clock limit for each spawn, 1800 seconds when unset. For a
series arm it is the limit for the whole engine run, and there is no limit when it is unset,
so always set it there.

### Comparator

A treatment arm is only worth buying where its control was bought too: a cell (one task and
repeat) that the control did not complete leaves the treatment's trial with nothing to be
compared against. An arm declares that dependency with a top-level key, before any table:

```toml
name = "nudge"
comparator = "bare"            # the arm this one is compared against
```

With it, `fathom run`:

- checks the declarations before the plan, `--dry-run` included. A `comparator` must name
  exactly one arm loaded from the same scenarios directory, not the arm itself, and the
  declarations must not form a cycle (`one` on `two` and `two` on `one`). Otherwise the run
  stops with exit 1 before anything spawns. A value that is not a string makes the file
  faulty, so the arm is skipped with a warning like any other faulty file.
- runs the comparator's trials before the dependent's. The arms otherwise keep the order they
  were loaded in (by file name); a comparator moves just ahead of the first arm that depends
  on it, and a set of arms with no `comparator` keeps its order.
- prints one line per dependent arm after the `arms:` line:
  `depends:  nudge on bare (a cell runs only after bare completed the same task and repeat)`.
- buys a cell of the dependent arm only when the comparator, as its file stands now (its
  current `config_hash`), has a completed trial for the same task and repeat at the bank's
  current `dataset_version`, recorded by an earlier run or earlier in this one. An errored
  comparator trial does not count. Otherwise the run prints
  `blocked: nudge/add r0 — comparator bare has no completed trial for this cell; nothing spent`,
  starts no spawn, writes no ledger row and goes on to the next trial. Blocked cells do not
  change the exit code; the run summary counts them (`authoring.md`, section 13). Run the
  same command again once the comparator's cell has completed, and the blocked cell is
  bought.

`comparator` is not part of `config_hash` (section 11), so adding it to, or removing it from,
an arm that already has trials keeps that arm's history.

## 11. `config_hash` and the resume key

Each trial is recorded under the key `(bank, dataset_version, task_id, config_hash, repeat)`.
A trial counts as done only when a row with that key has `status == "completed"`. Re-running
the same command therefore buys only what is missing, and a changed arm or task is bought
fresh instead of being mixed with old results.

What an edit does to trials already recorded:

| Edit | Effect |
|---|---|
| In an arm file: its name, model, effort, strategy, `[tools]` (including the order of `allowed`), `trial_timeout_s`; adding or removing a treatment table; an `[env]` template or a `[gate] extra` command | A new `config_hash`. The arm's old trials stop counting as done, and the next run buys the arm again from its first repeat. |
| The content of an injected context or settings file; any file inside a mounted plugin; a new commit in, or a move of, a series engine repository | The same: a new `config_hash`. |
| In a bank: an instruction, a fixture, a verifier, a limit, a gate, a criterion | Nothing automatic. Bump `dataset_version` (`authoring.md`, section 4) and every trial of the bank is bought again; without the bump, new trials mix with results measured on the old task. |
| Comments or formatting in an arm file; the arm file's name; moving an injected file to another path; the content of a script that a `[gate] extra` command runs; adding, changing or removing `comparator` | Nothing. For the script, rename the arm when you change it, so one history does not hold two versions. |
| In `bank.toml`: adding, changing or removing `[plan] repeats_per_cell` or `[contrasts]` | No hash and no resume key moves, and no trial is bought again. The plan changes only what the plan line, new trial rows, the scorecard and `fathom reconcile` say about replication (`authoring.md`, section 4). |

`config_hash` is the sha256 of a canonical JSON rendering (sorted keys) of the resolved arm.
That exact string, the text that was hashed, is called the **preimage** and is stored on every
row as `config_preimage`. It contains:

| Field | Source |
|---|---|
| `name`, `adapter`, `model`, `strategy`, `effort` | the scenario file |
| `limits.trial_timeout_s` | the scenario file (`null` when unset) |
| `model_id` | `null` for this adapter (the CLI reports the exact model at run time) |
| `tools` | `source`, `repo`, and `allowed` / `disallowed` when non-empty, in file order |
| `tool_repo_sha`, `tool_invocation_cmd` | for `source = "repo"`: the repo's git HEAD and the command that runs it, which contains the repo's absolute path |
| `context.inject_sha`, `settings.inject_sha` | the injected files' content sha256, when declared |
| `plugins` | `name`, `version` and `tree_sha` of each mount, when declared |
| `env` | the `[env]` templates, sorted by name, when declared |
| `gate.extra` | the `[gate] extra` command strings, when declared |

An absent table and an empty one produce the same hash, so adding an optional table to the
schema never changes existing arms.

`comparator` (section 10) is not in the preimage. It orders the run and decides which cells
are bought, and changes nothing an arm measures, so declaring it never re-buys an arm.

**Provenance.** Every row also records `engine_version`, the fathom version that wrote it,
`cli_version`, and `written_at`, the UTC time it was written (ISO 8601, to the second). A run
row also records `scenario`, the name of the arm that ran. None of these is part of
`config_hash`, its preimage or the resume key, so upgrading the engine does not re-buy
completed trials; `written_at` is the one field that differs between two otherwise identical
runs. Rows written before a field existed are never rewritten, and read as they always did.

**Keep every arm committed.** `fathom reconcile` holds each completed trial's arm name against
the scenario files in the data root (`scenario-known`) and each row's `config_hash` against the
hash of its own stored preimage, computed again (`config-hash-preimage`). An arm whose file was
never committed cannot be attributed later.

## 12. Series arms

A `series` arm hands the whole task to an external multi-PR engine that decomposes it,
implements each PR with its own agent spawns, gates and integrates them. fathom drives it as a
black box over a narrow contract, documented in
[`docs/specs/2026-07-03-series-engine-contract.md`](../../../docs/specs/2026-07-03-series-engine-contract.md);
[convoy](https://github.com/grimaldost/convoy) is the reference engine.

- The arm sets `strategy = "series"`, `[tools] source = "repo"` and `repo` to a checkout of the
  engine. A relative `repo` resolves against the data root, not the scenario file. The
  engine runs as `uv run --project <repo> convoy run <series.toml>`, with the repository's
  absolute path in that command.
- Each task a series arm runs ships a `series.toml` template and the prompt directory it names
  under `[paths] prompts`. Before each trial fathom copies the prompts outside the workspace,
  rewrites `[paths]` to absolute locations, pins `[governance]` model and effort to the arm's,
  sets a non-bypass permission mode and fixed per-spawn budgets (implementation $20, review $5,
  fix $3, or `--max-spawn-usd` for all three), and strips per-PR model, effort and budget
  overrides.
- The engine spawns its agents itself, so the arm's `[tools] allowed`, `[context]`,
  `[settings]`, `[plugins]` and `[env]` do not reach those spawns; the template's
  `[governance.tools]` sets their tools.
- The engine also runs the template's `[[checks]]` itself. fathom removes what a gated arm's
  gate commands create in the workspace, but nothing the engine's checks leave there, so a
  test runner's cache or compiled bytecode they write reaches the result view and can tell a
  series trial apart from the others. Write checks that create nothing in the workspace (for
  Python, `python -B`, and `-p no:cacheprovider` for pytest).
- The plan prices a series trial as `PRs × (1 implementation + max_fix_attempts fixes +
  reviews)` spawns, each at its cap, and prints that arithmetic. `max_fix_attempts` comes from
  the template's `[review]` (2 when unset). When `[review] blocking = true` the engine reviews
  each PR once and again after each fix, so `reviews` is `1 + max_fix_attempts`; otherwise it
  is 0. At the default caps a PR under a blocking review with 2 fix attempts is priced at
  $20 + 2 × $3 + 3 × $5 = $41.
- `fathom smoke` checks the engine boundary without spending tokens, by running the data
  root's `scenarios/series.toml` arm against a stub `claude`. Without that file the check fails;
  pass `--no-engine-boundary` when the data root has no series arm.
