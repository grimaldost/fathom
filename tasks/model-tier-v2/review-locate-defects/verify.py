"""Acceptance verifier for review-locate-defects (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed original ``billing/prorate.py`` and the shipped suite — come
from this task directory; both are identical for every arm, so reading them leaks no
scenario identity (ADR-0003).

**Genre: review.** The deliverable is a judgement, not a patch, and the arm is told
not to touch the code. That is a routing decision the rubric scores every day and this
bank had no rung for.

**The artifact-task exemption, asserted not assumed.** A review changes no code, so
``regression_test_present`` — "did the arm add a test that covers what it fixed" — has
no referent. This task emits ``code_unchanged`` in its place: the module must come back
byte-identical to the stash. Both are hygiene criteria, excluded from ``hard_criteria``
by the derivation rule, and ``tests/test_bank_model_tier_v2.py`` asserts the swap rather
than leaving it to prose.

**Parsing is deliberately forgiving about everything except the decision.** A defect
line counts when the `## Defects` section names the function; the rule id may be in
parentheses or not, the prose is unread. What is graded is which functions the review
named and which it did not — recall and precision — because that is the whole content
of a review.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates on
``standard`` only.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "billing"
MODULE = "prorate.py"
ORIGINAL_MODULE = HERE / "original" / "prorate.py"
SHIPPED_TESTS = HERE / "original" / "tests"

# The three functions that do not implement their rule, and the three that do.
DEFECTIVE = {"days_in_cycle": "P1", "unused_days": "P2", "credit": "P3"}
CLEAN = ("charge", "net", "is_refund")
ALL_FUNCTIONS = tuple(DEFECTIVE) + CLEAN

STANDARD = [
    "review_file_present",
    "names_at_least_one_defect",
    "names_every_defect",
    "cites_a_rule_for_every_named_defect",
    "no_regression",
    "code_unchanged",
]


def _defects_section(view: Path) -> str | None:
    """The body of the `## Defects` section of REVIEW.md, or None."""
    for candidate in (view / "REVIEW.md", view / "review.md"):
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace")
            break
    else:
        return None
    match = re.search(
        r"^\s{0,3}#{1,6}\s*defects\b(.*?)(?=^\s{0,3}#{1,6}\s|\Z)", text, re.I | re.S | re.M
    )
    return match.group(1) if match else None


def _named(view: Path) -> set[str]:
    """Function names the Defects section calls out, one per bullet line."""
    body = _defects_section(view)
    if body is None:
        return set()
    found: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("-", "*", "+")):
            continue
        # Only the head of the line names the subject; the prose after the colon may
        # mention any function without accusing it.
        head = stripped.lstrip("-*+ ").split(":", 1)[0]
        for fn in ALL_FUNCTIONS:
            if re.search(rf"\b{re.escape(fn)}\b", head):
                found.add(fn)
    return found


def _rule_cited_for_each(view: Path) -> bool:
    """Every bullet that names a function also carries that function's rule id."""
    body = _defects_section(view)
    if not body:
        return False
    seen = 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("-", "*", "+")):
            continue
        head = stripped.lstrip("-*+ ").split(":", 1)[0]
        for fn, rule in DEFECTIVE.items():
            if re.search(rf"\b{re.escape(fn)}\b", head):
                if not re.search(rf"\b{rule}\b", head, re.I):
                    return False
                seen += 1
    return seen == len(DEFECTIVE)


def _code_unchanged(view: Path) -> bool:
    target = bv.find_module_file(view, PACKAGE, MODULE)
    if target is None or not ORIGINAL_MODULE.is_file():
        return False
    return target.read_text(encoding="utf-8") == ORIGINAL_MODULE.read_text(encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])

    results = {
        # --- thin: a review exists and accuses something ------------------------
        "review_file_present": bv.check(lambda: _defects_section(view) is not None),
        "names_at_least_one_defect": bv.check(lambda: bool(_named(view) & set(DEFECTIVE))),
        # --- standard: recall over the planted defects, each tied to its rule ----
        "names_every_defect": bv.check(lambda: set(DEFECTIVE) <= _named(view)),
        "cites_a_rule_for_every_named_defect": bv.check(lambda: _rule_cited_for_each(view)),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        # The artifact-task stand-in for `regression_test_present`: this task forbids
        # a code change, so the preservation check IS the hygiene criterion. TRUE at
        # the starting state, therefore never admissible as a hard criterion.
        "code_unchanged": bv.check(lambda: _code_unchanged(view)),
        # --- strong: precision. A review that names every function has perfect
        #     recall and has decided nothing; one false positive is tolerated, two
        #     is a shotgun. The instruction says so, and nothing in the standard
        #     oracle measures it. ---------------------------------------------------
        "precision_within_one_false_positive": bv.check(
            lambda: len(_named(view) & set(CLEAN)) <= 1 and bool(_named(view) & set(DEFECTIVE))
        ),
        "names_no_clean_function": bv.check(
            lambda: not (_named(view) & set(CLEAN)) and bool(_named(view) & set(DEFECTIVE))
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
