"""Static guards for the `humble-vs-super-v5` bank and its arms — stdlib-runnable.

`fathom run` only *warns* on a plugin mount that does not exist. A missing tree
therefore does not stop the matrix: it silently degrades the contrast arm toward the
control and manufactures a null that looks like a measurement. The live gate against
that is `fathom verify-arming` (EXIT_UNARMED), which needs credentials and a real spawn;
these tests are the free, offline half — they run in CI, in a fresh clone, and with an
expired session, and they fail the moment a v5 scenario points at a tree that is not
there.

They also pin the two things a fork can quietly lose:

* v5's task content is a byte-for-byte fork of v2's, so the published v1–v4 verifier
  tests still describe it;
* the third-party `superpowers@6fd4507` snapshot is gitignored, so when it *is* present
  its bytes must match the manifest the measurement was authored against.

`python tests/test_humble_super_v5_mounts.py` runs without uv.
"""

from __future__ import annotations

import filecmp
import hashlib
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).parent.parent
BANK = REPO / "tasks" / "humble-vs-super-v5"
V2_BANK = REPO / "tasks" / "humble-vs-super-v2"
SCENARIOS = REPO / "scenarios" / "humble-vs-super-v5"
PLUGINS = BANK / "plugins"
VENDORED = PLUGINS / "VENDORED.md"
SUPERPOWERS = PLUGINS / "superpowers@6fd4507"
MANIFEST = PLUGINS / "superpowers-6fd4507.sha256"

ARMS = ("bare", "stack-humble", "stack-super")
HELD_CONSTANT_STACK = ("engineering-discipline", "session-workflow")

RE_VENDOR = (
    f"{SUPERPOWERS} is absent. It is gitignored third-party content "
    "(tasks/*/plugins/superpowers@*/), so a fresh clone has to re-vendor it before the "
    "`stack-super` arm can be run — see tasks/humble-vs-super-v5/plugins/VENDORED.md "
    "for the recipe and the sha256 manifest. Until then the arm is UNARMED and any "
    "matrix run against it is void."
)


def _scenario_files() -> list[Path]:
    return sorted(SCENARIOS.glob("*.toml"))


def _mounts(scenario: Path) -> list[Path]:
    """Absolute mount dirs declared by *scenario*, resolved the way fathom resolves them.

    `src/fathom/scenario.py` resolves a relative mount against the scenario file's own
    parent — not the cwd and not the bank — which is why an arm copied between scenario
    dirs can end up mounting a *different* bank's plugin trees.
    """
    data = tomllib.loads(scenario.read_text(encoding="utf-8"))
    return [(scenario.parent / m).resolve() for m in data.get("plugins", {}).get("mount", [])]


def _tree_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


class ScenarioShapeTests(unittest.TestCase):
    def test_exactly_the_three_published_arms(self) -> None:
        names = sorted(
            tomllib.loads(p.read_text(encoding="utf-8"))["name"] for p in _scenario_files()
        )
        self.assertEqual(names, sorted(ARMS))

    def test_every_field_but_plugins_is_held_constant_across_arms(self) -> None:
        """The contrast must be the plugin axis alone.

        A stray `model` or `effort` difference would confound the treatment with a
        capacity change, and `config_hash` would happily absorb it without complaint.
        """
        shared = []
        for path in _scenario_files():
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            data.pop("plugins", None)
            data.pop("name", None)
            shared.append((path.name, data))
        first_name, first = shared[0]
        for name, data in shared[1:]:
            self.assertEqual(data, first, f"{name} differs from {first_name} off the plugin axis")

    def test_disciplined_arms_mount_the_same_held_constant_stack(self) -> None:
        by_name = {
            tomllib.loads(p.read_text(encoding="utf-8"))["name"]: _mounts(p)
            for p in _scenario_files()
        }
        self.assertEqual(by_name["bare"], [], "the control arm must mount nothing")
        for arm in ("stack-humble", "stack-super"):
            tail = [m.name for m in by_name[arm][1:]]
            self.assertEqual(tail, list(HELD_CONSTANT_STACK), f"{arm}'s common stack drifted")
        self.assertEqual(by_name["stack-humble"][0].name, "humblepowers@0.9.1")
        self.assertEqual(by_name["stack-super"][0].name, "superpowers@6fd4507")

    def test_mounts_point_at_v5s_own_vendored_trees(self) -> None:
        """A mount that resolves outside this bank would measure another bank's content."""
        for path in _scenario_files():
            for mount in _mounts(path):
                self.assertEqual(
                    mount.parent,
                    PLUGINS.resolve(),
                    f"{path.name} mounts {mount}, outside {PLUGINS}",
                )


