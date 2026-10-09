"""Scorecard renderer — reads ledger JSONL and produces report/scorecard-<bank>.md."""

from __future__ import annotations

import json
import math
import os
import pathlib
import re
import warnings
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fathom import replication as _replication
from fathom.calibration import fisher_one_sided, hard_fraction

LEDGER_DIR = pathlib.Path("ledger")
REPORT_DIR = pathlib.Path("report")
TASKS_DIR = pathlib.Path("tasks")
_UNTAGGED = "(untagged)"

_BARE = "bare"
_SERIES_KEY = "series"
# An arm is saturated on a section when it passes at least this share of the section's tasks;
# when every arm is, the pass rate cannot tell the arms apart (see _saturation_banner).
_SATURATION_SHARE = 0.9
_ARM_DELTAS = [
    "human decomposition",
    "per-PR gates",
    "review/fix subagents",
    "engine settings",
]
# Where `fathom run` keeps an arm's agent streams when FATHOM_STREAM_DIR is unset, relative
# to the data root (cli._STREAM_ROOT and cli._default_stream_dir). The adapter names each file
# `<tag>--a<attempt>--<ms>.ndjson`, the tag being `<bank>--<arm>--<task>--r<repeat>` cleaned
# by _safe_file_part's rule (claude_cli._tee_stream).
_STREAM_ROOT = pathlib.Path(".fathom") / "streams"
_STREAM_FILE = re.compile(r"(?P<tag>.+)--a\d+--\d+\.ndjson")
_ALL_DENIED = "all calls denied or absent"
_MCP_CALLS_NOTE = (
    "> Counted from the agent streams `fathom run` kept, for each completed trial of an arm"
    " that mounts a plugin: the `mcp__*` calls to a server the spawn reported that returned"
    " without an error. *no streams kept* means no stream was found for any of the arm's"
    " trials. A count marked *partial* includes a stream with no closing `result` event (the"
    " spawn was cut off), so it is a lower bound. The flag means every trial with a stream"
    " made no such call: the mounted tools were denied or never called, so the arm's results"
    " describe the arm without its treatment. Re-runs of one cell share a stream name, so a"
    " cell run more than once sums the streams of every run."
)
_CONTRAST_ALPHA = 0.05
_CONTRAST_ALL_CRITERIA = "all criteria"
_CONTRASTS_HEADING = "### Contrasts"


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion. (0.0, 1.0) when n == 0."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def is_pass(verifier_results: Any) -> bool:
    """Determine if verifier results represent a pass.

    The pass rule: `None` gives `False`; a dict passes when non-empty and all values
    are truthy; otherwise the value's truthiness is returned. A trial passes when all
    its verifier results (compliance criteria, correctness checks) are truthy.

    Args:
        verifier_results: The `verifier_results` field from a trial record, which may be
            None (no verification run), a dict (one or more criteria: name -> bool), or
            another value type (for forward compatibility).

    Returns:
        bool: `False` if `None`, `False` if dict and empty or any value is falsy,
            `True` if dict and non-empty and all values truthy, otherwise the
            truthiness of the argument.
    """
    if verifier_results is None:
        return False
    if isinstance(verifier_results, dict):
        return bool(verifier_results) and all(bool(v) for v in verifier_results.values())
    return bool(verifier_results)


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _read_raw(bank: str, ledger_dir: pathlib.Path) -> list[dict]:
    path = ledger_dir / f"{bank}.jsonl"
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if stripped:
                try:
                    out.append(json.loads(stripped))
                except Exception as exc:
                    warnings.warn(
                        f"Skipping malformed record at {path}:{lineno}: {exc}",
                        stacklevel=2,
                    )
    return out


def _load_task_meta(bank: str, tasks_dir: pathlib.Path = TASKS_DIR) -> dict[str, dict]:
    """Per-task {score, hard_criteria} from tasks/<bank>/scores.toml + task.toml.

    Returns {} when the bank ships no scores.toml (every non-calibration bank), so the
    calibration section is simply absent and other banks' scorecards are byte-unchanged.

    A bank may also declare ONE positive control in scores.toml's ``[control]`` table
    (``task``, ``weak_arm``, ``strong_arm``, ``alpha``, ``min_repeats``). It is attached
    to that task's meta as ``entry["control"]``, which is what makes calibration.py read
    it by its own rule and keep it out of the confusion matrix.
    """
    import tomllib

    bank_dir = pathlib.Path(tasks_dir) / bank
    scores_path = bank_dir / "scores.toml"
    if not scores_path.is_file():
        return {}
    try:
        with open(scores_path, "rb") as f:
            scores_doc = tomllib.load(f)
        scores = scores_doc.get("scores", {})
        control = scores_doc.get("control") or {}
        # The routing layer: the reduced mechanism's per-task prediction, the task's
        # genre, and the pre-registered analysis parameters. Absent on a bank that
        # declares none, so its scorecard is byte-unchanged.
        reduced = scores_doc.get("reduced") or {}
        genre = scores_doc.get("genre") or {}
        analysis = scores_doc.get("analysis") or {}
        from fathom.taskbank import load_bank

        loaded = load_bank(bank_dir)
    except Exception:
        return {}
    meta: dict[str, dict] = {}
    for t in loaded.tasks:
        hard = t.verify.get("hard_criteria")
        if t.id in scores and isinstance(hard, list) and hard:
            entry: dict[str, Any] = {"score": float(scores[t.id]), "hard_criteria": list(hard)}
            if control.get("task") == t.id:
                entry["control"] = dict(control)
            if t.id in reduced:
                entry["reduced"] = dict(reduced[t.id])
            if t.id in genre:
                entry["genre"] = genre[t.id]
            if analysis:
                entry["analysis"] = dict(analysis)
            # load_bank's Task does not keep [context], so re-parse task.toml directly.
            try:
                with open(t.task_dir / "task.toml", "rb") as tf:
                    ctx = tomllib.load(tf).get("context") or {}
                if ctx.get("size"):
                    entry["context"] = ctx["size"]
                if ctx.get("pair"):
                    entry["pair"] = ctx["pair"]
            except Exception as exc:
                warnings.warn(
                    f"{t.id}: could not re-read task.toml for [context]: {exc}",
                    stacklevel=2,
                )
            meta[t.id] = entry
    return meta


def _load_task_criteria(
    bank: str, tasks_dir: pathlib.Path = TASKS_DIR
) -> dict[str, list[str] | None]:
    """{task_id: its ``[verify] hard_criteria``, or None when it declares none}.

    Read for every bank, with or without scores.toml: the core scorecard's Hard-Criteria
    Fraction counts a task's declared hard criteria, and every criterion of a task that
    declares none. Returns {} when the tasks dir or the bank is absent. A bank that cannot
    be loaded warns and returns {}, so every criterion counts and the table says so.
    """
    bank_dir = pathlib.Path(tasks_dir) / bank
    if not bank_dir.is_dir():
        return {}
    from fathom.taskbank import load_bank

    try:
        loaded = load_bank(bank_dir)
    except Exception as exc:
        warnings.warn(
            f"could not read hard_criteria for bank {bank!r}: {exc}; the Hard-Criteria "
            "Fraction counts every criterion",
            stacklevel=2,
        )
        return {}
    criteria: dict[str, list[str] | None] = {}
    for t in loaded.tasks:
        hard = t.verify.get("hard_criteria")
        criteria[t.id] = [str(c) for c in hard] if isinstance(hard, list) and hard else None
    return criteria


