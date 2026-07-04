"""§7 — context-size calibration view over a synthetic ledger (no spawn).

Proves the context dimension before any paid run: that the `[context]` tag is surfaced
into the calibration rows, that the per-`pair`-slug right-tier rises from weak (small)
to strong (large) when large context drags the weak model down, that a negative-control
pair shows no shift, and that the section heading switches to `## Context-Size
Calibration` (FM-B / FM-N3 / §7 acceptance).
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


# A bank with two matched pairs. `alpha`: small is weak-passable (all arms ace), large
# drags the weak (and mid) model to zero while opus still aces -> right-tier weak→strong.
# `neg` (negative control): both members weak-passable -> no shift.
META = {
    "alpha-small": {"score": 40, "hard_criteria": HARD, "context": "small", "pair": "alpha"},
    "alpha-large": {"score": 40, "hard_criteria": HARD, "context": "large", "pair": "alpha"},
    "neg-small": {"score": 20, "hard_criteria": HARD, "context": "small", "pair": "neg"},
    "neg-large": {"score": 20, "hard_criteria": HARD, "context": "large", "pair": "neg"},
}


def _ledger() -> list[dict]:
    raw: list[dict] = []
    for rep in range(5):
        # alpha-small: every arm aces -> empirical weak
        for arm in ("haiku", "sonnet", "opus"):
            raw.append(_trial(arm, "alpha-small", rep, 2))
        # alpha-large: haiku/sonnet fail, opus aces -> empirical strong
        raw.append(_trial("haiku", "alpha-large", rep, 0))
        raw.append(_trial("sonnet", "alpha-large", rep, 0))
        raw.append(_trial("opus", "alpha-large", rep, 2))
        # negative control: both members aced by every arm -> no shift
        for tid in ("neg-small", "neg-large"):
            for arm in ("haiku", "sonnet", "opus"):
                raw.append(_trial(arm, tid, rep, 2))
    return raw


class TestContextView(unittest.TestCase):
    def test_context_surfaced_into_rows(self):
        out = cal.build_calibration(_ledger(), META)
        by_task = {r["task_id"]: r for r in out["rows"]}
        self.assertEqual(by_task["alpha-small"]["context"], "small")
        self.assertEqual(by_task["alpha-large"]["context"], "large")
        self.assertEqual(by_task["alpha-large"]["pair"], "alpha")

    def test_pair_right_tier_rises_weak_to_strong(self):
        out = cal.build_calibration(_ledger(), META)
        pairs = {p["pair"]: p for p in out["pairs"]}
        alpha = pairs["alpha"]
        self.assertEqual(alpha["small"]["empirical"], "weak")
        self.assertFalse(alpha["small"]["indeterminate"])
        self.assertEqual(alpha["large"]["empirical"], "strong")
        self.assertFalse(alpha["large"]["indeterminate"])
        # weak model's hard-fraction collapses small→large (the volume signal)
        self.assertAlmostEqual(alpha["small"]["weak_mean"], 1.0)
        self.assertAlmostEqual(alpha["large"]["weak_mean"], 0.0)
        self.assertAlmostEqual(alpha["weak_delta"], -1.0)

    def test_negative_control_shows_no_shift(self):
        out = cal.build_calibration(_ledger(), META)
        neg = {p["pair"]: p for p in out["pairs"]}["neg"]
        self.assertEqual(neg["small"]["empirical"], "weak")
        self.assertEqual(neg["large"]["empirical"], "weak")
        self.assertAlmostEqual(neg["weak_delta"], 0.0)

    def test_render_uses_context_heading_and_shift_row(self):
        out = cal.build_calibration(_ledger(), META)
        md = "\n".join(cal.render_calibration(out, heading="## Context-Size Calibration"))
        self.assertIn("## Context-Size Calibration", md)
        self.assertNotIn("## Model-Tier Calibration", md)
        self.assertIn("per-pair small→large right-tier shift", md)
        # the alpha pair's rising shift is rendered
        self.assertIn("weak→strong", md)

    def test_model_tier_bank_unaffected(self):
        # No context tags -> empty pairs, default heading, no context section.
        meta = {"t": {"score": 45, "hard_criteria": HARD}}
        raw = [_trial("haiku", "t", 0, 0), _trial("sonnet", "t", 0, 2), _trial("opus", "t", 0, 2)]
        out = cal.build_calibration(raw, meta)
        self.assertEqual(out["pairs"], [])
        md = "\n".join(cal.render_calibration(out))
        self.assertIn("## Model-Tier Calibration", md)
        self.assertNotIn("Context-Size", md)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
