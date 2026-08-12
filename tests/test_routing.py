"""Tests for the routing-mechanism net-value composition.

The composition is the part of this study that is COMPUTED rather than bought, which
makes it the part where a silent error is cheapest to make and most expensive to
believe. So the arithmetic is pinned against hand-worked examples, and the refusals
(no invented ground truth, no cache-blind cost, no quality traded for cost) are
asserted as behaviour rather than described in prose.
"""

from __future__ import annotations

import math

import pytest

from fathom import routing as r


def _outcome(
    task_id: str = "t",
    score: int = 40,
    *,
    pass_rate: dict[str, float] | None = None,
    exec_cost: dict[str, float] | None = None,
    detect: float | dict[str, float] = 1.0,
    cheapest: str | None = None,
) -> r.TaskOutcome:
    detect_map = detect if isinstance(detect, dict) else dict.fromkeys(r.TIERS, detect)
    return r.TaskOutcome(
        task_id=task_id,
        rubric_score=score,
        pass_rate=pass_rate or {"weak": 0.5, "mid": 0.8, "strong": 1.0},
        exec_cost=exec_cost or {"weak": 0.10, "mid": 0.20, "strong": 0.40},
        detect_rate=detect_map,
        cheapest_adequate_tier=cheapest,
    )


class TestCacheAwareCost:
    """The measurement hazard that would flatter the arm under test."""

    def test_prices_the_four_buckets_separately(self):
        usage = {
            "input_tokens": 1000,
            "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 1000},
            "cache_read_input_tokens": 10000,
            "output_tokens": 1000,
        }
        # opus: in 0.005/1k, out 0.025/1k.
        # 1000 uncached + 1000*1.25 write + 10000*0.1 read = 3250 input-equivalent
        expected = 3.25 * 0.005 + 1.0 * 0.025
        assert r.cost_from_usage("claude-opus-5", usage) == pytest.approx(expected)

    def test_one_hour_writes_cost_more_than_five_minute_writes(self):
        base = {"input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0}
        short = dict(base, cache_creation={"ephemeral_5m_input_tokens": 1000})
        long = dict(base, cache_creation={"ephemeral_1h_input_tokens": 1000})
        assert r.cost_from_usage("claude-opus-5", long) > r.cost_from_usage("claude-opus-5", short)

    def test_flat_cache_creation_total_is_charged_at_the_cheaper_write_rate(self):
        usage = {
            "input_tokens": 0,
            "cache_creation_input_tokens": 1000,
            "cache_read_input_tokens": 0,
            "output_tokens": 0,
        }
        assert r.cost_from_usage("claude-opus-5", usage) == pytest.approx(1.25 * 0.005)

    def test_audit_flags_the_cache_blind_fallback(self):
        """A subscription-auth run reports near-zero cost on a heavily cached trial.

        This is the exact shape that would make the 6k-token rubric prompt look free,
        so the audit has to surface it rather than let the composition consume it.
        """
        rows = [
            {
                "kind": "run",
                "config_hash": "aaa",
                "cost_usd_est": 48 / 1000 * 0.005,  # the cache-blind fallback
                "usage": {
                    "input_tokens": 48,
                    "cache_creation": {"ephemeral_5m_input_tokens": 26441},
                    "cache_read_input_tokens": 547913,
                    "output_tokens": 7603,
                },
            }
        ]
        audit = r.audit_ledger_costs(rows, {"aaa": "claude-opus-5"})
        assert audit["ratio"] > 100
        assert audit["recomputed_usd"] > audit["reported_usd"]

    def test_unknown_model_falls_back_to_the_dearest_rate(self):
        assert r.rates_for("some-unreleased-model") == r.PRICE_PER_1K["opus"]


class TestDecisionCost:
    """Fixed vs marginal — the split that decides whether batching rescues the rubric."""

    def test_two_point_fit_recovers_the_generating_parameters(self):
        fitted = r.DecisionCost.from_two_points(
            "rubric", "strong", cost_at_1=0.05 + 0.01, cost_at_k=0.05 + 0.01 * 9, k=9
        )
        assert fitted.fixed_usd == pytest.approx(0.05)
        assert fitted.marginal_usd == pytest.approx(0.01)

    def test_per_task_cost_falls_as_the_batch_grows(self):
        cost = r.DecisionCost("rubric", "strong", fixed_usd=0.05, marginal_usd=0.01)
        assert cost.per_task(1) == pytest.approx(0.06)
        assert cost.per_task(9) == pytest.approx(0.05 / 9 + 0.01)
        assert cost.per_task(9) < cost.per_task(1)

    def test_zero_tasks_costs_nothing(self):
        cost = r.DecisionCost("rubric", "strong", fixed_usd=0.05, marginal_usd=0.01)
        assert cost.total(0) == 0.0
        assert cost.per_task(0) == 0.0

    def test_a_single_block_cannot_separate_fixed_from_marginal(self):
        with pytest.raises(ValueError, match="block size"):
            r.DecisionCost.from_two_points("rubric", "strong", cost_at_1=1, cost_at_k=1, k=1)

    def test_mechanisms_with_no_decision_pay_nothing(self):
        assert r.fixed_tier_mechanism("mid", ["a"]).decision_cost.per_task(5) == 0.0
        assert r.always_weak_start().decision_cost.per_task(5) == 0.0


class TestRetryEconomics:
    """`always-weak` lives or dies here, so the recursion is pinned by hand."""

    def test_expected_cost_matches_the_hand_worked_ladder(self):
        # weak 0.10 @ p=0.5 -> mid 0.20 @ p=0.8 -> strong 0.40 @ p=1.0, detection perfect.
        # mid leg:  0.20 + 0.2*0.40 = 0.28,  p = 0.8 + 0.2*1.0 = 1.0
        # weak leg: 0.10 + 0.5*0.28 = 0.24,  p = 0.5 + 0.5*1.0 = 1.0
        result = r.expected_task(_outcome(), "weak", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.24)
        assert result.p_correct_post_repair == pytest.approx(1.0)

    def test_an_undetected_failure_is_an_escape_not_a_retry(self):
        """The clause that stops a cheap tier from looking free.

        With detection at zero the weak tier never escalates: it costs one attempt and
        the quality loss stays on the books instead of being repaired.
        """
        result = r.expected_task(_outcome(detect=0.0), "weak", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.10)
        assert result.p_correct_post_repair == pytest.approx(0.5)

    def test_partial_detection_buys_a_partial_retry(self):
        result = r.expected_task(_outcome(detect=0.5), "weak", max_escalations=2)
        # mid leg with d=0.5: 0.20 + (0.2*0.5)*0.40 = 0.24, p = 0.8 + 0.1*1.0 = 0.9
        # weak leg:           0.10 + (0.5*0.5)*0.24 = 0.16, p = 0.5 + 0.25*0.9 = 0.725
        assert result.expected_cost == pytest.approx(0.16)
        assert result.p_correct_post_repair == pytest.approx(0.725)

    def test_no_escalation_budget_means_one_attempt(self):
        result = r.expected_task(_outcome(), "weak", max_escalations=0)
        assert result.expected_cost == pytest.approx(0.10)
        assert result.p_correct_post_repair == pytest.approx(0.5)

    def test_the_top_tier_has_nowhere_to_escalate(self):
        result = r.expected_task(_outcome(), "strong", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.40)

    def test_escalation_depth_is_environmental_not_per_mechanism(self):
        """Every mechanism gets the SAME ladder, whatever its name suggests.

        A failed task gets retried somewhere regardless of how its tier was chosen, so
        `fixed-mid` escalates on a failure exactly as `always-weak` does. Handing a
        ladder only to the mechanism whose name mentions one would flatter the
        challenger — the mirror image of the two defects that flattered the incumbent.

        Asserted by construction: two mechanisms that START at the same tier must give
        identical results, because starting tier is the only thing that differs between
        them once depth is environmental.
        """
        substrate = r.Substrate({"t": _outcome("t")})
        mix = r.Mix("m", {"t": 1.0})
        starts_weak = r.Mechanism("always-weak", {}, start_tier="weak")
        routed_weak = r.Mechanism("rubric", {"t": "weak"})
        for depth in (r.PRIMARY_MAX_ESCALATIONS, r.SENSITIVITY_MAX_ESCALATIONS):
            a = r.evaluate(starts_weak, substrate, mix, episode_size=1, max_escalations=depth)
            b = r.evaluate(routed_weak, substrate, mix, episode_size=1, max_escalations=depth)
            assert a.execution_usd == pytest.approx(b.execution_usd)
            assert a.quality_post_repair == pytest.approx(b.quality_post_repair)

    def test_the_primary_depth_is_the_one_least_favourable_to_cheap_starts(self):
        """The adversarial posture, asserted rather than described.

        Depth 1 credits less repair than depth 2, so a weak-start mechanism looks WORSE
        on quality and CHEAPER on cost under the primary assumption. If a cheap-start
        mechanism still clears the quality bar at depth 1, that survives its own least
        favourable setting. This test fails if the primary is ever quietly raised.
        """
        assert r.PRIMARY_MAX_ESCALATIONS < r.SENSITIVITY_MAX_ESCALATIONS
        outcome = _outcome()
        shallow = r.expected_task(outcome, "weak", max_escalations=r.PRIMARY_MAX_ESCALATIONS)
        deep = r.expected_task(outcome, "weak", max_escalations=r.SENSITIVITY_MAX_ESCALATIONS)
        assert shallow.p_correct_post_repair <= deep.p_correct_post_repair
        assert shallow.expected_cost <= deep.expected_cost

    def test_the_default_depth_is_the_primary(self):
        outcome = _outcome()
        assert r.expected_task(outcome, "weak") == r.expected_task(
            outcome, "weak", max_escalations=r.PRIMARY_MAX_ESCALATIONS
        )

    def test_every_result_carries_the_depth_it_was_computed_at(self):
        """So a headline and a sensitivity can never be confused once separated."""
        substrate = r.Substrate({"t": _outcome("t")})
        mix = r.Mix("m", {"t": 1.0})
        mech = r.Mechanism("m", {"t": "weak"})
        for depth in (1, 2):
            out = r.evaluate(mech, substrate, mix, episode_size=1, max_escalations=depth)
            assert out.max_escalations == depth


class TestRouteReconstruction:
    """The emitted routing has to survive the trip through fathom's flat-bool channel."""

    def test_reconstructs_the_routing_from_the_criteria_bits(self):
        criteria = {
            "answer_present": True,
            "chose__fix-clamp2__weak": True,
            "chose__fix-clamp2__mid": False,
            "chose__fix-clamp2__strong": False,
            "chose__fix-ledger-replay__weak": False,
            "chose__fix-ledger-replay__mid": False,
            "chose__fix-ledger-replay__strong": True,
        }
        assert r.routes_from_criteria(criteria) == {
            "fix-clamp2": "weak",
            "fix-ledger-replay": "strong",
        }

    def test_a_brief_with_no_true_bit_is_omitted_not_defaulted(self):
        criteria = {f"chose__t__{tier}": False for tier in r.TIERS}
        assert r.routes_from_criteria(criteria) == {}

    def test_task_ids_containing_the_separator_survive(self):
        criteria = {"chose__fix__odd__name__mid": True}
        assert r.routes_from_criteria(criteria) == {"fix__odd__name": "mid"}

    def test_a_mechanism_that_did_not_route_a_task_raises_rather_than_guessing(self):
        mech = r.Mechanism("rubric", {"a": "weak"})
        with pytest.raises(r.MissingGroundTruth, match="emitted no route"):
            mech.tier_for("b")


class TestEarlyStop:
    """The pre-registered T1 stop rule, pinned before the data exists.

    If two mechanisms route identically, the execution and retry terms of C(m) are
    identical too, so the comparison reduces to decision cost alone — decidable with
    no outcome table. These tests fix what "agree" means before any trial is bought,
    so the rule cannot be reinterpreted once the counts are visible.
    """

    def test_modal_route_picks_the_majority(self):
        assert r.modal_route(["weak", "weak", "mid"]) == "weak"

    def test_a_tie_is_unsettled_not_a_coin_flip(self):
        assert r.modal_route(["weak", "mid"]) is None

    def test_no_repeats_is_unsettled(self):
        assert r.modal_route([]) is None

    def test_unanimous_is_settled(self):
        assert r.modal_route(["strong"] * 3) == "strong"

    def test_agreement_counts_matching_briefs(self):
        a = {"t1": "weak", "t2": "mid", "t3": "strong"}
        b = {"t1": "weak", "t2": "mid", "t3": "mid"}
        assert r.agreement(a, b) == (2, 3)

    def test_an_unsettled_brief_shrinks_the_denominator_not_the_agreement(self):
        """A brief one side could not settle must not be scored as agreement."""
        a = {"t1": "weak", "t2": "mid"}
        b = {"t1": "weak"}  # t2 was a tie and was dropped upstream
        agree, comparable = r.agreement(a, b)
        assert (agree, comparable) == (1, 1)

    def test_identical_routings_agree_completely(self):
        routes = {"t1": "weak", "t2": "strong"}
        assert r.agreement(routes, dict(routes)) == (2, 2)

    def test_identical_routing_collapses_c_to_the_decision_cost_difference(self):
        """The claim the stop rule rests on, asserted rather than assumed."""
        substrate = r.Substrate({"t": _outcome("t")})
        mix = r.Mix("m", {"t": 1.0})
        rubric = r.Mechanism(
            "rubric", {"t": "weak"}, r.DecisionCost("rubric", "strong", 0.05, 0.01)
        )
        none = r.Mechanism("none", {"t": "weak"}, r.DecisionCost("none", "strong", 0.0, 0.005))
        a = r.evaluate(rubric, substrate, mix, episode_size=1)
        b = r.evaluate(none, substrate, mix, episode_size=1)
        assert a.execution_usd == pytest.approx(b.execution_usd)
        assert a.quality_post_repair == pytest.approx(b.quality_post_repair)
        assert a.total_usd - b.total_usd == pytest.approx(a.decision_usd - b.decision_usd)


class TestSubstrateRefusals:
    """ "Unmeasured" is never written as a number."""

    def test_requiring_an_absent_task_raises(self):
        substrate = r.Substrate({"a": _outcome("a")})
        with pytest.raises(r.MissingGroundTruth, match="no measured outcome"):
            substrate.require("b")

    def test_coverage_reports_both_sides(self):
        substrate = r.Substrate({"a": _outcome("a")})
        covered, missing = substrate.coverage(["a", "b"])
        assert covered == ["a"] and missing == ["b"]

    def test_evaluate_carries_the_missing_count_into_the_result(self):
        substrate = r.Substrate({"a": _outcome("a")})
        mech = r.Mechanism("m", {"a": "weak", "b": "weak"})
        out = r.evaluate(mech, substrate, r.Mix("x", {"a": 1.0, "b": 1.0}), episode_size=2)
        assert out.n_tasks == 1
        assert out.n_missing == 1
        assert out.missing == ("b",)

    def test_the_published_verdict_wins_over_the_local_derivation(self):
        outcome = _outcome(cheapest="strong")
        assert outcome.adequate_tier(threshold=0.4) == "strong"

    def test_the_local_derivation_is_used_only_when_the_column_is_absent(self):
        assert _outcome().adequate_tier(threshold=0.4) == "weak"
        assert _outcome().adequate_tier(threshold=0.9) == "strong"
        assert _outcome().adequate_tier(threshold=1.01) is None


class TestSubstrateJoin:
    """Consuming `calibration.routing_substrate`'s artifact — the coordination surface.

    The two programmes meet at exactly one JSON document, so the translation between
    their schema and this one is the highest-leverage place for a silent error: a
    mis-mapped field would still produce a plausible C(m).
    """

    ARTIFACT = {
        "schema_version": "1",
        "tau": 0.7,
        "non_inferiority_margin": 0.05,
        "tasks": [
            {
                "task_id": "fix-clamp2",
                "rubric_score": 20,
                "genre": "fix",
                "cheapest_adequate_tier": "weak",
                "per_tier": {
                    "weak": {
                        "trials": 10,
                        "passing": 9,
                        "pass_rate": 0.9,
                        "gate_caught_failures": 1,
                        "silent_failures": 0,
                        "mean_cost_usd": 0.08,
                    },
                    "mid": {
                        "trials": 10,
                        "passing": 10,
                        "pass_rate": 1.0,
                        "gate_caught_failures": 0,
                        "silent_failures": 0,
                        "mean_cost_usd": 0.22,
                    },
                    "strong": {
                        "trials": 10,
                        "passing": 10,
                        "pass_rate": 1.0,
                        "gate_caught_failures": 0,
                        "silent_failures": 0,
                        "mean_cost_usd": 0.34,
                    },
                },
            },
            {
                "task_id": "fix-ledger-replay",
                "rubric_score": 71,
                "genre": "data",
                "cheapest_adequate_tier": "strong",
                "per_tier": {
                    "weak": {
                        "trials": 10,
                        "passing": 2,
                        "pass_rate": 0.2,
                        "gate_caught_failures": 4,
                        "silent_failures": 4,
                        "mean_cost_usd": 0.08,
                    },
                    "mid": {
                        "trials": 10,
                        "passing": 5,
                        "pass_rate": 0.5,
                        "gate_caught_failures": 3,
                        "silent_failures": 2,
                        "mean_cost_usd": 0.22,
                    },
                    "strong": {
                        "trials": 10,
                        "passing": 9,
                        "pass_rate": 0.9,
                        "gate_caught_failures": 1,
                        "silent_failures": 0,
                        "mean_cost_usd": 0.34,
                    },
                },
            },
        ],
        "mechanisms": [],
    }

    def test_loads_every_task_with_measured_cells(self):
        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        assert set(substrate.tasks) == {"fix-clamp2", "fix-ledger-replay"}

    def test_detect_rate_denominator_is_failures_not_trials(self):
        """The one derived field, and the one most likely to be got wrong.

        `fix-ledger-replay` at weak: 10 trials, 2 passing, so 8 failures, 4 caught.
        detect_rate is 4/8 = 0.5. Dividing by trials would give 0.4, understating
        detection and silently converting repairable failures into escapes.
        """
        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        assert substrate.require("fix-ledger-replay").detect_rate["weak"] == pytest.approx(0.5)

    def test_a_cell_with_no_failures_makes_no_detection_claim(self):
        """detect_rate there is inert, not evidence — the retry term multiplies by zero."""
        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        outcome = substrate.require("fix-clamp2")
        assert outcome.detect_rate["mid"] == 1.0
        result = r.expected_task(outcome, "mid", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.22)

    def test_pass_rate_and_cost_come_across_unchanged(self):
        outcome = r.Substrate.from_artifact(self.ARTIFACT).require("fix-ledger-replay")
        assert outcome.pass_rate == {"weak": 0.2, "mid": 0.5, "strong": 0.9}
        assert outcome.exec_cost == {"weak": 0.08, "mid": 0.22, "strong": 0.34}

    def test_the_published_verdict_is_used(self):
        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        assert substrate.require("fix-clamp2").adequate_tier(threshold=0.7) == "weak"
        assert substrate.require("fix-ledger-replay").adequate_tier(threshold=0.7) == "strong"

    def test_indeterminate_is_not_coerced_into_a_tier(self):
        """No tier cleared the bar. Reading that as `strong` would invent adequacy."""
        artifact = {
            "tasks": [dict(self.ARTIFACT["tasks"][0], cheapest_adequate_tier="indeterminate")]
        }
        outcome = r.Substrate.from_artifact(artifact).require("fix-clamp2")
        assert outcome.cheapest_adequate_tier is None
        # falls back to the local derivation rather than asserting a verdict
        assert outcome.adequate_tier(threshold=1.01) is None

    def test_a_task_with_no_measured_cells_is_absent_not_empty(self):
        artifact = {"tasks": [{"task_id": "unrun", "rubric_score": 40, "per_tier": {}}]}
        substrate = r.Substrate.from_artifact(artifact)
        assert "unrun" not in substrate.tasks
        with pytest.raises(r.MissingGroundTruth):
            substrate.require("unrun")

    def test_an_empty_artifact_yields_an_empty_substrate_not_a_crash(self):
        assert r.Substrate.from_artifact({}).tasks == {}

    def test_agrees_with_calibration_mechanism_costs_at_one_escalation(self):
        """Cross-implementation check against the substrate owner's own C(m).

        `calibration.mechanism_costs` computes execution+retry independently, with a
        SINGLE escalation step. Constraining this module to `max_escalations=1` should
        reproduce its per-task total exactly. Two implementations agreeing is worth more
        than either one's tests, and a divergence here means the two programmes would
        publish different C(m) for the same run.
        """
        from fathom import calibration as cal

        rows = [
            {
                "task_id": t["task_id"],
                "score": t["rubric_score"],
                "predicted": "weak",
                "needed": t["cheapest_adequate_tier"],
                "per_tier": t["per_tier"],
            }
            for t in self.ARTIFACT["tasks"]
        ]
        theirs = next(m for m in cal.mechanism_costs(rows) if m["mechanism"] == "always-weak")

        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        mine = r.evaluate(
            r.always_weak_start(),
            substrate,
            r.uniform_mix(list(substrate.tasks)),
            episode_size=1,
            max_escalations=1,
        )
        assert mine.execution_usd == pytest.approx(theirs["total_cost_usd"])

    def test_the_two_quality_quantities_are_related_by_exactly_the_repair_credit(self):
        """THE CROSS-PROGRAMME CONTRACT, as an identity rather than a snapshot.

        The two halves report different quantities, and that is settled and fine — the
        substrate emits the raw first-attempt facts, this module derives the estimand.
        What must never drift is the RELATION between them:

            quality_post_repair = first_attempt_pass_rate + repair_credit

        where the repair credit is, per task, P(fail) * P(gate detects) * P(the dearer
        tier then succeeds). This test recomputes that credit from the raw per-tier
        facts and asserts both sides land on it, so it fails if EITHER programme
        silently changes what its number means — which a test that merely pinned
        today's 0.55 and 0.70 would not catch.
        """
        from fathom import calibration as cal

        rows = [
            {
                "task_id": t["task_id"],
                "score": t["rubric_score"],
                "predicted": "weak",
                "needed": t["cheapest_adequate_tier"],
                "per_tier": t["per_tier"],
            }
            for t in self.ARTIFACT["tasks"]
        ]
        theirs = next(m for m in cal.mechanism_costs(rows) if m["mechanism"] == "always-weak")

        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        mine = r.evaluate(
            r.always_weak_start(),
            substrate,
            r.uniform_mix(list(substrate.tasks)),
            episode_size=1,
            max_escalations=1,
        )

        # Recompute the credit straight from the artifact's raw facts.
        expected_credit = 0.0
        for task in self.ARTIFACT["tasks"]:
            weak, mid = task["per_tier"]["weak"], task["per_tier"]["mid"]
            failures = weak["trials"] - weak["passing"]
            detect = (weak["gate_caught_failures"] / failures) if failures else 1.0
            expected_credit += (1 - weak["pass_rate"]) * detect * mid["pass_rate"]
        expected_credit /= len(self.ARTIFACT["tasks"])

        # Their number IS the first-attempt leg of the identity, under either spelling.
        theirs_first_attempt = theirs.get("first_attempt_pass_rate", theirs.get("quality"))
        assert mine.first_attempt_pass_rate == pytest.approx(theirs_first_attempt)
        # And the gap between the two is exactly the repair the cost side already paid for.
        assert mine.repair_credit == pytest.approx(expected_credit)
        assert mine.quality_post_repair == pytest.approx(
            mine.first_attempt_pass_rate + expected_credit
        )

    def test_the_two_programmes_report_different_quantities_by_design(self):
        """The resolution, and the shim that lets it land without breaking this.

        Settled 2026-08-12: the substrate emits RAW FACTS and this module owns the
        derived estimand. Their mechanism-level number is a FIRST-ATTEMPT pass rate;
        `quality_post_repair` here is P(the task ends correct) after gate-detected
        repair, which is what the non-inferiority constraint is written against.

        The substrate owner is renaming their field `quality` -> `first_attempt_pass_rate`
        precisely because one name meant two things for a week. This test reads whichever
        name is present, so the rename STRENGTHENS it rather than breaking it, and the
        assertion below is on the quantity, never on the spelling.
        """
        from fathom import calibration as cal

        rows = [
            {
                "task_id": t["task_id"],
                "score": t["rubric_score"],
                "predicted": "weak",
                "needed": t["cheapest_adequate_tier"],
                "per_tier": t["per_tier"],
            }
            for t in self.ARTIFACT["tasks"]
        ]
        theirs = next(m for m in cal.mechanism_costs(rows) if m["mechanism"] == "always-weak")
        # Accept either spelling: the rename is in flight and the quantity is the point.
        assert ("first_attempt_pass_rate" in theirs) or ("quality" in theirs), (
            "the substrate stopped reporting a first-attempt rate under any known name"
        )
        theirs_first_attempt = theirs.get("first_attempt_pass_rate", theirs.get("quality"))

        substrate = r.Substrate.from_artifact(self.ARTIFACT)
        mine = r.evaluate(
            r.always_weak_start(),
            substrate,
            r.uniform_mix(list(substrate.tasks)),
            episode_size=1,
            max_escalations=1,
        )
        assert theirs_first_attempt == pytest.approx(0.55), "first-attempt pass rate"
        assert mine.quality_post_repair == pytest.approx(0.70), "P(correct) after detected repair"
        assert mine.quality_post_repair > theirs_first_attempt

    def test_their_total_is_a_lower_bound_until_the_decision_term_lands(self):
        """The contract that makes the two halves compose rather than compete."""
        from fathom import calibration as cal

        rows = [
            {
                "task_id": t["task_id"],
                "score": t["rubric_score"],
                "predicted": "weak",
                "needed": t["cheapest_adequate_tier"],
                "per_tier": t["per_tier"],
            }
            for t in self.ARTIFACT["tasks"]
        ]
        for mech in cal.mechanism_costs(rows):
            assert mech["decision_cost_usd"] is None


class TestEstimand:
    """C(m), its terms, and the constraint that quality is not tradeable."""

    def test_total_is_the_sum_of_its_named_terms(self):
        """Depth stated explicitly: these are the hand-worked depth-2 ladder numbers.

        Leaving it implicit would silently re-anchor this assertion the next time the
        primary depth moves, which is exactly the drift the depth stamp exists to stop.
        """
        substrate = r.Substrate({"a": _outcome("a")})
        mech = r.Mechanism("rubric", {"a": "weak"}, r.DecisionCost("rubric", "strong", 0.05, 0.01))
        out = r.evaluate(mech, substrate, r.Mix("x", {"a": 1.0}), episode_size=1, max_escalations=2)
        assert out.decision_usd == pytest.approx(0.06)
        assert out.execution_usd == pytest.approx(0.24)
        assert out.total_usd == pytest.approx(0.30)

    def test_the_same_case_costs_less_at_the_primary_depth(self):
        """One escalation, not two: 0.10 + 0.5*0.20 = 0.20 execution, 0.26 total."""
        substrate = r.Substrate({"a": _outcome("a")})
        mech = r.Mechanism("rubric", {"a": "weak"}, r.DecisionCost("rubric", "strong", 0.05, 0.01))
        out = r.evaluate(mech, substrate, r.Mix("x", {"a": 1.0}), episode_size=1)
        assert out.max_escalations == r.PRIMARY_MAX_ESCALATIONS
        assert out.execution_usd == pytest.approx(0.20)
        assert out.total_usd == pytest.approx(0.26)

    def test_batching_lowers_c_for_a_mechanism_with_a_fixed_cost(self):
        substrate = r.Substrate({"a": _outcome("a")})
        mech = r.Mechanism("rubric", {"a": "weak"}, r.DecisionCost("rubric", "strong", 0.05, 0.01))
        mix = r.Mix("x", {"a": 1.0})
        assert (
            r.evaluate(mech, substrate, mix, episode_size=9).total_usd
            < r.evaluate(mech, substrate, mix, episode_size=1).total_usd
        )

    def test_a_cheaper_mechanism_that_loses_quality_is_dropped_not_ranked_last(self):
        """C(m) is only defined subject to the constraint, so a quality loser is out."""
        cheap_bad = r.MechanismCost(
            "cheap",
            "x",
            0.0,
            0.05,
            0.05,
            quality_post_repair=0.50,
            first_attempt_pass_rate=0.50,
            n_tasks=1,
            n_missing=0,
            missing=(),
        )
        dear_good = r.MechanismCost(
            "dear",
            "x",
            0.0,
            0.40,
            0.40,
            quality_post_repair=1.00,
            first_attempt_pass_rate=1.00,
            n_tasks=1,
            n_missing=0,
            missing=(),
        )
        ranked = r.rank([cheap_bad, dear_good], delta=0.05)
        assert [m.mechanism for m in ranked] == ["dear"]

    def test_a_cheaper_mechanism_inside_the_margin_wins(self):
        cheap_ok = r.MechanismCost(
            "cheap",
            "x",
            0.0,
            0.05,
            0.05,
            quality_post_repair=0.97,
            first_attempt_pass_rate=0.97,
            n_tasks=1,
            n_missing=0,
            missing=(),
        )
        dear_good = r.MechanismCost(
            "dear",
            "x",
            0.0,
            0.40,
            0.40,
            quality_post_repair=1.00,
            first_attempt_pass_rate=1.00,
            n_tasks=1,
            n_missing=0,
            missing=(),
        )
        ranked = r.rank([cheap_ok, dear_good], delta=0.05)
        assert [m.mechanism for m in ranked] == ["cheap", "dear"]

    def test_ranking_nothing_returns_nothing(self):
        assert r.rank([], delta=0.05) == []


class TestEscalationSensitivity:
    """The depth-2 sensitivity as a computed value, not a paragraph."""

    def _substrate(self) -> r.Substrate:
        # weak fails often but its failures are always caught; mid repairs most of them;
        # strong repairs the rest. A second escalation is therefore worth real quality.
        return r.Substrate(
            {
                "t": _outcome(
                    "t",
                    pass_rate={"weak": 0.3, "mid": 0.6, "strong": 1.0},
                    exec_cost={"weak": 0.05, "mid": 0.20, "strong": 0.50},
                    detect=1.0,
                )
            }
        )

    def test_it_reports_both_rankings_and_whether_they_differ(self):
        substrate = self._substrate()
        mechanisms = [r.always_weak_start(), r.fixed_tier_mechanism("strong", ["t"])]
        out = r.rank_with_sensitivity(
            mechanisms, substrate, r.Mix("m", {"t": 1.0}), episode_size=1, delta=0.05
        )
        assert out.primary and out.sensitivity
        assert isinstance(out.ranking_changed, bool)
        assert isinstance(out.winner_changed, bool)

    def test_each_half_is_computed_at_its_own_depth(self):
        substrate = self._substrate()
        out = r.rank_with_sensitivity(
            [r.always_weak_start()],
            substrate,
            r.Mix("m", {"t": 1.0}),
            episode_size=1,
            delta=1.0,
        )
        assert all(m.max_escalations == r.PRIMARY_MAX_ESCALATIONS for m in out.primary)
        assert all(m.max_escalations == r.SENSITIVITY_MAX_ESCALATIONS for m in out.sensitivity)

    def test_a_depth_driven_ranking_flip_is_detected(self):
        """The case the ruling cares about: depth 2 changing the answer.

        At depth 1 the weak start cannot reach `strong`, so it caps below the quality
        bar and is excluded; `fixed-strong` wins. At depth 2 it reaches `strong`, clears
        the bar, and wins on cost. `winner_changed` must be True — that IS the finding,
        and it has to be a value the report cannot omit.
        """
        substrate = self._substrate()
        mechanisms = [r.always_weak_start(), r.fixed_tier_mechanism("strong", ["t"])]
        out = r.rank_with_sensitivity(
            mechanisms, substrate, r.Mix("m", {"t": 1.0}), episode_size=1, delta=0.05
        )
        assert out.primary_order[0] == "fixed-strong"
        assert out.sensitivity_order[0] == "always-weak"
        assert out.winner_changed is True
        assert out.ranking_changed is True

    def test_a_stable_ranking_reports_no_change(self):
        """Where depth does not matter, the sensitivity must say so rather than noise."""
        substrate = r.Substrate(
            {"t": _outcome("t", pass_rate={"weak": 1.0, "mid": 1.0, "strong": 1.0})}
        )
        mechanisms = [r.always_weak_start(), r.fixed_tier_mechanism("strong", ["t"])]
        out = r.rank_with_sensitivity(
            mechanisms, substrate, r.Mix("m", {"t": 1.0}), episode_size=1, delta=0.05
        )
        assert out.ranking_changed is False
        assert out.winner_changed is False

    def test_the_mechanism_is_named_for_where_it_starts_not_for_escalating(self):
        """`always-weak-escalate` -> `always-weak`: escalation is no longer its property.

        The name also matches `calibration`'s own `always-weak`, so the two programmes
        share one vocabulary for the same mechanism.
        """
        from fathom import calibration as cal

        assert r.always_weak_start().name == "always-weak"
        assert "always-weak" in cal.TASK_LEVEL_MECHANISMS


class TestMix:
    """A mechanism that wins on hard tasks can lose on a realistic session."""

    def test_band_mix_spreads_weight_inside_each_band(self):
        substrate = r.Substrate(
            {
                "easy": _outcome("easy", 20),
                "mid1": _outcome("mid1", 40),
                "mid2": _outcome("mid2", 50),
                "hard": _outcome("hard", 70),
            }
        )
        mix = r.band_mix("m", substrate, {"weak": 0.5, "mid": 0.5})
        weights = mix.normalised()
        assert weights["easy"] == pytest.approx(0.5)
        assert weights["mid1"] == pytest.approx(0.25)
        assert weights["mid2"] == pytest.approx(0.25)
        assert "hard" not in mix.weights

    def test_a_mix_with_no_weight_is_an_error_not_an_empty_average(self):
        with pytest.raises(ValueError, match="no positive weight"):
            r.Mix("empty", {"a": 0.0}).normalised()

    def test_uniform_mix_is_labelled_as_the_banks_own(self):
        assert r.uniform_mix(["a", "b"]).name == "bank-uniform"

    def test_break_even_finds_the_crossing(self):
        """A mechanism with a fixed cost that routes hard work well pays off late."""
        substrate = r.Substrate(
            {
                # On easy work, weak already suffices and routing buys nothing.
                "easy": _outcome(
                    "easy",
                    20,
                    pass_rate={"weak": 1.0, "mid": 1.0, "strong": 1.0},
                    exec_cost={"weak": 0.05, "mid": 0.20, "strong": 0.40},
                ),
                # On hard work, only strong passes and starting weak burns two attempts.
                "hard": _outcome(
                    "hard",
                    70,
                    pass_rate={"weak": 0.0, "mid": 0.0, "strong": 1.0},
                    exec_cost={"weak": 0.05, "mid": 0.20, "strong": 0.40},
                ),
            }
        )
        smart = r.Mechanism(
            "smart",
            {"easy": "weak", "hard": "strong"},
            r.DecisionCost("smart", "strong", 0.05, 0.0),
        )
        naive = r.always_weak_start()
        easy_mix = r.Mix("easy", {"easy": 1.0})
        hard_mix = r.Mix("hard", {"hard": 1.0})
        # Depth stated explicitly. At depth 2 the weak start burns three attempts on the
        # hard task, so routing eventually pays; at the primary depth 1 it cannot reach
        # `strong` at all and stays cheaper, so no crossing exists. The crossing is a
        # function of the environment assumption, which is the point of stamping it.
        crossing = r.break_even_hard_fraction(
            smart,
            naive,
            substrate,
            episode_size=1,
            easy_mix=easy_mix,
            hard_mix=hard_mix,
            max_escalations=r.SENSITIVITY_MAX_ESCALATIONS,
        )
        assert crossing is not None
        assert 0.0 < crossing < 1.0

    def test_the_crossing_can_depend_on_the_escalation_depth(self):
        """Same fixture, primary depth: the weak start never reaches `strong`, so it
        never pays the third attempt and routing never becomes the cheaper option.

        This is a sensitivity worth seeing, not a bug: the break-even a reader acts on
        is conditional on how many times the environment retries.
        """
        substrate = r.Substrate(
            {
                "easy": _outcome(
                    "easy",
                    20,
                    pass_rate={"weak": 1.0, "mid": 1.0, "strong": 1.0},
                    exec_cost={"weak": 0.05, "mid": 0.20, "strong": 0.40},
                ),
                "hard": _outcome(
                    "hard",
                    70,
                    pass_rate={"weak": 0.0, "mid": 0.0, "strong": 1.0},
                    exec_cost={"weak": 0.05, "mid": 0.20, "strong": 0.40},
                ),
            }
        )
        smart = r.Mechanism(
            "smart",
            {"easy": "weak", "hard": "strong"},
            r.DecisionCost("smart", "strong", 0.05, 0.0),
        )
        assert (
            r.break_even_hard_fraction(
                smart,
                r.always_weak_start(),
                substrate,
                episode_size=1,
                easy_mix=r.Mix("easy", {"easy": 1.0}),
                hard_mix=r.Mix("hard", {"hard": 1.0}),
                max_escalations=r.PRIMARY_MAX_ESCALATIONS,
            )
            is None
        )

    def test_break_even_returns_none_when_a_mechanism_never_catches_up(self):
        substrate = r.Substrate({"a": _outcome("a", 20)})
        loser = r.Mechanism("loser", {"a": "weak"}, r.DecisionCost("loser", "strong", 10.0, 0.0))
        winner = r.Mechanism("winner", {"a": "weak"})
        mix = r.Mix("m", {"a": 1.0})
        assert (
            r.break_even_hard_fraction(
                loser, winner, substrate, episode_size=1, easy_mix=mix, hard_mix=mix
            )
            is None
        )


class TestPrePurchaseProjection:
    """The forecast the design doc quotes, pinned so the doc cannot drift from the code.

    These are PROJECTIONS from existing numbers, not results: the decision costs come
    from a forward token model and the execution costs from `model-tier-v1`'s ledger
    medians, which were measured on a different (saturated) bank. They are pinned
    because a projection nobody can reproduce is a rumour, and because the first
    measured tranche has to be comparable against a forecast that did not move.
    """

    # Medians over 35 trials/arm on ledger/model-tier-v1.jsonl, mapped to the current
    # lineup by ascending cost (haiku / sonnet-5 / opus-5).
    EXEC = {"weak": 0.0756, "mid": 0.2254, "strong": 0.3368}
    MODELS = {"weak": "claude-haiku-4-5", "mid": "claude-sonnet-5", "strong": "claude-opus-5"}

    def _premium_per_task(self, tier: str, k: int) -> float:
        model = self.MODELS[tier]
        if k == 1:
            rubric = r.TokenModel(
                policy_tokens=6100, workspace_tokens=400, turns=5, output_tokens=1500
            ).price(model)
            none = r.TokenModel(
                policy_tokens=0, workspace_tokens=400, turns=4, output_tokens=500
            ).price(model)
        else:
            rubric = r.TokenModel(
                policy_tokens=6100, workspace_tokens=1400, turns=7, output_tokens=4500
            ).price(model)
            none = r.TokenModel(
                policy_tokens=0, workspace_tokens=1400, turns=6, output_tokens=1500
            ).price(model)
        return (rubric - none) / k

    def test_the_deciding_tier_dominates_the_rubrics_overhead(self):
        """Deciding on an expensive model is what makes the rubric expensive."""
        at_weak = self._premium_per_task("weak", 1)
        at_strong = self._premium_per_task("strong", 1)
        assert at_strong / at_weak > 4

    def test_batching_collapses_the_overhead(self):
        assert self._premium_per_task("strong", 9) / self._premium_per_task("strong", 1) < 0.25

    def test_the_worst_case_break_even_is_a_demanding_bar(self):
        """Strong deciding tier, one decision at a time: the documented ~31% / ~53%."""
        premium = self._premium_per_task("strong", 1)
        strong_to_weak = premium / (self.EXEC["strong"] - self.EXEC["weak"])
        mid_to_weak = premium / (self.EXEC["mid"] - self.EXEC["weak"])
        assert 0.28 < strong_to_weak < 0.34
        assert 0.50 < mid_to_weak < 0.57

    def test_the_best_case_break_even_is_easy(self):
        """Weak deciding tier in a batch: the documented ~1-2%."""
        premium = self._premium_per_task("weak", 9)
        assert premium / (self.EXEC["strong"] - self.EXEC["weak"]) < 0.02

    def test_the_full_matrix_is_affordable(self):
        """3 single-brief blocks + 1 batch block, 9 arms, 5 repeats, under $20."""
        total = 0.0
        for mech, policy, extra_turns, extra_out in (
            ("none", 0, 0, 0),
            ("shortcuts", 435, 0, 100),
            ("rubric", 6100, 1, 1000),
        ):
            for model in self.MODELS.values():
                one = r.TokenModel(
                    policy_tokens=policy,
                    workspace_tokens=400,
                    turns=4 + extra_turns,
                    output_tokens=500 + extra_out,
                ).price(model)
                nine = r.TokenModel(
                    policy_tokens=policy,
                    workspace_tokens=1400,
                    turns=6 + extra_turns,
                    output_tokens=1500 + 3 * extra_out,
                ).price(model)
                total += (3 * one + nine) * 5
        assert total < 20.0, f"matrix projected at ${total:.2f}"


class TestWilson:
    def test_saturated_cell_keeps_an_honest_lower_bound(self):
        low, high = r.wilson_interval(10, 10)
        assert high == pytest.approx(1.0)
        assert 0.65 < low < 0.80

    def test_no_trials_is_total_ignorance_not_zero(self):
        assert r.wilson_interval(0, 0) == (0.0, 1.0)

    def test_interval_narrows_with_n(self):
        def width(n):
            low, high = r.wilson_interval(n // 2, n)
            return high - low

        assert width(100) < width(10)

    def test_bounds_stay_inside_the_unit_interval(self):
        for successes, trials in ((0, 5), (5, 5), (1, 3)):
            low, high = r.wilson_interval(successes, trials)
            assert 0.0 <= low <= high <= 1.0
            assert not math.isnan(low) and not math.isnan(high)