def _load_task_tags(bank: str, tasks_dir: pathlib.Path = TASKS_DIR) -> dict[str, dict[str, str]]:
    """{task_id: its ``[tags]`` table, {} when it declares none} from tasks/<bank>/.

    Returns {} when the tasks dir or the bank is absent, or the bank cannot be loaded (the
    Hard-Criteria Fraction's loader already warns about that), so an unreadable bank renders
    no tag table.
    """
    bank_dir = pathlib.Path(tasks_dir) / bank
    if not bank_dir.is_dir():
        return {}
    from fathom.taskbank import load_bank

    try:
        loaded = load_bank(bank_dir)
    except Exception:
        return {}
    return {t.id: dict(t.tags) for t in loaded.tasks}


@dataclass(frozen=True)
class ContrastPair:
    """One declared comparison: does *treatment* pass more often than *control*?"""

    treatment: str
    control: str
    criterion: str | None = None  # None compares the all-criteria pass


def _load_contrasts(
    bank: str, tasks_dir: pathlib.Path = TASKS_DIR
) -> tuple[float, list[ContrastPair]]:
    """(alpha, pairs) from the optional ``[contrasts]`` table of tasks/<bank>/bank.toml.

    The shape is ``[contrasts]`` with an optional ``alpha`` (default 0.05), and one
    ``[[contrasts.pair]]`` per comparison with ``treatment``, ``control`` and an optional
    ``criterion``. ``load_bank`` reads only the three manifest keys and nothing hashes
    bank.toml, so the declaration changes no trial and no resume key.

    No table, no bank.toml, or a bank.toml that cannot be read gives no pairs (the
    Hard-Criteria Fraction's loader already warns about an unreadable bank). An alpha that is
    not a number between 0 and 1 warns and gives no pairs; a pair without a string
    ``treatment`` and ``control``, or with a ``criterion`` that is not a string, warns and is
    skipped.
    """
    import tomllib

    path = pathlib.Path(tasks_dir) / bank / "bank.toml"
    try:
        with open(path, "rb") as f:
            declared = tomllib.load(f).get("contrasts")
    except (OSError, tomllib.TOMLDecodeError):
        return _CONTRAST_ALPHA, []
    if declared is None:
        return _CONTRAST_ALPHA, []
    if not isinstance(declared, dict):
        warnings.warn(f"{path}: contrasts must be a table; no contrasts rendered", stacklevel=2)
        return _CONTRAST_ALPHA, []
    alpha = declared.get("alpha", _CONTRAST_ALPHA)
    if isinstance(alpha, bool) or not isinstance(alpha, int | float) or not 0 < alpha < 1:
        warnings.warn(
            f"{path}: contrasts alpha must be a number between 0 and 1, got {alpha!r}; "
            "no contrasts rendered",
            stacklevel=2,
        )
        return _CONTRAST_ALPHA, []
    raw_pairs = declared.get("pair", [])
    if not isinstance(raw_pairs, list):
        raw_pairs = [raw_pairs]
    pairs: list[ContrastPair] = []
    for number, raw in enumerate(raw_pairs, 1):
        entry = raw if isinstance(raw, dict) else {}
        problems = [key for key in ("treatment", "control") if not isinstance(entry.get(key), str)]
        criterion = entry.get("criterion")
        if criterion is not None and not isinstance(criterion, str):
            problems.append("criterion")
        if problems:
            warnings.warn(
                f"{path}: contrasts.pair {number} needs a string {' and '.join(problems)}; "
                "the pair is skipped",
                stacklevel=2,
            )
            continue
        pairs.append(ContrastPair(entry["treatment"], entry["control"], criterion))
    return float(alpha), pairs


def _holm(p_values: Sequence[float], alpha: float) -> list[tuple[float, bool]]:
    """Holm's step-down over one family: (threshold, below) for each p, in the input order.

    In ascending p order (ties keep the input order) the i-th p, counting from 0, has the
    threshold alpha / (m - i). A p is below when it is at or under its threshold and every
    p before it in that order is too: the first miss stops the step-down.
    """
    m = len(p_values)
    out: list[tuple[float, bool]] = [(alpha, False)] * m
    below = True
    for rank, i in enumerate(sorted(range(m), key=lambda j: p_values[j])):
        threshold = alpha / (m - rank)
        below = below and p_values[i] <= threshold
        out[i] = (threshold, below)
    return out


def _fmt_p(p: float) -> str:
    return "<0.0001" if p < 0.0001 else f"{p:.4f}"


# --- Spread and health: qualify the point estimates the ledger already lets us qualify ---


def _spread(values: Sequence[float]) -> tuple[float, float, float]:
    """(min, median, max) of *values*; (0, 0, 0) when empty.

    Reported beside every mean because at small n the mean alone can reverse the
    direction of a verdict, or move the Pareto star when one more repeat lands. A
    bimodal arm and a single blow-up run are invisible in a mean and obvious in a
    range.
    """
    if not values:
        return (0.0, 0.0, 0.0)
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    median = ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return (ordered[0], median, ordered[-1])


def _fmt_spread(values: Sequence[float], *, precision: int = 0) -> str:
    lo, med, hi = _spread(values)
    return f"{lo:.{precision}f}/{med:.{precision}f}/{hi:.{precision}f}"


def _load_turn_caps(bank: str, tasks_dir: pathlib.Path) -> dict[str, int]:
    """{task_id: max_turns} from tasks/<bank>/*/task.toml.

    An arm whose trials sit AT the cap has a pass rate that is a lower bound, not
    a score — and an arm's mean turns can exceed its task's max_turns with nothing on
    the page marking it unless the cap is read here.
    """
    import tomllib

    caps: dict[str, int] = {}
    bank_dir = pathlib.Path(tasks_dir) / bank
    if not bank_dir.is_dir():
        return caps
    for task_toml in sorted(bank_dir.glob("*/task.toml")):
        try:
            with open(task_toml, "rb") as f:
                data = tomllib.load(f)
            cap = (data.get("limits") or {}).get("max_turns")
            if data.get("id") and cap:
                caps[str(data["id"])] = int(cap)
        except Exception as exc:
            warnings.warn(f"Skipping unreadable {task_toml}: {exc}", stacklevel=2)
            continue
    return caps


def _ranges_overlap(a: Sequence[float], b: Sequence[float]) -> bool:
    """True when the observed [min, max] ranges of *a* and *b* intersect."""
    if not a or not b:
        return True
    return min(a) <= max(b) and min(b) <= max(a)


