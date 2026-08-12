"""Integrity of the routing-decision-v1 bank and its pre-registration.

The briefs in this bank are COPIES of another bank's tasks, and the study's value
depends on the join being exact — a brief that drifted from its source would still
join on the id and would silently be measuring two different tasks. These tests are
what stands between that and a wrong answer nobody can see.

They also pin the pre-registered scope (the arm grid, the deciding tiers, the block
sizes), because a design kept only in prose is a design that drifts.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from fathom import routing as r

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "tasks" / "routing-decision-v1"
SCENARIOS = ROOT / "scenarios" / "routing-decision"

PROVENANCE = tomllib.loads((BANK / "provenance.toml").read_text(encoding="utf-8"))
BLOCKS = ("route-1-mechanical", "route-1-review", "route-1-ledger", "route-9-mixed")


def _manifest(block: str) -> list[str]:
    path = BANK / block / "fixtures" / "briefs" / "manifest.json"
    return sorted(json.loads(path.read_text(encoding="utf-8"))["brief_ids"])


class TestProvenance:
    """Every brief is accounted for, in both directions."""

    def test_every_brief_file_has_a_provenance_entry(self):
        recorded = set(PROVENANCE["briefs"])
        for block in BLOCKS:
            for brief in _manifest(block):
                assert brief in recorded, f"{block}/{brief} has no provenance entry"

    def test_every_provenance_entry_is_used_by_a_block(self):
        used = {b for block in BLOCKS for b in _manifest(block)}
        assert set(PROVENANCE["briefs"]) == used

    def test_recorded_score_maps_to_the_recorded_predicted_tier(self):
        """The pinned thresholds are applied, not assumed.

        If a threshold moves in models.toml, this bank's recorded predictions do not
        silently move with it — the mismatch surfaces here and the change becomes a
        visible edit rather than a quiet re-interpretation of an already-bought run.
        """
        bands = PROVENANCE["thresholds"]
        for brief, meta in PROVENANCE["briefs"].items():
            score = meta["rubric_score"]
            low, high = bands[meta["predicted_tier"]]
            assert low <= score <= high, f"{brief}: score {score} is outside its recorded band"

    def test_briefs_are_non_empty(self):
        for block in BLOCKS:
            for brief in _manifest(block):
                body = (BANK / block / "fixtures" / "briefs" / f"{brief}.md").read_text(
                    encoding="utf-8"
                )
                assert body.strip(), f"{block}/{brief} is empty"

    def test_the_sealed_holdout_of_the_sibling_bank_is_not_sampled(self):
        """`fix-quota-rollup` stays sealed here too — no mechanism is scored on it."""
        assert "fix-quota-rollup" not in PROVENANCE["briefs"]


class TestShapeAndScoreCoverage:
    """The design asks the briefs to span real dispatch shapes and the score range."""

    def test_every_required_dispatch_shape_is_present(self):
        required = {"authoring", "refactor", "debugging", "data", "review", "planning"}
        present = {meta["shape"] for meta in PROVENANCE["briefs"].values()}
        assert required <= present, f"missing shapes: {sorted(required - present)}"

    def test_the_score_range_is_spanned_across_at_least_two_bands(self):
        scores = [m["rubric_score"] for m in PROVENANCE["briefs"].values()]
        assert min(scores) <= 25, "no weak-band brief — the cheap end is unrepresented"
        assert max(scores) >= 56, "no strong-band brief — the dear end is unrepresented"

    def test_the_recorded_band_shortfall_matches_the_roster(self):
        """The weak band holds one brief. Recorded as a limit, so it cannot be forgotten.

        This asserts the SHORTFALL, not its absence: if a later edit adds weak-band
        briefs, this test fails and the coverage note in provenance.toml has to be
        rewritten rather than left claiming a limit that no longer applies.
        """
        counts = {"weak": 0, "mid": 0, "strong": 0}
        for meta in PROVENANCE["briefs"].values():
            counts[meta["predicted_tier"]] += 1
        recorded = PROVENANCE["coverage"]
        assert counts["weak"] == recorded["weak_band_briefs"]
        assert counts["mid"] == recorded["mid_band_briefs"]
        assert counts["strong"] == recorded["strong_band_briefs"]


class TestBlockSizes:
    """The K=1 / K=9 split is what separates fixed decision cost from marginal."""

    def test_the_single_brief_blocks_hold_exactly_one_brief(self):
        for block in ("route-1-mechanical", "route-1-review", "route-1-ledger"):
            assert len(_manifest(block)) == 1

    def test_the_batch_block_holds_every_brief(self):
        assert len(_manifest("route-9-mixed")) == len(PROVENANCE["briefs"])

    def test_every_single_brief_block_also_appears_in_the_batch(self):
        """Otherwise the two-point cost fit compares different work, not different K."""
        batch = set(_manifest("route-9-mixed"))
        for block in ("route-1-mechanical", "route-1-review", "route-1-ledger"):
            assert set(_manifest(block)) <= batch


class TestVerifierContract:
    """Well-formedness gates; the routing record does not."""

    def test_hard_criteria_are_well_formedness_only(self):
        for block in BLOCKS:
            task = tomllib.loads((BANK / block / "task.toml").read_text(encoding="utf-8"))
            hard = task["verify"]["hard_criteria"]
            assert hard == list(r.HARD_WELL_FORMEDNESS)

    def test_no_chose_criterion_is_ever_hard(self):
        """A `chose__` bit is a RECORD of a decision, not a grade of one.

        Promoting one to a hard criterion would install an answer key that does not
        exist yet, and would convert this bank from a cost measurement into an accuracy
        claim the substrate cannot back.
        """
        for block in BLOCKS:
            task = tomllib.loads((BANK / block / "task.toml").read_text(encoding="utf-8"))
            assert not any(c.startswith("chose__") for c in task["verify"]["hard_criteria"])

    def test_the_reference_solution_is_well_formed_for_its_block(self):
        for block in BLOCKS:
            routes = json.loads(
                (BANK / block / "solution" / "routing.json").read_text(encoding="utf-8")
            )["routes"]
            assert sorted(routes) == _manifest(block)
            assert all(tier in r.TIERS for tier in routes.values())

    def test_the_verifiers_hard_list_matches_the_analysis_constant(self):
        """The bank verifier is stdlib-only and cannot import fathom, so the list is
        stated twice. This is the check that keeps the two copies the same one."""
        import sys

        sys.path.insert(0, str(BANK))
        import routingverify as rv  # noqa: PLC0415

        assert tuple(rv.HARD) == r.HARD_WELL_FORMEDNESS

    def test_a_round_trip_through_the_criteria_channel_preserves_the_routing(self):
        """The ledger only carries flat booleans, so this is the whole return path."""
        import sys

        sys.path.insert(0, str(BANK))
        import routingverify as rv  # noqa: PLC0415

        for block in BLOCKS:
            briefs = _manifest(block)
            criteria = rv.score(BANK / block / "solution", briefs)
            recovered = r.routes_from_criteria(criteria)
            original = json.loads(
                (BANK / block / "solution" / "routing.json").read_text(encoding="utf-8")
            )["routes"]
            assert recovered == original


class TestArmGrid:
    """The pre-registered grid: three mechanisms crossed with three deciding tiers."""

    MECHANISMS = ("none", "rubric", "shortcuts")
    TIERS = {"weak": "claude-haiku-4-5", "mid": "claude-sonnet-5", "strong": "claude-opus-5"}

    def test_every_cell_of_the_grid_exists(self):
        found = {p.stem for p in SCENARIOS.glob("*.toml")}
        expected = {f"{m}-{t}" for m in self.MECHANISMS for t in self.TIERS}
        assert found == expected

    def test_each_arm_names_the_model_its_tier_claims(self):
        for mech in self.MECHANISMS:
            for tier, model in self.TIERS.items():
                cfg = tomllib.loads((SCENARIOS / f"{mech}-{tier}.toml").read_text(encoding="utf-8"))
                assert cfg["model"] == model, f"{mech}-{tier} names {cfg['model']}"

    def test_arms_differ_only_by_model_and_injected_policy(self):
        """Anything else differing would confound the mechanism axis with a config axis."""
        seen = set()
        for path in SCENARIOS.glob("*.toml"):
            cfg = tomllib.loads(path.read_text(encoding="utf-8"))
            seen.add(
                (
                    cfg["adapter"],
                    cfg["strategy"],
                    cfg["effort"],
                    tuple(cfg["tools"]["allowed"]),
                    cfg["tools"]["source"],
                    cfg["limits"]["trial_timeout_s"],
                )
            )
        assert len(seen) == 1, f"arms differ on a confounding axis: {seen}"

    def test_the_control_arm_injects_nothing(self):
        for tier in self.TIERS:
            cfg = tomllib.loads((SCENARIOS / f"none-{tier}.toml").read_text(encoding="utf-8"))
            assert "context" not in cfg

    def test_both_treatment_arms_inject_their_own_policy(self):
        for mech in ("rubric", "shortcuts"):
            for tier in self.TIERS:
                cfg = tomllib.loads((SCENARIOS / f"{mech}-{tier}.toml").read_text(encoding="utf-8"))
                asset = SCENARIOS / cfg["context"]["inject"]
                assert asset.is_file(), f"{mech}-{tier} injects a missing asset"
                assert asset.stem == mech

    def test_the_rubric_asset_is_materially_larger_than_the_shortcuts_asset(self):
        """The size gap IS the hypothesis, so it is asserted rather than assumed.

        If a future edit shrinks the rubric copy or inflates the shortcuts card, the
        decision-cost contrast this study is built on quietly weakens; this fails first.
        """
        rubric = (SCENARIOS / "assets" / "rubric.md").read_text(encoding="utf-8")
        shortcuts = (SCENARIOS / "assets" / "shortcuts.md").read_text(encoding="utf-8")
        assert len(rubric.split()) > 5 * len(shortcuts.split())

    def test_the_shortcuts_card_carries_no_scoring_arithmetic(self):
        """`shortcuts` is defined by the absence of a score, so that is enforced."""
        body = (SCENARIOS / "assets" / "shortcuts.md").read_text(encoding="utf-8").lower()
        for banned in ("+5", "+10", "base 30", "total:", "add the"):
            assert banned not in body, f"shortcuts card leaked arithmetic: {banned!r}"


@pytest.mark.parametrize("block", BLOCKS)
def test_the_gate_is_green_on_the_untouched_fixture(block):
    """fathom's validation triad needs this, and a red baseline would mask a real red."""
    import subprocess

    proc = subprocess.run(
        ["python", "gate.py"],
        cwd=BANK / block / "fixtures",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
