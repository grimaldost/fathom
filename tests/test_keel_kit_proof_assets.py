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

import difflib
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


def fenced(text: str) -> str:
    """The fenced blocks of *text* — for these bodies, the gate's own reference contract."""
    out, inside = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


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


class TestWhatTheArmsShareAndWhatTheCutRemoves(unittest.TestCase):
    """The two facts that decide which classes the run may be read on.

    Both were missing from the first publication of this report and both change the reading, so
    they are asserted rather than described: a later edit that makes either false must fail here
    before it can quietly restore the stronger claim.
    """

    def test_every_armed_body_states_the_oracles_predicates_verbatim(self):
        """The behaviour class is not "stated by neither body" — every armed arm holds the key.

        Consequence, in the verifier's docstring and report §1.6: an armed-versus-bare gap on
        `anchors_resolve` / `concept_map_paths_resolve` / `section_refs_resolve` /
        `ledger_rows_anchor` measures possession of the rubric, not craft.
        """
        for arm in ARMED:
            block = fenced(injected(arm).read_text(encoding="utf-8"))
            for predicate in (
                "A5 each concept->module path",
                "A6 each `path:line` anchor",
                "A8 each bare intra-spec `§N` reference",
                "A12 when a `### Fold ledger` sub-table is present",
            ):
                self.assertIn(predicate, block, f"{arm}: the fence no longer states {predicate}")

    def test_the_cut_pair_shares_a_byte_identical_fence(self):
        """B and C state the ruler in the same words, so a B→C null on it is not a measurement."""
        full = fenced(injected("b-vnext-full.toml").read_text(encoding="utf-8"))
        core = fenced(injected("c-vnext-core.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            full,
            core,
            "the cut pair's reference fences now differ — the behaviour class is no longer held "
            "constant across them and §1.6's reading rules must be re-derived",
        )

    def test_the_relocation_pair_does_not_share_a_fence(self):
        """A→B is not one edit: the vNext fence describes a gate the pinned ruler does not run.

        The A12 clause is the demonstrated case — B and C tell the author a fold-ledger
        confirmation may be `artifact:lo-hi`, and the pinned 0.14.0 oracle's `_LEDGER_ANCHOR_RE`
        has no range form, so an arm that obeys the newer kit loses `gate_part_a_passes` and
        `ledger_rows_anchor`. The penalty falls only on B and C; report §1.1 records it.
        """
        old = fenced((PREREG / "assets" / "kit-full.md").read_text(encoding="utf-8"))
        new = fenced(injected("b-vnext-full.toml").read_text(encoding="utf-8"))
        self.assertNotEqual(old, new)
        self.assertIn("or `artifact:lo-hi`", new)
        self.assertNotIn("artifact:lo-hi", old)

    def test_most_of_the_cut_is_invisible_to_the_bank(self):
        """The B→C words the bank cannot see, measured — the coverage gap in report §1.2.

        11 of the 21 removed lines are Definition-of-Ready checklist items ("every invariant …
        has an ADR", the post-fold coherence re-read, the measurement-profile item). No criterion
        in `keelgate_verify.py` can detect their loss: they are asks about the spec's substance,
        not about a construct the pinned gate parses. Only the A10/A9/A11 template notes map to a
        criterion at all.
        """
        full = injected("b-vnext-full.toml").read_text(encoding="utf-8").splitlines()
        core = injected("c-vnext-core.toml").read_text(encoding="utf-8").splitlines()
        removed = [
            ln[1:]
            for ln in difflib.unified_diff(full, core, lineterm="", n=0)
            if ln.startswith("-") and not ln.startswith("---")
        ]
        checklist, mode = [], None
        for line in removed:
            if not line.strip():
                continue
            if line.lstrip().startswith("- [ ]"):
                mode = "checklist"
            elif not line.startswith("      "):
                mode = "note"
            if mode == "checklist":
                checklist.append(line)
        words = sum(len(ln.split()) for ln in removed)
        blind = sum(len(ln.split()) for ln in checklist)
        self.assertGreater(
            blind / words,
            0.5,
            "the majority of the cut is no longer DoR-checklist prose — re-derive the coverage "
            "gap in §1.2 before reading a B→C null as licensing the cut",
        )


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
