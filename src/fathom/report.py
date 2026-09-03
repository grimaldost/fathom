"""Scorecard renderer — reads ledger JSONL and produces report/scorecard-<bank>.md."""

from __future__ import annotations

import json
import math
import pathlib
import re
import warnings
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

LEDGER_DIR = pathlib.Path("ledger")
REPORT_DIR = pathlib.Path("report")
TASKS_DIR = pathlib.Path("tasks")

_BARE = "bare"
_SERIES_KEY = "series"
_ARM_DELTAS = [
    "human decomposition",
    "per-PR gates",
    "review/fix subagents",
    "engine settings",
]


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion. (0.0, 1.0) when n == 0."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _is_pass(verifier_results: Any) -> bool:
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
        for line in f:
            stripped = line.strip()
            if stripped:
                try:
                    out.append(json.loads(stripped))
                except Exception:
                    pass
    return out


def _load_task_meta(bank: str) -> dict[str, dict]:
    """Per-task {score, hard_criteria} from tasks/<bank>/scores.toml + task.toml (§7).

    Returns {} when the bank ships no scores.toml (every non-calibration bank), so the
    calibration section is simply absent and other banks' scorecards are byte-unchanged.

    A bank may also declare ONE positive control in scores.toml's ``[control]`` table
    (``task``, ``weak_arm``, ``strong_arm``, ``alpha``, ``min_repeats``). It is attached
    to that task's meta as ``entry["control"]``, which is what makes calibration.py read
    it by its own rule and keep it out of the confusion matrix.
    """
    import tomllib

    bank_dir = pathlib.Path("tasks") / bank
    scores_path = bank_dir / "scores.toml"
    if not scores_path.is_file():
        return {}
    try:
        with open(scores_path, "rb") as f:
            scores_doc = tomllib.load(f)
        scores = scores_doc.get("scores", {})
        control = scores_doc.get("control") or {}
        # The routing layer: the reduced mechanism's per-task prediction, the task's
        # genre, and the pre-registered analysis parameters. Absent on every other
        # bank, so their scorecards are byte-unchanged.
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
            # [context] is dropped by load_bank's Task (FM-N4) — re-parse task.toml directly.
            try:
                with open(t.task_dir / "task.toml", "rb") as tf:
                    ctx = tomllib.load(tf).get("context") or {}
                if ctx.get("size"):
                    entry["context"] = ctx["size"]
                if ctx.get("pair"):
                    entry["pair"] = ctx["pair"]
            except Exception:
                pass
            meta[t.id] = entry
    return meta


# --- FATH-B05: qualify the point estimates the ledger already lets us qualify ---


