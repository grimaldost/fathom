"""Bank validation — the rule that decides whether a bank can measure anything.

CONTRIBUTING stated the validation triad in prose.  A rule that must always hold
belongs in a gate: without these checks banks can be created that produce no signal.

The triad, and what each property protects against:

1. :data:`PROP_FIXTURE_FAILS` — **the unmodified fixture must leave the arm
   something to do**: at least one verifier criterion starts false.  This is the
   anti-ceiling property and the answer to "does the bare arm ever actually
   fail?".  A fixture on which every criterion is already true scores every arm
   100%, and the run returns a null that reads as "the tool does not help" —
   precisely the answer the decisions downstream of this harness are hoping for.
   Read the CRITERIA, not the exit code: a verifier may legitimately gate exit 0
   on a preservation criterion that holds before the agent starts, while the
   signal being measured lives in the criteria that do not.  Always checked.

   What this property does NOT catch: a bank whose tasks are simply too EASY, so
   every arm succeeds.  That ceiling is invisible before the spend and stays
   authoring judgement (turn budget, task scale, a pilot's discrimination); see
   "What no check covers" in ``skills/fathom-eval/reference/bank-design.md``.
2. :data:`PROP_SOLUTION_PASSES` — **the verifier must PASS on a reference
   solution** (``<task>/solution/`` overlaid on the fixture).  Guards the mirror
   failure: an unsatisfiable verifier no arm can ever satisfy.
3. :data:`PROP_GATE_RUNNABLE` — **the task's gate command must actually run on
   the untouched fixture.**  Deliberately weaker than "must be green", because
   green is not the universally correct answer: a task that encodes the target
   feature in its test suite starts red BY DESIGN, and that red is the signal
   a gated arm works against.  The harness cannot tell a deliberate red baseline
   from a broken one, so it refuses only when the gate could not execute at all
   (command not found) and reports the observed colour otherwise as a WARN the
   author must confirm.

4. :data:`PROP_GATE_PATHS` — **the gate commands name paths that exist** (FATH-B54).
   A gate command whose script is missing runs, fails to find it and contributes
   nothing, so a gated arm runs as the ungated one; a gate that went red is a
   result, a gate that could never have run is a broken arm. The task's ``[gate]
   run`` and the ``[gate] extra`` of every arm whose strategy runs it are split into
   words as the gate's shell reads them, and each path-shaped word is resolved the
   way the arm will resolve it (:func:`_gate_path_checks`). A missing path anchored
   on ``${task_dir}``, a missing absolute path the gate runs (a command word, or a
   word with a script suffix such as ``.py``) and a ``${NAME}`` that nothing fills
   are FAILs, because the agent cannot create them. Any other missing absolute word
   is a WARN, because it may be a pattern rather than a path (``grep -q "/health"``),
   and so is a missing path relative to the workspace, because the task may ask the
   agent to create it. Words the check cannot resolve (shell variables, globs) and
   words holding pattern syntax (a sed address, an awk program) are left alone, so
   its errors lean toward a broken gate it did not catch rather than a working one
   it refused. Only checked when the bank or an arm declares a gate.

Properties 2 and 3 are ``unverifiable`` when the bank ships no reference solution
or declares no gate.  ``unverifiable`` is deliberately NOT a pass: it is reported
as its own status and blocks under ``--strict``.  Calling an unmeasurable
property green is the vacuous-gate failure mode this module exists to remove —
and so is refusing a bank the harness merely cannot interpret, which is why the
ambiguous red-gate case is ``warn`` rather than ``fail``.

What stays out: the measured turn budget, the scale of the task material and a
pilot's discrimination are authoring judgement, not machine checks, and are
written down under "What no check covers" in the authoring guide's ``bank-design.md``.

Free — every check runs the verifier locally against a staged fixture.  No spawn,
no spend.
"""

from __future__ import annotations

import dataclasses
import os
import re
import shlex
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fathom.adapters.claude_cli import env_for_agent_code, run_shell_bounded
from fathom.strategies.gated_session import PLACEHOLDER_TASK_DIR, PLACEHOLDER_WORKSPACE
from fathom.taskbank import Bank, Task

if TYPE_CHECKING:
    from fathom.scenario import ResolvedScenario

PROP_FIXTURE_FAILS = "verifier fails on the unmodified fixture"
PROP_SOLUTION_PASSES = "verifier passes on the reference solution"
PROP_GATE_RUNNABLE = "task gate is runnable on the fixture"
PROP_GATE_PATHS = "gate commands name paths that exist"
PROP_PLAN = "bank.toml [plan] is well formed"

