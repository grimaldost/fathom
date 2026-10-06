"""Gated-session strategy: one spawn + a deterministic gate + a bounded fix loop.

Models a series engine's engine-INDEPENDENT gate discipline WITHOUT the
orchestration engine: the agent implements once, the harness runs the task's
visible gate command, and on failure re-prompts the agent with the gate output up
to ``max_fix_attempts`` times. The ``with_review`` variant adds one structured
review pass (VERDICT + feedback -> one fix) after the gate is green. Ablation
companion to ``single_session`` / ``series`` (spec 6).

The gate the agent runs is the task's OWN visible suite (``task.gate["run"]``),
distinct from the blind harness-side acceptance oracle (``verify.py``, ADR-0003)
that grades every arm afterward. ``detail`` records the gate outcome (first/final,
fix count) so the defect-escape metric is recoverable from the ledger, plus a
bounded excerpt of whatever the scenario's ``[gate].extra`` commands printed — a
bare verdict cannot say WHICH tool ran or what it found, and for an arm whose extra
gate is an external tool that provenance is the thing being attested.

A gate runs code the agent wrote and its output is re-briefed to the agent, so it is
held to the same blindness as the spawn (ADR-0003, ADR-0004): it runs without
fathom's ``FATHOM_*`` variables, the launch directory or any value naming the data
root, and the agent sees each command as written, with ``${task_dir}`` left
unexpanded and masked in the output and in the command line.

A gate also runs in the workspace the verifier scores, and a single-session arm has
no gate. Whatever a gate command creates there (a test runner's cache, compiled
bytecode) is removed when it exits, so the scored tree does not tell a gated arm from
one without a gate.

Stdlib only.
"""

from __future__ import annotations

import contextlib
import functools
import os
import re
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fathom.adapters.base import ExitStatus
from fathom.adapters.claude_cli import env_for_agent_code, hidden_dirs
from fathom.adapters.claude_cli import run_shell_bounded as _run_shell
from fathom.strategies.base import PIN_STRONG, TrialResult, TrialStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fathom.adapters.base import Runner, RunRecord
    from fathom.scenario import ResolvedScenario
    from fathom.taskbank import Task

_GATE_TIMEOUT_S = 120

# How much of the extra gate's output a trial row keeps, per recorded round, as a
# whitespace-condensed head + tail. The task's own gate needs no excerpt — it is the
# project's suite, and first/final says all a reader needs. An extra gate is a
# harness-side augmentation, often an external tool: whether it ran at all, which
# build of it ran, and what it reported are not recoverable from `red`/`green`, and
# a run whose only record of them is the fix prompt keeps nothing once the trial ends.
_EXTRA_HEAD_CHARS = 500
_EXTRA_TAIL_CHARS = 500
# An extra gate that never executed is a different fact from one that ran silently:
# the task's own gate went red first and short-circuited the list.
_EXTRA_NOT_REACHED = "<not run: the task's own gate was red>"
_EXTRA_SILENT = "<ran, no output>"

# `subprocess.run` decodes each stream on its own reader THREAD. When a decode
# raises there, nothing propagates to the caller: the call returns with the exit
# code intact and that stream as ``None``. Read strictly (the pre-0.6.0 posture),
# a single non-ASCII byte from a cp1252 console therefore turned the gate's whole
# output into ``(None or "") + (None or "")`` — an empty string — and the fix loop
# was re-briefed with nothing while the red/green verdict stayed correct.
# ``errors="replace"`` (below) removes the cause; this names what is left, because
# a lost stream must not be able to re-enter the same silence by another route.
GATE_STREAM_LOST = (
    "<gate output unavailable: a reader thread produced no text for this stream; "
    "the exit code below is still the gate's own verdict>"
)

