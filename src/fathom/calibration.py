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

**Arm → tier resolution.** An arm is matched to the capacity ladder by the model family
token in its NAME (``FAMILY_TIERS``, longest match wins), not by a fixed list of arm
names — so a renamed/effort/gated-but-tiered arm (``sonnet5``, ``haiku-xhigh``,
``sonnet-lo-gate``) lands on the ladder without an edit. ``FAMILY_TIERS`` is a MIRROR of
the choosing-models tier map, carried here and never referenced back (see
``docs/method/recalibration-playbook.md`` Step 0). An arm that resolves to no family
(``bare-gate``, ``orchestrated``) is *untiered*: it renders in every per-arm view but
takes no part in the tier verdict — a strategy is not a capacity tier. The ``frontier``
tier is never *score*-assigned (``tier_for_score`` tops out at ``strong``), yet it is
reachable *empirically* (a ``fable`` arm cheapest-adequate), so it appears as a confusion
COLUMN with no predicted ROW. Caveat: the ladder is tier-ordered, not observed-cost
ordered — on the committed ledger ``sonnet5`` costs more than ``opus``; this is harmless
to every tier verdict (a comparison feeds a tier, and both sonnets share the ``mid`` tier),
and the dose-response column reads ``Δquality vs prev arm`` rather than ``vs cheaper`` so
the rendered scorecard never asserts a dollar order the ladder does not promise.

The cost axis is the token×price estimate (``cost_usd_est``; subscription auth reports
``total_cost_usd=0``, D2 / FM-13). The judge is NOT used here (verifier-fraction only).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

EPS = 0.10  # ε in hard-criteria fraction units (ADR-0007 D3)

# The capacity ladder: tier → cheapness rank (weak cheapest, frontier dearest). The one
# place rank and tier come from, replacing a per-arm-name (rank, tier) table.
TIER_ORDER = {"weak": 1, "mid": 2, "strong": 3, "frontier": 4}
# A MIRROR of the choosing-models tier map: model family → capacity tier. Carried, never
# referenced back — the same substring-resolution precedent as
# adapters/claude_cli.py:_PRICE_PER_1K. Refresh via /refresh-models when the lineup moves.
FAMILY_TIERS = {"haiku": "weak", "sonnet": "mid", "opus": "strong", "fable": "frontier"}
THRESHOLDS = {"weak": (0, 25), "mid": (26, 55), "strong": (56, 100)}


def arm_tier(arm: str) -> str | None:
    """Capacity tier of an arm, from the model family token in its NAME (longest match).

    Collects every ``FAMILY_TIERS`` token appearing in the lowercased arm name and returns
    the tier of the LONGEST hit (deterministic when a name embeds more than one token).
    Resolves ``sonnet5``→mid, ``haiku-xhigh``→weak, ``sonnet-lo-gate``→mid,
    ``stack-sonnet``→mid without an edit. Returns ``None`` for an untiered strategy arm
    (``bare-gate``, ``orchestrated``): it renders everywhere but takes no part in the tier
    verdict. Extension point (not built — no bank needs it): a per-bank ``[arms]`` table in
    ``scores.toml`` would override this for arms that are not family-inferable.
    """
    lower = arm.lower()
    hits = [family for family in FAMILY_TIERS if family in lower]
    if not hits:
        return None
    return FAMILY_TIERS[max(hits, key=len)]


def _ladder_key(arm: str) -> tuple[int, str]:
    """Sort key: tiered arms cheapest→dearest, untiered last, ties within a tier by name."""
    return (TIER_ORDER.get(arm_tier(arm) or "", 99), arm)


