"""§7/§8 — model-tier calibration analysis over synthetic ledgers (no spawn).

Proves the decision logic before any paid run: the confusion matrix cells, the
indeterminate label when the ε-decision rests on overlapping CIs, and that the
cost-quality Pareto frontier is exactly the non-dominated set (a dominated point is
never flagged) — closing the prior efficiency view's false-Pareto bug.
"""

import sys
import unittest
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from fathom import calibration as cal  # noqa: E402

HARD = ["h1", "h2"]


def _vr(n_true: int) -> dict:
    return {"h1": n_true >= 1, "h2": n_true >= 2}


def _trial(arm: str, task: str, rep: int, n_true: int) -> dict:
    return {
        "kind": "trial",
        "scenario": arm,
        "task_id": task,
        "repeat": rep,
        "status": "completed",
        "config_hash": f"ch-{arm}",
        "verifier_results": _vr(n_true),
    }


def _run(arm: str, task: str, rep: int, cost: float) -> dict:
    return {
        "kind": "run",
        "scenario": arm,
        "task_id": task,
        "repeat": rep,
        "config_hash": f"ch-{arm}",
        "usage": {"input_tokens": 100, "output_tokens": 100},
        "cost_usd_est": cost,
    }


class TestConfusionMatrix(unittest.TestCase):
    def test_diagonal_and_overprovision(self):
        # low(10): all arms ace -> empirical weak == predicted weak (diagonal)
        # mid(45): haiku 0, sonnet/opus ace -> empirical mid == predicted mid
        # high(70): only opus aces -> empirical strong == predicted strong
        # overp(70): all arms ace -> empirical weak, predicted strong (over-provisioned)
        meta = {
            "low": {"score": 10, "hard_criteria": HARD},
            "mid": {"score": 45, "hard_criteria": HARD},
            "high": {"score": 70, "hard_criteria": HARD},
            "overp": {"score": 70, "hard_criteria": HARD},
        }
        raw = []
        for rep in range(5):
            for arm in ("haiku", "sonnet", "opus"):
                raw.append(_trial(arm, "low", rep, 2))
                raw.append(_trial(arm, "overp", rep, 2))
            raw.append(_trial("haiku", "mid", rep, 0))
            raw.append(_trial("sonnet", "mid", rep, 2))
            raw.append(_trial("opus", "mid", rep, 2))
            raw.append(_trial("haiku", "high", rep, 0))
            raw.append(_trial("sonnet", "high", rep, 0))
            raw.append(_trial("opus", "high", rep, 2))
        out = cal.build_calibration(raw, meta)
        conf = out["confusion"]
        self.assertEqual(conf["weak"]["weak"], 1)  # low
        self.assertEqual(conf["mid"]["mid"], 1)  # mid
        self.assertEqual(conf["strong"]["strong"], 1)  # high
        self.assertEqual(conf["strong"]["weak"], 1)  # overp: predicted strong, weak suffices
        by_task = {r["task_id"]: r for r in out["rows"]}
        self.assertEqual(by_task["overp"]["empirical"], "weak")
        self.assertFalse(by_task["overp"]["indeterminate"])

    def test_a_task_no_arm_can_do_reads_indeterminate_not_weak(self):
        """The floor guard. "Cheapest tier that does the job" needs a tier to do it.

        Without it, a task every arm fails scores 0.0 everywhere, the cheapest arm is
        trivially within eps of the best, and the row reads `weak` — a floored task
        becomes indistinguishable from one the weak tier genuinely suffices for, and it
        reads in the direction that would license retiring the dear tiers. Whether the
        floor is the task's difficulty or a broken fixture, the instrument had no
        purchase on it and the row must say so.
        """
        meta = {"floored": {"score": 70, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            for arm in ("haiku", "sonnet", "opus"):
                raw.append(_trial(arm, "floored", rep, 0))
        out = cal.build_calibration(raw, meta)
        row = out["rows"][0]
        self.assertTrue(row["indeterminate"], f"a floored task must not read as a tier: {row}")
        self.assertEqual(row["empirical"], "indeterminate")
        self.assertEqual(out["confusion"]["strong"]["indeterminate"], 1)
        self.assertEqual(out["confusion"]["strong"]["weak"], 0)

    def test_a_partial_pass_is_still_a_real_reading(self):
        """The guard fires only at a true floor, not at "hard but sometimes done"."""
        meta = {"hard-task": {"score": 70, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            raw.append(_trial("haiku", "hard-task", rep, 0))
            raw.append(_trial("sonnet", "hard-task", rep, 0))
            raw.append(_trial("opus", "hard-task", rep, 2))
        out = cal.build_calibration(raw, meta)
        row = out["rows"][0]
        self.assertFalse(row["indeterminate"])
        self.assertEqual(row["empirical"], "strong")

    def test_indeterminate_when_cis_overlap(self):
        # haiku 1/2 each trial (mean .5, wide CI), opus 2/2 (mean 1.0). Point says
        # strong (only opus within eps); CI overlap says haiku might suffice -> ?.
        meta = {"t": {"score": 70, "hard_criteria": HARD}}
        raw = []
        for rep in range(2):
            raw.append(_trial("haiku", "t", rep, 1))
            raw.append(_trial("opus", "t", rep, 2))
        out = cal.build_calibration(raw, meta)
        row = out["rows"][0]
        self.assertTrue(row["indeterminate"], f"expected indeterminate, got {row}")
        self.assertEqual(out["confusion"]["strong"]["indeterminate"], 1)


class TestParetoFrontier(unittest.TestCase):
    def test_dominated_point_not_flagged(self):
        # haiku(q.5,c.1) sonnet(q.9,c.3) opus(q.9,c.5): opus dominated by sonnet.
        meta = {
            "a": {"score": 40, "hard_criteria": HARD},
            "b": {"score": 40, "hard_criteria": HARD},
        }
        raw = []
        # quality: haiku .5, sonnet .9, opus .9  (use 10 tasks-worth via two tasks x reps)
        for rep in range(5):
            raw.append(_trial("haiku", "a", rep, 1))  # .5
            raw.append(_trial("haiku", "b", rep, 1))  # .5
            raw.append(_trial("sonnet", "a", rep, 2))  # 1.0
            raw.append(_trial("sonnet", "b", rep, 1))  # .5  -> mean .75
            raw.append(_trial("opus", "a", rep, 2))  # 1.0
            raw.append(_trial("opus", "b", rep, 1))  # .5  -> mean .75
            raw.append(_run("haiku", "a", rep, 0.05))
            raw.append(_run("haiku", "b", rep, 0.05))
            raw.append(_run("sonnet", "a", rep, 0.15))
            raw.append(_run("sonnet", "b", rep, 0.15))
            raw.append(_run("opus", "a", rep, 0.25))
            raw.append(_run("opus", "b", rep, 0.25))
        out = cal.build_calibration(raw, meta)
        pareto = {p["arm"]: p for p in out["pareto"]}
        # sonnet and opus have equal quality (.75) but opus costs more -> opus dominated
        self.assertAlmostEqual(pareto["sonnet"]["quality"], pareto["opus"]["quality"])
        self.assertLess(pareto["sonnet"]["cost"], pareto["opus"]["cost"])
        self.assertFalse(pareto["opus"]["frontier"], "opus is dominated by sonnet")
        self.assertTrue(pareto["haiku"]["frontier"], "haiku cheapest -> frontier")
        self.assertTrue(pareto["sonnet"]["frontier"], "sonnet best quality at its cost")

    def test_render_smoke(self):
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = [_trial("haiku", "t", 0, 0), _trial("sonnet", "t", 0, 2), _trial("opus", "t", 0, 2)]
        out = cal.build_calibration(raw, meta)
        md = "\n".join(cal.render_calibration(out))
        self.assertIn("Model-Tier Calibration", md)
        self.assertIn("Pareto", md)
        # 3-arm bank per-task header stays byte-identical after the dynamic-column rewrite.
        self.assertIn("| task | score | predicted | empirical | haiku | sonnet | opus | note |", md)
        # The dose-response Δ column names the arm one step down the ladder, not a dollar
        # order — the ladder is tier-ordered and can list a dearer arm above a cheaper one.
        self.assertIn(
            "| band | arm | mean first-attempt pass | mean $/trial | Δ first-attempt vs prev arm |",
            md,
        )
        self.assertNotIn("vs cheaper", md)

    def test_no_rendered_column_calls_a_first_attempt_rate_quality(self):
        """`quality` is the estimand's name, and none of these rates is the estimand.

        The scorecard shows pass rates in three places — the routing table, the
        dose-response and the Pareto frontier — and every one of them is a FIRST-ATTEMPT
        rate. The estimand for a routing decision is post-repair quality, which this bank
        does not compute. Leaving `quality` on any of these columns preserves the exact
        ambiguity that had this module reporting 0.55 against a sibling programme's 0.70
        on one fixture, in the most-read surface the project has.
        """
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = [_trial("haiku", "t", 0, 0), _trial("sonnet", "t", 0, 2), _trial("opus", "t", 0, 2)]
        md = "\n".join(cal.render_calibration(cal.build_calibration(raw, meta)))
        self.assertIn("mean first-attempt pass", md)
        self.assertNotIn("mean quality", md)
        self.assertNotIn("Δquality", md)
        self.assertNotIn("Cost-quality", md)


class TestArmResolution(unittest.TestCase):
    def test_family_token_resolves_renamed_and_effort_arms(self):
        # Every name here is a REAL arm in this repo (scenarios/model-tier/sonnet5.toml,
        # scenarios/model-tier-effort/haiku-xhigh.toml, scenarios/ablation-v2/*).
        self.assertEqual(cal.arm_tier("sonnet5"), "mid")
        self.assertEqual(cal.arm_tier("haiku-xhigh"), "weak")
        self.assertEqual(cal.arm_tier("sonnet-lo-gate"), "mid")
        self.assertEqual(cal.arm_tier("opus"), "strong")
        self.assertEqual(cal.arm_tier("fable"), "frontier")
        self.assertIsNone(cal.arm_tier("bare-gate"))
        self.assertIsNone(cal.arm_tier("orchestrated"))


class TestNewLineupArm(unittest.TestCase):
    def test_renamed_mid_arm_lands_on_the_ladder(self):
        # The 2026-07-01 Sonnet 5 shape: haiku fails, both sonnets and opus ace, so the
        # cheapest adequate tier is mid. Today sonnet5 is silently absent from the view.
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            raw.append(_trial("haiku", "t", rep, 0))
            raw.append(_trial("sonnet", "t", rep, 2))
            raw.append(_trial("sonnet5", "t", rep, 2))
            raw.append(_trial("opus", "t", rep, 2))
        out = cal.build_calibration(raw, meta)
        row = {r["task_id"]: r for r in out["rows"]}["t"]
        self.assertEqual(set(row["means"]), {"haiku", "sonnet", "sonnet5", "opus"})
        self.assertEqual(row["empirical"], "mid")
        md = "\n".join(cal.render_calibration(out))
        # sonnet5 renders on the ladder, between sonnet and opus (cheapest→dearest, ties by name).
        self.assertIn("| haiku | sonnet | sonnet5 | opus | note |", md)

    def test_two_arms_in_one_tier_is_not_indeterminate(self):
        # sonnet5 aces (within ε), opus aces (best), sonnet is 1/2 each trial (wide CI that
        # overlaps opus's lower bound but is NOT within ε). So the within-ε cheapest is
        # sonnet5 and the CI-overlap cheapest is sonnet — DIFFERENT arms, SAME tier (mid).
        # Arm-identity comparison flags a disagreement that does not exist; tier comparison
        # must not, and the verdict is mid.
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            raw.append(_trial("sonnet", "t", rep, 1))  # 0.5, wide CI, ci-overlaps
            raw.append(_trial("sonnet5", "t", rep, 2))  # aces, within ε
            raw.append(_trial("opus", "t", rep, 2))  # aces, best
        out = cal.build_calibration(raw, meta)
        row = out["rows"][0]
        self.assertFalse(row["indeterminate"])
        self.assertEqual(row["empirical"], "mid")


class TestGatedArm(unittest.TestCase):
    def test_untiered_arm_renders_but_takes_no_tier(self):
        # bare-gate carries no family token -> untiered. It must render in every per-arm
        # view yet take no part in the tier verdict (haiku fails, opus aces -> strong).
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            raw.append(_trial("haiku", "t", rep, 0))
            raw.append(_trial("opus", "t", rep, 2))
            raw.append(_trial("bare-gate", "t", rep, 2))
            raw.append(_run("haiku", "t", rep, 0.05))
            raw.append(_run("opus", "t", rep, 0.25))
            raw.append(_run("bare-gate", "t", rep, 0.15))
        out = cal.build_calibration(raw, meta)
        row = out["rows"][0]
        # renders: per-task means + header, Pareto points, dose-response band
        self.assertIn("bare-gate", row["means"])
        md = "\n".join(cal.render_calibration(out))
        self.assertIn("bare-gate", md)
        self.assertIn("bare-gate", {p["arm"] for p in out["pareto"]})
        self.assertIn("bare-gate", out["dose_response"]["mid"])
        # takes no tier: the verdict is decided by the tiered arms alone
        self.assertEqual(row["empirical"], "strong")
        self.assertFalse(row["indeterminate"])
        self.assertIsNone(cal.arm_tier("bare-gate"))

    def test_frontier_arm_gets_a_column_and_no_row(self):
        # fable is empirically cheapest-adequate here -> the empirical tier is frontier.
        # Frontier is never score-assigned (no predicted row) but is reachable empirically
        # (a column). Today the fixed confusion keys make this a KeyError.
        meta = {"t": {"score": 70, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            raw.append(_trial("haiku", "t", rep, 0))
            raw.append(_trial("fable", "t", rep, 2))
        out = cal.build_calibration(raw, meta)
        self.assertEqual(out["confusion"]["strong"]["frontier"], 1)
        self.assertNotIn("frontier", set(out["confusion"]))  # no predicted frontier row
        md = "\n".join(cal.render_calibration(out))
        self.assertIn("frontier", md)  # the rendered matrix carries a frontier column


def _prod_run(arm: str, task: str, rep: int, cost: float) -> dict:
    """A run record shaped like production: NO ``scenario`` field.

    The suite's ``_run`` helper stamps ``scenario`` on the run, which the real cli.py
    RunRecord (cli.py) does NOT — the arm is stamped only on the trial. That extra key
    masks the attribution bug, so the realistic fixture drops it. This is the first
    fixture in either calibration test module that matches how cli.py actually writes a
    ledger (run-before-trial, run without a scenario).
    """
    return {
        "kind": "run",
        "task_id": task,
        "repeat": rep,
        "config_hash": f"ch-{arm}",
        "usage": {"input_tokens": 100, "output_tokens": 100},
        "cost_usd_est": cost,
    }


class TestRunAttribution(unittest.TestCase):
    def test_runs_appended_before_the_trial_record_are_attributed(self):
        # Built the way cli.py actually writes a ledger: a trial's RUN records are appended
        # BEFORE its TRIAL record, and a run carries no `scenario`. A single-pass
        # config_hash→arm map resolves the first repeat's runs against an empty map and
        # orphans them under the raw config_hash, so they never join the cost. Here all the
        # cost sits in the first (orphaned) repeat, so the orphan zeroes the reported $/trial.
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = []
        for rep in range(5):
            cost = 1.0 if rep == 0 else 0.0  # all cost in the first (orphaned) repeat
            raw.append(_prod_run("opus", "t", rep, cost))  # run FIRST, as production does
            raw.append(_trial("opus", "t", rep, 2))  # then the trial record
        trials, runs = cal.parse_ledger(raw)
        # (i) every run attributes to a real arm — no key is a bare config_hash
        self.assertTrue(all(k[0] == "opus" for k in runs), f"orphaned run keys: {list(runs)}")
        # (ii) the Pareto cost is the full mean $/trial (1.0/5), not diluted by the orphan
        out = cal.build_calibration(raw, meta)
        opus = {p["arm"]: p for p in out["pareto"]}["opus"]
        self.assertAlmostEqual(opus["cost"], 0.20)


class TestParseAnomalyWarnings(unittest.TestCase):
    """parse_ledger surfaces the two silent-wrong cost anomalies report.py already warns on."""

    def test_duplicate_completed_trial_warns(self):
        # A resume never re-runs a completed cell, so two completed trial lines for the same
        # (dataset_version, config_hash, task, repeat) mean its runs would be summed twice in
        # the cost path. parse_ledger must warn rather than double-count silently.
        raw = [_trial("opus", "t", 0, 2), _trial("opus", "t", 0, 2)]  # same cell twice
        with self.assertWarnsRegex(UserWarning, "duplicate completed trial"):
            cal.parse_ledger(raw)

    def test_dangling_run_without_a_trial_warns(self):
        # A run whose config_hash appears on no trial line (a trial interrupted mid-write) has
        # its economy silently dropped from the scorecard; parse_ledger must warn once.
        raw = [_prod_run("ghost", "t", 0, 1.0)]  # run with ch-ghost, no matching trial
        with self.assertWarnsRegex(UserWarning, "no trial line"):
            cal.parse_ledger(raw)

    def test_clean_ledger_emits_no_warning(self):
        # A well-formed ledger (one completed trial + its matching run) must not trip either
        # guard — otherwise the warnings are noise on the normal path.
        raw = [_trial("opus", "t", 0, 2), _run("opus", "t", 0, 0.5)]
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any warning becomes an error
            cal.parse_ledger(raw)  # must not raise


class TestPerTrialScoring(unittest.TestCase):
    """ADR-0009: a trial is ONE Bernoulli draw, not one per hard criterion.

    The estimator this replaces pooled criteria across trials, which multiplies the
    CI's ``n`` by k. On the committed ``ledger/model-tier-v1.jsonl`` the hard set came
    out all-true or all-false on 175 of 175 multi-criterion trials, so those extra
    draws were copies — the interval was narrowed by ~sqrt(k) for free, and repeat
    counts were sized against a resolution the run could not buy.
    """

    def test_a_k_criterion_cell_is_n_draws_not_k_times_n(self):
        raw = [_trial("opus", "t", rep, 2) for rep in range(3)]  # 3 trials x 2 criteria
        trials, _ = cal.parse_ledger(raw)
        stats = cal.arm_task_stats(trials, "t", "opus", HARD)
        self.assertEqual(stats["draws"], (3, 3), "the cell must be 3 draws, not 6")
        self.assertEqual(stats["n_trials"], 3)
        self.assertEqual(stats["ci"], cal._wilson(3, 3))
        self.assertNotEqual(stats["ci"], cal._wilson(6, 6), "the CI still pools criteria")

    def test_a_mixed_trial_scores_zero_and_is_counted(self):
        # 1-of-2 hard criteria true is not half a pass: the conjunction is the draw, and
        # the count is recorded so the correlation assumption stays checkable.
        raw = [_trial("opus", "t", 0, 1), _trial("opus", "t", 1, 2)]
        trials, _ = cal.parse_ledger(raw)
        stats = cal.arm_task_stats(trials, "t", "opus", HARD)
        self.assertEqual(stats["draws"], (1, 2))
        self.assertEqual(stats["mean"], 0.5)
        self.assertEqual(stats["mixed_trials"], 1)

    def test_repeats_two_and_three_cannot_resolve_even_a_noiseless_rung(self):
        """The repeat count the design actually needs, re-derived at 1 draw/trial.

        Under the noiseless alternative (the weak arm fails every trial, the mid and
        strong arms pass every trial) a mid-band rung must read ``mid``, determinate.
        Pooled scoring said repeats=2 sufficed. At one draw per trial it does not: 2/2
        and 0/2 have overlapping Wilson intervals, and so do 3/3 and 0/3. Four is the
        first repeat count where a perfect contrast separates at all — which is why the
        pre-registered matrix is bought at 5, not 2.
        """
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        seen = {}
        for repeats in (2, 3, 4, 5):
            raw = []
            for rep in range(repeats):
                raw.append(_trial("haiku", "t", rep, 0))
                raw.append(_trial("sonnet5", "t", rep, 2))
                raw.append(_trial("opus5", "t", rep, 2))
            row = cal.build_calibration(raw, meta)["rows"][0]
            seen[repeats] = (row["empirical"], row["indeterminate"])
        self.assertTrue(seen[2][1], "repeats=2 must read indeterminate")
        self.assertTrue(seen[3][1], "repeats=3 must read indeterminate")
        self.assertEqual(seen[4], ("mid", False))
        self.assertEqual(seen[5], ("mid", False))

    def test_the_committed_model_tier_v1_reading_is_unchanged(self):
        """A new estimator may not rewrite a reading the record already carries.

        model-tier-v1 was read three times at 1/7 on-diagonal with fix-nonlocal-parse
        indeterminate. Because its hard criteria are perfectly correlated, the per-trial
        point estimates are identical to the pooled ones and only the intervals widen —
        so the committed verdict must reproduce exactly. If this fails, the change is
        not a re-estimation, it is a revision of history.
        """
        import json
        import tomllib

        ledger = REPO / "ledger" / "model-tier-v1.jsonl"
        bank_dir = REPO / "tasks" / "model-tier-v1"
        if not ledger.is_file():
            self.skipTest("model-tier-v1 ledger absent")
        raw = [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        with (bank_dir / "scores.toml").open("rb") as fh:
            scores = tomllib.load(fh)["scores"]
        meta = {}
        for task_dir in sorted(bank_dir.iterdir()):
            path = task_dir / "task.toml"
            if not path.is_file():
                continue
            with path.open("rb") as fh:
                doc = tomllib.load(fh)
            if doc["id"] in scores:
                meta[doc["id"]] = {
                    "score": float(scores[doc["id"]]),
                    "hard_criteria": doc["verify"]["hard_criteria"],
                }
        out = cal.build_calibration(raw, meta)
        on_diag = sum(out["confusion"][t][t] for t in ("weak", "mid", "strong"))
        self.assertEqual(on_diag, 1, "the committed 1/7 on-diagonal reading moved")
        rows = {r["task_id"]: r for r in out["rows"]}
        self.assertTrue(rows["fix-nonlocal-parse"]["indeterminate"])
        self.assertEqual(
            {a: round(m, 2) for a, m in rows["fix-nonlocal-parse"]["means"].items()},
            {"haiku": 0.40, "sonnet": 0.60, "sonnet5": 0.80, "opus": 1.00, "opus5": 1.00},
        )
        self.assertEqual(sum(r["mixed"] for r in out["rows"]), 0, "v1 had no mixed trials")


class TestFisherExact(unittest.TestCase):
    def test_known_left_tail_values(self):
        # 2x2 with both arms at n=5. Hypergeometric left tail, computed by hand.
        self.assertAlmostEqual(cal.fisher_one_sided(0, 5, 5, 5), 1 / 252, places=6)
        self.assertAlmostEqual(cal.fisher_one_sided(1, 5, 5, 5), 6 / 252, places=6)
        self.assertAlmostEqual(cal.fisher_one_sided(2, 5, 5, 5), 21 / 252, places=6)
        self.assertAlmostEqual(cal.fisher_one_sided(5, 5, 5, 5), 1.0, places=6)

    def test_the_shipped_control_rate_is_significant_only_from_ten_repeats(self):
        """Why the control's repeat count is 10 and not 5 (issue: coin-flip control).

        At model-tier-v1's own observed rates for the control task the weak arm passes
        ~0.4 of trials and the strong arm ~1.0. The modal draw at repeats=5 is 2/5 vs
        5/5, which the rule does NOT call significant; the modal draw at repeats=10 is
        4/10 vs 10/10, which it does.
        """
        self.assertGreater(cal.fisher_one_sided(2, 5, 5, 5), 0.05)
        self.assertLessEqual(cal.fisher_one_sided(4, 10, 10, 10), 0.05)


class TestPositiveControl(unittest.TestCase):
    CONTROL = {
        "task": "ctl",
        "weak_arm": "haiku",
        "strong_arm": "opus5",
        "alpha": 0.05,
        "min_repeats": 10,
    }

    def _meta(self, **over):
        control = {**self.CONTROL, **over}
        return {"ctl": {"score": 65, "hard_criteria": HARD, "control": control}}

    def _ledger(self, weak_pass: int, strong_pass: int, repeats: int) -> list[dict]:
        raw = []
        for rep in range(repeats):
            raw.append(_trial("haiku", "ctl", rep, 2 if rep < weak_pass else 0))
            raw.append(_trial("opus5", "ctl", rep, 2 if rep < strong_pass else 0))
        return raw

    def test_it_separates_at_the_preregistered_repeats(self):
        out = cal.build_calibration(self._ledger(4, 10, 10), self._meta())
        control = out["control"]
        self.assertTrue(control["separates"])
        self.assertEqual(control["weak_draws"], (4, 10))
        self.assertIn("SEPARATES", "\n".join(cal.render_calibration(out)))

    def test_a_short_run_is_underpowered_not_a_null(self):
        # 2/5 vs 5/5 is the modal v1 draw at repeats=5. Reading it as "does not
        # separate" would license the very conclusion the control exists to block, so
        # the verdict names the missing repeats instead.
        out = cal.build_calibration(self._ledger(2, 5, 5), self._meta())
        self.assertFalse(out["control"]["separates"])
        self.assertTrue(out["control"]["underpowered"])
        self.assertIn("Underpowered", "\n".join(cal.render_calibration(out)))

    def test_a_genuine_null_blocks_every_tier_conclusion(self):
        out = cal.build_calibration(self._ledger(10, 10, 10), self._meta())
        self.assertFalse(out["control"]["separates"])
        self.assertFalse(out["control"]["underpowered"])
        self.assertIn("did not separate", "\n".join(cal.render_calibration(out)))

    def test_the_control_is_kept_out_of_the_confusion_matrix(self):
        """It is read by its own rule, so it may not also move the on-diagonal count."""
        meta = self._meta()
        meta["rung"] = {"score": 45, "hard_criteria": HARD}
        raw = self._ledger(4, 10, 10)
        for rep in range(5):
            raw.append(_trial("haiku", "rung", rep, 0))
            raw.append(_trial("sonnet5", "rung", rep, 2))
            raw.append(_trial("opus5", "rung", rep, 2))
        out = cal.build_calibration(raw, meta)
        total = sum(sum(row.values()) for row in out["confusion"].values())
        self.assertEqual(total, 1, "only the rung may be counted")
        self.assertEqual(out["confusion"]["mid"]["mid"], 1)
        self.assertIn("ctl", {r["task_id"] for r in out["rows"]})
        self.assertNotIn("ctl", out["dose_response"].get("strong", {}))
        self.assertIn("positive control", "\n".join(cal.render_calibration(out)))

    def test_a_control_that_never_ran_is_reported_as_absent(self):
        out = cal.build_calibration([_trial("haiku", "ctl", 0, 0)], self._meta())
        self.assertFalse(out["control"]["ran"])
        self.assertIn("did not run", "\n".join(cal.render_calibration(out)))

    def test_a_bank_without_a_control_declares_none(self):
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = [_trial("opus", "t", rep, 2) for rep in range(3)]
        out = cal.build_calibration(raw, meta)
        self.assertIsNone(out["control"])
        self.assertNotIn("Positive control", "\n".join(cal.render_calibration(out)))


# ------------------------------------------------------------------------- routing


def _routing_trial(arm: str, task: str, rep: int, *, passes: bool, gate_red: bool) -> dict:
    """A trial that also carries the gate signal, so failures can be classified."""
    rec = _trial(arm, task, rep, 2 if passes else 0)
    rec["verifier_results"]["no_regression"] = not gate_red
    return rec


def _rung(task: str, score: float, reduced: str, passes: dict, costs: dict, *, gate_split=2):
    """(raw records, meta entry) for one rung at five repeats per arm.

    `passes[arm]` is how many of the five repeats pass; of the failures, every
    `gate_split`-th one is made visible to the gate so both failure modes occur.
    """
    raw = []
    for arm, k in passes.items():
        for rep in range(5):
            ok = rep < k
            raw.append(_run(arm, task, rep, costs[arm]))
            raw.append(
                _routing_trial(
                    arm, task, rep, passes=ok, gate_red=(not ok) and rep % gate_split == 0
                )
            )
    meta = {
        "score": score,
        "hard_criteria": HARD,
        "reduced": {"prediction": reduced},
        "genre": "bugfix",
        "analysis": {"tau": 0.7, "alpha": 0.05, "escalation_cost_multiplier": 1.0},
    }
    return raw, meta


COSTS = {"haiku": 0.02, "sonnet": 0.12, "opus": 0.40}


class TestNeededTier(unittest.TestCase):
    """The ground truth: the cheapest tier that clears the adequacy bar."""

    @staticmethod
    def _stats(rates: dict, n: int = 5) -> dict:
        return {
            arm: {"mean": k / n, "ci": cal._wilson(k, n), "draws": (k, n), "n_trials": n}
            for arm, k in rates.items()
        }

    def test_the_cheapest_tier_that_clears_the_bar_is_the_one_returned(self):
        tier, _ = cal.needed_tier(self._stats({"haiku": 1, "sonnet": 4, "opus": 5}))
        self.assertEqual(tier, "mid")

    def test_a_task_the_weak_tier_aces_reads_weak_rather_than_being_dropped(self):
        """The screen's defect, inverted into a test.

        A rung the weak tier passes every time used to be DROPPED as saturated. It is
        the single most informative observation for the cost question — a mechanism
        that routed it dear paid for capacity it did not need — so it must survive as a
        reading.
        """
        tier, robust = cal.needed_tier(self._stats({"haiku": 5, "sonnet": 5, "opus": 5}))
        self.assertEqual(tier, "weak")
        self.assertFalse(robust, "five perfect repeats is still not a robust reading")

    def test_a_task_no_tier_clears_is_indeterminate_not_weak(self):
        tier, _ = cal.needed_tier(self._stats({"haiku": 0, "sonnet": 1, "opus": 2}))
        self.assertEqual(tier, "indeterminate")

    def test_robustness_needs_ten_repeats_and_says_so(self):
        """At five repeats nothing is robust; at ten a perfect record is."""
        _, at_five = cal.needed_tier(self._stats({"haiku": 5, "sonnet": 5, "opus": 5}, 5))
        _, at_ten = cal.needed_tier(
            {
                "haiku": {"mean": 1.0, "ci": cal._wilson(10, 10), "draws": (10, 10)},
                "opus": {"mean": 1.0, "ci": cal._wilson(10, 10), "draws": (10, 10)},
            }
        )
        self.assertFalse(at_five)
        self.assertTrue(at_ten)

    def test_it_beats_the_relative_statistic_on_a_realistic_rung(self):
        """Why the primary changed, demonstrated rather than asserted.

        The relative statistic asks which tier is indistinguishable from the best and
        answers `indeterminate` on an ordinary noisy rung at buyable repeat counts. The
        absolute bar answers the routing question and reads a tier.
        """
        stats = self._stats({"haiku": 1, "sonnet": 4, "opus": 5})
        _, indeterminate = cal.empirical_right_tier(stats)
        tier, _ = cal.needed_tier(stats)
        self.assertTrue(indeterminate, "the relative statistic used to be determinate here")
        self.assertEqual(tier, "mid")


class TestFailureMode(unittest.TestCase):
    """A failure's mode is a cost term, so it is counted and not just totalled."""

    def test_gate_caught_and_silent_failures_are_counted_separately(self):
        raw, meta = _rung("t", 45, "weak", {"haiku": 1}, COSTS)
        trials, _ = cal.parse_ledger(raw)
        stats = cal.arm_task_stats(trials, "t", "haiku", HARD)
        self.assertEqual(stats["draws"], (1, 5))
        self.assertEqual(stats["gate_caught"] + stats["silent"], 4)
        self.assertEqual(stats["gate_caught"], 2)
        self.assertEqual(stats["silent"], 2)

    def test_a_failure_the_shipped_suite_never_sees_is_silent(self):
        vr = {"h1": False, "h2": False, "no_regression": True}
        self.assertEqual(cal.trial_outcome(vr, HARD), "silent")

    def test_a_failure_the_shipped_suite_catches_is_gate_caught(self):
        vr = {"h1": False, "h2": False, "no_regression": False}
        self.assertEqual(cal.trial_outcome(vr, HARD), "gate_caught")


class TestMechanismCosts(unittest.TestCase):
    """C(m) = execution + retry, with the retry term priced off gate-caught failures."""

    def _bank(self):
        raw, meta = [], {}
        rungs = [
            # cheap task the weak tier aces; the rubric routes it dear
            ("cheap", 70.0, "weak", {"haiku": 5, "sonnet": 5, "opus": 5}),
            # hard task only the strong tier does; the reduced model routes it cheap
            ("hard", 40.0, "weak", {"haiku": 0, "sonnet": 1, "opus": 5}),
        ]
        for task, score, reduced, passes in rungs:
            r, m = _rung(task, score, reduced, passes, COSTS)
            raw.extend(r)
            meta[task] = m
        return raw, meta

    def test_the_oracle_floor_is_never_beaten_on_first_attempt_pass_rate(self):
        out = cal.build_calibration(*self._bank())
        by = {m["mechanism"]: m for m in out["mechanisms"]}
        best = max(m["first_attempt_pass_rate"] for m in out["mechanisms"])
        self.assertAlmostEqual(by["oracle"]["first_attempt_pass_rate"], best, places=6)

    def test_no_mechanism_reports_a_field_called_quality(self):
        """The rename is a contract, not a preference.

        `quality` meant two things in one week — this module's first-attempt rate and
        the routing programme's post-repair rate — and the two were found disagreeing
        (0.55 against 0.70) on the same fixture. Both were right. A field name that can
        carry either meaning across a programme boundary is the defect; this test keeps
        it from coming back under the old name.
        """
        out = cal.build_calibration(*self._bank())
        for m in out["mechanisms"]:
            with self.subTest(mechanism=m["mechanism"]):
                self.assertNotIn("quality", m)
                self.assertIn("first_attempt_pass_rate", m)

    def test_the_exported_facts_bound_the_post_repair_estimand(self):
        """This module exports facts; the consuming analysis owns the estimand.

        Post-repair quality cannot be below the first-attempt rate (repair only ever
        adds) and cannot exceed `1 - escape_rate` (a silent failure is never repaired,
        because nothing knows to try). Both bounds must be computable from what the
        artifact exports, or the consumer has to guess.
        """
        out = cal.build_calibration(*self._bank())
        for m in out["mechanisms"]:
            with self.subTest(mechanism=m["mechanism"]):
                lower = m["first_attempt_pass_rate"]
                upper = 1.0 - m["escape_rate"]
                self.assertLessEqual(lower, upper + 1e-9)

    def test_a_mechanism_that_over_provisions_costs_more(self):
        out = cal.build_calibration(*self._bank())
        by = {m["mechanism"]: m for m in out["mechanisms"]}
        self.assertGreater(
            by["always-strong"]["total_cost_usd"], by["always-weak"]["total_cost_usd"]
        )

    def test_the_retry_term_uses_gate_caught_failures_only(self):
        """A silent failure buys an escape, not a repair loop.

        Summing the two would let a mechanism that fails invisibly look cheaper than
        one that fails loudly, which is the wrong way round: the invisible failure is
        the worse outcome.
        """
        out = cal.build_calibration(*self._bank())
        by = {m["mechanism"]: m for m in out["mechanisms"]}
        self.assertGreater(by["always-weak"]["escape_rate"], 0.0)
        self.assertGreater(by["always-weak"]["retry_cost_usd"], 0.0)
        # The dearest tier passes everything here, so it has neither term.
        self.assertEqual(by["always-strong"]["retry_cost_usd"], 0.0)
        self.assertEqual(by["always-strong"]["escape_rate"], 0.0)

    def test_decision_cost_is_null_and_not_zero(self):
        """`unmeasured` is never written as `0` — it would make the totals look final."""
        out = cal.build_calibration(*self._bank())
        for m in out["mechanisms"]:
            self.assertIsNone(m["decision_cost_usd"], m["mechanism"])
        self.assertIn("not measured", "\n".join(cal.render_calibration(out)))


class TestDiscordanceAnalysis(unittest.TestCase):
    """The two task-level mechanisms, compared only where they route differently."""

    def _bank(self, n_discordant: int):
        raw, meta = [], {}
        for i in range(n_discordant):
            # points says strong (score 70), reduced says weak; the truth is weak, so
            # the reduced mechanism routes right and cheaper on every one of them.
            r, m = _rung(f"d{i}", 70.0, "weak", {"haiku": 5, "sonnet": 5, "opus": 5}, COSTS)
            raw.extend(r)
            meta[f"d{i}"] = m
        r, m = _rung("c0", 40.0, "mid", {"haiku": 0, "sonnet": 5, "opus": 5}, COSTS)
        raw.extend(r)
        meta["c0"] = m
        return raw, meta

    def test_only_discordant_rungs_enter_the_comparison(self):
        out = cal.build_calibration(*self._bank(3))
        d = out["discordance"]
        self.assertEqual(sorted(d["discordant_tasks"]), ["d0", "d1", "d2"])
        self.assertNotIn("c0", d["discordant_tasks"])

    def test_too_few_discordant_rungs_reports_underpowered_not_a_null(self):
        """The arithmetic that sank the first bank.

        With K discordant rungs the smallest attainable one-sided p is 2**-K. At K=4
        that is 0.0625, above alpha, so NO result is reachable however the trials fall.
        That must read as "no test", never as "no difference".
        """
        out = cal.build_calibration(*self._bank(4))
        d = out["discordance"]
        self.assertTrue(d["underpowered"])
        self.assertLess(0.05, 2 ** -d["n_informative"])
        rendered = "\n".join(cal.render_calibration(out))
        self.assertIn("Underpowered", rendered)
        # No verdict line is emitted at all — the reader is told a test was not run,
        # rather than being handed a number that looks like a null result.
        self.assertNotIn("Points right on", rendered)
        # And the cost comparison, which does not depend on the sign test, still reads.
        self.assertIn("Paired cost difference", rendered)

    def test_enough_discordant_rungs_produce_a_verdict(self):
        out = cal.build_calibration(*self._bank(8))
        d = out["discordance"]
        self.assertFalse(d["underpowered"])
        self.assertEqual(d["reduced_right"], 8)
        self.assertEqual(d["points_right"], 0)
        self.assertLessEqual(d["sign_p"], 0.05)

    def test_the_cost_delta_is_reported_in_dollars_and_signed_toward_the_dearer(self):
        out = cal.build_calibration(*self._bank(8))
        d = out["discordance"]
        # points routes these to strong ($0.40), reduced to weak ($0.02).
        self.assertAlmostEqual(d["cost_delta_points_minus_reduced"], 0.38, places=6)
        self.assertLessEqual(d["cost_delta_p"], 0.05)


class TestRoutingSubstrate(unittest.TestCase):
    """The artifact a separate programme consumes; its schema is the coordination surface."""

    def _bank(self):
        raw, meta = [], {}
        for task, score, reduced, passes in (
            ("a", 20.0, "weak", {"haiku": 5, "sonnet": 5, "opus": 5}),
            ("b", 60.0, "mid", {"haiku": 0, "sonnet": 4, "opus": 5}),
        ):
            r, m = _rung(task, score, reduced, passes, COSTS)
            raw.extend(r)
            meta[task] = m
        return raw, meta

    def test_every_row_carries_what_a_mechanism_comparison_needs(self):
        raw, meta = self._bank()
        out = cal.build_calibration(raw, meta)
        sub = cal.routing_substrate(out, meta, out["analysis_params"])
        self.assertEqual(len(sub["tasks"]), 2)
        for row in sub["tasks"]:
            with self.subTest(task=row["task_id"]):
                for field in (
                    "rubric_score",
                    "genre",
                    "tier_points",
                    "tier_reduced",
                    "discordant",
                    "cheapest_adequate_tier",
                    "cheapest_adequate_robust",
                    "per_tier",
                ):
                    self.assertIn(field, row)
                for tier in ("weak", "mid", "strong"):
                    cell = row["per_tier"][tier]
                    # The RAW facts, per tier. The consuming analysis derives the
                    # post-repair estimand from these; it must never have to derive a
                    # count, so `failures` is stated as well as its two components.
                    for field in (
                        "trials",
                        "passing",
                        "failures",
                        "pass_rate",
                        "ci",
                        "gate_caught_failures",
                        "silent_failures",
                        "mean_cost_usd",
                    ):
                        self.assertIn(field, cell)
                    self.assertEqual(
                        cell["failures"],
                        cell["gate_caught_failures"] + cell["silent_failures"],
                    )
                    self.assertEqual(cell["passing"] + cell["failures"], cell["trials"])

    def test_a_renamed_field_bumps_the_schema_version(self):
        """A consumer pinned to schema 1 must fail loudly, not read a missing key.

        `mechanisms[].quality` became `first_attempt_pass_rate` in schema 2. Silently
        keeping the version would let a pinned consumer see the key as absent and treat
        it as absent DATA, which is the same class of error as the rename itself.
        """
        raw, meta = self._bank()
        out = cal.build_calibration(raw, meta)
        sub = cal.routing_substrate(out, meta, out["analysis_params"])
        self.assertEqual(sub["schema_version"], "2")

    def test_decision_cost_survives_serialisation_as_null(self):
        """The contract the routing programme pinned: null, never 0, through JSON."""
        import json

        raw, meta = self._bank()
        out = cal.build_calibration(raw, meta)
        sub = cal.routing_substrate(out, meta, out["analysis_params"])
        round_tripped = json.loads(json.dumps(sub))
        for m in round_tripped["mechanisms"]:
            with self.subTest(mechanism=m["mechanism"]):
                self.assertIsNone(m["decision_cost_usd"])
                self.assertNotEqual(m["decision_cost_usd"], 0)

    def test_it_records_the_config_hash_behind_every_arm(self):
        """Cost is aggregated per arm for reading, but identity is the config hash."""
        raw, meta = self._bank()
        out = cal.build_calibration(raw, meta)
        sub = cal.routing_substrate(out, meta, out["analysis_params"])
        self.assertEqual(sub["arm_config_hashes"]["haiku"], ["ch-haiku"])

    def test_an_arm_under_two_config_hashes_warns_rather_than_averaging_silently(self):
        """Two configurations under one label is the failure the owner named."""
        raw, meta = self._bank()
        forked = dict(raw[1])
        forked["config_hash"] = "ch-haiku-v2"
        forked["repeat"] = 99
        raw.append(forked)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cal.build_calibration(raw, meta)
        self.assertTrue(any("config hashes" in str(w.message) for w in caught))


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