# Run-time path placeholders a scenario's ``[gate].extra`` command may carry.
# A gate command runs with ``cwd`` = the trial workspace (a fresh temp dir), so a
# harness-side probe living in the task directory is unreachable by any relative
# path and a machine-absolute path is neither portable nor committable.  These are
# substituted at RUN time, exactly as ``[env]`` substitutes ``${workspace}`` at
# spawn time, so the *template* — not a per-machine path — is what enters
# ``config_hash`` (scenario.py ``GateConfig``): the arm stays reproducible across
# checkouts, and relocating the repo does not fork longitudinal history.  The agent
# is shown the template too: the fix prompt quotes each command as written, and the
# gate's output has the task directory masked back to its placeholder
# (:func:`mask_task_dir`), because that directory lies inside the data root.
PLACEHOLDER_TASK_DIR = "${task_dir}"
PLACEHOLDER_WORKSPACE = "${workspace}"
# What a withheld directory (the data root, :func:`~fathom.adapters.claude_cli.hidden_dirs`)
# becomes in text the agent is shown. No placeholder names it, so it gets a plain mark.
MASKED_DIR = "<withheld>"
_FIX_PROMPT = (
    "The project's quality gate is failing. Fix the implementation so the gate passes. "
    "Do not modify the tests.\n\nGate command: {cmd}\nGate output (tail):\n{output}"
)
_REVIEW_PROMPT = (
    "Review your implementation for correctness against the task. If it is complete and "
    "correct, reply with a line 'VERDICT: APPROVE'. Otherwise reply 'VERDICT: "
    "REQUEST_CHANGES' followed by the specific fixes needed."
)


def _describe_extra(output: str | None) -> str:
    """A one-line, bounded view of an extra gate's output for the ledger's ``detail``.

    ``None`` means the commands never ran. Long output keeps its head and its tail:
    a driver prints its provenance and its verdict at opposite ends of the stream,
    and the middle is the part a reader can afford to lose.
    """
    if output is None:
        return _EXTRA_NOT_REACHED
    condensed = " ".join(output.split())
    if not condensed:
        return _EXTRA_SILENT
    budget = _EXTRA_HEAD_CHARS + _EXTRA_TAIL_CHARS
    if len(condensed) <= budget:
        return condensed
    dropped = len(condensed) - budget
    return (
        f"{condensed[:_EXTRA_HEAD_CHARS]} ...[{dropped} chars omitted]... "
        f"{condensed[len(condensed) - _EXTRA_TAIL_CHARS :]}"
    )


def _as_posix(path: Path) -> str:
    """Absolute, forward-slash path string (safe inside a shell command on both OSes)."""
    return str(Path(path).resolve()).replace("\\", "/")


_SEP = r"[\\/]+"


def _component(part: str) -> str:
    """A pattern for one path component, as written or percent-encoded (a file URI)."""
    forms = {re.escape(part), re.escape(urllib.parse.quote(part))}
    if len(forms) == 1:
        return forms.pop()
    return "(?:" + "|".join(sorted(forms, key=len, reverse=True)) + ")"


@functools.cache
def _get_short_path_name() -> Any:
    """``GetShortPathNameW`` from kernel32, typed for ctypes."""
    import ctypes
    from ctypes import wintypes

    fn = ctypes.WinDLL("kernel32").GetShortPathNameW
    fn.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    fn.restype = wintypes.DWORD
    return fn


def _short_name(path: str) -> str | None:
    """*path*'s 8.3 short spelling on Windows (``C:\\Users\\LONGNA~1\\...``), or ``None``:
    on another OS, for a path that does not exist, or when the volume keeps no short
    names."""
    if os.name != "nt":
        return None
    try:
        import ctypes

        fn = _get_short_path_name()
        size = fn(path, None, 0)
        if not size:
            return None
        buf = ctypes.create_unicode_buffer(size)
        if not fn(path, buf, size):
            return None
    except (OSError, AttributeError):
        return None
    return buf.value


def _absolute_forms(path: Path) -> set[str]:
    """*path* as given (made absolute), resolved, and in its short spelling on Windows."""
    forms = {str(Path(path).absolute())}
    with contextlib.suppress(OSError):
        forms.add(str(Path(path).resolve()))
    for form in list(forms):
        short = _short_name(form)
        if short:
            forms.add(short)
    return forms


