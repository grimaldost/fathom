"""Acceptance verifier for plan-migration-order (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed original ``schema/migrations.py`` and the shipped suite — come
from this task directory; both are identical for every arm, so reading them leaks no
scenario identity (ADR-0003).

**Genre: planning.** The deliverable is an ordering and its justification, not a patch.
Nothing in the bank measured that shape, and the rubric routes planning work every
day.

**The artifact-task exemption, asserted not assumed.** A plan changes no code, so
``regression_test_present`` has no referent; this task emits ``code_unchanged`` in its
place, and ``tests/test_bank_model_tier_v2.py`` asserts the swap.

The constraints are re-derived here from the candidate's own migration data rather than
hard-coded, so a plan is graded against the set that was actually in its workspace.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates on
``standard`` only.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "schema"
MODULE = "migrations.py"
ORIGINAL_MODULE = HERE / "original" / "migrations.py"
SHIPPED_TESTS = HERE / "original" / "tests"

CONSTRAINTS = ("C1", "C2", "C3")

STANDARD = [
    "plan_file_present",
    "every_migration_listed_once",
    "dependencies_respected",
    "backfills_after_every_add",
    "same_table_contiguous",
    "no_regression",
    "code_unchanged",
]


def _section(view: Path, heading: str) -> str | None:
    for candidate in (view / "PLAN.md", view / "plan.md"):
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace")
            break
    else:
        return None
    match = re.search(
        rf"^\s{{0,3}}#{{1,6}}\s*{heading}\b(.*?)(?=^\s{{0,3}}#{{1,6}}\s|\Z)",
        text,
        re.I | re.S | re.M,
    )
    return match.group(1) if match else None


def _migrations(view: Path) -> dict[str, dict]:
    mod = bv.import_candidate(view, f"{PACKAGE}.{MODULE[:-3]}", PACKAGE)
    if mod is None or not hasattr(mod, "MIGRATIONS"):
        raise RuntimeError("the migration set did not import")
    return {m["id"]: m for m in mod.MIGRATIONS}


def _order(view: Path) -> list[str]:
    """Migration ids from the `## Order` section, in the order they appear."""
    body = _section(view, "order")
    if body is None:
        return []
    out = []
    for line in body.splitlines():
        token = line.strip().lstrip("-*+ ").strip("`").strip()
        if re.fullmatch(r"m\d+", token, re.I):
            out.append(token.lower())
    return out


def _complete(view: Path) -> bool:
    order, known = _order(view), _migrations(view)
    return len(order) == len(known) and set(order) == set(known)


def _dependencies_respected(view: Path) -> bool:
    order, known = _order(view), _migrations(view)
    if not _complete(view):
        return False
    position = {mid: i for i, mid in enumerate(order)}
    return all(position[dep] < position[mid] for mid, m in known.items() for dep in m["depends_on"])


def _backfills_after_every_add(view: Path) -> bool:
    """C3: EVERY add precedes EVERY backfill, dependency or not."""
    order, known = _order(view), _migrations(view)
    if not _complete(view):
        return False
    last_add = max((i for i, mid in enumerate(order) if known[mid]["kind"] == "add"), default=-1)
    first_backfill = min(
        (i for i, mid in enumerate(order) if known[mid]["kind"] == "backfill"), default=len(order)
    )
    return last_add < first_backfill


def _same_table_contiguous(view: Path) -> bool:
    """C2, scoped to a phase: within the adds, and within the backfills, contiguous.

    Whole-order contiguity is unsatisfiable alongside C3 — C3 splits every table that
    has both an add and a backfill into two runs — so the constraint is read on the
    two phases separately, which is what CONSTRAINTS.md states and what the reference
    order satisfies.
    """
    order, known = _order(view), _migrations(view)
    if not _complete(view):
        return False
    for kind in ("add", "backfill"):
        phase = [mid for mid in order if known[mid]["kind"] == kind]
        seen: set[str] = set()
        previous = None
        for mid in phase:
            table = known[mid]["table"]
            if table != previous:
                if table in seen:
                    return False
                seen.add(table)
                previous = table
    return True


def _rationale_cites_every_constraint(view: Path) -> bool:
    """A `## Rationale` line per constraint, each opening with that constraint's id."""
    body = _section(view, "rationale")
    if not body:
        return False
    opened = set()
    for line in body.splitlines():
        head = line.strip().lstrip("-*+ ")
        for cid in CONSTRAINTS:
            if re.match(rf"^{cid}\b", head, re.I):
                opened.add(cid)
    return opened == set(CONSTRAINTS)


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
        # --- thin: a plan exists and covers the whole set -----------------------
        "plan_file_present": bv.check(lambda: _section(view, "order") is not None),
        "every_migration_listed_once": bv.check(lambda: _complete(view)),
        # --- standard: C1 (which a dependency sort already gives), then the two
        #     constraints a dependency sort will not find ------------------------
        "dependencies_respected": bv.check(lambda: _dependencies_respected(view)),
        "backfills_after_every_add": bv.check(lambda: _backfills_after_every_add(view)),
        "same_table_contiguous": bv.check(lambda: _same_table_contiguous(view)),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        # The artifact-task stand-in for `regression_test_present` — see the module
        # docstring. TRUE at the starting state, so never admissible as hard.
        "code_unchanged": bv.check(lambda: _code_unchanged(view)),
        # --- strong: the plan has to say WHY. An order that satisfies all three
        #     constraints by luck and an order that satisfies them by reasoning are
        #     the same artifact under the standard oracle and different work. ------
        "rationale_cites_every_constraint": bv.check(
            lambda: _rationale_cites_every_constraint(view)
        ),
        "order_is_deterministic_and_bare": bv.check(
            lambda: _complete(view) and len(_order(view)) == len(set(_order(view)))
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