class MountExistenceTests(unittest.TestCase):
    def test_every_committed_mount_exists_and_is_a_plugin(self) -> None:
        for path in _scenario_files():
            for mount in _mounts(path):
                if mount == SUPERPOWERS.resolve() and not mount.is_dir():
                    self.skipTest(RE_VENDOR)
                self.assertTrue(mount.is_dir(), f"{path.name} mounts a missing dir: {mount}")
                self.assertTrue(
                    (mount / ".claude-plugin" / "plugin.json").is_file(),
                    f"{mount} has no .claude-plugin/plugin.json — fathom cannot resolve its "
                    "name/version and the arm's config_hash records an unnamed tree",
                )

    def test_every_mount_is_documented_in_vendored_md(self) -> None:
        body = VENDORED.read_text(encoding="utf-8")
        for path in _scenario_files():
            for mount in _mounts(path):
                self.assertIn(mount.name, body, f"{mount.name} has no provenance entry")

    def test_treatment_is_the_merged_humblepowers_version(self) -> None:
        import json

        meta = json.loads(
            (PLUGINS / "humblepowers@0.9.1" / ".claude-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual((meta["name"], meta["version"]), ("humblepowers", "0.9.1"))

    def test_superpowers_snapshot_matches_the_measured_bytes(self) -> None:
        if not SUPERPOWERS.is_dir():
            self.skipTest(RE_VENDOR)
        expected = {}
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, name = line.split(None, 1)
            expected[name.strip().lstrip("*")] = digest
        actual = {
            rel: hashlib.sha256((SUPERPOWERS / rel).read_bytes()).hexdigest()
            for rel in _tree_files(SUPERPOWERS)
        }
        self.assertEqual(
            actual,
            expected,
            "the re-vendored superpowers tree differs from the snapshot v1–v4 were "
            "measured against; the contrast arm is not the published one",
        )


class ForkIntegrityTests(unittest.TestCase):
    def test_bank_declares_the_fork(self) -> None:
        meta = tomllib.loads((BANK / "bank.toml").read_text(encoding="utf-8"))
        self.assertEqual(meta["name"], "humble-vs-super-v5")
        self.assertEqual(meta["holdout"], ["fix-cache-eviction-bug"])
        v2 = tomllib.loads((V2_BANK / "bank.toml").read_text(encoding="utf-8"))
        self.assertNotEqual(
            meta["dataset_version"],
            v2["dataset_version"],
            "dataset_version is in the resume key — a fork that reuses v2's could pool "
            "two instruments into one ledger bucket",
        )

    def test_task_content_is_a_byte_identical_fork_of_v2(self) -> None:
        """The v1/v2 verifier tests are v5's coverage; they only apply if nothing drifted."""
        for task in sorted(p.name for p in BANK.iterdir() if p.is_dir() and p.name != "plugins"):
            ours, theirs = BANK / task, V2_BANK / task
            self.assertTrue(theirs.is_dir(), f"{task} has no v2 counterpart")
            self.assertEqual(_tree_files(ours), _tree_files(theirs), f"{task}: file set drifted")
            for rel in sorted(_tree_files(ours)):
                self.assertTrue(
                    filecmp.cmp(ours / rel, theirs / rel, shallow=False),
                    f"{task}/{rel} differs from v2 — v5 is a plugin/model fork, not a task fork",
                )
        self.assertTrue(
            filecmp.cmp(BANK / "bugfix_verify.py", V2_BANK / "bugfix_verify.py", shallow=False),
            "the shared verifier library drifted from v2's",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