def _scope_to_current_dataset_version(
    bank: str, raw: list[dict], dataset_version: str | None = None
) -> list[dict]:
    """Keep only records at the CURRENT dataset_version — the last-appended trial's.

    The ledger is append-only, so the most-recently-run trials are last in the file;
    their dataset_version is the bank's current version. A ``dataset_version`` bump
    (bumped on any task/fixture/verifier change — it is in the resume key) otherwise
    lets an older task version's trials silently co-render with the new one: the
    scorecard keys trials by (scenario, task, repeat) with no dataset_version, so
    last-write-wins keeps the newest per cell but any cell the current version has
    not re-run yet still shows the *old* version's result — a silent conflation of
    two task definitions under one arm.

    Scoping to the current version keeps the scorecard a coherent current-state view
    (matching the resume key, which includes dataset_version). Older-version trials
    remain in the committed ledger untouched (append-only); they are excluded from
    this render and the exclusion is surfaced, never silent. A single-version bank is
    unaffected — nothing is excluded and the output is byte-identical.

    *dataset_version* names another version to keep instead of the current one, for a
    historical view: its rows are kept, and the warning names the versions left out. A
    version no trial carries raises ``ValueError`` naming the versions the ledger holds.
    ``None`` keeps the current version, as before.
    """
    # Voided trials (and their runs) are excluded as of the void row: the re-run counts.
    from fathom.ledger import apply_voids as _apply_voids

    raw = _apply_voids(raw)
    trial_dvs = [r.get("dataset_version") for r in raw if r.get("kind") == "trial"]
    trial_dvs = [dv for dv in trial_dvs if dv is not None]
    if not trial_dvs:
        return raw
    current_dv = trial_dvs[-1]
    distinct = sorted(set(trial_dvs))
    if dataset_version is not None and dataset_version != current_dv:
        if dataset_version not in distinct:
            raise ValueError(
                f"ledger for {bank!r} holds no trials at dataset_version "
                f"{dataset_version!r}; it holds {distinct}"
            )
        excluded_dvs = [dv for dv in distinct if dv != dataset_version]
        warnings.warn(
            f"ledger for {bank!r} holds {len(distinct)} dataset_versions {distinct}; the "
            f"scorecard reflects dataset_version {dataset_version!r} only, not the "
            f"current {current_dv!r} ({excluded_dvs} excluded — they stay in the "
            "committed ledger).",
            stacklevel=2,
        )
        return [r for r in raw if r.get("dataset_version", dataset_version) == dataset_version]
    if len(distinct) == 1:
        return raw
    excluded = sum(1 for dv in trial_dvs if dv != current_dv)
    warnings.warn(
        f"ledger for {bank!r} holds {len(distinct)} dataset_versions {distinct}; the "
        f"scorecard reflects the current dataset_version {current_dv!r} only "
        f"({excluded} older-dataset_version trial(s) excluded — the older versions "
        "stay in the committed ledger). Re-run the current version to full N.",
        stacklevel=2,
    )
    # Records without a dataset_version (none in practice) are kept, not dropped.
    return [r for r in raw if r.get("dataset_version", current_dv) == current_dv]


def _safe_file_part(text: str) -> str:
    """*text* as a file-name part, by the rule the adapter applies to a stream tag: letters,
    digits and ``-_.`` are kept, anything else becomes ``_``."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in text)


def default_streams_dir(bank: str) -> pathlib.Path:
    """Where `fathom run` kept *bank*'s agent streams: ``FATHOM_STREAM_DIR`` when set, else
    ``.fathom/streams/<bank>`` under the working directory, which is the data root while a
    command runs."""
    explicit = os.environ.get("FATHOM_STREAM_DIR")
    return pathlib.Path(explicit) if explicit else pathlib.Path.cwd() / _STREAM_ROOT / bank


def _mounts_a_plugin(trial: dict) -> bool | None:
    """Whether a trial row's arm mounts a plugin: its ``config_preimage`` has a ``plugins``
    key. None for a row with no readable preimage (rows written before it was recorded)."""
    try:
        preimage = json.loads(trial.get("config_preimage") or "")
    except ValueError:
        return None
    return isinstance(preimage, dict) and "plugins" in preimage


def _kept_streams(streams_dir: pathlib.Path) -> dict[str, list[pathlib.Path]]:
    """The stream files in *streams_dir*, grouped by the trial tag they are named after."""
    by_tag: defaultdict[str, list[pathlib.Path]] = defaultdict(list)
    if streams_dir.is_dir():
        for path in sorted(streams_dir.glob("*.ndjson")):
            match = _STREAM_FILE.fullmatch(path.name)
            if match:
                by_tag[match["tag"]].append(path)
    return by_tag


def _served_mcp_calls(paths: Sequence[pathlib.Path]) -> tuple[int, bool]:
    """(the successful ``mcp__*`` calls to a server the spawn reported, summed over *paths*;
    whether any of them lacks its closing ``result`` event, so the sum is partial)."""
    from fathom import streams
    from fathom.arming import tools_served_by

    calls = 0
    partial = False
    for path in paths:
        try:
            events = streams.read_stream_file(path)
        except OSError:
            events = []
        partial = partial or not streams.stream_completed(events)
        served = streams.init_mcp_servers(events)
        calls += len(tools_served_by(served, streams.successful_mcp_calls(events)))
    return calls, partial


def _historical_note(raw: list[dict], scoped: list[dict], dataset_version: str | None) -> str:
    """The note that opens a historical view, or "" when the view is the current one.

    *raw* is the ledger as read; the current version is the last-appended trial's of
    the unscoped, void-applied rows, which is what the default render would show.
    """
    if dataset_version is None:
        return ""
    from fathom.ledger import apply_voids as _apply_voids

    dvs = [r.get("dataset_version") for r in _apply_voids(raw) if r.get("kind") == "trial"]
    dvs = [dv for dv in dvs if dv is not None]
    if not dvs or dvs[-1] == dataset_version:
        return ""
    return (
        f"> Historical view: dataset_version `{dataset_version}`, not the current one "
        f"(`{dvs[-1]}`). Task metadata (calibration, turn caps, hard criteria) comes from "
        "the current tasks/ tree, not from this version."
    )


def _replication_line(bank: str, tasks_dir: pathlib.Path, scoped: list[dict]) -> str:
    """The line under the title: the bank's ``[plan] repeats_per_cell`` against the cells.

    The plan is read from the current ``tasks/<bank>/bank.toml`` (there is no other copy of
    it); a malformed plan warns and reads as undeclared, so the scorecard still renders. The
    cells are this view's (arm, task) cells, attributed as the rest of the scorecard is,
    counting completed trials (:func:`fathom.replication.cell_counts`).
    """
    reading = _replication.read_plan(pathlib.Path(tasks_dir) / bank)
    if reading.problem is not None:
        warnings.warn(
            f"bank {bank!r}: {reading.path.name} has a malformed [plan] ({reading.problem}); "
            "the scorecard reads it as undeclared",
            stacklevel=3,
        )
    counts = _replication.cell_counts(scoped)
    return _replication.scorecard_line(reading, counts, f"tasks/{bank}")


def calibration_heading(*, is_context: bool) -> str:
    """The calibration section's heading. Pinned: a scorecard renders the same across releases."""
    return "## Context-Size Calibration" if is_context else "## Model-Tier Calibration"


