"""Net-value composition for model-tier ROUTING MECHANISMS.

The question this module answers is not "does the rubric route accurately" but "is the
rubric worth what it costs to run". Those come apart, and the pre-registered estimand
is the second one:

    C(m) = decision_cost(m) + execution_cost(tier chosen by m) + retry_cost(m)
    subject to  quality_post_repair(m) >= quality_post_repair(best) - delta

Winner is argmin C(m). **Quality is a constraint, not the objective.** Every term is
measured or computed from measurements; nothing here defaults to an assumed number.

WHY A MODULE AND NOT A SPREADSHEET. The substrate this composes against
(`model-tier-v2`'s per-task per-tier outcome table) does not exist yet, and will land
incrementally. The analysis therefore has to be re-runnable against a table that grows,
and it has to fail loudly rather than quietly when a task it needs is missing. Both are
testable properties of code and neither is a property of a spreadsheet.

THE THREE THINGS THIS MODULE REFUSES TO DO

1. It does not invent `cheapest_adequate_tier`. A task with no measured outcome is
   excluded from the quality and routing-accuracy terms and counted in `n_missing`,
   which every result carries. "Unmeasured" is never rendered as a number.
2. It does not trust ``cost_usd_est`` blindly. Under subscription auth the CLI reports
   ``total_cost_usd == 0`` and fathom's fallback prices only the uncached
   ``input_tokens`` field — 48 tokens on a trial that actually read 548k from cache.
   That failure mode understates a big cached system prompt by orders of magnitude,
   which is precisely the arm under test, so :func:`cost_from_usage` recomputes from
   the raw buckets and :func:`audit_ledger_costs` reports the disagreement.
3. It does not pick a task mix for you. A mechanism that wins on a bank of hard tasks
   can lose on a realistic session mix, so every headline is reported per mix and the
   decision-relevant output is :func:`break_even_hard_fraction` — the share of hard
   work above which a mechanism starts paying for itself.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Iterable, Mapping, Sequence

# Cheapest first. The ladder is ordered, and "escalate" means "one step right".
TIERS: tuple[str, ...] = ("weak", "mid", "strong")

# ---------------------------------------------------------------- escalation depth
#
# How many times a gate-detected failure may escalate. It is a property of the
# ENVIRONMENT, not of any mechanism: a failed task gets retried somewhere regardless of
# how its tier was chosen, so every mechanism is evaluated at the same depth. Handing a
# ladder only to the mechanism whose name mentions one would flatter the challenger the
# way the first two design defects flattered the incumbent.
#
# WHY THE PRIMARY IS 1, AND THE REASONING IS ADVERSARIAL RATHER THAN PHYSICAL. Depth 1
# credits less repair, so it is the assumption LEAST favourable to the cheap-start
# mechanisms — which are the ones the projection expects to win. A result that survives
# its own least favourable assumption is worth something; one that needs the generous
# setting is a finding about the setting. The author of this analysis is an interested
# party in that outcome, so the posture is chosen to make the conclusion credible rather
# than merely defensible.
#
# Depth 2 is reported BESIDE the headline as a sensitivity, never as an alternative
# headline. If it changes the ranking, that IS the finding and
# :func:`rank_with_sensitivity` returns it as a value so it cannot be left in a
# paragraph nobody reads.
PRIMARY_MAX_ESCALATIONS = 1
SENSITIVITY_MAX_ESCALATIONS = 2

# The only criteria a routing-decision task is allowed to gate on. Routing ACCURACY is
# deliberately absent: its ground truth does not exist yet, so a bank that graded it
# would be asserting an answer key rather than measuring one. Kept here (not only in
# the bank's verifier) so the bank's task.toml files can be checked against it.
HARD_WELL_FORMEDNESS: tuple[str, ...] = (
    "answer_present",
    "covers_every_brief",
    "tiers_are_legal",
)

# Published cache multipliers on the input rate. Re-check against the platform model
# reference when prices move; they are multipliers, not prices, so a family repricing
# does not touch them.
CACHE_WRITE_5M = 1.25
CACHE_WRITE_1H = 2.0
CACHE_READ = 0.1

# Per-1k (input, output) USD by family substring — the same table fathom's adapter
# uses, kept here so a recomputation never silently depends on adapter internals.
PRICE_PER_1K: dict[str, tuple[float, float]] = {
    "haiku": (0.001, 0.005),
    "sonnet": (0.003, 0.015),
    "opus": (0.005, 0.025),
    "fable": (0.010, 0.050),
}
_DEFAULT_PRICE = PRICE_PER_1K["opus"]


class MissingGroundTruth(KeyError):
    """A task was asked for that the outcome table does not carry."""


def rates_for(model_id: str) -> tuple[float, float]:
    """(input, output) per-1k USD for *model_id*, by family substring."""
    lower = model_id.lower()
    for family, rate in PRICE_PER_1K.items():
        if family in lower:
            return rate
    return _DEFAULT_PRICE


def cost_from_usage(model_id: str, usage: Mapping[str, object]) -> float:
    """Cache-aware USD for one trial, recomputed from the raw usage buckets.

    Prices the four buckets the CLI reports separately — uncached input, 5-minute and
    1-hour cache writes, and cache reads — instead of collapsing them. This is the
    number the composition uses; ``cost_usd_est`` is kept only for the audit.
    """
    rate_in, rate_out = rates_for(model_id)

    def _int(mapping: Mapping[str, object], key: str) -> int:
        value = mapping.get(key)
        return int(value) if isinstance(value, (int, float)) else 0

    creation = usage.get("cache_creation")
    write_1h = _int(creation, "ephemeral_1h_input_tokens") if isinstance(creation, Mapping) else 0
    write_5m = _int(creation, "ephemeral_5m_input_tokens") if isinstance(creation, Mapping) else 0
    if not (write_1h or write_5m):
        # Older rows carry only the flat total; charge it at the 5m rate, which is the
        # cheaper of the two write multipliers and therefore the conservative choice
        # for an arm whose cost we are trying not to overstate.
        write_5m = _int(usage, "cache_creation_input_tokens")

    tokens_in_equiv = (
        _int(usage, "input_tokens")
        + write_1h * CACHE_WRITE_1H
        + write_5m * CACHE_WRITE_5M
        + _int(usage, "cache_read_input_tokens") * CACHE_READ
    )
    return tokens_in_equiv / 1000 * rate_in + _int(usage, "output_tokens") / 1000 * rate_out


@dataclasses.dataclass(frozen=True)
class TokenModel:
    """A forward price model for one decision trial, in tokens.

    EVERY FIELD IS AN ESTIMATE AND IS NAMED AS ONE. This exists to price tranches
    before buying them, not to stand in for the measurement: once the first tranche
    lands, the fitted :class:`DecisionCost` replaces it and this model is only ever
    used to check how far the forecast was out.

    ``baseline_context_tokens`` is the CLI's own system prompt, tool schemas and first
    user turn — grounded at the LIGHTEST value observed across `model-tier-v1`'s five
    arms (median cache-creation 9.1k on the cheapest arm), because a routing decision
    stages a far smaller workspace than a bug-fix task and overstating the shared
    baseline would compress the very contrast being priced.

    The per-turn term is a cache READ, not a fresh write: the adapter runs with prompt
    caching on, so an injected policy is written once and re-read each turn at a tenth
    of the input rate. Pricing it as a full re-send would overstate the rubric arm by
    roughly an order of magnitude — the mistake this dataclass exists to prevent.
    """

    baseline_context_tokens: int = 9_000
    policy_tokens: int = 0
    workspace_tokens: int = 0
    turns: int = 4
    output_tokens: int = 500

    @property
    def context_tokens(self) -> int:
        return self.baseline_context_tokens + self.policy_tokens + self.workspace_tokens

    def price(self, model_id: str) -> float:
        """Expected USD for one trial under this model."""
        context = self.context_tokens
        usage = {
            "input_tokens": 0,
            "cache_creation": {"ephemeral_5m_input_tokens": context},
            "cache_read_input_tokens": max(self.turns - 1, 0) * context,
            "output_tokens": self.output_tokens,
        }
        return cost_from_usage(model_id, usage)


def audit_ledger_costs(
    rows: Iterable[Mapping[str, object]], model_of: Mapping[str, str]
) -> dict[str, float]:
    """Compare recomputed cost against the ledger's ``cost_usd_est``.

    Returns the two totals and their ratio. A ratio far from 1.0 means the run was
    priced by the cache-blind fallback (the subscription-auth case), and the composition
    must use the recomputed figure. Reported, never silently corrected.
    """
    recomputed = 0.0
    reported = 0.0
    for row in rows:
        if row.get("kind") != "run":
            continue
        arm = str(row.get("config_hash", ""))
        usage = row.get("usage")
        if isinstance(usage, Mapping):
            recomputed += cost_from_usage(model_of.get(arm, ""), usage)
        value = row.get("cost_usd_est")
        reported += float(value) if isinstance(value, (int, float)) else 0.0
    ratio = recomputed / reported if reported else math.inf
    return {"recomputed_usd": recomputed, "reported_usd": reported, "ratio": ratio}


# --------------------------------------------------------------------------- substrate


@dataclasses.dataclass(frozen=True)
class TaskOutcome:
    """One row of the substrate table: how each tier does on one task, and at what cost.

    ``pass_rate`` and ``exec_cost`` are per tier and come from `model-tier-v2`'s run.
    ``detect_rate`` is P(the task's gate reports a failure that happened) at that tier —
    the term that decides whether a failure buys a retry or becomes a silent escape, and
    the reason `always-weak` is not free.
    """

    task_id: str
    rubric_score: int
    pass_rate: Mapping[str, float]
    exec_cost: Mapping[str, float]
    detect_rate: Mapping[str, float]
    cheapest_adequate_tier: str | None = None

    def adequate_tier(self, threshold: float) -> str | None:
        """The cheapest tier whose pass rate clears *threshold*, or None if none does.

        Prefers the substrate's own published ``cheapest_adequate_tier`` when present —
        that column is the pre-registered join field and its owner derives it under its
        own pre-registered rule. The local derivation is the fallback for a table that
        publishes rates but not the verdict, and it is deliberately the same rule stated
        in one place rather than two.
        """
        if self.cheapest_adequate_tier is not None:
            return self.cheapest_adequate_tier
        for tier in TIERS:
            if self.pass_rate.get(tier, 0.0) >= threshold:
                return tier
        return None


@dataclasses.dataclass(frozen=True)
class Substrate:
    """The per-task outcome table, plus the record of what it does not cover."""

    tasks: Mapping[str, TaskOutcome]

    @classmethod
    def from_artifact(cls, artifact: Mapping[str, object]) -> Substrate:
        """Load `calibration.routing_substrate`'s JSON — the coordination surface.

        THE DIVISION OF LABOUR THIS ENCODES. That artifact owns execution cost, retry,
        quality and `cheapest_adequate_tier`; it reports `decision_cost_usd` as `null`
        and says so explicitly, because measuring it means *running* each mechanism,
        which is this bank's programme. Its `total_cost_usd` is therefore a documented
        LOWER BOUND, and C(m) is only complete once the decision term measured here is
        added to the execution term measured there. Neither half is a duplicate of the
        other and neither is sufficient alone.

        The field translation is where the two schemas actually meet, and one field is
        derived rather than copied: their `gate_caught_failures` is a COUNT of failures
        the gate caught, while `detect_rate` here is the per-failure probability that a
        failure is caught. So the denominator is the number of FAILURES (`trials -
        passing`), not the number of trials. Dividing by trials instead would understate
        detection on a mostly-passing tier and silently convert repairable failures into
        escapes — which biases every mechanism that starts cheap.

        A tier whose cell records no failures has no evidence about detection at all.
        It gets `detect_rate = 1.0`, which is inert there (the retry term is multiplied
        by `1 - pass_rate`, which is 0) rather than a claim.
        """
        tasks: dict[str, TaskOutcome] = {}
        for row in artifact.get("tasks", []) or []:
            if not isinstance(row, Mapping):
                continue
            per_tier = row.get("per_tier") or {}
            if not isinstance(per_tier, Mapping) or not per_tier:
                continue  # no measured cells: excluded, and it will show up as missing

            pass_rate: dict[str, float] = {}
            exec_cost: dict[str, float] = {}
            detect_rate: dict[str, float] = {}
            for tier, cell in per_tier.items():
                if tier not in TIERS or not isinstance(cell, Mapping):
                    continue
                trials = int(cell.get("trials") or 0)
                passing = int(cell.get("passing") or 0)
                pass_rate[tier] = float(cell.get("pass_rate") or 0.0)
                exec_cost[tier] = float(cell.get("mean_cost_usd") or 0.0)
                failures = trials - passing
                caught = float(cell.get("gate_caught_failures") or 0.0)
                detect_rate[tier] = (caught / failures) if failures > 0 else 1.0

            if not pass_rate:
                continue

            needed = row.get("cheapest_adequate_tier")
            tasks[str(row["task_id"])] = TaskOutcome(
                task_id=str(row["task_id"]),
                rubric_score=int(row.get("rubric_score") or 0),
                pass_rate=pass_rate,
                exec_cost=exec_cost,
                detect_rate=detect_rate,
                # `indeterminate` means no tier cleared the bar. That is NOT a tier, and
                # coercing it to `strong` would invent an adequacy the run refuted.
                cheapest_adequate_tier=needed if needed in TIERS else None,
            )
        return cls(tasks)

    def require(self, task_id: str) -> TaskOutcome:
        if task_id not in self.tasks:
            raise MissingGroundTruth(
                f"{task_id!r} has no measured outcome — it cannot be scored, and "
                "substituting a guess is the one thing this analysis must not do"
            )
        return self.tasks[task_id]

    def coverage(self, task_ids: Sequence[str]) -> tuple[list[str], list[str]]:
        """(covered, missing) — reported with every result so n is never implied."""
        covered = [t for t in task_ids if t in self.tasks]
        return covered, [t for t in task_ids if t not in self.tasks]


# ------------------------------------------------------------------------ decision cost


@dataclasses.dataclass(frozen=True)
class DecisionCost:
    """Cost of *taking* the routing decision, split into fixed and marginal.

    The split is the whole point. A mechanism that loads a 6k-token policy pays that
    once per decision episode and then a little per task, so its per-task decision cost
    collapses as the batch grows. A single spawn decision (K=1) and a nine-task series
    authoring pass (K=9) are therefore different economies, and a study that measured
    only one of them would generalise a number that does not generalise.

    Fitted from the measured K=1 and K=9 blocks by :meth:`from_two_points`.
    """

    mechanism: str
    deciding_tier: str
    fixed_usd: float
    marginal_usd: float

    @classmethod
    def from_two_points(
        cls, mechanism: str, deciding_tier: str, *, cost_at_1: float, cost_at_k: float, k: int
    ) -> DecisionCost:
        if k <= 1:
            raise ValueError("need a block size > 1 to separate fixed from marginal cost")
        marginal = (cost_at_k - cost_at_1) / (k - 1)
        return cls(mechanism, deciding_tier, fixed_usd=cost_at_1 - marginal, marginal_usd=marginal)

    def total(self, n_tasks: int) -> float:
        """Decision cost for one episode routing *n_tasks* tasks."""
        return 0.0 if n_tasks <= 0 else self.fixed_usd + self.marginal_usd * n_tasks

    def per_task(self, n_tasks: int) -> float:
        return self.total(n_tasks) / n_tasks if n_tasks > 0 else 0.0


ZERO_DECISION_COST = DecisionCost("(none)", "(n/a)", fixed_usd=0.0, marginal_usd=0.0)


# --------------------------------------------------------------------------- mechanisms


@dataclasses.dataclass(frozen=True)
class Mechanism:
    """A routing rule plus what it costs to run.

    ``routes`` maps task_id to the tier this mechanism chose. For the three measured
    mechanisms (`rubric`, `shortcuts`, `none`) it is RECONSTRUCTED from the ledger's
    ``chose__<task>__<tier>`` booleans — the mechanism's real behaviour, not a
    simulation of it. For `fixed-mid` it is a constant, and for `always-weak`
    it is `weak` everywhere with the escalation carried by the retry machinery.
    """

    name: str
    routes: Mapping[str, str]
    decision_cost: DecisionCost = ZERO_DECISION_COST
    start_tier: str | None = None  # overrides `routes`; used by always-weak

    def tier_for(self, task_id: str) -> str:
        if self.start_tier is not None:
            return self.start_tier
        try:
            return self.routes[task_id]
        except KeyError:
            raise MissingGroundTruth(
                f"mechanism {self.name!r} emitted no route for {task_id!r}"
            ) from None


def routes_from_criteria(criteria: Mapping[str, bool]) -> dict[str, str]:
    """Reconstruct ``{task_id: tier}`` from a trial's ``chose__<task>__<tier>`` bits.

    A brief with no true bit is omitted rather than defaulted: the arm did not decide,
    and recording a decision it did not make would fabricate the measurement.
    """
    routes: dict[str, str] = {}
    for key, value in criteria.items():
        if not value or not key.startswith("chose__"):
            continue
        _, _, rest = key.partition("chose__")
        task_id, _, tier = rest.rpartition("__")
        if task_id and tier in TIERS:
            routes[task_id] = tier
    return routes


def modal_route(per_repeat: Sequence[str]) -> str | None:
    """The tier an arm chose most often for one brief across repeats.

    Ties return None rather than picking one. An arm that split 2-2 between `weak` and
    `mid` did not have a settled answer, and recording either as *the* answer would
    invent a determinism the arm did not show.
    """
    if not per_repeat:
        return None
    counts = {tier: per_repeat.count(tier) for tier in set(per_repeat)}
    best = max(counts.values())
    winners = [tier for tier, count in counts.items() if count == best]
    return winners[0] if len(winners) == 1 else None


def agreement(a: Mapping[str, str], b: Mapping[str, str]) -> tuple[int, int]:
    """(agreeing briefs, comparable briefs) between two mechanisms' routings.

    THE PRE-REGISTERED EARLY STOP RUNS ON THIS. If two mechanisms emit the same tier on
    nearly every brief, then C(a) - C(b) collapses to decision_cost(a) - decision_cost(b)
    — the execution and retry terms are identical because the tiers are identical — and
    the cheaper decision wins outright. That comparison needs NO outcome table and no
    ground truth, which is why it can settle the question while the substrate is still
    unrun.

    Only briefs where BOTH sides have a settled modal route are comparable; a brief
    either side was unsettled on is excluded from both numerator and denominator and
    shows up as a shortfall in the denominator rather than as a silent agreement.
    """
    comparable = [task for task in a if task in b]
    return sum(1 for task in comparable if a[task] == b[task]), len(comparable)


def fixed_tier_mechanism(tier: str, task_ids: Sequence[str]) -> Mechanism:
    """`fixed-<tier>` — one tier for everything, zero decision cost."""
    return Mechanism(f"fixed-{tier}", {t: tier for t in task_ids}, ZERO_DECISION_COST)


def always_weak_start() -> Mechanism:
    """`always-weak` — start every task at the weak tier. Zero decision cost.

    RENAMED from `always-weak-escalate`, and the rename is the ruling. Escalation is a
    property of the ENVIRONMENT, not of this mechanism: a failed task gets retried
    somewhere regardless of how its tier was chosen, so `rubric` and `fixed-mid` escalate
    on a failure exactly as this one does. Giving a ladder only to the mechanism whose
    name mentions one would be the mirror image of the bias this study already recorded
    — it would flatter the challenger instead of the incumbent.

    What actually distinguishes this mechanism is therefore only where it STARTS. The
    name now says that and nothing more, and it matches `calibration`'s own
    `always-weak` so the two programmes share one vocabulary.
    """
    return Mechanism("always-weak", {}, ZERO_DECISION_COST, start_tier="weak")


# ------------------------------------------------------------------- retry / quality


@dataclasses.dataclass(frozen=True)
class TaskResult:
    """One task's expected cost and BOTH quality quantities, kept separate.

    Two different things have been called "quality" in this study's two halves, so
    neither is allowed to travel unnamed:

    * ``p_first_attempt`` — the pass rate at the tier the mechanism chose, with no
      repair. This is what `calibration.mechanism_costs` reports.
    * ``p_correct_post_repair`` — P(the task ends correct) after any gate-DETECTED
      failure has been escalated and retried. **This is the pre-registered estimand**
      and the quantity the non-inferiority constraint is written against.

    The exact relation is ``p_correct_post_repair = p_first_attempt + repair_credit``,
    and :attr:`repair_credit` is exposed so the difference is a value that can be
    asserted rather than a discrepancy to be explained.

    Why post-repair is the right estimand, decided rather than assumed: C(m) already
    CHARGES the retry. If quality did not credit the repair that retry buys, every
    mechanism that starts cheap and escalates would pay twice — once in cost, once in
    an unearned quality penalty. It also matches what the work is for: a failure the
    gate caught and repaired is delivered correct, at a price already on the books. An
    escape is not delivered correct, which is why ``detect_rate`` decides which of the
    two a failure becomes.
    """

    expected_cost: float
    p_correct_post_repair: float
    p_first_attempt: float

    @property
    def repair_credit(self) -> float:
        """Quality the retry bought — exactly the term the cost side already paid for."""
        return self.p_correct_post_repair - self.p_first_attempt


def expected_task(
    outcome: TaskOutcome, start_tier: str, *, max_escalations: int = PRIMARY_MAX_ESCALATIONS
) -> TaskResult:
    """Expected execution cost and P(correct) for one task started at *start_tier*.

    The recursion is the retry model, and it is the same for every mechanism so no
    mechanism is credited with a repair loop another is denied:

        pay for the attempt at this tier;
        it passes with p;
        if it fails, the gate notices with probability d, and only then does a retry
        happen (one tier up, if one is left and the escalation budget allows);
        a failure the gate does NOT notice is an escape — it costs nothing more and
        the task ends incorrect.

    That last clause is why a cheap tier is not free. An undetected failure converts a
    cost saving into a quality loss, which is exactly what the pre-registered
    non-inferiority constraint is there to bound.
    """
    index = TIERS.index(start_tier)
    cost = outcome.exec_cost[TIERS[index]]
    p_pass = outcome.pass_rate[TIERS[index]]
    p_correct = p_pass

    if max_escalations > 0 and index + 1 < len(TIERS):
        detect = outcome.detect_rate.get(TIERS[index], 0.0)
        p_retry = (1.0 - p_pass) * detect
        if p_retry > 0.0:
            deeper = expected_task(outcome, TIERS[index + 1], max_escalations=max_escalations - 1)
            cost += p_retry * deeper.expected_cost
            p_correct += p_retry * deeper.p_correct_post_repair

    return TaskResult(expected_cost=cost, p_correct_post_repair=p_correct, p_first_attempt=p_pass)


# ---------------------------------------------------------------------------- the mix


@dataclasses.dataclass(frozen=True)
class Mix:
    """A weighting over tasks — what share of dispatched work each task stands for.

    Mixes are HYPOTHESES about a session's composition, not measurements: nothing in
    this study observed the distribution of task shapes in real sessions. They are
    named and varied precisely so no single one is mistaken for the answer, and the
    decision-relevant output is the break-even (:func:`break_even_hard_fraction`)
    rather than any one mix's headline.
    """

    name: str
    weights: Mapping[str, float]

    def normalised(self) -> dict[str, float]:
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError(f"mix {self.name!r} has no positive weight")
        return {k: v / total for k, v in self.weights.items()}


def uniform_mix(task_ids: Sequence[str]) -> Mix:
    """The bank's own mix. Recorded as unrepresentative: the bank is mid-band heavy."""
    return Mix("bank-uniform", {t: 1.0 for t in task_ids})


def band_mix(name: str, substrate: Substrate, band_weights: Mapping[str, float]) -> Mix:
    """A mix specified by rubric band share, spread evenly within each band.

    Bands come from the pinned thresholds (0-25 weak, 26-55 mid, 56-100 strong), which
    are the rubric's own cuts — so a mix is stated in the vocabulary of the thing under
    test rather than in ad-hoc task names.
    """
    bands: dict[str, list[str]] = {"weak": [], "mid": [], "strong": []}
    for task_id, outcome in substrate.tasks.items():
        score = outcome.rubric_score
        band = "weak" if score <= 25 else ("mid" if score <= 55 else "strong")
        bands[band].append(task_id)

    weights: dict[str, float] = {}
    for band, share in band_weights.items():
        members = bands.get(band) or []
        if not members or share <= 0:
            continue
        for task_id in members:
            weights[task_id] = share / len(members)
    return Mix(name, weights)


# ------------------------------------------------------------------------ the estimand


@dataclasses.dataclass(frozen=True)
class MechanismCost:
    """C(m) for one mechanism on one mix, with the terms kept separable."""

    mechanism: str
    mix: str
    decision_usd: float
    execution_usd: float  # includes the retry expectation
    total_usd: float
    # THE ESTIMAND, named so it cannot be confused with the sibling programme's number.
    # `calibration.mechanism_costs` reports a first-attempt rate; this is P(delivered
    # correct) after gate-detected repair. Both are carried so the difference is a
    # reported value rather than an unexplained gap between two documents.
    quality_post_repair: float
    first_attempt_pass_rate: float
    n_tasks: int
    n_missing: int
    missing: tuple[str, ...]
    # The environment assumption this result was computed under. Stamped on every row so
    # a primary figure and a sensitivity figure can never be mistaken for each other
    # once they are out of the function that produced them.
    max_escalations: int = PRIMARY_MAX_ESCALATIONS

    @property
    def repair_credit(self) -> float:
        """The quality the retry bought — the term the cost side already paid for."""
        return self.quality_post_repair - self.first_attempt_pass_rate


def evaluate(
    mechanism: Mechanism,
    substrate: Substrate,
    mix: Mix,
    *,
    episode_size: int,
    max_escalations: int = PRIMARY_MAX_ESCALATIONS,
) -> MechanismCost:
    """Compute C(m) on *mix*, per dispatched task.

    ``episode_size`` is how many tasks one decision episode routes — the K that the
    fixed decision cost amortises over. It is a property of the WORKFLOW, not of the
    mix, which is why it is a separate argument: the same mix routed one task at a time
    and routed as a nine-task batch give different C(m) for the same mechanism, and
    that difference is one of this study's findings rather than a nuisance to average
    away.
    """
    weights = mix.normalised()
    covered, missing = substrate.coverage(list(weights))

    execution = 0.0
    quality = 0.0
    first_attempt = 0.0
    live_weight = sum(weights[t] for t in covered)
    for task_id in covered:
        outcome = substrate.require(task_id)
        result = expected_task(
            outcome, mechanism.tier_for(task_id), max_escalations=max_escalations
        )
        share = weights[task_id] / live_weight
        execution += share * result.expected_cost
        quality += share * result.p_correct_post_repair
        first_attempt += share * result.p_first_attempt

    decision = mechanism.decision_cost.per_task(episode_size)
    return MechanismCost(
        mechanism=mechanism.name,
        mix=mix.name,
        decision_usd=decision,
        execution_usd=execution,
        total_usd=decision + execution,
        quality_post_repair=quality,
        first_attempt_pass_rate=first_attempt,
        n_tasks=len(covered),
        n_missing=len(missing),
        missing=tuple(missing),
        max_escalations=max_escalations,
    )


def non_inferior(candidate: MechanismCost, best_quality: float, delta: float) -> bool:
    """The pre-registered constraint, on the POST-REPAIR estimand.

    Running it on first-attempt rates instead would penalise every mechanism that
    starts cheap and escalates a second time — once in the retry cost C(m) already
    charges, and again in a quality figure that ignores the repair that retry bought.
    """
    return candidate.quality_post_repair >= best_quality - delta


def rank(results: Sequence[MechanismCost], *, delta: float) -> list[MechanismCost]:
    """Cheapest first among mechanisms that clear the quality constraint.

    Mechanisms that fail the constraint are dropped, not ranked last: C(m) is only
    defined subject to it, so a cheap mechanism that loses quality is not a cheap
    winner, it is out of scope.
    """
    if not results:
        return []
    best_quality = max(r.quality_post_repair for r in results)
    eligible = [r for r in results if non_inferior(r, best_quality, delta)]
    return sorted(eligible, key=lambda r: r.total_usd)


@dataclasses.dataclass(frozen=True)
class RankingSensitivity:
    """The primary ranking, the depth-2 ranking, and whether they disagree.

    The point of returning this rather than writing a paragraph: "depth 2 changes the
    ranking" is a finding that must be as prominent as the headline, and a boolean in a
    result object cannot be quietly dropped from a write-up the way a sentence can.
    """

    primary: tuple[MechanismCost, ...]
    sensitivity: tuple[MechanismCost, ...]

    @property
    def primary_order(self) -> tuple[str, ...]:
        return tuple(m.mechanism for m in self.primary)

    @property
    def sensitivity_order(self) -> tuple[str, ...]:
        return tuple(m.mechanism for m in self.sensitivity)

    @property
    def ranking_changed(self) -> bool:
        return self.primary_order != self.sensitivity_order

    @property
    def winner_changed(self) -> bool:
        """The sharper question: did the CHOICE move, or only the order behind it?"""
        return self.primary_order[:1] != self.sensitivity_order[:1]


def rank_with_sensitivity(
    mechanisms: Sequence[Mechanism],
    substrate: Substrate,
    mix: Mix,
    *,
    episode_size: int,
    delta: float,
) -> RankingSensitivity:
    """Rank at the primary depth and at the sensitivity depth, and compare.

    Every mechanism is evaluated at the SAME depth within each run — escalation is an
    environment property, so `fixed-mid` gets the same ladder `always-weak` does. The
    two runs differ only in how deep that shared ladder goes.
    """

    def _rank(depth: int) -> tuple[MechanismCost, ...]:
        results = [
            evaluate(m, substrate, mix, episode_size=episode_size, max_escalations=depth)
            for m in mechanisms
        ]
        return tuple(rank(results, delta=delta))

    return RankingSensitivity(
        primary=_rank(PRIMARY_MAX_ESCALATIONS),
        sensitivity=_rank(SENSITIVITY_MAX_ESCALATIONS),
    )


def break_even_hard_fraction(
    mechanism: Mechanism,
    reference: Mechanism,
    substrate: Substrate,
    *,
    episode_size: int,
    easy_mix: Mix,
    hard_mix: Mix,
    max_escalations: int = PRIMARY_MAX_ESCALATIONS,
    steps: int = 200,
) -> float | None:
    """The share of hard work at which *mechanism* stops losing to *reference*.

    Sweeps a blend from *easy_mix* to *hard_mix* and returns the first fraction where
    C(mechanism) <= C(reference), or None if it never gets there. This is the output a
    decision actually needs: not "the rubric costs $X on some mix" but "the rubric
    only pays for itself once more than this share of dispatched work is hard" — a
    sentence an owner can check against their own week.
    """
    easy = easy_mix.normalised()
    hard = hard_mix.normalised()
    keys = set(easy) | set(hard)

    for step in range(steps + 1):
        fraction = step / steps
        blended = Mix(
            f"blend@{fraction:.3f}",
            {k: (1 - fraction) * easy.get(k, 0.0) + fraction * hard.get(k, 0.0) for k in keys},
        )
        try:
            a = evaluate(
                mechanism,
                substrate,
                blended,
                episode_size=episode_size,
                max_escalations=max_escalations,
            )
            b = evaluate(
                reference,
                substrate,
                blended,
                episode_size=episode_size,
                max_escalations=max_escalations,
            )
        except MissingGroundTruth:
            continue
        if a.total_usd <= b.total_usd:
            return fraction
    return None


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — the interval reported on every rate in this study.

    Used rather than the normal approximation because the rates here are small counts
    near 0 and 1, where the normal interval runs outside [0, 1] and reports certainty
    the data does not carry.
    """
    if trials <= 0:
        return (0.0, 1.0)
    phat = successes / trials
    denom = 1 + z**2 / trials
    centre = (phat + z**2 / (2 * trials)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / trials + z**2 / (4 * trials**2)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))
