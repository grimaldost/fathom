"""§7/§8 — model-tier calibration analysis over synthetic ledgers (no spawn).

Proves the decision logic before any paid run: the confusion matrix cells, the
indeterminate label when the ε-decision rests on overlapping CIs, and that the
cost-quality Pareto frontier is exactly the non-dominated set (a dominated point is
never flagged) — closing the prior efficiency view's false-Pareto bug.
"""

import sys
import unittest
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


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
