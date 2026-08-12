"""Acceptance verifier for fix-ledger-replay (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/live.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

Backend parity. ``replay`` is correct by construction (it sees the whole log);
``fold`` is the incremental path and must reach the same answer without one. The
instruction names a single post followed by its void. Decrementing the count in the
void branch settles exactly that case and still double-counts a repeated void — the
standard oracle sits there. The strong oracle sits on a void that arrives BEFORE the
post it cancels, and on a prefix sweep of a longer log: both need the incremental
path to remember which ids are void, which is the actual root cause and which no
patch to the reported case reaches.

The expected answers are recomputed here from the documented rules, not read from the
candidate's ``replay``, so "make them agree by breaking replay" gains nothing.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "book"
MODULE = "live.py"
BUGGY_ORIGINAL = HERE / "original" / "live.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "parity_posts_only",
    "parity_single_void",
    "parity_duplicate_void",
    "fold_excludes_voided",
    "no_regression",
    "regression_test_present",
]


def post(entry_id, amount):
    return {"kind": "post", "id": entry_id, "amount": amount}


def void(entry_id):
    return {"kind": "void", "id": entry_id}


POSTS_ONLY = [post("a", 100), post("b", 50), post("c", 25)]
SINGLE_VOID = [post("a", 100), void("a")]  # the log the instruction names
DUPLICATE_VOID = [post("a", 100), post("b", 50), void("a"), void("a")]
MIXED = [post("a", 100), post("b", 50), void("a"), post("c", 25)]
VOID_FIRST = [void("a"), post("a", 100), post("b", 50)]
SWEEP = [
    post("a", 100),
    post("b", 50),
    void("a"),
    post("c", 25),
    void("z"),
    post("d", 10),
    void("c"),
    post("e", 5),
    void("b"),
    post("f", 1),
    void("b"),
    post("g", 7),
    void("h"),
    post("h", 3),
    post("i", 2),
]


def expected(events) -> dict:
    """The documented totals, recomputed here rather than taken from the candidate."""
    voided = {e["id"] for e in events if e["kind"] == "void"}
    kept = [e for e in events if e["kind"] == "post" and e["id"] not in voided]
    return {"total": sum(e["amount"] for e in kept), "count": len(kept)}


def _parity(mod_live, mod_replay, events) -> bool:
    want = expected(events)
    return mod_live.fold(events) == want and mod_replay.replay(events) == want


def _prefix_sweep(mod_live, mod_replay) -> bool:
    return all(_parity(mod_live, mod_replay, SWEEP[:n]) for n in range(len(SWEEP) + 1))


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    live = bv.import_candidate(view, "book.live", PACKAGE)
    rep = bv.import_candidate(view, "book.replay", PACKAGE)

    results = {
        # --- thin: the anchor plus the log the instruction names ------------------
        "parity_posts_only": bv.check(lambda: _parity(live, rep, POSTS_ONLY)),
        "parity_single_void": bv.check(lambda: _parity(live, rep, SINGLE_VOID)),
        # --- standard: a repeated void, and the documented semantics of a voided
        #     entry in a longer log — neither named in the instruction -------------
        "parity_duplicate_void": bv.check(lambda: _parity(live, rep, DUPLICATE_VOID)),
        "fold_excludes_voided": bv.check(lambda: live.fold(MIXED) == {"total": 75, "count": 2}),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: out-of-order arrival, and every prefix of a longer log ------
        "parity_void_before_post": bv.check(lambda: _parity(live, rep, VOID_FIRST)),
        "parity_prefix_sweep": bv.check(lambda: _prefix_sweep(live, rep)),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
