"""Acceptance verifier for fix-graph-cycle (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/builder.py``) and the shipped
suite (``original/tests/``) — come from this task directory; both are identical for
every arm, so reading them leaks no scenario identity (ADR-0003).

Displaced cause. The symptom surfaces in ``traverse.topo_order``: a duplicated edge
inflates the pending-dependency count, the queue never drains, and the walk reports a
cycle that is not there. The fault is in the builder, which appends the edge twice.
De-duplicating inside ``topo_order`` clears the reported symptom and leaves
``report.dependency_count`` and ``report.tree`` counting the same dependency twice —
the standard oracle sits there, together with a genuine cycle that must still be
reported (so deleting the cycle check is not a way through). The strong oracle reads
``Graph.neighbours``, the documented accessor, which the instruction never names.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "deps"
MODULE = "builder.py"
BUGGY_ORIGINAL = HERE / "original" / "builder.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "topo_order_plain",
    "topo_order_with_duplicate_edge",
    "dependency_count_deduplicated",
    "tree_lists_each_dependency_once",
    "real_cycle_still_raises",
    "no_regression",
    "regression_test_present",
]

PLAIN = (("app", "lib"), ("lib", "core"))
# The reported shape: the same dependency listed twice.
DOUBLED = (("app", "lib"), ("app", "lib"), ("lib", "core"))
# Duplicates everywhere — a build file that lists everything twice.
ALL_DOUBLED = (
    ("app", "lib"),
    ("app", "lib"),
    ("app", "core"),
    ("app", "core"),
    ("lib", "core"),
    ("lib", "core"),
)
CYCLIC = (("a", "b"), ("b", "c"), ("c", "a"))


class _Pkg:
    def __init__(self, view: Path):
        self.builder = bv.import_candidate(view, "deps.builder", PACKAGE)
        self.traverse = bv.import_candidate(view, "deps.traverse", PACKAGE)
        self.report = bv.import_candidate(view, "deps.report", PACKAGE)

    def graph(self, edges):
        graph = self.builder.Graph()
        for src, dst in edges:
            self.builder.add_edge(graph, src, dst)
        return graph


def _real_cycle_raises(pkg) -> bool:
    graph = pkg.graph(CYCLIC)
    try:
        pkg.traverse.topo_order(graph)
    except pkg.traverse.CycleError:
        return True
    return False


def _no_duplicate_neighbours(pkg) -> bool:
    graph = pkg.graph(ALL_DOUBLED)
    for name in graph.nodes():
        neighbours = graph.neighbours(name)
        if len(neighbours) != len(set(neighbours)):
            return False
    return sorted(graph.neighbours("app")) == ["core", "lib"]


def _add_edge_idempotent(pkg) -> bool:
    """Building with every edge listed twice must give the same graph as once."""
    once = pkg.graph((("app", "lib"), ("app", "core"), ("lib", "core")))
    twice = pkg.graph(ALL_DOUBLED)
    if once.nodes() != twice.nodes():
        return False
    return all(once.neighbours(n) == twice.neighbours(n) for n in once.nodes())


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    pkg = _Pkg(view)

    results = {
        # --- thin: the anchor plus the graph the instruction names ----------------
        "topo_order_plain": bv.check(
            lambda: pkg.traverse.topo_order(pkg.graph(PLAIN)) == ["core", "lib", "app"]
        ),
        "topo_order_with_duplicate_edge": bv.check(
            lambda: pkg.traverse.topo_order(pkg.graph(DOUBLED)) == ["core", "lib", "app"]
        ),
        # --- standard: the other readers of the same edges, and the cycle check
        #     that must survive — none of them named in the instruction ------------
        "dependency_count_deduplicated": bv.check(
            lambda: (
                pkg.report.dependency_count(pkg.graph(DOUBLED), "app") == 1
                and pkg.report.dependency_count(pkg.graph(ALL_DOUBLED), "app") == 2
            )
        ),
        "tree_lists_each_dependency_once": bv.check(
            lambda: pkg.report.tree(pkg.graph(DOUBLED), "app") == ["app", "  lib", "    core"]
        ),
        "real_cycle_still_raises": bv.check(lambda: _real_cycle_raises(pkg)),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the documented accessor itself, and idempotence of the build
        #     — the invariant at its source ----------------------------------------
        "neighbours_lists_each_dependency_once": bv.check(lambda: _no_duplicate_neighbours(pkg)),
        "add_edge_idempotent": bv.check(lambda: _add_edge_idempotent(pkg)),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
