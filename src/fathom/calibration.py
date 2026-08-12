"""Model-tier calibration analysis (spec §7/§8).

Pure functions over ledger records + per-task metadata. Computes, for the
``model-tier-*`` studies:

* the **per-trial pass rate** per (task, arm) — ONE Bernoulli draw per trial, the
  draw being ``every hard criterion true`` (ADR-0009, superseding ADR-0007 D3). The
  point estimate is ``passing trials / trials`` and the Wilson CI is computed on that
  same integer pair, so the interval's ``n`` is the number of trials actually bought;
* the **empirically-right tier** — the cheapest model whose mean is within ε of the
  best AND whose CI overlaps the best's; ``indeterminate`` when the point and
  interval criteria disagree on the cheapest adequate tier (FM-10);
* the **positive-control separation** — a one-sided Fisher exact test between a
  bank-declared weak and strong arm on a bank-declared control task, read by its own
  rule and excluded from the confusion matrix;
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
import warnings
from collections import defaultdict
from math import comb
from typing import Any

EPS = 0.10  # ε in per-trial pass-rate units (ADR-0007 D3 as amended by ADR-0009)

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

    Pass 2 also mirrors report.py's two anomaly warnings, which the cost path is
    otherwise silent-wrong without: a **duplicate completed trial** (a resume never
    re-runs a completed cell, so two completed lines for one cell mean its runs would be
    summed twice in ``_arm_cost``) and a **dangling run** whose ``config_hash`` never
    appears on a trial line (its economy is dropped from the scorecard with no trace).
    Both warn rather than corrupt the cost silently — the operator archives the invalid
    ledger and re-runs fresh.
    """
    ch_to_sc: dict[str, str] = {}
    trials: dict[tuple, Any] = {}
    runs: defaultdict[tuple, list[dict]] = defaultdict(list)
    # Pass 1 — the COMPLETE config_hash → scenario-name map, from every trial record.
    for rec in raw:
        if rec.get("kind") == "trial":
            ch = rec.get("config_hash", "")
            ch_to_sc[ch] = rec.get("scenario") or ch
    # Pass 2 — attribute trials and runs against the finished map, warning on anomalies.
    seen_completed: set[tuple] = set()
    dangling_warned: set[str] = set()
    for rec in raw:
        kind = rec.get("kind")
        ch = rec.get("config_hash", "")
        sc = rec.get("scenario") or ch_to_sc.get(ch, ch)
        tid = rec.get("task_id", "")
        rep = rec.get("repeat", 0)
        if kind == "trial":
            if rec.get("status") == "completed" and not rec.get("infra_error"):
                ckey = (rec.get("dataset_version"), ch, tid, rep)
                if ckey in seen_completed:
                    warnings.warn(
                        f"duplicate completed trial for {sc}/{tid} repeat={rep} "
                        f"(config_hash={ch[:12]}…): per-arm cost may double-count; "
                        "inspect the ledger and archive+re-run if it is a stale re-run",
                        stacklevel=2,
                    )
                seen_completed.add(ckey)
                trials[(sc, tid, rep)] = rec.get("verifier_results")
        elif kind == "run":
            if ch not in ch_to_sc and ch not in dangling_warned:
                dangling_warned.add(ch)
                warnings.warn(
                    f"run record with config_hash={ch[:12]}… has no trial line; its economy "
                    "is excluded from the calibration cost (likely a trial interrupted mid-write)",
                    stacklevel=2,
                )
            runs[(sc, tid, rep)].append(rec)
    return trials, runs


def hard_fraction(vr: Any, hard: list[str]) -> tuple[int, int]:
    """(#true hard criteria, #hard criteria present) for one trial's results."""
    if not isinstance(vr, dict):
        return (0, 0)
    present = [c for c in hard if c in vr]
    return (sum(1 for c in present if vr[c]), len(present))