def substrate_display_path(path: pathlib.Path, *, root: pathlib.Path) -> str:
    """*path* as the scorecard shows it: relative to the data root when it lies inside it.

    A scorecard is quoted in reports and committed, so it must not carry the absolute
    location of the data root.
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def render(
    bank: str,
    *,
    ledger_dir: pathlib.Path = LEDGER_DIR,
    report_dir: pathlib.Path = REPORT_DIR,
    tasks_dir: pathlib.Path = TASKS_DIR,
    dataset_version: str | None = None,
    streams_dir: pathlib.Path | None = None,
) -> pathlib.Path:
    """Read ledger/<bank>.jsonl and write report/scorecard-<bank>.md.

    With *dataset_version* naming a version other than the current one, the scorecard
    is that version's view and goes to ``scorecard-<bank>--<version>.md``, so it never
    overwrites the current scorecard. Its first line says so.

    *streams_dir* is where the run kept the agent streams (:func:`default_streams_dir` when
    None). It is read only when an arm mounts a plugin, for the MCP-call table.
    """
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", bank):
        raise ValueError(f"Invalid bank name: {bank!r}")
    raw = _read_raw(bank, ledger_dir)
    scoped = _scope_to_current_dataset_version(bank, raw, dataset_version)
    historical_note = _historical_note(raw, scoped, dataset_version)
    raw = scoped
    turn_caps = _load_turn_caps(bank, tasks_dir)
    task_criteria = _load_task_criteria(bank, tasks_dir)
    task_tags = _load_task_tags(bank, tasks_dir)
    contrast_alpha, contrast_pairs = _load_contrasts(bank, tasks_dir)

    trials: dict[tuple, dict] = {}
    runs: defaultdict[tuple, list[dict]] = defaultdict(list)
    gradings: list[dict] = []
    ch_to_sc: dict[str, str] = {}
    task_holdout: dict[str, bool] = {}

    # Pass 1 — build the COMPLETE config_hash -> scenario-name map from every trial
    # before attributing any run. cli.py (run_matrix) appends a trial's run records
    # BEFORE its trial record, and a ledger RunRecord carries no `scenario` field, so
    # resolving a run's arm against a map built incrementally in a single pass silently
    # orphaned every arm's first trial's runs under the raw config_hash — they never
    # joined Economy/Efficiency, and a real share of the tokens went missing. Two passes
    # make attribution independent of record order.
    for rec in raw:
        if rec.get("kind") == "trial":
            ch = rec.get("config_hash", "")
            ch_to_sc[ch] = rec.get("scenario") or ch

    # Pass 2 — attribute trials and runs against the complete map.
    seen_completed: set[tuple] = set()
    dangling_warned: set[str] = set()
    for rec in raw:
        kind = rec.get("kind")
        if kind == "trial":
            ch = rec.get("config_hash", "")
            sc = ch_to_sc.get(ch, ch)
            tid = rec.get("task_id", "")
            rep = rec.get("repeat", 0)
            task_holdout[tid] = bool(rec.get("holdout", False))
            # A resume never re-runs a COMPLETED cell, so two completed lines for one
            # (dataset_version, config_hash, task, repeat) mean the same scored cell was
            # recorded twice; its runs would then be summed twice in Economy. The renderer
            # cannot un-sum runs it cannot attribute to a specific attempt (a ledger run
            # carries no trial id), so it warns rather than double-count silently; the
            # remedy is to archive the invalid ledger and re-run fresh.
            if rec.get("status") == "completed":
                ckey = (rec.get("dataset_version"), ch, tid, rep)
                if ckey in seen_completed:
                    warnings.warn(
                        f"duplicate completed trial for {sc}/{tid} repeat={rep} "
                        f"(config_hash={ch[:12]}…): Economy/Efficiency may double-count; "
                        "inspect the ledger and archive+re-run if it is a stale re-run",
                        stacklevel=2,
                    )
                seen_completed.add(ckey)
            trials[(sc, tid, rep)] = rec
        elif kind == "run":
            ch = rec.get("config_hash", "")
            # A run whose config_hash appears in NO trial line (e.g. a crash between the
            # run-append loop and the trial-append in cli.run_matrix) resolves to the raw
            # hash, which is never in all_sc, so its economy would be dropped from the
            # scorecard with no trace. Warn once per dangling hash — silent-wrong -> visible.
            if ch not in ch_to_sc and ch not in dangling_warned:
                dangling_warned.add(ch)
                warnings.warn(
                    f"run record with config_hash={ch[:12]}… has no trial line; its economy "
                    "is excluded from the scorecard (likely a trial interrupted mid-write)",
                    stacklevel=2,
                )
            sc = ch_to_sc.get(ch, ch)
            tid = rec.get("task_id", "")
            rep = rec.get("repeat", 0)
            runs[(sc, tid, rep)].append(rec)
        elif kind == "grading":
            gradings.append(rec)

    all_sc = sorted({sc for sc, _, _ in trials})
    dev_tasks = sorted({tid for (_, tid, _) in trials if not task_holdout.get(tid, False)})
    holdout_tasks = sorted({tid for (_, tid, _) in trials if task_holdout.get(tid, False)})

    # first-write-wins: avoids silently dropping grading records when a scenario is
    # re-run with a new config hash (last-write-wins would change bare_ch and miss
    # grading records keyed to the earlier hash)
    sc_to_ch: dict[str, str] = {}
    for ch, sc in ch_to_sc.items():
        sc_to_ch.setdefault(sc, ch)
    bare_ch = sc_to_ch.get(_BARE)

    reps_for: defaultdict[tuple, list[int]] = defaultdict(list)
    for sc, tid, rep in trials:
        reps_for[(sc, tid)].append(rep)
    for k in reps_for:
        reps_for[k].sort()

    lines: list[str] = [f"# Scorecard — {bank}", "", _replication_line(bank, tasks_dir, raw), ""]
    if historical_note:
        lines = [historical_note, "", *lines]

    # The kept stream files, listed on first use: only an arm that mounts a plugin reads them.
    kept: dict[str, list[pathlib.Path]] | None = None

    def _mcp_calls_table(task_list: list[str]) -> list[str]:
        # One row per arm that mounts a plugin: how many of its completed trials have a kept
        # stream, and the served MCP calls per such trial. Empty when no arm mounts one.
        nonlocal kept
        rows: list[str] = []
        legacy: list[str] = []
        for sc in all_sc:
            trials_n = partial = 0
            counts: list[float] = []
            for tid in task_list:
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    mounts = _mounts_a_plugin(t)
                    if mounts is None and sc not in legacy:
                        legacy.append(sc)
                    if not mounts:
                        continue
                    trials_n += 1
                    if kept is None:
                        kept = _kept_streams(streams_dir or default_streams_dir(bank))
                    paths = kept.get(_safe_file_part(f"{bank}--{sc}--{tid}--r{rep}"), [])
                    if paths:
                        calls, cut = _served_mcp_calls(paths)
                        counts.append(calls)
                        partial += cut
            if not trials_n:
                continue
            if counts:
                cell = _fmt_spread(counts) + (f" ({partial} partial)" if partial else "")
            else:
                cell = "no streams kept"
            flag = _ALL_DENIED if counts and not any(counts) else ""
            rows.append(f"| {sc} | {len(counts)}/{trials_n} | {cell} | {flag} |")
        if not rows:
            return []
        out = [
            "### Arm Health: MCP calls",
            "",
            "| Scenario | Trials with streams | MCP calls per trial (min/med/max) | Flag |",
            "|---|---|---|---|",
            *rows,
            "",
            _MCP_CALLS_NOTE,
            "",
        ]
        if legacy:
            left_out = (
                f"> Left out: the trials of {', '.join(legacy)}: their rows carry no"
                " `config_preimage` (written before fathom recorded it), so the ledger does"
                " not say whether the arm mounts a plugin."
            )
            out += [left_out, ""]
        return out

    def _stats(sc: str, task_list: list[str]) -> tuple[int, int, int, int]:
        # Returns (passes, n, infra, k) where k = distinct tasks contributing a
        # completed trial — the CLUSTER count. n pools every task×repeat cell, but
        # repeats within a task and different tasks are correlated, so k lets the
        # reader see the design effect the pooled Wilson CI ignores (ADR-0007 D3
        # precedent).
        passes = n = infra = 0
        completed_tasks: set[str] = set()
        for tid in task_list:
            for rep in reps_for.get((sc, tid), []):
                t = trials.get((sc, tid, rep))
                if t is None:
                    continue
                if t.get("infra_error"):
                    infra += 1
                elif t.get("status") == "completed":
                    n += 1
                    completed_tasks.add(tid)
                    if is_pass(t.get("verifier_results")):
                        passes += 1
        return passes, n, infra, len(completed_tasks)

    def _criterion_counts(sc: str, task_list: list[str], criterion: str | None) -> tuple[int, int]:
        # (passes, completed trials) on *criterion*, counted as in Per-Criterion Pass Rates:
        # the completed trials whose verifier returned it. None counts the all-criteria pass.
        if criterion is None:
            passes, n, _infra, _k = _stats(sc, task_list)
            return passes, n
        passes = n = 0
        for tid in task_list:
            for rep in reps_for.get((sc, tid), []):
                t = trials.get((sc, tid, rep))
                if t is None or t.get("infra_error") or t.get("status") != "completed":
                    continue
                vr = t.get("verifier_results")
                if isinstance(vr, dict) and criterion in vr:
                    n += 1
                    passes += bool(vr[criterion])
        return passes, n

    def _contrasts_block(task_list: list[str]) -> list[str]:
        # One row per declared pair whose arms the ledger holds: both arms' counts with a
        # Wilson interval, a one-sided Fisher p for "treatment passes more often", and Holm's
        # step-down over the pairs of this section that have a p. A pair naming an arm the
        # ledger does not hold gets a note line instead. Empty when the bank declares none.
        if not contrast_pairs:
            return []

        def _arm_cell(passes: int, n: int) -> str:
            if not n:
                return "0/0"
            lo, hi = wilson_interval(passes, n)
            return f"{passes}/{n} ({_pct(passes / n)}) [{_pct(lo)}, {_pct(hi)}]"

        tested: list[tuple[float, str]] = []  # (p, the row's cells up to the p)
        untested: list[str] = []
        notes: list[str] = []
        for pair in contrast_pairs:
            missing = [arm for arm in (pair.treatment, pair.control) if arm not in all_sc]
            if missing:
                notes.append(
                    f"> Not compared: {pair.treatment} vs {pair.control}. The ledger has no arm"
                    f" named {' or '.join(dict.fromkeys(missing))}."
                )
                continue
            tp, tn = _criterion_counts(pair.treatment, task_list, pair.criterion)
            cp, cn = _criterion_counts(pair.control, task_list, pair.criterion)
            cells = (
                f"| {pair.treatment} vs {pair.control}"
                f" | {pair.criterion or _CONTRAST_ALL_CRITERIA}"
                f" | {_arm_cell(tp, tn)} | {_arm_cell(cp, cn)} |"
            )
            if tn and cn:
                tested.append((fisher_one_sided(cp, cn, tp, tn), cells))
            else:
                untested.append(cells)
        holm = _holm([p for p, _ in tested], contrast_alpha)
        out = [_CONTRASTS_HEADING, ""]
        if tested or untested:
            out += [
                (
                    "| Treatment vs control | Criterion | Treatment | Control"
                    " | Fisher p (one-sided) | Holm threshold | Below threshold |"
                ),
                "|---|---|---|---|---|---|---|",
            ]
            # In p order, so the step-down reads top to bottom; sorted() keeps ties in
            # declaration order, as _holm does.
            for (p, cells), (threshold, below) in sorted(
                zip(tested, holm, strict=True), key=lambda item: item[0][0]
            ):
                out.append(f"{cells} {_fmt_p(p)} | {threshold:.4f} | {'yes' if below else 'no'} |")
            out += [f"{cells} N/A | — | — |" for cells in untested]
            out.append("")
        for note in notes:
            out += [note, ""]
        if tested or untested:
            out += [
                (
                    "> Pairs declared in the bank's `bank.toml` under `[contrasts]`. Each arm"
                    " cell is passes/completed trials, the rate and its Wilson 95% interval;"
                    " infra and errored trials are left out, and on a named criterion only the"
                    " trials whose verifier returned it count. The p is a one-sided Fisher exact"
                    " test of the treatment passing more often than the control. Holm's"
                    " step-down runs over this section's pairs that have a p, at α ="
                    f" {contrast_alpha:g}: in p order the thresholds are α/m, α/(m-1), … α, and"
                    " a pair is below threshold when its p and every smaller p are at or under"
                    " theirs. A pair with an arm that has no completed trial here has no p."
                    " Trials pool tasks and repeats, which are correlated, and N per cell is"
                    " small, so read a contrast as directional."
                ),
                "",
            ]
        return out

    def _saturation_banner(task_list: list[str]) -> str | None:
        # An arm passes a task when at least half of its completed trials on that task pass.
        # When two or more arms have completed trials and every one of them passes at least
        # K = ceil(_SATURATION_SHARE x N) of the section's N tasks, the pass rate cannot
        # separate them, so the banner points at the economy axis instead.
        n_tasks = len(task_list)
        k_needed = math.ceil(round(_SATURATION_SHARE * n_tasks, 9))
        arms = 0
        saturated = True
        for sc in all_sc:
            completed = passed = 0
            for tid in task_list:
                wins = n = 0
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    n += 1
                    wins += is_pass(t.get("verifier_results"))
                completed += n
                passed += n > 0 and 2 * wins >= n
            if completed == 0:
                continue
            arms += 1
            saturated = saturated and passed >= k_needed
        if arms < 2 or not saturated:
            return None
        return (
            f"> **Saturated:** every arm passes at least {k_needed} of {n_tasks} tasks, so the "
            "pass rate cannot separate the arms here; compare them on Economy and Efficiency, "
            "or make the bank harder."
        )

    def _section(title: str, task_list: list[str]) -> None:
        if not task_list:
            return
        lines.append(f"## {title}")
        lines.append("")

        lines.append("### Pass Rates")
        lines.append("")
        lines.append("| Scenario | Pass | N | Pass Rate | Wilson 95% CI | Infra Errors |")
        lines.append("|---|---|---|---|---|---|")
        for sc in all_sc:
            passes, n, infra, _k = _stats(sc, task_list)
            if n == 0 and infra == 0:
                continue
            if n > 0:
                lo, hi = wilson_interval(passes, n)
                rate = _pct(passes / n)
                ci = f"[{_pct(lo)}, {_pct(hi)}]"
            else:
                rate = ci = "N/A"
            lines.append(f"| {sc} | {passes} | {n} | {rate} | {ci} | {infra} |")
        lines.append("")
        saturated = _saturation_banner(task_list)
        if saturated:
            lines.append(saturated)
            lines.append("")
        # CI-honesty caveat (ADR-0007 D3 precedent): N pools
        # every task×repeat cell, and repeats within a task and the different tasks
        # are correlated, so the Wilson interval is a heuristic width — an
        # under-estimate of true uncertainty, not exact 95% coverage. Each verdict
        # line prints K (distinct tasks) so the reader can see the clustering.
        lines.append(
            "> **CI caveat:** N pools every task×repeat cell; repeats within a task and "
            "the different (heterogeneous) tasks are correlated repeats, so the Wilson "
            "95% CI is a **heuristic width** (an under-estimate of true uncertainty), not "
            "exact 95% coverage — cf. ADR-0007 D3. Each verdict shows K = distinct tasks."
        )
        lines.append("")

        lines.append("### Verdicts")
        lines.append("")
        for sc in all_sc:
            passes, n, infra, k = _stats(sc, task_list)
            if n == 0 and infra == 0:
                continue
            if n > 0:
                lo, hi = wilson_interval(passes, n)
                rate = _pct(passes / n)
                ci = f"[{_pct(lo)}, {_pct(hi)}]"
                v = (
                    f"- **{sc}** — {passes}/{n} ({rate}), "
                    f"Wilson 95% CI {ci}, n={n} across K={k} task(s) — directional, not final"
                )
            else:
                # n=0 with infra>0: no scored trials — avoid misleading "0/0" fraction
                v = (
                    f"- **{sc}** — no scored trials, Wilson 95% CI N/A, n=0 — "
                    "directional, not final"
                )
            if infra:
                v += f"; {infra} infra error(s) excluded"
            if _SERIES_KEY in sc:
                v += f"; arm deltas vs bare: {', '.join(_ARM_DELTAS)}"
            lines.append(v)
        lines.append("")

        # Per-tag pass rates: one table per tag key the bank declares on this section's
        # tasks, one row per tag value (tasks without the key group as "(untagged)"), one
        # column per arm. Counts are the Pass Rates table's, restricted to those tasks. A
        # bank that declares no tags renders none of this.
        tag_keys = sorted({k for tid in task_list for k in task_tags.get(tid, {})})
        tag_arms = [sc for sc in all_sc if _stats(sc, task_list)[1] or _stats(sc, task_list)[2]]
        for key in tag_keys:
            groups: dict[str, list[str]] = {}
            for tid in task_list:
                groups.setdefault(task_tags.get(tid, {}).get(key, _UNTAGGED), []).append(tid)
            ordered = sorted(v for v in groups if v != _UNTAGGED)
            if _UNTAGGED in groups:
                ordered.append(_UNTAGGED)
            lines.append(f"### By tag: {key}")
            lines.append("")
            lines.append(f"| {key} | " + " | ".join(tag_arms) + " |")
            lines.append("|---|" + "|".join(["---"] * len(tag_arms)) + "|")
            for value in ordered:
                cells = []
                for sc in tag_arms:
                    passes, n, _infra, _k = _stats(sc, groups[value])
                    cells.append(f"{passes}/{n} ({_pct(passes / n)})" if n else "—")
                lines.append(f"| {value} | " + " | ".join(cells) + " |")
            lines.append("")

        # Per-criterion pass rates: separate compliance criteria from correctness
        # (the blended all-truthy pass-rate cannot show which criteria a scenario moved).
        crit_counts: dict[str, dict[str, list[int]]] = {}
        all_crits: set[str] = set()
        for sc in all_sc:
            for tid in task_list:
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    vr = t.get("verifier_results")
                    if not isinstance(vr, dict):
                        continue
                    for crit, val in vr.items():
                        all_crits.add(crit)
                        pc = crit_counts.setdefault(crit, {}).setdefault(sc, [0, 0])
                        pc[1] += 1
                        if val:
                            pc[0] += 1
        crit_scs = [sc for sc in all_sc if any(sc in crit_counts.get(c, {}) for c in all_crits)]
        if all_crits and crit_scs:
            lines.append("### Per-Criterion Pass Rates")
            lines.append("")
            lines.append("| Criterion | " + " | ".join(crit_scs) + " |")
            lines.append("|---|" + "|".join(["---"] * len(crit_scs)) + "|")
            for crit in sorted(all_crits):
                cells = []
                for sc in crit_scs:
                    pc = crit_counts.get(crit, {}).get(sc)
                    cells.append(
                        f"{_pct(pc[0] / pc[1])} ({pc[0]}/{pc[1]})" if pc and pc[1] else "—"
                    )
                lines.append(f"| {crit} | " + " | ".join(cells) + " |")
            lines.append("")

        # Hard-criteria fraction: partial credit per arm, for every bank. The pass rate
        # counts a trial only when every criterion is true, so two arms can tie there
        # while one meets more criteria than the other; this pools true over present
        # criteria across the arm's completed trials. A task that declares
        # [verify] hard_criteria counts those; any other task counts every criterion
        # its verifier returned. No interval: criteria within a trial are correlated
        # (ADR-0009), so pooled criteria are not independent draws.
        frac_rows: list[str] = []
        for sc in all_sc:
            true_n = present_n = 0
            declared: set[bool] = set()
            for tid in task_list:
                hard = task_criteria.get(tid)
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    vr = t.get("verifier_results")
                    returned = list(vr) if isinstance(vr, dict) else []
                    s, p = hard_fraction(vr, returned if hard is None else hard)
                    true_n += s
                    present_n += p
                    declared.add(hard is not None)
            if not declared:
                continue
            if len(declared) > 1:
                used = "mixed"
            elif True in declared:
                used = "hard_criteria"
            else:
                used = "all criteria (no hard_criteria declared)"
            frac = _pct(true_n / present_n) if present_n else "N/A"
            frac_rows.append(f"| {sc} | {true_n}/{present_n} | {frac} | {used} |")
        if frac_rows:
            lines.append("### Hard-Criteria Fraction")
            lines.append("")
            lines.append("| Scenario | True / Present | Fraction | Criteria used |")
            lines.append("|---|---|---|---|")
            lines.extend(frac_rows)
            lines.append("")
            lines.append(
                "> **Partial credit.** Criteria true over criteria present, summed over the"
                " arm's completed trials; infra and errored trials are left out. A task that"
                " declares `[verify] hard_criteria` counts only those, and any other task"
                " counts every criterion its verifier returned. Two arms with the same pass"
                " rate can differ here. It is a point estimate with no interval: criteria"
                " within one trial tend to pass or fail together (ADR-0009)."
            )
            lines.append("")

        lines.extend(_contrasts_block(task_list))

        if bare_ch:
            pw_rows: list[tuple] = []
            for sc in all_sc:
                if sc == _BARE:
                    continue
                tested_ch = sc_to_ch.get(sc)
                if not tested_ch:
                    continue
                w = t_count = loss = 0
                for g in gradings:
                    if (
                        g.get("config_hash_a") == bare_ch
                        and g.get("config_hash_b") == tested_ch
                        and g.get("task_id") in task_list
                    ):
                        verdict = g.get("verdict", "tie")
                        if verdict == "b":
                            w += 1
                        elif verdict == "a":
                            loss += 1
                        else:
                            t_count += 1
                if w + t_count + loss > 0:
                    pw_rows.append((sc, w, t_count, loss, w + t_count + loss))
            if pw_rows:
                lines.append("### Pairwise vs Bare Anchor")
                lines.append("")
                lines.append("| Scenario | Win | Tie | Loss | N Pairs |")
                lines.append("|---|---|---|---|---|")
                for sc, w, t_count, loss, tot in pw_rows:
                    lines.append(f"| {sc} | {w} | {t_count} | {loss} | {tot} |")
                lines.append("")

        # Collect economy rows before emitting the header so we only emit the header
        # when there is at least one data row (avoids an orphaned header when all
        # trials in the section are infra-errored).
        economy_rows: list[str] = []
        # Per-trial values, kept rather than only summed: the spread beside each
        # mean is what lets a reader see whether two arms are separated at this N.
        per_trial_tokens: dict[str, list[float]] = {}
        per_trial_turns: dict[str, list[float]] = {}
        turn_cap_hits: dict[str, tuple[int, int]] = {}
        for sc in all_sc:
            tokens = turns = 0
            wall = usd = 0.0
            sc_counts: list[int] = []
            tok_list: list[float] = []
            turn_list: list[float] = []
            capped = 0
            for tid in task_list:
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    trial_runs = runs.get((sc, tid, rep), [])
                    # Only count trials that have run records in the sessions-per-trial
                    # average; a completed trial with no runs represents missing data,
                    # not a zero-session trial.
                    if trial_runs:
                        sc_counts.append(len(trial_runs))
                    trial_tokens = 0
                    trial_turns = 0
                    for run in trial_runs:
                        u = run.get("usage") or {}
                        trial_tokens += u.get("input_tokens", 0) + u.get("output_tokens", 0)
                        trial_turns += run.get("turns", 0)
                        wall += run.get("duration", 0.0)
                        # Cost lives on the run record's top-level
                        # cost_usd_est (the adapter figure persisted by cli.py),
                        # NOT usage['cost_usd'] — the CLI never emits that key.
                        # Legacy lines without the field default to 0.0.
                        usd += run.get("cost_usd_est", 0.0)
                    tokens += trial_tokens
                    turns += trial_turns
                    if trial_runs:
                        tok_list.append(trial_tokens)
                        turn_list.append(trial_turns)
                        cap = turn_caps.get(tid)
                        if cap and trial_turns >= cap:
                            capped += 1
            if not sc_counts:
                continue
            per_trial_tokens[sc] = tok_list
            per_trial_turns[sc] = turn_list
            turn_cap_hits[sc] = (capped, len(tok_list))
            spt = sum(sc_counts) / len(sc_counts)
            economy_rows.append(
                f"| {sc} | {len(tok_list)} | {tokens} | {_fmt_spread(tok_list)} | {turns}"
                f" | {_fmt_spread(turn_list)} | {wall:.1f} | {spt:.2f} | {usd:.4f} |"
            )
        if economy_rows:
            lines.append("### Economy")
            lines.append("")
            lines.append(
                "| Scenario | N | Tokens | Tokens (min/med/max) | Turns"
                " | Turns (min/med/max) | Wall-clock (s) | Sessions/Trial | Est. USD |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---|")
            lines.extend(economy_rows)
            lines.append("")
            lines.append(
                "> **Read the spread, not the mean.** Totals and means pool every"
                " task x repeat cell; a single blow-up trial or a bimodal arm moves a"
                " mean without moving the median. Where min/med/max ranges overlap"
                " between arms, the arms are not separated at this N."
            )
            lines.append("")

            # --- Arm Health: what makes a pass rate a lower bound ------
            health_rows = [
                f"| {sc} | {n} | {hit}/{n} |" for sc, (hit, n) in turn_cap_hits.items() if hit
            ]
            if health_rows:
                lines.append("### Arm Health")
                lines.append("")
                lines.append("| Scenario | N | Trials at/over max_turns |")
                lines.append("|---|---|---|")
                lines.extend(health_rows)
                lines.append("")
                lines.append(
                    "> An arm whose trials sit AT the turn cap was truncated, not"
                    " finished: its pass rate is a **lower bound**, not a score. Raise"
                    " `[limits] max_turns` and re-run before comparing it with an arm"
                    " that had room to work."
                )
                lines.append("")

        lines.extend(_mcp_calls_table(task_list))

        # --- Efficiency view (§9): per-trial means + quality-per-100k + Pareto flag ---
        eff_data: dict[str, dict] = {}
        for sc in all_sc:
            in_tok = out_tok = cache_tok = 0
            turns_sum = 0
            wall_sum = 0.0
            n_trials = 0
            passes_count = 0
            for tid in task_list:
                for rep in reps_for.get((sc, tid), []):
                    t = trials.get((sc, tid, rep))
                    if t is None or t.get("infra_error") or t.get("status") != "completed":
                        continue
                    n_trials += 1
                    if is_pass(t.get("verifier_results")):
                        passes_count += 1
                    for run in runs.get((sc, tid, rep), []):
                        u = run.get("usage") or {}
                        in_tok += u.get("input_tokens", 0)
                        out_tok += u.get("output_tokens", 0)
                        cache_tok += u.get("cache_creation_input_tokens", 0) + u.get(
                            "cache_read_input_tokens", 0
                        )
                        turns_sum += run.get("turns", 0)
                        wall_sum += run.get("duration", 0.0)
            if n_trials == 0:
                continue
            eff_data[sc] = {
                "mean_in": in_tok / n_trials,
                "mean_out": out_tok / n_trials,
                "mean_cache": cache_tok / n_trials,
                "mean_turns": turns_sum / n_trials,
                "mean_wall": wall_sum / n_trials,
                "quality": passes_count / n_trials,
                "mean_total": (in_tok + out_tok + cache_tok) / n_trials,
            }

        # Pareto frontier: arm A is flagged when NO other arm strictly dominates it —
        # another arm with quality >= AND tokens <= AND strictly better on at least one
        # axis. (The prior test "quality_A >= quality_B and tokens_A <= tokens_B for some
        # B" flagged any arm that merely beat SOMEONE, so it starred strictly-dominated
        # arms — even 0%-quality ones — and matched calibration.py's already-fixed
        # _pareto only by accident on two-arm cases. This is that same strict fix.)
        pareto: dict[str, bool] = {
            sc_a: not any(
                sc_b != sc_a
                and db["quality"] >= da["quality"]
                and db["mean_total"] <= da["mean_total"]
                and (db["quality"] > da["quality"] or db["mean_total"] < da["mean_total"])
                for sc_b, db in eff_data.items()
            )
            for sc_a, da in eff_data.items()
        }

        # A star earned on means that sit inside each other's observed spread is an
        # artefact of where this N happened to land — one more repeat can move it to
        # another arm. Qualify it rather than printing an unhedged frontier the data
        # does not support.
        contested: dict[str, bool] = {}
        for sc_a in eff_data:
            others = [
                sc_b
                for sc_b in eff_data
                if sc_b != sc_a
                and _ranges_overlap(per_trial_tokens.get(sc_a, []), per_trial_tokens.get(sc_b, []))
            ]
            contested[sc_a] = bool(others) and pareto.get(sc_a, False)

        if eff_data:
            lines.append("### Efficiency")
            lines.append("")
            lines.append(
                "| Scenario | N | Mean In-Tok | Mean Out-Tok | Mean Cache-Tok"
                " | Mean Turns | Turns (min/med/max) | Mean Wall (s)"
                " | Quality / 100k Tok | Pareto |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---|---|")
            any_contested = False
            for sc in all_sc:
                if sc not in eff_data:
                    continue
                d = eff_data[sc]
                mt = d["mean_total"]
                qp100k = f"{d['quality'] * 100_000 / mt:.2f}" if mt > 0 else "N/A"
                if not pareto.get(sc, False):
                    flag = ""
                elif contested.get(sc, False):
                    flag = "★?"
                    any_contested = True
                else:
                    flag = "★"
                n_cell = len(per_trial_tokens.get(sc, []))
                lines.append(
                    f"| {sc} | {n_cell} | {d['mean_in']:.0f} | {d['mean_out']:.0f}"
                    f" | {d['mean_cache']:.0f} | {d['mean_turns']:.1f}"
                    f" | {_fmt_spread(per_trial_turns.get(sc, []))} | {d['mean_wall']:.1f}"
                    f" | {qp100k} | {flag} |"
                )
            lines.append("")
            if any_contested:
                lines.append(
                    "> **★? = contested frontier.** This arm is Pareto-optimal on the"
                    " MEANS, but its per-trial token range overlaps another arm's, so"
                    " the ordering is not established at this N. Treat it as"
                    " directional; add repeats before quoting it as a result."
                )
                lines.append("")

    _section("Dev Tasks", dev_tasks)
    _section("Holdout Tasks", holdout_tasks)

    # --- Calibration: only when the bank ships scores + hard_criteria ---
    # Heading switches to Context-Size when the bank's tasks carry [context] tags;
    # non-context banks keep the default heading, so their scorecards are byte-unchanged.
    task_meta = _load_task_meta(bank, tasks_dir)
    routing_path: pathlib.Path | None = None
    if task_meta:
        from fathom import calibration as _cal

        is_ctx = any("context" in m for m in task_meta.values())
        heading = calibration_heading(is_context=is_ctx)
        cal = _cal.build_calibration(raw, task_meta)
        lines.extend(_cal.render_calibration(cal, heading=heading))
        # The routing substrate, emitted as a machine-readable artifact beside the
        # scorecard. A study that compares routing MECHANISMS on cost consumes this
        # table rather than parsing markdown or reading the ledger a second way — one
        # producer, one schema, one place the numbers come from.
        # Written only for a bank that declares a reduced mechanism.
        if any(m.get("reduced") for m in task_meta.values()):
            report_dir.mkdir(parents=True, exist_ok=True)
            routing_path = report_dir / f"routing-substrate-{bank}.json"
            substrate = _cal.routing_substrate(cal, task_meta, cal.get("analysis_params"))
            substrate["bank"] = bank
            routing_path.write_text(
                json.dumps(substrate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            lines += [
                (
                    "> Routing substrate written to"
                    f" `{substrate_display_path(routing_path, root=pathlib.Path.cwd())}`"
                    " (schema documented on `routing_substrate` in"
                    " `src/fathom/calibration.py`). It is the input to the"
                    " mechanism-cost comparison; regenerate it any time with"
                    f" `fathom report {bank}`."
                ),
                "",
            ]

    while lines and not lines[-1]:
        lines.pop()

    report_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"--{_safe_file_part(dataset_version)}" if historical_note else ""
    out_path = report_dir / f"scorecard-{bank}{suffix}.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


@dataclass(frozen=True)
class PerTrialRow:
    """One trial's economy: its run rows summed, keyed by config_hash, not by arm name."""

    label: str  # the arm name, plus a config_hash prefix when one name carries several hashes
    config_hash: str
    task_id: str
    repeat: int
    status: str
    runs: int  # run rows summed into this row
    usd: float  # the sum of the run rows' cost_usd_est
    usd_missing: bool  # a run row carries cost_source "none": the sum leaves that run out
    input_tokens: int
    output_tokens: int
    turns: int
    wall: float  # seconds


