"""Acceptance verifier for fix-strip-unicode (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/core.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

The instruction names only Latin-1 accented words. The canonical shortcut for that
report — ``unicodedata.normalize("NFKD", text).encode("ascii", "ignore")`` — fixes
exactly the reported words and keeps deleting every non-ASCII character that is not
an accent, which is the *original* bug. The standard oracle's criteria sit on those
survivors (non-Latin scripts, currency and punctuation), none of which the
instruction mentions.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "textnorm"
MODULE = "core.py"
BUGGY_ORIGINAL = HERE / "original" / "core.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "ascii_unchanged",
    "accent_stripped_reported",
    "non_latin_preserved",
    "symbols_preserved",
    "no_regression",
    "regression_test_present",
]

# Composed / decomposed spellings of the same two words: a correct implementation
# maps both to the same output. Written with explicit escapes so an editor cannot
# silently normalise the pair into a single spelling.
COMPOSED = "café naïve"  # precomposed (NFC)
DECOMPOSED = "café naïve"  # the same two words, decomposed (NFD)


def _strip(view: Path):
    mod = bv.import_candidate(view, "textnorm.core", PACKAGE)
    if mod is None or not hasattr(mod, "strip_accents"):
        return None
    return mod.strip_accents


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    strip = _strip(view)

    results = {
        # --- thin: the anchor plus the words the instruction names ---------------
        "ascii_unchanged": bv.check(
            lambda: strip("hello world 42") == "hello world 42" and strip("") == ""
        ),
        "accent_stripped_reported": bv.check(
            lambda: strip("café") == "cafe" and strip("naïve") == "naive"
        ),
        # --- standard: everything that is NOT an accent must survive -------------
        "non_latin_preserved": bv.check(
            lambda: strip("東京 café") == "東京 cafe" and strip("Ωμεγα カフェ") == "Ωμεγα カフェ"
        ),
        "symbols_preserved": bv.check(
            lambda: strip("€10 — ok") == "€10 — ok" and strip("résumé » 50%") == "resume » 50%"
        ),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: independent checks that exercise the root cause through
        #     inputs the instruction never names -----------------------------------
        "decomposed_input_equivalent": bv.check(
            lambda: strip(DECOMPOSED) == strip(COMPOSED) == "cafe naive"
        ),
        "covers_unlisted_accents": bv.check(
            lambda: strip("ā ř ő") == "a r o" and strip("Ωμέγα") == "Ωμεγα"
        ),
        "idempotent_and_mark_free": bv.check(
            lambda: all(
                strip(strip(s)) == strip(s)
                and not any(unicodedata.combining(ch) for ch in strip(s))
                for s in (COMPOSED, DECOMPOSED, "東京 café", "āř", "")
            )
        ),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