def arm_task_stats(trials: dict, task_id: str, arm: str, hard: list[str]) -> dict | None:
    """PER-TRIAL stats for one (arm, task): one Bernoulli draw per trial.

    A trial scores 1 iff EVERY hard criterion present is true, 0 otherwise. The point
    estimate is ``passing / n_trials`` and the Wilson CI is computed on that same
    integer pair — so the interval's ``n`` is the number of trials actually bought.

    WHY, MEASURED (ADR-0009, superseding ADR-0007 D3). The prior estimator pooled
    criteria across trials (``successes = Σ true hard``, ``n = Σ total hard``), which
    treats a task's k hard criteria as k independent draws. On this bank family they
    are not independent — they are perfectly correlated. Over every completed
    multi-criterion trial on the committed ``ledger/model-tier-v1.jsonl`` (175 trials,
    7 tasks, 5 arms) the hard set came out **all-true or all-false, 175 times out of
    175**: zero mixed trials. Pooling therefore multiplied the CI's ``n`` by k while
    buying no information, narrowing every interval by roughly ``sqrt(k)`` and
    licensing repeat counts that cannot in fact resolve the cells they were sized for.

    The conjunction is the honest single draw whether or not the correlation holds: if
    criteria ever do come apart, an all-pass draw is a conservative statistic rather
    than an inflated one. ``mixed_trials`` records how often they came apart, so the
    assumption is checkable from the ledger instead of asserted — a nonzero count is
    the signal to re-open ADR-0009, not a silent estimator error.

    ``draws`` is the ``(passing, n_trials)`` integer pair the CI rests on. It replaces
    the old ``pooled`` key, which named the very inflation this estimator removes.
    """
    passing = n_trials = mixed = 0
    for (sc, tid, _rep), vr in trials.items():
        if sc != arm or tid != task_id:
            continue
        s, t = hard_fraction(vr, hard)
        if t == 0:
            continue
        n_trials += 1
        if s == t:
            passing += 1
        elif s > 0:
            mixed += 1
    if n_trials == 0:
        return None
    return {
        "mean": passing / n_trials,
        "ci": _wilson(passing, n_trials),
        "n_trials": n_trials,
        "draws": (passing, n_trials),
        "mixed_trials": mixed,
    }


def fisher_one_sided(a: int, n_a: int, b: int, n_b: int) -> float:
    """One-sided Fisher exact p: P(arm A scores ≤ ``a``) given the observed margins.

    The left tail of the hypergeometric under H0 (both arms share one pass rate), which
    is the exact test for "the weak arm did WORSE than the strong arm" on two columns of
    per-trial pass counts. Exact, integer-only, and defined at the trial counts this
    program can afford — where a normal approximation is not.
    """
    total, succ = n_a + n_b, a + b
    denom = comb(total, n_a)
    if denom == 0:
        return 1.0
    lo = max(0, succ - n_b)
    return sum(comb(succ, k) * comb(total - succ, n_a - k) for k in range(lo, a + 1)) / denom


def empirical_right_tier(stats_by_arm: dict[str, dict], eps: float = EPS) -> tuple[str, bool]:
    """(tier, indeterminate). Cheapest arm within ε AND CI-overlapping the best.

    ``indeterminate`` when the point-estimate and CI-overlap criteria disagree on the
    cheapest adequate TIER (the ε-decision rests on overlapping CIs, FM-10). The
    comparison is by tier, not arm identity, so two arms sharing a tier (``sonnet`` +
    ``sonnet5``) that agree on the verdict are not flagged as a disagreement.

    FLOOR GUARD. "Cheapest tier that does the job" is undefined when NO tier does the
    job. Without the guard, a task every arm fails scores 0.0 everywhere, the cheapest
    arm is trivially within ε of the best, and the row reads ``weak`` — a floored task
    is indistinguishable from one the weak tier genuinely suffices for, and it reads in
    the direction that would license retiring the dear tiers. A floored task is
    therefore ``indeterminate``: the instrument had no purchase on it, which is a
    statement about the task, not about the ladder.
    """
    arms = [a for a in stats_by_arm if arm_tier(a)]
    if not arms:
        return ("indeterminate", True)
    best_arm = max(arms, key=lambda a: stats_by_arm[a]["mean"])
    best_mean = stats_by_arm[best_arm]["mean"]
    best_lo = stats_by_arm[best_arm]["ci"][0]
    if best_mean <= 0.0:
        return ("indeterminate", True)

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
    per-trial pass-rate delta with Wilson CIs. Empty list for banks with no context
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
            "weak_draws": weak["draws"] if weak else None,
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


