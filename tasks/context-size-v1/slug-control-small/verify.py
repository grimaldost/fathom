"""Acceptance verifier for slug-control-small (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/slug.py``) and the shipped suite
(``original/tests/``) — come from this task directory; identical for every arm, so reading
them leaks no scenario identity (ADR-0003). Emits a flat ``{criterion: bool}`` JSON and
exits 0 iff every criterion holds.

NEGATIVE CONTROL: the whole bug lives in one self-contained module (``slug.py``) — no
contract modules to find. Both criteria fall to a local edit of ``slugify``. The matched
``-large`` twin still buries ``slug.py`` among ~40 siblings, but those siblings reference
nothing under test (a star around a hub), so this pair isolates the effect of pure module
count on a single-file fix.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bugfix_verify` resolves

import bugfix_verify as bv  # noqa: E402

PACKAGE = "textkit"
MODULE = "slug.py"
BUGGY_ORIGINAL = HERE / "original" / "slug.py"
SHIPPED_TESTS = HERE / "original" / "tests"


def _slug(view: Path):
    return bv.import_candidate(view, "textkit.slug", PACKAGE)


def _collapses_repeated_separators(view: Path) -> bool:
    """Runs of separators collapse to a single hyphen."""
    mod = _slug(view)
    if mod is None or not hasattr(mod, "slugify"):
        return False
    try:
        return mod.slugify("Hello   World") == "hello-world"
    except Exception:
        return False


def _strips_edges(view: Path) -> bool:
    """A slug never starts or ends with a stray hyphen."""
    mod = _slug(view)
    if mod is None or not hasattr(mod, "slugify"):
        return False
    try:
        return mod.slugify("  Hi!  ") == "hi"
    except Exception:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    view = Path(sys.argv[1])
    results = {
        "collapses_repeated_separators": _collapses_repeated_separators(view),
        "strips_edges": _strips_edges(view),
        "no_regression": bv.no_regression(view, SHIPPED_TESTS),
        "regression_test_present": bv.regression_test_present(
            view, PACKAGE, MODULE, BUGGY_ORIGINAL
        ),
    }
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