def _relative_tails(path: Path, start: Path) -> set[tuple[str, ...]]:
    """The components of *path* relative to *start* that follow the leading ``..`` ones,
    for each spelling of the two, when that relative path climbs out of *start*.

    A relative path that stays inside *start* names nothing *start* does not hold, and
    one made of ``..`` alone would match in any text that climbs a directory.
    """
    tails: set[tuple[str, ...]] = set()
    for target in _absolute_forms(path):
        for origin in _absolute_forms(start):
            try:
                rel = os.path.relpath(target, origin)
            except ValueError:  # another drive: there is no relative spelling
                continue
            parts = [p for p in re.split(r"[\\/]+", rel) if p]
            ups = 0
            while ups < len(parts) and parts[ups] == "..":
                ups += 1
            if 0 < ups < len(parts):
                tails.add(tuple(parts[ups:]))
    return tails


def _path_patterns(path: Path, start: Path | None = None) -> list[str]:
    """Patterns for every spelling of *path* a tool is likely to print.

    Absolute and resolved, and on Windows the 8.3 short spelling, with either separator
    (doubled ones included, as a repr prints them), percent-encoded components (a file
    URI), and for a path on a drive, the forms Git Bash, Cygwin and WSL tools print
    (``/c/...``, ``/cygdrive/c/...``, ``/mnt/c/...``). When a spelling holds whitespace,
    its part before the first whitespace is matched too: that is what an unquoted command
    line splits it into.

    With *start* (the directory the command runs in), the relative spelling is matched
    too, from any depth: one or more ``..`` and then the rest of the path relative to
    *start*. A tool that prints whichever of the two spellings is shorter (pytest does)
    prints this one when *path* and *start* share a long prefix, and whoever knows
    *start* can read *path* back from it.
    """
    # Absolute spellings, and relative ones that climb out of *start*: a relative one
    # inside it ("t") would match inside unrelated words, and a filesystem root would
    # match every separator.
    forms = _absolute_forms(path)
    patterns: list[str] = []
    if start is not None:
        for tail in _relative_tails(path, start):
            patterns.append(r"(?:\.\." + _SEP + ")+" + _SEP.join(_component(p) for p in tail))
    for form in sorted(forms, key=len, reverse=True):
        if Path(form).parent == Path(form):
            continue
        # (spelling, what must follow it): a split-off head is a word of its own, so it
        # is not matched as the start of a longer name.
        spellings = [(form, "")]
        head = re.split(r"\s", form, maxsplit=1)[0]
        if head != form and len([p for p in re.split(r"[\\/]+", head) if p]) > 2:
            spellings.append((head, r"(?=$|[\s'\"),;\]])"))
        for spelling, tail in spellings:
            parts = [p for p in re.split(r"[\\/]+", spelling) if p]
            lead = _SEP if spelling[:1] in "\\/" else ""
            patterns.append(lead + _SEP.join(_component(p) for p in parts) + tail)
            drive = re.fullmatch(r"([A-Za-z]):", parts[0])
            if drive and len(parts) > 1:
                patterns.append(
                    r"(?:/cygdrive|/mnt)?/"
                    + re.escape(drive.group(1))
                    + _SEP
                    + _SEP.join(_component(p) for p in parts[1:])
                    + tail
                )
    return patterns


def _mask(text: str, path: Path, replacement: str, start: Path | None = None) -> str:
    patterns = _path_patterns(path, start)
    if not patterns:
        return text
    flags = re.IGNORECASE if os.name == "nt" else 0
    # Longest first, so a whole path wins over the part of it before a space.
    patterns.sort(key=len, reverse=True)
    return re.sub("|".join(patterns), lambda _m: replacement, text, flags=flags)


def mask_task_dir(text: str, task_dir: Path, workspace: Path | None = None) -> str:
    """*text* with every spelling of *task_dir* replaced by :data:`PLACEHOLDER_TASK_DIR`.

    ``${task_dir}`` is the one data-root path a gate is handed, and what a gate prints
    goes back to the agent in the fix prompt: a probe's traceback names the probe's own
    file. The directory is matched in every spelling :func:`_path_patterns` knows, the
    ones relative to *workspace* (where a gate runs) included, and without regard to
    case on Windows, where paths ignore it.
    """
    return _mask(text, task_dir, PLACEHOLDER_TASK_DIR, workspace)