def control_separation(trials: dict, task_meta: dict[str, dict]) -> dict | None:
    """Read a bank-declared positive control BY ITS OWN RULE, not off the diagonal.

    A bank declares its control in ``scores.toml``'s ``[control]`` table, which
    ``report.py`` attaches to that task's meta as ``{"control": {...}}`` with the arm
    names, α, and the pre-registered repeat count. The rule is a one-sided Fisher exact
    test on the two arms' PER-TRIAL pass counts: the control separates iff the weak arm
    scored strictly worse than the strong arm at ``p ≤ α``.

    WHY NOT THE CONFUSION MATRIX. The control's job is to distinguish "the score does
    not predict the tier" from "the bank had no headroom for a tier to matter". The
    cheapest-adequate statistic cannot do that job — at the control's own recorded v1
    rates it reads ``indeterminate``, which is a correct answer to a different question.
    So the control is scored by this rule and is EXCLUDED from the confusion matrix; it
    would otherwise contribute an off-diagonal cell to a count it is not evidence about.

    WHY FISHER AND NOT DISJOINT CIs. Both were costed by exact enumeration at the
    control's own v1 rates (haiku 2/5, opus5 5/5) under per-trial scoring. Disjoint
    Wilson CIs reproduce with probability 0.078 at repeats=5 and need repeats=15 to
    clear 0.9; the Fisher rule reaches 0.945 at repeats=10. A control that fires less
    than half the time when the ladder really does separate is not a control.
    """
    for tid, meta in task_meta.items():
        spec = meta.get("control")
        if not spec:
            continue
        hard = meta["hard_criteria"]
        weak_arm, strong_arm = spec["weak_arm"], spec["strong_arm"]
        weak = arm_task_stats(trials, tid, weak_arm, hard)
        strong = arm_task_stats(trials, tid, strong_arm, hard)
        if not weak or not strong:
            return {
                "task_id": tid,
                "weak_arm": weak_arm,
                "strong_arm": strong_arm,
                "ran": False,
                "separates": False,
                "reason": "the control did not run on both arms",
            }
        alpha = float(spec.get("alpha", 0.05))
        min_repeats = int(spec.get("min_repeats", 0))
        p = fisher_one_sided(*weak["draws"], *strong["draws"])
        underpowered = min(weak["n_trials"], strong["n_trials"]) < min_repeats
        return {
            "task_id": tid,
            "weak_arm": weak_arm,
            "strong_arm": strong_arm,
            "ran": True,
            "weak_draws": weak["draws"],
            "strong_draws": strong["draws"],
            "p": p,
            "alpha": alpha,
            "min_repeats": min_repeats,
            "underpowered": underpowered,
            "separates": p <= alpha and not underpowered,
            "reason": (
                f"fewer than the pre-registered {min_repeats} repeats per arm"
                if underpowered
                else ""
            ),
        }
    return None