def _spread(values: Sequence[float]) -> tuple[float, float, float]:
    """(min, median, max) of *values*; (0, 0, 0) when empty.

    Reported beside every mean because the mean alone reversed the direction of
    the verdict on 3 of 5 banks in one campaign and moved the Pareto star between
    n=2 and n=3 in another. A bimodal arm and a single blow-up run are invisible
    in a mean and obvious in a range.
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
    a score — one recorded arm's mean turns (41.1) exceeded its task's max_turns
    (40) with nothing on the page marking it.
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
        except Exception:
            continue
    return caps


def _ranges_overlap(a: Sequence[float], b: Sequence[float]) -> bool:
    """True when the observed [min, max] ranges of *a* and *b* intersect."""
    if not a or not b:
        return True
    return min(a) <= max(b) and min(b) <= max(a)


def _scope_to_current_dataset_version(bank: str, raw: list[dict]) -> list[dict]:
    """Keep only records at the CURRENT dataset_version — the last-appended trial's.

    The ledger is append-only, so the most-recently-run trials are last in the file;
    their dataset_version is the bank's current version. A ``dataset_version`` bump
    (bumped on any task/fixture/verifier change — it is in the resume key) otherwise
    lets an older task version's trials silently co-render with the new one: the
    scorecard keys trials by (scenario, task, repeat) with no dataset_version, so
    last-write-wins keeps the newest per cell but any cell the current version has
    not re-run yet still shows the *old* version's result — a silent conflation of
    two task definitions under one arm (2026-07-01 feedback #1).

    Scoping to the current version keeps the scorecard a coherent current-state view
    (matching the resume key, which includes dataset_version). Older-version trials
    remain in the committed ledger untouched (append-only); they are excluded from
    this render and the exclusion is surfaced, never silent. A single-version bank is
    unaffected — nothing is excluded and the output is byte-identical.
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


def render(
    bank: str,
    *,
    ledger_dir: pathlib.Path = LEDGER_DIR,
    report_dir: pathlib.Path = REPORT_DIR,
    tasks_dir: pathlib.Path = TASKS_DIR,
) -> pathlib.Path:
    """Read ledger/<bank>.jsonl and write report/scorecard-<bank>.md."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", bank):
        raise ValueError(f"Invalid bank name: {bank!r}")
    raw = _read_raw(bank, ledger_dir)
    raw = _scope_to_current_dataset_version(bank, raw)
    turn_caps = _load_turn_caps(bank, tasks_dir)

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
    # joined Economy/Efficiency (12.6% of tokens dropped on a real matrix). Two passes
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
            # carries no trial id), so it warns rather than double-count silently — the
            # operator's convention is to archive the invalid ledger and re-run fresh.
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

    lines: list[str] = [f"# Scorecard — {bank}", ""]

    def _stats(sc: str, task_list: list[str]) -> tuple[int, int, int, int]:
        # Returns (passes, n, infra, k) where k = distinct tasks contributing a
        # completed trial — the CLUSTER count. n pools every task×repeat cell, but
        # repeats within a task and different tasks are correlated, so k lets the
        # reader see the design effect the pooled Wilson CI ignores (review-panel
        # Option a; ADR-0007 D3 precedent).
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
                    if _is_pass(t.get("verifier_results")):
                        passes += 1
        return passes, n, infra, len(completed_tasks)

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
        # CI-honesty caveat (review-panel Option a; ADR-0007 D3 precedent): N pools
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
                v = f"- **{sc}** — no scored trials, Wilson 95% CI N/A, n=0 — directional, not final"
            if infra:
                v += f"; {infra} infra error(s) excluded"
            if _SERIES_KEY in sc:
                v += f"; arm deltas vs bare: {', '.join(_ARM_DELTAS)}"
            lines.append(v)
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
        # mean is the whole point of FATH-B05.
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
                        # §11/D2: cost lives on the run record's top-level
                        # cost_usd_est (the adapter estimate persisted by cli.py),
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

            # --- Arm Health (FATH-B05): what makes a pass rate a lower bound ------
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
                    if _is_pass(t.get("verifier_results")):
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
        # artefact of where this N happened to land — the recorded case moved the
        # star between n=2 and n=3 on the same arms and bank. Qualify it rather than
        # printing an unhedged frontier the data does not support.
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

    # --- Calibration (§7/§8): only when the bank ships scores + hard_criteria ---
    # Heading switches to Context-Size when the bank's tasks carry [context] tags (FM-B);
    # model-tier banks keep the default heading, so their scorecards are byte-unchanged.
    task_meta = _load_task_meta(bank)
    routing_path: pathlib.Path | None = None
    if task_meta:
        from fathom import calibration as _cal

        is_ctx = any("context" in m for m in task_meta.values())
        heading = "## Context-Size Calibration" if is_ctx else "## Model-Tier Calibration"
        cal = _cal.build_calibration(raw, task_meta)
        lines.extend(_cal.render_calibration(cal, heading=heading))
        # The routing substrate, emitted as a machine-readable artifact beside the
        # scorecard. A separate programme compares routing MECHANISMS on cost, and it
        # consumes this table rather than parsing markdown or reading the ledger a
        # second way — one producer, one schema, one place the numbers come from.
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
                f"> Routing substrate written to `{routing_path.as_posix()}`"
                " (schema in the bank README). It is the input to the"
                " mechanism-cost comparison; regenerate it any time with"
                f" `fathom report {bank}`.",
                "",
            ]

    while lines and not lines[-1]:
        lines.pop()

    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"scorecard-{bank}.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
