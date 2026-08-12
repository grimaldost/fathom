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
        assert r.always_weak_escalate().decision_cost.per_task(5) == 0.0


class TestRetryEconomics:
    """`always-weak-escalate` lives or dies here, so the recursion is pinned by hand."""

    def test_expected_cost_matches_the_hand_worked_ladder(self):
        # weak 0.10 @ p=0.5 -> mid 0.20 @ p=0.8 -> strong 0.40 @ p=1.0, detection perfect.
        # mid leg:  0.20 + 0.2*0.40 = 0.28,  p = 0.8 + 0.2*1.0 = 1.0
        # weak leg: 0.10 + 0.5*0.28 = 0.24,  p = 0.5 + 0.5*1.0 = 1.0
        result = r.expected_task(_outcome(), "weak", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.24)
        assert result.p_correct == pytest.approx(1.0)

    def test_an_undetected_failure_is_an_escape_not_a_retry(self):
        """The clause that stops a cheap tier from looking free.

        With detection at zero the weak tier never escalates: it costs one attempt and
        the quality loss stays on the books instead of being repaired.
        """
        result = r.expected_task(_outcome(detect=0.0), "weak", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.10)
        assert result.p_correct == pytest.approx(0.5)

    def test_partial_detection_buys_a_partial_retry(self):
        result = r.expected_task(_outcome(detect=0.5), "weak", max_escalations=2)
        # mid leg with d=0.5: 0.20 + (0.2*0.5)*0.40 = 0.24, p = 0.8 + 0.1*1.0 = 0.9
        # weak leg:           0.10 + (0.5*0.5)*0.24 = 0.16, p = 0.5 + 0.25*0.9 = 0.725
        assert result.expected_cost == pytest.approx(0.16)
        assert result.p_correct == pytest.approx(0.725)

    def test_no_escalation_budget_means_one_attempt(self):
        result = r.expected_task(_outcome(), "weak", max_escalations=0)
        assert result.expected_cost == pytest.approx(0.10)
        assert result.p_correct == pytest.approx(0.5)

    def test_the_top_tier_has_nowhere_to_escalate(self):
        result = r.expected_task(_outcome(), "strong", max_escalations=2)
        assert result.expected_cost == pytest.approx(0.40)

    def test_every_mechanism_gets_the_same_retry_machinery(self):
        """No mechanism may be credited with a repair loop another is denied."""
        outcome = _outcome()
        started_weak = r.expected_task(outcome, "weak", max_escalations=2)
        fixed_at_weak = r.expected_task(outcome, "weak", max_escalations=2)
        assert started_weak == fixed_at_weak


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


class TestEstimand:
    """C(m), its terms, and the constraint that quality is not tradeable."""

    def test_total_is_the_sum_of_its_named_terms(self):
        substrate = r.Substrate({"a": _outcome("a")})
        mech = r.Mechanism("rubric", {"a": "weak"}, r.DecisionCost("rubric", "strong", 0.05, 0.01))
        out = r.evaluate(mech, substrate, r.Mix("x", {"a": 1.0}), episode_size=1)
        assert out.decision_usd == pytest.approx(0.06)
        assert out.execution_usd == pytest.approx(0.24)
        assert out.total_usd == pytest.approx(0.30)

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
            "cheap", "x", 0.0, 0.05, 0.05, quality=0.50, n_tasks=1, n_missing=0, missing=()
        )
        dear_good = r.MechanismCost(
            "dear", "x", 0.0, 0.40, 0.40, quality=1.00, n_tasks=1, n_missing=0, missing=()
        )
        ranked = r.rank([cheap_bad, dear_good], delta=0.05)
        assert [m.mechanism for m in ranked] == ["dear"]

    def test_a_cheaper_mechanism_inside_the_margin_wins(self):
        cheap_ok = r.MechanismCost(
            "cheap", "x", 0.0, 0.05, 0.05, quality=0.97, n_tasks=1, n_missing=0, missing=()
        )
        dear_good = r.MechanismCost(
            "dear", "x", 0.0, 0.40, 0.40, quality=1.00, n_tasks=1, n_missing=0, missing=()
        )
        ranked = r.rank([cheap_ok, dear_good], delta=0.05)
        assert [m.mechanism for m in ranked] == ["cheap", "dear"]

    def test_ranking_nothing_returns_nothing(self):
        assert r.rank([], delta=0.05) == []


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
        naive = r.always_weak_escalate()
        easy_mix = r.Mix("easy", {"easy": 1.0})
        hard_mix = r.Mix("hard", {"hard": 1.0})
        crossing = r.break_even_hard_fraction(
            smart, naive, substrate, episode_size=1, easy_mix=easy_mix, hard_mix=hard_mix
        )
        assert crossing is not None
        assert 0.0 < crossing < 1.0

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
