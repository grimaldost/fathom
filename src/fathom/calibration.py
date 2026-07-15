"""Model-tier calibration analysis (spec §7/§8).

Pure functions over ledger records + per-task metadata. Computes, for the
``model-tier-v1`` study:

* the **hard-criteria quality fraction** per (task, arm) — ``(#true hard) / (#hard)``
  per trial, mean across repeats as the point estimate, with a Wilson CI on criteria
  **pooled across trials** (``successes = Σ true hard``, ``n = Σ total hard``), per
  ADR-0007 / FM-N1;
* the **empirically-right tier** — the cheapest model whose mean is within ε of the
  best AND whose pooled CI overlaps the best's; ``indeterminate`` when the point and
  interval criteria disagree on the cheapest adequate tier (FM-10);
* the **calibration confusion matrix** (predicted vs empirical tier) + the crossover
  score where the empirically-right model steps up, vs the 25/55 thresholds;
* the **per-band dose-response** (Δquality × Δcost per upgrade) and the
  **(model×effort) cost-quality Pareto frontier** (strict non-domination — fixes the
  prior efficiency view's "not-the-worst" flag).

The cost axis is the token×price estimate (``cost_usd_est``; subscription auth reports
``total_cost_usd=0``, D2 / FM-13). The judge is NOT used here (verifier-fraction only).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

EPS = 0.10  # ε in hard-criteria fraction units (ADR-0007 D3)

# Base auto-routed model arms, cheapest → dearest, with their tier label.
MODEL_ORDER = {"haiku": (1, "weak"), "sonnet": (2, "mid"), "opus": (3, "strong")}
THRESHOLDS = {"weak": (0, 25), "mid": (26, 55), "strong": (56, 100)}


def tier_for_score(score: float) -> str:
    """Predicted tier from a complexity score (the mapping under test)."""
    if score <= 25:
        return "weak"
    if score <= 55:
        return "mid"
    return "strong"


def _wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def parse_ledger(raw: list[dict]) -> tuple[dict, dict]:
    """Return (trials, runs) keyed by (arm, task_id, repeat).

    trials[k] = verifier_results dict (or None); runs[k] = list of run records.
    Only ``status == completed`` trials are kept (errored/truncated excluded).

    Two passes, because a ledger RunRecord carries no ``scenario`` field — the arm name is
    stamped only on TRIAL records (cli.py) — and cli.py appends a trial's run records
    BEFORE its trial record. Resolving a run's arm against a config_hash→scenario map built
    incrementally in a single pass therefore orphaned every arm's first trial's runs under
    the raw config_hash, biasing every cost this module reports off them. Pass 1 builds the
    COMPLETE map from every trial; pass 2 attributes trials and runs against it, so
    attribution is independent of record order. This mirrors the sibling fix in
    report.py:160-171 (the same single-pass bug shipped twice).
    """
    ch_to_sc: dict[str, str] = {}
    trials: dict[tuple, Any] = {}
    runs: defaultdict[tuple, list[dict]] = defaultdict(list)
    # Pass 1 — the COMPLETE config_hash → scenario-name map, from every trial record.
    for rec in raw:
        if rec.get("kind") == "trial":
            ch = rec.get("config_hash", "")
            ch_to_sc[ch] = rec.get("scenario") or ch
    # Pass 2 — attribute trials and runs against the finished map.
    for rec in raw:
        kind = rec.get("kind")
        ch = rec.get("config_hash", "")
        sc = rec.get("scenario") or ch_to_sc.get(ch, ch)
        if kind == "trial":
            if rec.get("status") == "completed" and not rec.get("infra_error"):
                trials[(sc, rec.get("task_id", ""), rec.get("repeat", 0))] = rec.get(
                    "verifier_results"
                )
        elif kind == "run":
            runs[(sc, rec.get("task_id", ""), rec.get("repeat", 0))].append(rec)
    return trials, runs


def hard_fraction(vr: Any, hard: list[str]) -> tuple[int, int]:
    """(#true hard criteria, #hard criteria present) for one trial's results."""
    if not isinstance(vr, dict):
        return (0, 0)
    present = [c for c in hard if c in vr]
    return (sum(1 for c in present if vr[c]), len(present))


def arm_task_stats(trials: dict, task_id: str, arm: str, hard: list[str]) -> dict | None:
    """Pooled hard-criteria stats for one (arm, task): mean, CI, n_trials."""
    succ = tot = n_trials = 0
    per_trial: list[float] = []
    for (sc, tid, _rep), vr in trials.items():
        if sc != arm or tid != task_id:
            continue
        s, t = hard_fraction(vr, hard)
        if t == 0:
            continue
        succ += s
        tot += t
        n_trials += 1
        per_trial.append(s / t)
    if n_trials == 0:
        return None
    return {
        "mean": sum(per_trial) / len(per_trial),
        "ci": _wilson(succ, tot),
        "n_trials": n_trials,
        "pooled": (succ, tot),
    }


def empirical_right_tier(stats_by_arm: dict[str, dict], eps: float = EPS) -> tuple[str, bool]:
    """(tier, indeterminate). Cheapest arm within ε AND CI-overlapping the best.

    ``indeterminate`` when the point-estimate and CI-overlap criteria disagree on the
    cheapest adequate arm (the ε-decision rests on overlapping CIs, FM-10).
    """
    arms = [a for a in stats_by_arm if a in MODEL_ORDER]
    if not arms:
        return ("indeterminate", True)
    best_arm = max(arms, key=lambda a: stats_by_arm[a]["mean"])
    best_mean = stats_by_arm[best_arm]["mean"]
    best_lo = stats_by_arm[best_arm]["ci"][0]

    def cheapest(passing: list[str]) -> str | None:
        return min(passing, key=lambda a: MODEL_ORDER[a][0]) if passing else None

    within_eps = cheapest([a for a in arms if stats_by_arm[a]["mean"] >= best_mean - eps])
    ci_overlap = cheapest([a for a in arms if stats_by_arm[a]["ci"][1] >= best_lo])
    if within_eps is None:
        return ("indeterminate", True)
    indeterminate = within_eps != ci_overlap
    return (MODEL_ORDER[within_eps][1], indeterminate)


def _context_pairs(trials: dict, task_meta: dict[str, dict]) -> list[dict]:
    """Per matched pair: small vs large empirically-right tier + weak-model delta (§7).

    Groups tasks by their ``[context] pair`` slug (the machine-readable pair key, FM-N3)
    and reports, for each pair, the small→large right-tier shift and the weak (haiku)
    hard-fraction delta with pooled-Wilson CIs. Empty list for banks with no context
    tags (every model-tier bank), so their scorecard is unaffected.
    """
    by_pair: defaultdict[str, dict[str, str]] = defaultdict(dict)
    for tid, meta in task_meta.items():
        ctx, pair = meta.get("context"), meta.get("pair")
        if ctx in ("small", "large") and pair:
            by_pair[pair][ctx] = tid

    def member(tid: str | None) -> dict | None:
        if not tid:
            return None
        hard = task_meta[tid]["hard_criteria"]
        stats = {a: s for a in MODEL_ORDER if (s := arm_task_stats(trials, tid, a, hard))}
        if not stats:
            return None
        emp, indet = empirical_right_tier(stats)
        weak = stats.get("haiku")
        return {
            "task_id": tid,
            "score": task_meta[tid]["score"],
            "empirical": emp,
            "indeterminate": indet,
            "means": {a: stats[a]["mean"] for a in stats},
            "weak_mean": weak["mean"] if weak else None,
            "weak_ci": weak["ci"] if weak else None,
            "weak_pooled": weak["pooled"] if weak else None,
        }

    out: list[dict] = []
    for pair, members in by_pair.items():
        small, large = member(members.get("small")), member(members.get("large"))
        score = (small or large or {}).get("score")
        delta = None
        if small and large and small["weak_mean"] is not None and large["weak_mean"] is not None:
            delta = large["weak_mean"] - small["weak_mean"]
        out.append(
            {"pair": pair, "score": score, "small": small, "large": large, "weak_delta": delta}
        )
    return sorted(out, key=lambda e: (e["score"] if e["score"] is not None else 0.0, e["pair"]))


def build_calibration(raw: list[dict], task_meta: dict[str, dict]) -> dict:
    """Top-level: confusion matrix + per-task rows + dose-response + Pareto.

    task_meta[task_id] = {"score": float, "hard_criteria": [...]}. Only non-holdout
    tasks that actually ran are included.
    """
    trials, runs = parse_ledger(raw)
    ran_tasks = sorted({tid for (_sc, tid, _r) in trials})

    rows: list[dict] = []
    for tid in ran_tasks:
        meta = task_meta.get(tid)
        if not meta:
            continue
        hard = meta["hard_criteria"]
        stats_by_arm = {}
        for arm in MODEL_ORDER:
            s = arm_task_stats(trials, tid, arm, hard)
            if s:
                stats_by_arm[arm] = s
        if not stats_by_arm:
            continue
        predicted = tier_for_score(meta["score"])
        empirical, indet = empirical_right_tier(stats_by_arm)
        rows.append(
            {
                "task_id": tid,
                "score": meta["score"],
                "predicted": predicted,
                "empirical": empirical,
                "indeterminate": indet,
                "means": {a: stats_by_arm[a]["mean"] for a in stats_by_arm},
                "n": {a: stats_by_arm[a]["n_trials"] for a in stats_by_arm},
                # Context dimension (§7) — None for model-tier banks; surfaced for context banks.
                "context": meta.get("context"),
                "pair": meta.get("pair"),
            }
        )

    # Confusion matrix counts (predicted × empirical), indeterminate as its own column.
    tiers = ["weak", "mid", "strong"]
    confusion: dict[str, dict[str, int]] = {
        p: dict.fromkeys([*tiers, "indeterminate"], 0) for p in tiers
    }
    for r in rows:
        col = "indeterminate" if r["indeterminate"] else r["empirical"]
        confusion[r["predicted"]][col] += 1

    return {
        "rows": rows,
        "confusion": confusion,
        "dose_response": _dose_response(trials, runs, task_meta),
        "pareto": _pareto(trials, runs, task_meta),
        # Context-size view (§7): empty list for banks with no `[context]` tags.
        "pairs": _context_pairs(trials, task_meta),
    }


def _arm_cost(runs: dict, arm: str, tasks: list[str]) -> float:
    """Mean estimated USD per trial for an arm over the given tasks."""
    total = 0.0
    keys = set()
    for (sc, tid, rep), rlist in runs.items():
        if sc != arm or tid not in tasks:
            continue
        keys.add((sc, tid, rep))
        total += sum(r.get("cost_usd_est", 0.0) for r in rlist)
    return total / len(keys) if keys else 0.0


def _dose_response(trials: dict, runs: dict, task_meta: dict) -> dict:
    """Per band: mean hard-fraction quality + mean cost for haiku→sonnet→opus."""
    band_tasks: defaultdict[str, list[str]] = defaultdict(list)
    for tid, meta in task_meta.items():
        band_tasks[tier_for_score(meta["score"])].append(tid)
    out: dict[str, dict] = {}
    for band, tids in band_tasks.items():
        ran = [t for t in tids if any(sc_t == t for (_s, sc_t, _r) in trials)]
        if not ran:
            continue
        per_arm = {}
        for arm in MODEL_ORDER:
            fracs = []
            for tid in ran:
                s = arm_task_stats(trials, tid, arm, task_meta[tid]["hard_criteria"])
                if s:
                    fracs.append(s["mean"])
            if fracs:
                per_arm[arm] = {
                    "quality": sum(fracs) / len(fracs),
                    "cost": _arm_cost(runs, arm, ran),
                }
        if per_arm:
            out[band] = per_arm
    return out


def _pareto(trials: dict, runs: dict, task_meta: dict) -> list[dict]:
    """(arm) cost-quality points + strict non-domination flag (frontier).

    A point is on the frontier iff NO other point strictly dominates it: another arm
    with quality >= AND cost <= AND strictly better on at least one axis. (Fixes the
    prior 'flag if it beats some arm' bug.)
    """
    tasks = list(task_meta)
    arms = sorted({sc for (sc, _t, _r) in trials})
    points = []
    for arm in arms:
        fracs = []
        for tid in tasks:
            s = arm_task_stats(trials, tid, arm, task_meta[tid]["hard_criteria"])
            if s:
                fracs.append(s["mean"])
        if not fracs:
            continue
        points.append(
            {"arm": arm, "quality": sum(fracs) / len(fracs), "cost": _arm_cost(runs, arm, tasks)}
        )
    for p in points:
        p["frontier"] = not any(
            q is not p
            and q["quality"] >= p["quality"]
            and q["cost"] <= p["cost"]
            and (q["quality"] > p["quality"] or q["cost"] < p["cost"])
            for q in points
        )
    return points


# --------------------------------------------------------------------------- render


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def _render_context_pairs(pairs: list[dict]) -> list[str]:
    """Per-pair small→large right-tier shift table (§7); empty for model-tier banks."""
    if not pairs:
        return []
    order = {"weak": 1, "mid": 2, "strong": 3}
    lines = ["### Context-size: per-pair small→large right-tier shift", ""]
    lines.append(
        "| pair | difficulty | small right-tier | large right-tier | shift "
        "| haiku small | haiku large | Δ haiku |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")

    def emp(m: dict | None) -> str:
        if not m:
            return "—"
        return "?" if m["indeterminate"] else m["empirical"]

    for e in pairs:
        sm, lg = e.get("small"), e.get("large")
        shift = "—"
        if sm and lg and not sm["indeterminate"] and not lg["indeterminate"]:
            so, lo = order[sm["empirical"]], order[lg["empirical"]]
            if lo > so:
                shift = f"↑ {sm['empirical']}→{lg['empirical']}"
            elif lo < so:
                shift = f"↓ {sm['empirical']}→{lg['empirical']}"
            else:
                shift = "="
        hs = _pct(sm["weak_mean"]) if sm and sm.get("weak_mean") is not None else "—"
        hl = _pct(lg["weak_mean"]) if lg and lg.get("weak_mean") is not None else "—"
        dlt = f"{e['weak_delta']:+.2f}" if e.get("weak_delta") is not None else "—"
        diff = f"{e['score']:.0f}" if e.get("score") is not None else "—"
        lines.append(
            f"| {e['pair']} | {diff} | {emp(sm)} | {emp(lg)} | {shift} | {hs} | {hl} | {dlt} |"
        )
    lines.append("")
    return lines


def render_calibration(cal: dict, *, heading: str = "## Model-Tier Calibration") -> list[str]:
    """Markdown lines for the calibration section (appended to the scorecard).

    ``heading`` selects the section title (FM-B): report.py passes
    ``## Context-Size Calibration`` for a context bank (one whose tasks carry
    ``[context]`` tags), the default otherwise — so model-tier scorecards are unchanged.
    """
    rows = cal["rows"]
    if not rows:
        return []
    tiers = ["weak", "mid", "strong"]
    lines = [heading, ""]

    # Confusion matrix
    lines += ["### Calibration: predicted tier vs empirically-right tier", ""]
    lines.append("| predicted ↓ / empirical → | weak | mid | strong | indeterminate |")
    lines.append("|---|---|---|---|---|")
    conf = cal["confusion"]
    for p in tiers:
        c = conf[p]
        lines.append(
            f"| **{p}** | {c['weak']} | {c['mid']} | {c['strong']} | {c['indeterminate']} |"
        )
    on_diag = sum(conf[t][t] for t in tiers)
    total = sum(sum(conf[p].values()) for p in tiers)
    lines += ["", f"On-diagonal (well-tuned): **{on_diag}/{total}**.", ""]

    # Per-task detail
    lines += ["### Per-task (hard-criteria quality fraction by arm)", ""]
    lines.append("| task | score | predicted | empirical | haiku | sonnet | opus | note |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: x["score"]):
        m = r["means"]

        def cell(a: str) -> str:
            return _pct(m[a]) if a in m else "—"

        note = (
            "indeterminate"
            if r["indeterminate"]
            else ("✓" if r["predicted"] == r["empirical"] else f"{r['predicted']}→{r['empirical']}")
        )
        lines.append(
            f"| {r['task_id']} | {r['score']:.0f} | {r['predicted']} | "
            f"{'?' if r['indeterminate'] else r['empirical']} | "
            f"{cell('haiku')} | {cell('sonnet')} | {cell('opus')} | {note} |"
        )
    lines.append("")

    # Dose-response
    dr = cal["dose_response"]
    if dr:
        lines += ["### Dose-response (quality × cost per upgrade, by band)", ""]
        lines.append("| band | arm | mean quality | mean $/trial | Δquality vs cheaper |")
        lines.append("|---|---|---|---|---|")
        for band in tiers:
            if band not in dr:
                continue
            prev_q = None
            for arm in MODEL_ORDER:
                if arm not in dr[band]:
                    continue
                d = dr[band][arm]
                dq = "—" if prev_q is None else f"{d['quality'] - prev_q:+.2f}"
                lines.append(f"| {band} | {arm} | {d['quality']:.2f} | ${d['cost']:.3f} | {dq} |")
                prev_q = d["quality"]
        lines.append("")

    # Pareto
    pareto = cal["pareto"]
    if pareto:
        lines += ["### Cost-quality Pareto frontier (★ = non-dominated)", ""]
        lines.append("| arm | mean quality | mean $/trial | frontier |")
        lines.append("|---|---|---|---|")
        for p in sorted(pareto, key=lambda x: x["cost"]):
            lines.append(
                f"| {p['arm']} | {p['quality']:.2f} | ${p['cost']:.3f} | "
                f"{'★' if p['frontier'] else ''} |"
            )
        lines.append("")

    # Context-size: per-pair small→large shift (§7) — only for context banks.
    lines += _render_context_pairs(cal.get("pairs") or [])

    return lines
