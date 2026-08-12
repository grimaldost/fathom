"""Acceptance verifier for refactor-dedupe-validators (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed original ``forms/common.py`` and the shipped suite — come from
this task directory; both are identical for every arm, so reading them leaks no
scenario identity (ADR-0003).

**Genre: refactor.** The bank's other rungs are bug fixes whose instruction points at a
symptom. This one names every edit site, so the cross-shape floor does not fire and its
rubric score is the additive total alone — which is what makes it a discordant rung
between the points model and the floor+shortcut model (README § *The two models under
test*). Its headroom comes not from a hidden fix site but from the fact that the three
copies have DRIFTED: converging them requires reading the rules document rather than
lifting whichever copy is nearest.

**Delegation is checked behaviourally, not by reading source.** A source scan for
"is there still a regex in signup.py" is brittle against legitimate variation and
rewards cosmetics. Instead the checks replace ``forms.common.check_email`` and observe
whether all three validators change with it — patched on the module AND on each form
module, so both ``from forms import common`` and ``from forms.common import
check_email`` are covered.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates on
``standard`` only.
"""

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "forms"
MODULE = "common.py"
BUGGY_ORIGINAL = HERE / "original" / "common.py"
SHIPPED_TESTS = HERE / "original" / "tests"

FORMS = (
    ("forms.signup", "validate_signup"),
    ("forms.profile", "validate_profile"),
    ("forms.invite", "validate_invite"),
)

STANDARD = [
    "forms_import",
    "all_three_accept_a_plain_address",
    "converged_rules_all_three",
    "all_three_delegate_to_common",
    "invite_stays_case_insensitive",
    "no_regression",
    "regression_test_present",
]

# RULES.md's own worked lists, plus the cases the four rules cover but the document
# does not spell out. (address, valid?)
GRID = [
    ("a@example.com", True),
    ("a+tag@example.com", True),
    ("first.last@example.co.uk", True),
    ("A@Example.COM", True),
    ("user9@sub.example.com", True),
    ("a@example.com.", True),
    ("a@example", False),
    (".a@example.com", False),
    ("a..b@example.com", False),
    ("a@@example.com", False),
    ("@example.com", False),
    ("a@.", False),
    ("A..B@Example.COM", False),
    (".A@EXAMPLE.COM", False),
    ("a.b+c@example.com", True),
    ("ab@x.y", True),
]

# The three rules the drifted copies disagree on: a leading dot (R2), consecutive
# dots (R3), and case-insensitive comparison.
DRIFTED = [
    (".a@example.com", False),
    ("a..b@example.com", False),
    ("A@Example.COM", True),
    (".A@Example.COM", False),
    ("A..B@Example.COM", False),
]


def _load_all(view: Path):
    """Import ``forms.common`` and the three form modules in ONE consistent set.

    ``bankverify.import_candidate`` purges the package from ``sys.modules`` on every
    call, so importing the four modules with four calls hands back objects from four
    different import generations — and a ``check_email`` patched on the first
    generation's ``forms.common`` is invisible to the last generation's
    ``forms.signup``. One purge, one path insertion, one generation.
    """
    root = bv.import_root_for(view, PACKAGE)
    if root is None:
        return None
    for key in [k for k in sys.modules if k == PACKAGE or k.startswith(PACKAGE + ".")]:
        del sys.modules[key]
    root_str = str(root)
    sys.path.insert(0, root_str)
    try:
        common = importlib.import_module(f"{PACKAGE}.common")
        modules = []
        for dotted, name in FORMS:
            mod = importlib.import_module(dotted)
            if not hasattr(mod, name):
                return None
            modules.append((mod, name))
    except Exception:
        return None
    finally:
        try:
            sys.path.remove(root_str)
        except ValueError:
            pass
    return common, modules


def _validators(view: Path):
    """The three validator callables, or None when any form module will not load."""
    loaded = _load_all(view)
    if loaded is None:
        return None
    _common, modules = loaded
    return [getattr(mod, name) for mod, name in modules]


def _agrees(fns, cases) -> bool:
    return all(bool(fn(addr)) is expected for fn in fns for addr, expected in cases)


def _with_patched_common(view: Path, replacement):
    """Swap ``check_email`` everywhere, then return the three validators.

    The replacement is bound on ``forms.common`` and, when a form module holds its own
    reference (``from forms.common import check_email``), on that module too — so a
    delegating candidate is detected under either import style. Returns ``None`` when
    ``forms.common`` has no ``check_email`` at all, which is itself the failure every
    criterion using this helper is meant to record.
    """
    loaded = _load_all(view)
    if loaded is None:
        return None
    common, modules = loaded
    if not hasattr(common, "check_email"):
        return None
    common.check_email = replacement
    for mod, _name in modules:
        if hasattr(mod, "check_email"):
            mod.check_email = replacement
    return [getattr(mod, name) for mod, name in modules]


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])

    def validators():
        loaded = _validators(view)
        if loaded is None:
            raise RuntimeError("a form module did not import")
        return loaded

    def patched(replacement, address: str, expected: bool) -> bool:
        """All three validators answer *expected* on *address* once common is swapped."""
        fns = _with_patched_common(view, replacement)
        return bool(fns) and all(bool(fn(address)) is expected for fn in fns)

    results = {
        # --- thin: the package still loads and still accepts a plain address -----
        "forms_import": bv.check(lambda: len(validators()) == 3),
        "all_three_accept_a_plain_address": bv.check(
            lambda: all(fn("a@example.com") for fn in validators())
        ),
        # --- standard: the three copies now agree with the document on the rules
        #     they had drifted apart on, and they do so through ONE implementation -
        "converged_rules_all_three": bv.check(lambda: _agrees(validators(), DRIFTED)),
        "all_three_delegate_to_common": bv.check(
            lambda: patched(lambda _e: False, "a@example.com", False)
        ),
        # A regression guard, TRUE before the arm starts: invite already lower-cases.
        # Kept in the standard oracle (it still gates the exit code) but excluded from
        # `hard_criteria` by the derivation rule, because a criterion satisfied at the
        # starting state measures no capability.
        "invite_stays_case_insensitive": bv.check(
            lambda: validators()[2]("A@EXAMPLE.COM") == validators()[2]("a@example.com")
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: an independent check the instruction never names — the whole
        #     grid RULES.md's four rules imply, including the POSITIVE cases. A
        #     converged implementation that also invented a rule (rejecting `+`
        #     addressing) satisfies every standard criterion and fails here. --------
        "rules_match_the_document_exactly": bv.check(lambda: _agrees(validators(), GRID)),
        "delegation_survives_a_rule_change": bv.check(
            lambda: patched(lambda _e: True, ".a@example.com", True)
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