_HASH_LABEL_CHARS = 8


def per_trial_rows(
    bank: str,
    ledger_dir: pathlib.Path = LEDGER_DIR,
    dataset_version: str | None = None,
) -> list[PerTrialRow]:
    """Each trial of *bank* with the USD, tokens, turns and wall time of its run rows summed.

    Voids and the dataset_version scope are those of :func:`render`. A run row has no trial
    id, so the rows of one (config_hash, task, repeat) are all summed, as the Economy section
    sums them. The key is the config_hash and not the arm name: one name can carry more than
    one hash (FATH-B49), and pooling them would hide a changed arm. A name that carries more
    than one hash is labelled with a prefix of each hash.
    """
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", bank):
        raise ValueError(f"Invalid bank name: {bank!r}")
    raw = _scope_to_current_dataset_version(bank, _read_raw(bank, ledger_dir), dataset_version)
    trials: dict[tuple[str, str, int], dict] = {}
    runs: defaultdict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for rec in raw:
        key = (rec.get("config_hash", ""), rec.get("task_id", ""), rec.get("repeat", 0))
        if rec.get("kind") == "trial":
            trials[key] = rec
        elif rec.get("kind") == "run":
            runs[key].append(rec)
    hashes_of: defaultdict[str, set[str]] = defaultdict(set)
    for (ch, _, _), rec in trials.items():
        hashes_of[rec.get("scenario") or ch].add(ch)

    rows = []
    for key, rec in trials.items():
        ch, tid, rep = key
        name = rec.get("scenario") or ch
        label = f"{name} ({ch[:_HASH_LABEL_CHARS]})" if len(hashes_of[name]) > 1 else name
        trial_runs = runs.get(key, [])
        usage = [r.get("usage") or {} for r in trial_runs]
        rows.append(
            PerTrialRow(
                label=label,
                config_hash=ch,
                task_id=tid,
                repeat=rep,
                status=rec.get("status", ""),
                runs=len(trial_runs),
                usd=sum(r.get("cost_usd_est", 0.0) for r in trial_runs),
                usd_missing=any(r.get("cost_source") == "none" for r in trial_runs),
                input_tokens=sum(u.get("input_tokens", 0) for u in usage),
                output_tokens=sum(u.get("output_tokens", 0) for u in usage),
                turns=sum(r.get("turns", 0) for r in trial_runs),
                wall=sum(r.get("duration", 0.0) for r in trial_runs),
            )
        )
    return sorted(rows, key=lambda r: (r.label, r.config_hash, r.task_id, r.repeat))


def render_per_trial(bank: str, rows: Sequence[PerTrialRow]) -> str:
    """A markdown table of :func:`per_trial_rows`, one line per trial."""
    header = (
        "| Arm | Task | Repeat | Status | Runs | Est. USD | Input tokens | Output tokens"
        " | Turns | Wall-clock (s) |"
    )
    lines = [
        f"## Per-trial economy: {bank}",
        "",
        header,
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        usd = f"{r.usd:.4f}" + ("*" if r.usd_missing else "")
        lines.append(
            f"| {r.label} | {r.task_id} | {r.repeat} | {r.status} | {r.runs} | {usd}"
            f" | {r.input_tokens} | {r.output_tokens} | {r.turns} | {r.wall:.1f} |"
        )
    if any(r.usd_missing for r in rows):
        note = (
            "`*` marks a trial with a run that reported no cost (cost_source `none`); its USD"
            " leaves that run out."
        )
        lines += ["", note]
    return "\n".join(lines) + "\n"
