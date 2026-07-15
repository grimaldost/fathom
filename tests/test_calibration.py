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


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