def mask_gate_text(text: str, task_dir: Path, workspace: Path | None = None) -> str:
    """*text* as the agent may see it: the task directory masked to its placeholder,
    and then each withheld directory, the data root among them, to :data:`MASKED_DIR`.

    A gate that prints other paths inside the data root (a probe that walks up from
    its own file, say) has them masked too, while the command runs under ``fathom``,
    which registers the data root. Paths outside every withheld directory pass as
    they are. Pass the *workspace* the gate ran in, so that the spellings relative to
    it are masked as well: a test runner run from there prints one when it is shorter.
    """
    text = mask_task_dir(text, task_dir, workspace)
    for hidden in hidden_dirs():
        text = _mask(text, hidden, MASKED_DIR, workspace)
    return text


def _quoted(value: str, quote: str | None) -> str:
    """*value* made one shell word, given the quote the command is inside at that point.

    Double quotes work in both shells ``shell=True`` uses (``cmd.exe`` and ``/bin/sh``).
    Inside double quotes on POSIX, the characters the shell still treats specially are
    escaped; inside single quotes, a quote closes, is escaped, and reopens.
    """
    if quote == "'":
        return value.replace("'", "'\\''")
    if os.name != "nt":
        value = re.sub(r'([\\"$`])', r"\\\1", value)
    return value if quote == '"' else f'"{value}"'


def expand_gate_placeholders(cmd: str, *, task_dir: Path, workspace: Path) -> str:
    """Substitute :data:`PLACEHOLDER_TASK_DIR` / :data:`PLACEHOLDER_WORKSPACE` in *cmd*.

    Substitution happens here — at run time, per trial — and never at parse time,
    so the hashed scenario keeps the portable template.  A command carrying no
    placeholder is returned unchanged, so every pre-existing gate string is
    byte-identical and no committed resume key moves.

    Each value is substituted as one shell word, however the template writes it: a
    placeholder outside quotes gets double quotes of its own, and one inside quotes is
    escaped for them. So ``python ${task_dir}/probe.py`` and
    ``python "${task_dir}/probe.py"`` run the same probe, and a data root or a
    temporary directory whose path holds a space does not split the command.
    """
    values = {
        PLACEHOLDER_TASK_DIR: _as_posix(task_dir),
        PLACEHOLDER_WORKSPACE: _as_posix(workspace),
    }
    if not any(p in cmd for p in values):
        return cmd
    # cmd.exe knows only double quotes; /bin/sh knows single quotes and backslash too.
    quote_chars = '"' if os.name == "nt" else "\"'"
    out: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(cmd):
        placeholder = next((p for p in values if cmd.startswith(p, i)), None)
        if placeholder is not None:
            out.append(_quoted(values[placeholder], quote))
            i += len(placeholder)
            continue
        ch = cmd[i]
        if ch == "\\" and os.name != "nt" and quote != "'" and i + 1 < len(cmd):
            out.append(cmd[i : i + 2])
            i += 2
            continue
        if quote is None and ch in quote_chars:
            quote = ch
        elif ch == quote:
            quote = None
        out.append(ch)
        i += 1
    return "".join(out)


def _tree_entries(root: Path) -> set[str]:
    """Every file and directory under *root*, as relative paths, ``.git`` left out.

    Symbolic links are listed and not followed.
    """
    entries: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda _e: None):
        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            dirnames[:] = [d for d in dirnames if d != ".git"]
            rel = ""
        for name in (*dirnames, *filenames):
            entries.add(os.path.join(rel, name))
    return entries


def _remove_new_entries(root: Path, before: set[str]) -> None:
    """Remove what was created under *root* since *before* was listed. Best effort:
    something that cannot be removed (a file another process still holds) stays."""
    created = _tree_entries(root) - before
    for rel in sorted(created, key=lambda r: r.count(os.sep)):
        if os.path.dirname(rel) in created:
            continue  # removed with the directory that holds it
        target = root / rel
        with contextlib.suppress(OSError):
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink()