def arms_in(trials: dict, task_id: str | None = None) -> list[str]:
    """Arms present in ``trials`` (optionally for one task), ordered on the capacity ladder.

    Tiered arms first (cheapest→dearest), untiered arms last, ties within a tier by name.
    One ordering rule, shared by every iteration site and both renders, so the ladder can
    never disagree with itself.
    """
    arms = {sc for (sc, tid, _rep) in trials if task_id is None or tid == task_id}
    return sorted(arms, key=_ladder_key)


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
    cheapest adequate TIER (the ε-decision rests on overlapping CIs, FM-10). The
    comparison is by tier, not arm identity, so two arms sharing a tier (``sonnet`` +
    ``sonnet5``) that agree on the verdict are not flagged as a disagreement.
    """
    arms = [a for a in stats_by_arm if arm_tier(a)]
    if not arms:
        return ("indeterminate", True)
    best_arm = max(arms, key=lambda a: stats_by_arm[a]["mean"])
    best_mean = stats_by_arm[best_arm]["mean"]
    best_lo = stats_by_arm[best_arm]["ci"][0]

    def cheapest(passing: list[str]) -> str | None:
        return min(passing, key=_ladder_key) if passing else None

    within_eps = cheapest([a for a in arms if stats_by_arm[a]["mean"] >= best_mean - eps])
    ci_overlap = cheapest([a for a in arms if stats_by_arm[a]["ci"][1] >= best_lo])
    if within_eps is None:
        return ("indeterminate", True)
    indeterminate = arm_tier(within_eps) != arm_tier(ci_overlap)
    return (arm_tier(within_eps) or "indeterminate", indeterminate)


def _tier_arm(stats: dict[str, dict], tier: str) -> dict | None:
    """Stats of the (deterministic) arm resolving to ``tier`` in ``stats``, else None.

    Arms in ``stats`` whose ``arm_tier`` is ``tier``, sorted by name, first one — exactly
    one such arm per tier on every real bank today, so the value is unchanged; the sort
    only fixes the tie-break if a bank ever runs two arms in one tier.
    """
    matches = sorted(a for a in stats if arm_tier(a) == tier)
    return stats[matches[0]] if matches else None


def _context_pairs(trials: dict, task_meta: dict[str, dict]) -> list[dict]:
    """Per matched pair: small vs large empirically-right tier + weak-model delta (§7).

    Groups tasks by their ``[context] pair`` slug (the machine-readable pair key, FM-N3)
    and reports, for each pair, the small→large right-tier shift and the weak-tier
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
        stats = {a: s for a in arms_in(trials, tid) if (s := arm_task_stats(trials, tid, a, hard))}
        if not stats:
            return None
        emp, indet = empirical_right_tier(stats)
        weak = _tier_arm(stats, "weak")
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
        for arm in arms_in(trials, tid):
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
    # Predicted rows are only weak/mid/strong — tier_for_score never assigns frontier
    # (the "frontier is never score-assigned" invariant). frontier IS reachable
    # empirically (a fable arm cheapest-adequate), so it is a COLUMN with no predicted row.
    predicted_tiers = ["weak", "mid", "strong"]
    columns = [*TIER_ORDER, "indeterminate"]
    confusion: dict[str, dict[str, int]] = {p: dict.fromkeys(columns, 0) for p in predicted_tiers}
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
    """Per band: mean hard-fraction quality + mean cost for every arm on the ladder."""
    band_tasks: defaultdict[str, list[str]] = defaultdict(list)
    for tid, meta in task_meta.items():
        band_tasks[tier_for_score(meta["score"])].append(tid)
    out: dict[str, dict] = {}
    for band, tids in band_tasks.items():
        ran = [t for t in tids if any(sc_t == t for (_s, sc_t, _r) in trials)]
        if not ran:
            continue
        per_arm = {}
        for arm in arms_in(trials):
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
    lines = ["### Context-size: per-pair small→large right-tier shift", ""]
    lines.append(
        "| pair | difficulty | small right-tier | large right-tier | shift "
        "| weak small | weak large | Δ weak |"
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
            so, lo = TIER_ORDER[sm["empirical"]], TIER_ORDER[lg["empirical"]]
            if lo > so:
                shift = f"↑ {sm['empirical']}→{lg['empirical']}"
            elif lo < so:
                shift = f"↓ {sm['empirical']}→{lg['empirical']}"
            else:
                shift = "="
        ws = _pct(sm["weak_mean"]) if sm and sm.get("weak_mean") is not None else "—"
        wl = _pct(lg["weak_mean"]) if lg and lg.get("weak_mean") is not None else "—"
        dlt = f"{e['weak_delta']:+.2f}" if e.get("weak_delta") is not None else "—"
        diff = f"{e['score']:.0f}" if e.get("score") is not None else "—"
        lines.append(
            f"| {e['pair']} | {diff} | {emp(sm)} | {emp(lg)} | {shift} | {ws} | {wl} | {dlt} |"
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

    # Confusion matrix. Empirical columns are the fixed three, then `frontier` ONLY when
    # a cell uses it (keeps today's scorecards byte-identical; a future fable arm lights
    # the column up), then indeterminate. Predicted rows never include frontier.
    conf = cal["confusion"]
    show_frontier = any(conf[p].get("frontier", 0) for p in tiers)
    emp_cols = (
        ["weak", "mid", "strong"] + (["frontier"] if show_frontier else []) + ["indeterminate"]
    )
    lines += ["### Calibration: predicted tier vs empirically-right tier", ""]
    lines.append("| predicted ↓ / empirical → | " + " | ".join(emp_cols) + " |")
    lines.append("|" + "---|" * (len(emp_cols) + 1))
    for p in tiers:
        c = conf[p]
        lines.append(f"| **{p}** | " + " | ".join(str(c[col]) for col in emp_cols) + " |")
    on_diag = sum(conf[t][t] for t in tiers)
    total = sum(sum(conf[p].values()) for p in tiers)
    lines += ["", f"On-diagonal (well-tuned): **{on_diag}/{total}**.", ""]

    # Per-task detail. Arm columns are derived from the arms that actually ran, on the
    # ladder — so a renamed/gated arm (sonnet5, bare-gate) renders, and a 3-arm bank's
    # header stays byte-identical to `haiku | sonnet | opus`.
    lines += ["### Per-task (hard-criteria quality fraction by arm)", ""]
    arm_cols = sorted({a for r in rows for a in r["means"]}, key=_ladder_key)
    lines.append("| task | score | predicted | empirical | " + " | ".join(arm_cols) + " | note |")
    lines.append("|" + "---|" * (len(arm_cols) + 5))
    for r in sorted(rows, key=lambda x: x["score"]):
        m = r["means"]

        def cell(a: str) -> str:
            return _pct(m[a]) if a in m else "—"

        note = (
            "indeterminate"
            if r["indeterminate"]
            else ("✓" if r["predicted"] == r["empirical"] else f"{r['predicted']}→{r['empirical']}")
        )
        cells = " | ".join(cell(a) for a in arm_cols)
        emp = "?" if r["indeterminate"] else r["empirical"]
        lines.append(
            f"| {r['task_id']} | {r['score']:.0f} | {r['predicted']} | {emp} | {cells} | {note} |"
        )
    lines.append("")

    # Dose-response
    dr = cal["dose_response"]
    if dr:
        lines += ["### Dose-response (quality × cost per upgrade, by band)", ""]
        # Δ is against the arm one step DOWN the ladder (the row above). The rows are
        # tier-ordered, not dollar-ordered, so the column reads "vs prev arm" not "vs
        # cheaper" — on the committed ledger sonnet5 (mid) sorts above opus (strong) yet
        # costs more, and "vs cheaper" would misstate a dollar order the ladder never promises.
        lines.append("| band | arm | mean quality | mean $/trial | Δquality vs prev arm |")
        lines.append("|---|---|---|---|---|")
        for band in tiers:
            if band not in dr:
                continue
            prev_q = None
            for arm in sorted(dr[band], key=_ladder_key):
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
