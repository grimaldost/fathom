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
        self.assertIn("| band | arm | mean quality | mean $/trial | Δquality vs prev arm |", md)
        self.assertNotIn("vs cheaper", md)


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


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