def build_calibration(raw: list[dict], task_meta: dict[str, dict]) -> dict:
    """Top-level: confusion matrix + per-task rows + control + dose-response + Pareto.

    task_meta[task_id] = {"score": float, "hard_criteria": [...]}, optionally with
    ``"control"`` on the one task that is a positive control. Only non-holdout tasks
    that actually ran are included.
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
                "mixed": sum(stats_by_arm[a]["mixed_trials"] for a in stats_by_arm),
                # A control is read by its own rule and never counted on the diagonal.
                "control": bool(meta.get("control")),
                # Context dimension (§7) — None for model-tier banks; surfaced for context banks.
                "context": meta.get("context"),
                "pair": meta.get("pair"),
            }
        )

    # Confusion matrix counts (predicted × empirical), indeterminate as its own column.
    # Predicted rows are only weak/mid/strong — tier_for_score never assigns frontier
    # (the "frontier is never score-assigned" invariant). frontier IS reachable
    # empirically (a fable arm cheapest-adequate), so it is a COLUMN with no predicted row.
    # Control tasks are excluded: they are not rungs of the ladder under test, and the
    # cheapest-adequate statistic is not the question they answer (see control_separation).
    predicted_tiers = ["weak", "mid", "strong"]
    columns = [*TIER_ORDER, "indeterminate"]
    confusion: dict[str, dict[str, int]] = {p: dict.fromkeys(columns, 0) for p in predicted_tiers}
    for r in rows:
        if r["control"]:
            continue
        col = "indeterminate" if r["indeterminate"] else r["empirical"]
        confusion[r["predicted"]][col] += 1

    return {
        "rows": rows,
        "confusion": confusion,
        "control": control_separation(trials, task_meta),
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
    """Per band: mean per-trial pass rate + mean cost for every arm on the ladder.

    A declared control is excluded: this view is a claim about a BAND of the ladder,
    and the control is a task ported from another bank to make a null interpretable,
    not a rung whose score places it in a band under test.
    """
    band_tasks: defaultdict[str, list[str]] = defaultdict(list)
    for tid, meta in task_meta.items():
        if meta.get("control"):
            continue
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


def _render_control(control: dict | None) -> list[str]:
    """The positive control, read by its own rule; empty for banks that declare none."""
    if not control:
        return []
    lines = ["### Positive control (read by its own rule, not the confusion matrix)", ""]
    tid, weak, strong = control["task_id"], control["weak_arm"], control["strong_arm"]
    if not control.get("ran"):
        lines += [
            f"`{tid}`: **did not run on both `{weak}` and `{strong}`** — the control is"
            " absent, so a null on this bank stays uninterpretable and no tier"
            " conclusion is available from any part of the matrix.",
            "",
        ]
        return lines
    wa, wn = control["weak_draws"]
    sa, sn = control["strong_draws"]
    verdict = "SEPARATES" if control["separates"] else "DOES NOT SEPARATE"
    lines += [
        f"| control | {weak} | {strong} | one-sided Fisher p | α | verdict |",
        "|---|---|---|---|---|---|",
        f"| `{tid}` | {wa}/{wn} | {sa}/{sn} | {control['p']:.4f} |"
        f" {control['alpha']:.2f} | **{verdict}** |",
        "",
    ]
    if control.get("underpowered"):
        lines += [
            f"> Underpowered: {control['reason']}. The verdict is forced to DOES NOT"
            " SEPARATE rather than read off an underpowered comparison.",
            "",
        ]
    if not control["separates"]:
        lines += [
            "> **The ladder did not separate on the control.** The instrument or the"
            ' lineup moved; no conclusion of the form "tier X should be dropped" is'
            " available from any part of this matrix, and a null here is not evidence"
            " against the complexity score.",
            "",
        ]
    return lines


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
    if any(r.get("control") for r in rows):
        lines += [
            "> A declared positive control ran and is NOT counted above — it is read by"
            " its own rule (below), because the cheapest-adequate statistic answers a"
            " different question than the one a control is bought to answer.",
            "",
        ]

    lines += _render_control(cal.get("control"))

    # Per-task detail. Arm columns are derived from the arms that actually ran, on the
    # ladder — so a renamed/gated arm (sonnet5, bare-gate) renders, and a 3-arm bank's
    # header stays byte-identical to `haiku | sonnet | opus`.
    lines += ["### Per-task (per-trial pass rate by arm: all hard criteria true)", ""]
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
        if r.get("control"):
            note = "positive control (not counted)"
        cells = " | ".join(cell(a) for a in arm_cols)
        emp = "?" if r["indeterminate"] else r["empirical"]
        lines.append(
            f"| {r['task_id']} | {r['score']:.0f} | {r['predicted']} | {emp} | {cells} | {note} |"
        )
    lines.append("")

    # The estimator's own assumption, checked against the data it just scored. A trial
    # scores one draw because a task's hard criteria come out all-true or all-false; a
    # nonzero count here means they came apart, and ADR-0009 asks to be re-opened.
    mixed = sum(r.get("mixed", 0) for r in rows)
    trials_scored = sum(sum(r["n"].values()) for r in rows)
    lines += [
        f"Mixed-hard trials: **{mixed}/{trials_scored}** (a trial where some hard criteria"
        " passed and others failed). The per-trial estimator treats a cell as one draw;"
        " at 0 that is exact, above 0 it is conservative — see ADR-0009.",
        "",
    ]

    # Dose-response
    dr = cal["dose_response"]
    if dr:
        lines += [
            "### Dose-response (per-trial pass rate × cost per upgrade, by band)",
            "",
        ]
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
