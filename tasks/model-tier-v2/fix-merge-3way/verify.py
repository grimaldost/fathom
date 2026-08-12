"""Acceptance verifier for fix-merge-3way (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/merge.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

Cross-module, duplicated rule. The four documented merge rules are implemented twice
— once in ``merge.merge``, once in ``nested.merge_tree`` — and both copies get two of
them wrong: an agreed change is reported as a conflict, and a deletion writes the
``MISSING`` marker into the result instead of dropping the key. The instruction names
the first defect in the flat entry point only. A patch there leaves the nested copy
reporting the same false conflict — the standard oracle sits there, with a genuine
conflict that must still be reported. The strong oracle sits on the deletion rule,
which the instruction never mentions and which a copy of the same-change patch does
not touch; a fix that routes both entry points through one complete rule gets it.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "cfg"
MODULE = "merge.py"
BUGGY_ORIGINAL = HERE / "original" / "merge.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "merge_one_sided_change",
    "merge_same_change_agrees",
    "nested_same_change_agrees",
    "true_conflict_still_reported",
    "no_regression",
    "regression_test_present",
]


def _is_conflict(value, base, ours, theirs) -> bool:
    """A Conflict carrying the three sides, without importing the candidate's class."""
    return (
        getattr(value, "base", object()) == base
        and getattr(value, "ours", object()) == ours
        and getattr(value, "theirs", object()) == theirs
    )


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    flat = bv.import_candidate(view, "cfg.merge", PACKAGE)
    tree = bv.import_candidate(view, "cfg.nested", PACKAGE)

    results = {
        # --- thin: the anchor plus the case the instruction names -----------------
        "merge_one_sided_change": bv.check(
            lambda: (
                flat.merge({"a": 1, "b": 2}, {"a": 2, "b": 2}, {"a": 1, "b": 2}) == {"a": 2, "b": 2}
            )
        ),
        "merge_same_change_agrees": bv.check(
            lambda: flat.merge({"a": 1}, {"a": 2}, {"a": 2}) == {"a": 2}
        ),
        # --- standard: the same rule in the nested entry point, which the
        #     instruction never names, and the conflict that must survive ----------
        "nested_same_change_agrees": bv.check(
            lambda: (
                tree.merge_tree(
                    {"db": {"port": 1, "host": "h"}},
                    {"db": {"port": 2, "host": "h"}},
                    {"db": {"port": 2, "host": "h"}},
                )
                == {"db": {"port": 2, "host": "h"}}
            )
        ),
        "true_conflict_still_reported": bv.check(
            lambda: (
                _is_conflict(flat.merge({"a": 1}, {"a": 2}, {"a": 3})["a"], 1, 2, 3)
                and _is_conflict(
                    tree.merge_tree({"db": {"p": 1}}, {"db": {"p": 2}}, {"db": {"p": 3}})["db"][
                        "p"
                    ],
                    1,
                    2,
                    3,
                )
            )
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the deletion rule, in both entry points — documented in the
        #     README, named nowhere in the instruction ----------------------------
        "deletion_applies_flat": bv.check(
            lambda: (
                flat.merge({"a": 1, "b": 2}, {"b": 2}, {"a": 1, "b": 2}) == {"b": 2}
                and flat.merge({"a": 1, "b": 2}, {"b": 2}, {"b": 2}) == {"b": 2}
            )
        ),
        "deletion_applies_nested": bv.check(
            lambda: (
                tree.merge_tree(
                    {"db": {"port": 1, "host": "h"}},
                    {"db": {"host": "h"}},
                    {"db": {"port": 1, "host": "h"}},
                )
                == {"db": {"host": "h"}}
            )
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