# The strategies that run an arm's `[gate] extra` (`cli._default_executor_factory`).
# Every other strategy ignores it, so an extra on such an arm never runs and is not checked.
_GATE_EXTRA_STRATEGIES = frozenset({"gated-session", "gated-review"})
# A word ending in one of these names a script even without a separator (`python probe.py`).
# `.bat` and `.cmd` are left out: a bare `npm.cmd` is found on PATH, not in the workspace.
_SCRIPT_SUFFIXES = (".py", ".sh", ".bash", ".ps1", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl")
_PLACEHOLDER = re.compile(r"\$\{[^}]*\}")
# The placeholders an arm fills in its `[gate] extra`; the task's own gate takes none.
_FILLED = (PLACEHOLDER_TASK_DIR, PLACEHOLDER_WORKSPACE)
_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# A cmd.exe switch (`/c`, `/q`): a slash and a name, no further separator and no suffix.
_WINDOWS_SWITCH = re.compile(r"^/[A-Za-z?][^/\\.]*$")
# Options whose next word is code or a module name, not a path.
_NON_PATH_OPTIONS = frozenset({"-c", "-m"})
_SHELL_OPERATOR_CHARS = frozenset("();<>|&")
# A word holding one of these is the shell's to resolve: a variable or a glob.
_SHELL_RESOLVED_CHARS = frozenset("$%*?[")
# A word holding one of these is a regular expression, a sed or awk address, or a brace
# expansion (`/^def /`, `/start/,/end/p`, `src/{a,b}.py`), not a file name.
_PATTERN_CHARS = frozenset("^{},|")
# The shell a gate runs under: `/bin/sh` on POSIX, `cmd.exe` on Windows.
_POSIX_SHELL = os.name != "nt"

# Where a bank ships the reference implementation, as an overlay copied over the
# staged fixture tree.
SOLUTION_DIRNAME = "solution"

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_WARN = "warn"  # observed, ambiguous, reported — blocks only under --strict
STATUS_UNVERIFIABLE = "unverifiable"

# A shell reporting "command not found" — the gate never ran at all, which is a
# broken bank rather than a red baseline.
_UNRUNNABLE_RCS = (127, 9009)

_GATE_TIMEOUT_S = 300


@dataclasses.dataclass(frozen=True)
class BankCheck:
    """One property, checked against one task."""

    task_id: str
    prop: str
    status: str  # pass | fail | unverifiable
    detail: str = ""


def overlay_solution(task: Task, workspace: Path) -> bool:
    """Copy ``<task>/solution/`` over *workspace*; True when a solution existed."""
    solution = task.task_dir / SOLUTION_DIRNAME
    if not solution.is_dir():
        return False
    shutil.copytree(solution, workspace, dirs_exist_ok=True)
    return True


def run_gate(command: str, workspace: Path) -> tuple[int, str]:
    """Run a task's gate command from *workspace*; return (returncode, output).

    The environment is the one a gated arm's gate gets: fathom's own, without its
    ``FATHOM_*`` variables, the launch directory's ``PWD`` / ``OLDPWD``, any value
    naming the data root, or the billing and API credential variables a spawn is denied
    (:func:`~fathom.adapters.claude_cli.env_for_agent_code`), so a gate checked here
    behaves as it will under a run, where it executes code the agent wrote. A gate that
    finds its tools only through a virtual environment inside the data root therefore
    fails here as it would under a run.

    A gate that outlives :data:`_GATE_TIMEOUT_S` is stopped with every process under it
    (:func:`~fathom.adapters.claude_cli.run_shell_bounded`), and ``TimeoutExpired`` is
    raised once they are gone.
    """
    proc = run_shell_bounded(
        command,
        cwd=workspace,
        env=env_for_agent_code(),
        timeout=_GATE_TIMEOUT_S,
        encoding=None,
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-2000:]


def validate_bank(
    bank: Bank,
    *,
    stage_fn: Callable[..., Any],
    verifier_fn: Callable[..., Any],
    gate_fn: Callable[[str, Path], tuple[int, str]] = run_gate,
    overlay_fn: Callable[[Task, Path], bool] = overlay_solution,
    base_branch: str = "main",
    scenarios: Sequence[ResolvedScenario] = (),
) -> list[BankCheck]:
    """Check the validation triad for every task in *bank*.

    Seams are injected so the logic is unit-testable without git, a subprocess or
    a real verifier — the same split the smoke gate uses.

    *scenarios* are the arms that will run against the bank. Their ``[gate] extra``
    commands are path-checked against every task (:data:`PROP_GATE_PATHS`); with
    none given, only the tasks' own gates are.
    """
    checks: list[BankCheck] = []

    if not bank.tasks:
        return [
            BankCheck(
                "(bank)",
                PROP_FIXTURE_FAILS,
                STATUS_FAIL,
                "the bank declares no tasks — an empty bank measures nothing, and "
                "vacuously passing it would be the failure this check exists to catch",
            )
        ]

    for task in bank.tasks:
        checks.extend(
            _check_task(task, stage_fn, verifier_fn, gate_fn, overlay_fn, base_branch, scenarios)
        )
    return checks


def plan_checks(bank_dir: Path) -> list[BankCheck]:
    """A FAIL when ``<bank_dir>/bank.toml`` carries a malformed ``[plan]``; nothing otherwise.

    The plan is parsed apart from :func:`fathom.taskbank.load_bank`
    (:func:`fathom.replication.read_plan`), so ``fathom validate`` checks it here: ``fathom
    run`` refuses a malformed plan, and validation should not pass a bank that run refuses.
    A well-formed or absent plan adds no line, so a bank without one validates as before.
    """
    from fathom.replication import read_plan

    reading = read_plan(bank_dir)
    if reading.problem is None:
        return []
    return [BankCheck("(bank)", PROP_PLAN, STATUS_FAIL, f"{reading.path}: {reading.problem}")]


def _fixture_check(task: Task, result: Any) -> BankCheck:
    """Property 1: does the untouched fixture leave the arm something to do?

    Read the CRITERIA, not just the exit code.  A verifier legitimately gates
    exit 0 on a preservation criterion that is trivially true before the agent
    touches anything (``behavior_preserved``) while the signal being measured
    lives in the other criteria.  Some banks by design gate on preservation while
    the discriminating signal lives in per-criterion variation.  An exit-code-only
    check cannot detect this and would misreport it as unmeasurable.  Always read
    criteria, not headline exit code.
    """
    outcome = getattr(result, "outcome", "error")
    criteria = getattr(result, "criteria", None)

    if outcome == "error":
        return BankCheck(
            task.id,
            PROP_FIXTURE_FAILS,
            STATUS_FAIL,
            "the verifier errored on the unmodified fixture (crash, timeout or "
            f"non-JSON): {(getattr(result, 'stderr', '') or '')[:200]}",
        )

    if not criteria:
        return BankCheck(
            task.id,
            PROP_FIXTURE_FAILS,
            STATUS_FAIL,
            "the verifier emitted no criteria on the unmodified fixture — there is "
            "nothing for the per-criterion table to report and nothing to discriminate on",
        )

    start_false = sorted(k for k, v in criteria.items() if not v)
    if start_false:
        return BankCheck(
            task.id,
            PROP_FIXTURE_FAILS,
            STATUS_PASS,
            f"{len(start_false)}/{len(criteria)} criteria start false, so an arm has "
            f"something to fix: {start_false}"
            + (
                ""
                if outcome == "fail"
                else " (the exit-code gate is already green — the "
                "discriminating signal is per-criterion, not headline pass-rate)"
            ),
        )

    return BankCheck(
        task.id,
        PROP_FIXTURE_FAILS,
        STATUS_FAIL,
        f"every criterion ({sorted(criteria)}) is ALREADY TRUE on the unmodified "
        "fixture — this task cannot discriminate between arms and will score every arm 100%",
    )


def _gate_check(task: Task, gate_cmd: str, rc: int, output: str) -> BankCheck:
    """Property 3, scoped to what the harness can actually tell apart."""
    if rc == 0:
        return BankCheck(
            task.id, PROP_GATE_RUNNABLE, STATUS_PASS, f"`{gate_cmd}` exited 0 (green baseline)"
        )
    if rc in _UNRUNNABLE_RCS:
        return BankCheck(
            task.id,
            PROP_GATE_RUNNABLE,
            STATUS_FAIL,
            f"`{gate_cmd}` exited {rc} — the gate command could not be executed at all, "
            f"so every gated arm's gate is meaningless: {output[-400:]}",
        )
    return BankCheck(
        task.id,
        PROP_GATE_RUNNABLE,
        STATUS_WARN,
        f"`{gate_cmd}` exited {rc} — the baseline is RED. Deliberate for a brownfield "
        "task whose visible suite encodes the target feature; a defect if the fixture "
        f"is simply broken. Confirm which: {output[-300:]}",
    )


def _check_task(
    task: Task,
    stage_fn: Callable[..., Any],
    verifier_fn: Callable[..., Any],
    gate_fn: Callable[[str, Path], tuple[int, str]],
    overlay_fn: Callable[[Task, Path], bool],
    base_branch: str,
    scenarios: Sequence[ResolvedScenario] = (),
) -> list[BankCheck]:
    entry = task.task_dir / task.verify["entry"]
    timeout_s = int(task.verify.get("timeout_s", 60))
    checks: list[BankCheck] = []

    # --- 1. the verifier must FAIL on the untouched fixture ----------------
    try:
        with stage_fn(task, base_branch) as workspace:
            # --- 4. read before the verifier or the gate can write into the fixture
            path_checks = _gate_path_checks(task, Path(workspace), scenarios)
            checks.append(_fixture_check(task, verifier_fn(entry, workspace, timeout_s=timeout_s)))

            # --- 3. the task's gate must be green on that same fixture -----
            gate_cmd = task.gate.get("run")
            if not gate_cmd:
                checks.append(
                    BankCheck(
                        task.id,
                        PROP_GATE_RUNNABLE,
                        STATUS_UNVERIFIABLE,
                        "the task declares no [gate] run command",
                    )
                )
            else:
                checks.append(_gate_check(task, str(gate_cmd), *gate_fn(str(gate_cmd), workspace)))
            checks.extend(path_checks)
    except Exception as exc:
        return [
            BankCheck(
                task.id,
                PROP_FIXTURE_FAILS,
                STATUS_FAIL,
                f"could not stage the task: {type(exc).__name__}: {exc}",
            )
        ]

    # --- 2. the verifier must PASS on the reference solution ---------------
    try:
        with stage_fn(task, base_branch) as workspace:
            if not overlay_fn(task, workspace):
                checks.append(
                    BankCheck(
                        task.id,
                        PROP_SOLUTION_PASSES,
                        STATUS_UNVERIFIABLE,
                        f"no {SOLUTION_DIRNAME}/ directory — the verifier is not known to be "
                        "satisfiable, so a null result from this task cannot be distinguished "
                        "from an unsatisfiable verifier",
                    )
                )
            else:
                result = verifier_fn(entry, workspace, timeout_s=timeout_s)
                outcome = getattr(result, "outcome", "error")
                checks.append(
                    BankCheck(
                        task.id,
                        PROP_SOLUTION_PASSES,
                        STATUS_PASS if outcome == "pass" else STATUS_FAIL,
                        f"verifier outcome on {SOLUTION_DIRNAME}/ = {outcome}"
                        + (
                            ""
                            if outcome == "pass"
                            else " — the reference implementation does not satisfy the verifier, "
                            "so NO arm can; every result this task produces is a manufactured null"
                        ),
                    )
                )
    except Exception as exc:
        checks.append(
            BankCheck(
                task.id,
                PROP_SOLUTION_PASSES,
                STATUS_FAIL,
                f"could not check the reference solution: {type(exc).__name__}: {exc}",
            )
        )

    return checks


def _shell_words(cmd: str) -> list[str]:
    """*cmd* split into words as the gate's shell reads them, each operator a word of its own.

    A gate runs with ``shell=True``: ``/bin/sh`` on POSIX, ``cmd.exe`` on Windows, which
    knows double quotes only and no backslash escape, so Windows splits in shlex's non-POSIX
    mode with the double quotes then dropped. A command that does not split (an unclosed
    quote) gives no words, and so no finding.
    """
    posix = _POSIX_SHELL
    lexer = shlex.shlex(cmd, posix=posix, punctuation_chars=True)
    lexer.whitespace_split = True
    if not posix:
        lexer.quotes = '"'
    try:
        words = list(lexer)
    except ValueError:
        return []
    return words if posix else [w.replace('"', "") for w in words]


def _path_words(cmd: str) -> list[tuple[str, bool]]:
    """The words of *cmd* that name a path, as written, placeholders not filled in.

    A word names a path when it holds a separator or a ``${...}``, or ends in a script
    suffix. Left out: options (except a ``--name=value`` whose value holds a
    placeholder), the word after ``-c`` or ``-m`` (code, a module name), the target of an
    output redirection (written, not read), URLs, and on Windows a ``cmd.exe`` switch or
    a single-quoted word. A ``NAME=value`` assignment is read as its value, and a pytest
    node id as the file before ``::``.

    Each word comes with whether it is a command word, the program the shell runs: the
    first word of the command, or the first after ``;``, ``&&``, ``||``, ``|``, ``&``,
    ``(`` or ``!``, past any ``NAME=value`` and redirection.
    """
    words: list[tuple[str, bool]] = []
    skip_next = False
    command_next = True
    for word in _shell_words(cmd):
        is_command, command_next = command_next, False
        if skip_next:
            skip_next, command_next = False, is_command
            continue
        if word in _NON_PATH_OPTIONS:
            skip_next = True
            continue
        if word and set(word) <= _SHELL_OPERATOR_CHARS:
            skip_next = ">" in word
            # A redirection leaves the command word where it was; any other operator
            # starts a new command.
            command_next = is_command if ("<" in word or ">" in word) else True
            continue
        if word == "!":
            command_next = is_command
            continue
        if word.startswith("-"):
            _, sep, value = word.partition("=")
            if not (sep and "${" in value):
                continue
            word = value
        if _ASSIGNMENT.match(word):
            command_next, is_command = is_command, False
            word = word.split("=", 1)[1]
        word = word.split("::", 1)[0]
        if _URL.match(word):
            continue
        if not _POSIX_SHELL and ("'" in word or _WINDOWS_SWITCH.match(word)):
            continue
        if "${" in word or "/" in word or "\\" in word or word.lower().endswith(_SCRIPT_SUFFIXES):
            words.append((word, is_command))
    return words


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except (OSError, ValueError):
        return False


def _gate_path_checks(
    task: Task, workspace: Path, scenarios: Sequence[ResolvedScenario]
) -> list[BankCheck]:
    """Property 4: every path a gate command names exists on the untouched fixture.

    The commands are the task's ``[gate] run``, which runs as written, and the ``[gate]
    extra`` of each arm whose strategy runs it, which the arm runs with ``${task_dir}``
    and ``${workspace}`` filled in for this task (``GatedSessionExecutor.run_trial``). A
    relative path resolves against the staged workspace, the gate's working directory.

    FAIL, which ``fathom run`` refuses: a ``${...}`` the command's runner does not fill (any
    placeholder in the task's own gate), a missing path anchored on ``${task_dir}``, and a
    missing absolute path the gate runs: a command word, or a word with a script suffix.
    The agent cannot create any of them. WARN, which blocks only under ``--strict``: any
    other missing absolute word, which may be a pattern rather than a path (``grep -q
    "/health"``), and a missing path relative to the workspace or under ``${workspace}``,
    which the task may ask the agent to create. A word holding a shell variable (``$NAME``,
    ``%NAME%``), a glob, a leading ``~`` or pattern syntax (:data:`_PATTERN_CHARS`) is not
    resolved and not reported. No gate command, no check.
    """
    sources: list[tuple[str, str, frozenset[str]]] = []  # (where, command, placeholders)
    gate_cmd = task.gate.get("run")
    if gate_cmd:
        sources.append(("the task's [gate] run", str(gate_cmd), frozenset()))
    for sc in scenarios:
        if sc.strategy in _GATE_EXTRA_STRATEGIES:
            sources.extend(
                (f"arm `{sc.name}` [gate] extra", str(cmd), frozenset(_FILLED))
                for cmd in sc.gate.extra
                if cmd
            )
    if not sources:
        return []

    values = {
        PLACEHOLDER_TASK_DIR: Path(task.task_dir).resolve().as_posix(),
        PLACEHOLDER_WORKSPACE: workspace.resolve().as_posix(),
    }
    # (status, command, message) -> where; the same command on several arms is one finding.
    findings: dict[tuple[str, str, str], list[str]] = {}
    checked = 0
    for where, cmd, filled in sources:
        for name in dict.fromkeys(_PLACEHOLDER.findall(cmd)):
            if name not in filled:
                findings.setdefault((STATUS_FAIL, cmd, _unfilled(name, filled)), []).append(where)
        for word, is_command in _path_words(cmd):
            if any(name not in filled for name in _PLACEHOLDER.findall(word)):
                continue  # reported above
            unfilled = _PLACEHOLDER.sub("", word)
            if not _SHELL_RESOLVED_CHARS.isdisjoint(unfilled) or unfilled.startswith("~"):
                continue  # a shell variable or a glob: the shell resolves it, not this check
            if not _PATTERN_CHARS.isdisjoint(unfilled):
                continue  # a pattern, an address or a brace expansion, not a file name
            expanded = word
            for name, value in values.items():
                expanded = expanded.replace(name, value)
            checked += 1
            path = Path(expanded)
            target = path if path.anchor else workspace / path
            if _exists(target):
                continue
            absolute = bool(path.anchor) and PLACEHOLDER_WORKSPACE not in word
            runs = is_command or word.lower().endswith(_SCRIPT_SUFFIXES)
            if PLACEHOLDER_TASK_DIR in word or (absolute and runs):
                message = (
                    f"`{word}` is {target.as_posix()}, which does not exist. The gate cannot "
                    "run what it names, so a gated trial's gate contributes nothing and the "
                    "arm runs as an ungated one."
                )
                status = STATUS_FAIL
            elif absolute:
                message = (
                    f"`{word}` would be {target.as_posix()}, which does not exist. Fine if the "
                    "word is a pattern rather than a path, or the command creates it first; "
                    "otherwise the gate can never read it."
                )
                status = STATUS_WARN
            else:
                message = (
                    f"`{word}` is not in the staged fixture (a relative path resolves against "
                    "the workspace, the gate's working directory). Fine if the task asks the "
                    "agent to create it; otherwise the gate can never find it."
                )
                status = STATUS_WARN
            findings.setdefault((status, cmd, message), []).append(where)

    if not findings:
        return [
            BankCheck(
                task.id,
                PROP_GATE_PATHS,
                STATUS_PASS,
                f"{checked} path(s) named by {len(sources)} gate command(s) exist"
                if checked
                else f"{len(sources)} gate command(s) name no path this check resolves",
            )
        ]
    return [
        BankCheck(task.id, PROP_GATE_PATHS, status, f"`{cmd}` ({'; '.join(wheres)}): {message}")
        for (status, cmd, message), wheres in sorted(
            findings.items(), key=lambda item: item[0][0] != STATUS_FAIL
        )
    ]


def _unfilled(name: str, filled: frozenset[str]) -> str:
    """Why *name* in a gate command is a FAIL."""
    if not filled:
        return (
            f"`{name}` is not filled in. The task's own gate runs as written; only an arm's "
            f"[gate] extra takes {PLACEHOLDER_TASK_DIR} and {PLACEHOLDER_WORKSPACE}."
        )
    return (
        f"`{name}` is not a placeholder fathom fills ({PLACEHOLDER_TASK_DIR} and "
        f"{PLACEHOLDER_WORKSPACE} are), so it reaches the shell as written. Write an environment "
        "variable the shell's own way ($NAME, %NAME%)."
    )


def validation_ok(checks: Sequence[BankCheck], *, strict: bool = False) -> bool:
    """True when no check FAILED (and, under *strict*, none warned or was unverifiable)."""
    blocking = {STATUS_FAIL} | ({STATUS_WARN, STATUS_UNVERIFIABLE} if strict else set())
    return not any(c.status in blocking for c in checks)


def render_validation(bank_name: str, checks: Sequence[BankCheck]) -> str:
    """Human-readable validation report for one bank."""
    marks = {
        STATUS_PASS: "PASS",
        STATUS_FAIL: "FAIL",
        STATUS_WARN: "WARN",
        STATUS_UNVERIFIABLE: "UNVERIFIABLE",
    }
    lines = [f"validate: {bank_name}"]
    by_task: dict[str, list[BankCheck]] = {}
    for c in checks:
        by_task.setdefault(c.task_id, []).append(c)
    for task_id, task_checks in by_task.items():
        lines.append(f"  {task_id}:")
        for c in task_checks:
            lines.append(f"    [{marks.get(c.status, c.status)}] {c.prop}")
            if c.detail:
                lines.append(f"           {c.detail}")

    failed = sum(1 for c in checks if c.status == STATUS_FAIL)
    warned = sum(1 for c in checks if c.status == STATUS_WARN)
    unver = sum(1 for c in checks if c.status == STATUS_UNVERIFIABLE)
    passed = sum(1 for c in checks if c.status == STATUS_PASS)
    lines.append("")
    lines.append(
        f"VALIDATION: {passed} pass, {failed} fail, {warned} warn, {unver} unverifiable"
        + ("  — BANK CANNOT MEASURE" if failed else "")
    )
    return "\n".join(lines)