class GatedSessionExecutor:
    """One spawn + deterministic gate + bounded fix loop (optional review pass).

    Satisfies :class:`~fathom.strategies.base.StrategyExecutor`. ``task.gate["run"]``
    is the visible gate command; a task that defines no gate degrades to a single
    spawn (such a task should use ``single-session`` instead).
    """

    def __init__(
        self,
        max_fix_attempts: int = 2,
        with_review: bool = False,
        extra_gate_cmds: Sequence[str] = (),
    ) -> None:
        self.max_fix_attempts = max_fix_attempts
        self.with_review = with_review
        # Scenario-level gate augmentation (harness-side oracle strengthening):
        # commands run after the task's own gate, same red/green contract.
        self.extra_gate_cmds = tuple(extra_gate_cmds)

    def run_trial(
        self,
        task: Task,
        workspace: Path,
        scenario: ResolvedScenario,
        runner: Runner,
    ) -> TrialResult:
        max_turns = task.limits.get("max_turns")
        runs: list[RunRecord] = []
        task_dir = Path(task.task_dir)
        gate_cmd = (getattr(task, "gate", None) or {}).get("run", "")
        # Each command twice: expanded, to run, and as written, to show the agent. An
        # expanded `${task_dir}` is a path inside the data root, which the agent under
        # test must not learn; the template names nothing it can reach. Only the arm's
        # extra commands take placeholders; the task's own gate runs as written.
        extra_templates = [c for c in self.extra_gate_cmds if c]
        templates = ([gate_cmd] if gate_cmd else []) + extra_templates
        gate_cmds = ([gate_cmd] if gate_cmd else []) + [
            expand_gate_placeholders(c, task_dir=task_dir, workspace=workspace)
            for c in extra_templates
        ]

        impl = runner.execute(task.instruction, workspace, scenario, max_turns=max_turns)
        runs.append(impl)
        if impl.status is ExitStatus.INFRASTRUCTURE:
            return self._infra(runs)

        notes: list[str] = []
        gate_ok = True
        if gate_cmds:
            extra_from = 1 if gate_cmd else 0
            first_ok: bool | None = None
            first_extra: str | None = None
            extra_out: str | None = None
            rounds = 0
            for attempt in range(self.max_fix_attempts + 1):
                gate_ok, output, extra_out = self._run_gates(
                    gate_cmds, workspace, extra_from=extra_from, shown=templates
                )
                # What a gate prints reaches the agent (the fix prompt) and the ledger
                # (the extra-gate excerpt); a probe run from `${task_dir}` names its
                # own path when it fails.
                output = mask_gate_text(output, task_dir, workspace)
                if extra_out is not None:
                    extra_out = mask_gate_text(extra_out, task_dir, workspace)
                rounds += 1
                if first_ok is None:
                    first_ok, first_extra = gate_ok, extra_out
                if gate_ok or attempt == self.max_fix_attempts:
                    break
                # The command line is masked as the output is: a template may spell a
                # path under the data root out instead of using the placeholder.
                shown_cmd = mask_gate_text(" && ".join(templates), task_dir, workspace)
                fix = runner.execute(
                    _FIX_PROMPT.format(cmd=shown_cmd, output=output[-3000:]),
                    workspace,
                    scenario,
                    max_turns=max_turns,
                )
                runs.append(fix)
                if fix.status is ExitStatus.INFRASTRUCTURE:
                    return self._infra(runs)
            notes.append(
                f"gate first={'green' if first_ok else 'red'} "
                f"final={'green' if gate_ok else 'red'} fixes={len(runs) - 1}"
            )
            if self.extra_gate_cmds:
                notes.append(f"extra-gate first: {_describe_extra(first_extra)}")
                if rounds > 1:
                    notes.append(f"extra-gate final: {_describe_extra(extra_out)}")

        if self.with_review and gate_ok:
            rev = runner.execute(_REVIEW_PROMPT, workspace, scenario, max_turns=max_turns)
            runs.append(rev)
            if rev.status is ExitStatus.INFRASTRUCTURE:
                return self._infra(runs)
            if "REQUEST_CHANGES" in (rev.result_text or "").upper():
                fix = runner.execute(
                    "Apply the changes from the review, then ensure the gate still passes.",
                    workspace,
                    scenario,
                    max_turns=max_turns,
                )
                runs.append(fix)
                if fix.status is ExitStatus.INFRASTRUCTURE:
                    return self._infra(runs)
                notes.append("review=REQUEST_CHANGES")
            else:
                notes.append("review=APPROVE")

        # A gradeable result view always exists (the workspace); the blind verifier
        # scores it regardless of the gate verdict. Trial status reflects whether the
        # primary implementation spawn ran, not the gate outcome (gate-red is a
        # measured result, not a trial error).
        status = (
            TrialStatus.ERRORED
            if impl.status in (ExitStatus.ERROR, ExitStatus.TIMEOUT)
            else TrialStatus.COMPLETED
        )
        return TrialResult(
            status=status,
            runs=runs,
            pin_level=PIN_STRONG,
            wall_clock_s=sum(r.duration_s for r in runs),
            detail="; ".join(notes),
        )

    @classmethod
    def _run_gates(
        cls,
        cmds: Sequence[str],
        workspace: Path,
        *,
        extra_from: int = 0,
        shown: Sequence[str] | None = None,
    ) -> tuple[bool, str, str | None]:
        """Run *cmds* in order; first red short-circuits.

        Returns ``(ok, output, extra_output)``. *output* is ``""`` when every command
        exits 0 and otherwise identifies the failing command (the fix prompt quotes
        it) by its entry in *shown* — the command as written, before placeholders are
        filled in — or by the command itself when *shown* is not given.
        *extra_output* is what the commands from index *extra_from* on — the
        scenario's own gate augmentation — printed, green or red, and is ``None``
        when none of them ran because an earlier command short-circuited the list.
        """
        labels = list(shown) if shown is not None else list(cmds)
        extra: list[str] = []
        ran_extra = False
        for index, cmd in enumerate(cmds):
            ok, output = cls._run_gate(cmd, workspace)
            if index >= extra_from:
                ran_extra = True
                extra.append(output)
            if not ok:
                return (
                    False,
                    f"$ {labels[index]}\n{output}",
                    "\n".join(extra) if ran_extra else None,
                )
        return True, "", "\n".join(extra) if ran_extra else None

    @staticmethod
    def _run_gate(cmd: str, workspace: Path) -> tuple[bool, str]:
        """Run one gate command; return ``(exited_zero, combined output)``.

        ``errors="replace"`` matches the posture already applied to the harness's own
        stdout: a gate is a task-authored command, often an external tool, and what it
        prints is not fathom's to constrain to ASCII. A lost stream is reported as
        :data:`GATE_STREAM_LOST` rather than as an empty string, so "the gate said
        nothing" and "we could not read what the gate said" stay distinguishable in the
        fix prompt and in the trial row's ``detail``.

        The gate runs code the agent wrote, and what it prints goes back to the agent,
        so its environment is the one the agent's own spawn gets, less the config dir
        (:func:`~fathom.adapters.claude_cli.env_for_agent_code`): no ``FATHOM_*``
        variable, which would name the arm and the data root, no inherited
        ``PWD`` / ``OLDPWD``, no value naming the data root (``PATH`` loses only
        its entries there), and none of the billing and API credential variables the
        spawn is denied. Everything else is kept.

        A gate that outlives :data:`_GATE_TIMEOUT_S` is stopped with every process
        under it (:func:`~fathom.adapters.claude_cli.run_shell_bounded`), so a hung
        test neither holds the matrix nor runs on into the next spawn and the verifier.

        The gate runs in the workspace the verifier scores, so whatever it creates
        there is removed once it and its children are gone (``.git`` aside, which the
        result view leaves out): a test runner's cache or compiled bytecode would
        otherwise mark the trial as one a gate ran in. Files that were there before
        stay, as the gate left them.
        """
        before = _tree_entries(workspace)
        try:
            proc = _run_shell(cmd, cwd=workspace, env=env_for_agent_code(), timeout=_GATE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return False, f"gate timed out after {_GATE_TIMEOUT_S}s"
        finally:
            # After the tree is gone: a child still running could write after this.
            _remove_new_entries(workspace, before)
        if proc.stdout is None or proc.stderr is None:
            return proc.returncode == 0, GATE_STREAM_LOST
        return proc.returncode == 0, proc.stdout + proc.stderr

    @staticmethod
    def _infra(runs: list[RunRecord]) -> TrialResult:
        return TrialResult(
            status=TrialStatus.INFRASTRUCTURE,
            runs=runs,
            pin_level=PIN_STRONG,
            wall_clock_s=sum(r.duration_s for r in runs),
            detail="infrastructure",
        )
