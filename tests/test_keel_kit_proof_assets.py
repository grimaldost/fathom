"""Guards for the `scenarios/keel-kit-proof/` arms — the properties the proof run's reading depends on.

The proof run adds two generations of the kit to the pre-registered ablation, so it can separate
two independent edits that the original bank could not:

    a-full-014   keel 0.14.0 as shipped                       (3,789 w)
    b-vnext-full after the T0.5 relocations                   (2,669 w)
    c-vnext-core after the candidate core cut                 (2,438 w)
    d-bare       nothing                                      (    0 w)

Three things would silently invalidate that reading, and `fathom validate` catches none of them:

1. `c-vnext-core` stops being a strict deletion of `b-vnext-full`, so a B→C gap is no longer
   attributable to the removed prose rather than to a rewrite.
2. An arm starts differing in something other than the injected body, so the ablation has two axes.
3. An asset is edited after the run, so the published report describes a body that no longer
   exists. The shas below are the provenance pin; `a-full-014` must still resolve to the byte-
   identical asset the pre-registered `scenarios/keel-kit/a-full.toml` injects.

Stdlib only; runs without uv (`python tests/test_keel_kit_proof_assets.py`).
"""

from __future__ import annotations

import hashlib
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARMS = REPO / "scenarios" / "keel-kit-proof"
PREREG = REPO / "scenarios" / "keel-kit"

# Provenance pins. `kit-full.md` is the pre-registered asset and is NOT owned by this
# directory — the pin is here so a change to it under the proof run is loud.
SHA = {
    "kit-full.md": "5685cfac7f3c3172ca8c1b8d479bc1100a9181de6ee153344e9c313cedd9870a",
    "kit-vnext-full.md": "a8570b7f422462eb1944dd6a1bf7e00214b399991502ed6ecb519042cb660c8c",
    "kit-vnext-core.md": "f286c0a9eb92eff77dff7eceec2e9263f813b6a49b08d3a6521002b1ccf5774b",
}

# The framing preamble every armed arm carries identically. If it ever differs between
# arms, the injected-body axis is contaminated by the framing.
PREAMBLE = (
    "The project you are working in uses a spec-first method. Its kit is reproduced below: "
    "read it and\nfollow it when you write or repair a design spec.\n"
)


def load(name: str) -> dict:
    return tomllib.loads((ARMS / name).read_text(encoding="utf-8"))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def nonblank(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def is_ordered_subsequence(sub: list[str], sup: list[str]) -> bool:
    it = iter(sup)
    return all(any(x == y for y in it) for x in sub)


def injected(arm: str) -> Path:
    cfg = load(arm)
    return (ARMS / cfg["context"]["inject"]).resolve()


ARM_FILES = ["a-full-014.toml", "b-vnext-full.toml", "c-vnext-core.toml", "d-bare.toml"]
ARMED = ["a-full-014.toml", "b-vnext-full.toml", "c-vnext-core.toml"]


class TestAssetProvenance(unittest.TestCase):
    def test_assets_match_their_pins(self):
        for name, want in SHA.items():
            p = next(
                q
                for q in (
                    ARMS / "assets" / name,
                    PREREG / "assets" / name,
                )
                if q.exists()
            )
            self.assertEqual(sha256(p), want, f"{name} changed since the proof run")

    def test_a_full_reuses_the_preregistered_asset(self):
        """Arm A must inject the SAME file the pre-registered bank injects, not a copy."""
        pre = tomllib.loads((PREREG / "a-full.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            injected("a-full-014.toml"),
            (PREREG / pre["context"]["inject"]).resolve(),
        )

    def test_every_armed_arm_carries_the_same_preamble(self):
        for arm in ARMED:
            text = injected(arm).read_text(encoding="utf-8")
            self.assertTrue(text.startswith(PREAMBLE), f"{arm}: framing preamble differs")


class TestDeletionOnly(unittest.TestCase):
    def test_core_is_a_strict_ordered_deletion_of_vnext_full(self):
        full = nonblank(injected("b-vnext-full.toml").read_text(encoding="utf-8"))
        core = nonblank(injected("c-vnext-core.toml").read_text(encoding="utf-8"))
        self.assertTrue(
            is_ordered_subsequence(core, full),
            "c-vnext-core is not a strict order-preserving deletion of b-vnext-full: "
            "a B->C gap would no longer be attributable to the removed prose",
        )
        self.assertLess(len(core), len(full), "the core must actually remove something")

    def test_the_cut_is_small_and_the_report_must_say_so(self):
        """Pre-registered power warning, asserted so it cannot be quietly forgotten."""
        full = injected("b-vnext-full.toml").read_text(encoding="utf-8").split()
        core = injected("c-vnext-core.toml").read_text(encoding="utf-8").split()
        delta = (len(full) - len(core)) / len(full)
        self.assertLess(delta, 0.15, "if the cut grew, re-derive the power discussion")
        self.assertGreater(delta, 0.02)


class TestOneAxisOnly(unittest.TestCase):
    def test_arms_differ_only_in_the_injected_body(self):
        base = None
        for arm in ARM_FILES:
            cfg = load(arm)
            cfg.pop("context", None)
            cfg.pop("name", None)
            if base is None:
                base = cfg
            else:
                self.assertEqual(cfg, base, f"{arm} differs from the others outside [context]")

    def test_bare_arm_declares_no_context(self):
        self.assertNotIn("context", load("d-bare.toml"))

    def test_arm_names_match_their_filenames(self):
        for arm in ARM_FILES:
            self.assertEqual(load(arm)["name"], arm[: -len(".toml")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
