"""The reconciliation gate, and the two ways it could go hollow.

Every check here derives one fact twice and fails while the derivations disagree.  The
interesting tests are not that it passes on a clean tree — that is the easy half, and a
check that only ever passes is indistinguishable from one that asserts nothing.  They are:

1. **each check actually fires** when its fact is perturbed, and
2. **an exception expires** once the discrepancy it excuses stops occurring.

(2) is the load-bearing one.  Some discrepancies are permanent facts about committed history
— the void arm has no preimage and never will — so exceptions must exist.  The moment they
exist, the gate's failure mode changes from "red forever" to "silently excused forever", and
only the staleness direction catches that.

Stdlib-only; runs without uv as ``python tests/test_reconcile.py``.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from fathom import reconcile  # noqa: E402
from fathom.reconcile import Discrepancy  # noqa: E402


def _mirror(tmp: Path) -> Path:
    """A throwaway copy of the repo's reconciliation inputs."""
    repo = tmp / "repo"
    (repo / "docs" / "reports").mkdir(parents=True)
    shutil.copytree(REPO / "ledger", repo / "ledger", ignore=shutil.ignore_patterns("archive"))
    shutil.copy(
        REPO / "docs" / "reports" / "LEDGER-INDEX.md",
        repo / "docs" / "reports" / "LEDGER-INDEX.md",
    )
    return repo


class ReconciliationTests(unittest.TestCase):
    def test_the_repo_reconciles(self) -> None:
        """The committed tree agrees with itself on every registered check."""
        found = reconcile.run_all(REPO)
        self.assertEqual(
            [str(d) for d in reconcile.unexpected(found)],
            [],
            "a derivation disagrees with its counterpart; see each line for the fix",
        )

    def test_no_exception_outlives_the_discrepancy_it_excuses(self) -> None:
        """A stale exception is a failure, not housekeeping.

        This is how an exception list becomes the vacuous gate: entries accumulate, nobody
        removes them, and eventually every real discrepancy is matched by a stale excuse.
        """
        found = reconcile.run_all(REPO)
        stale = reconcile.stale_exceptions(found)
        self.assertEqual(
            stale,
            [],
            "these exceptions no longer excuse anything and must be deleted — an exception "
            f"that outlives its discrepancy silently widens the gate: {stale}",
        )

    def test_the_registry_is_not_empty(self) -> None:
        """A registry of zero checks passes everything forever."""
        self.assertTrue(reconcile.CHECKS, "no reconciliations registered — the gate is vacuous")
        names = [c.name for c in reconcile.CHECKS]
        self.assertEqual(len(names), len(set(names)), f"duplicate check names: {names}")
        for check in reconcile.CHECKS:
            self.assertTrue(check.describe.strip(), f"{check.name} has no description")

    def test_an_unknown_check_name_is_an_error(self) -> None:
        """Selecting a typo'd check must not silently run nothing."""
        with self.assertRaises(KeyError):
            reconcile.registry(["ledger-index", "no-such-check"])

    def test_ledger_index_fires_when_a_ledger_moves(self) -> None:
        """Append one trial row; the committed index must stop matching."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = _mirror(Path(tmp))
            self.assertEqual(reconcile.check_ledger_index(repo), [], "mirror should start clean")

            victim = sorted((repo / "ledger").glob("*.jsonl"))[0]
            with victim.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write('{"kind": "trial", "scenario": "seeded", "status": "completed"}\n')

            found = reconcile.check_ledger_index(repo)
            self.assertEqual(len(found), 1, "an appended trial did not move the index")
            self.assertEqual(found[0].check, "ledger-index")

    # -- config-hash-preimage -------------------------------------------------

    def test_the_preimage_of_every_scenario_in_the_tree_hashes_to_its_config_hash(self) -> None:
        """The invariant the whole exact check rests on, asserted on real scenarios.

        If these two ever drift apart, every row written afterwards records an identity that
        does not match its own configuration — and the check would report the corruption it
        caused itself.
        """
        import hashlib
        import tomllib

        from fathom.scenario import load_scenario, resolve_scenario

        class _StubResolver:
            def resolve_model_id(self, model: str) -> str | None:
                return None

            def resolve_tool_repo_sha(self, repo: str) -> str | None:
                return "0" * 40

            def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
                return ("stub", "0.0.0", "0" * 64)

        checked = 0
        for toml_path in sorted((REPO / "scenarios").rglob("*.toml")):
            try:
                data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if not (isinstance(data.get("name"), str) and data.get("adapter")):
                continue
            try:
                resolved = resolve_scenario(load_scenario(toml_path), _StubResolver())
            except Exception:
                continue  # unresolvable arms are the coverage story, not this invariant
            digest = hashlib.sha256(resolved.config_preimage.encode("utf-8")).hexdigest()
            self.assertEqual(
                digest,
                resolved.config_hash,
                f"{toml_path.name}: the stored preimage does not hash to config_hash",
            )
            checked += 1

        self.assertGreater(
            checked, 50, f"only {checked} scenarios resolved — the sweep is too thin"
        )

    def test_config_hash_preimage_fires_when_a_row_disagrees_with_itself(self) -> None:
        """Corrupt one row's preimage; the exact check must name that row."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "ledger").mkdir(parents=True)
            good = json.dumps({"kind": "trial", "config_hash": "x" * 64, "config_preimage": "{}"})
            (repo / "ledger" / "b.jsonl").write_text(good + "\n", encoding="utf-8", newline="\n")

            found = reconcile.check_config_hash_preimage(repo)
            self.assertEqual(
                len(found), 1, "a row whose preimage does not hash to its digest passed"
            )
            self.assertEqual(found[0].check, "config-hash-preimage")

    def test_config_hash_preimage_is_silent_on_rows_that_predate_the_field(self) -> None:
        """A missing second derivation is a coverage gap, not a disagreement.

        Treating it as a failure is what would have required a 58-entry exception table
        churning with every unrelated plugin edit.
        """
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "ledger").mkdir(parents=True)
            legacy = json.dumps({"kind": "trial", "config_hash": "x" * 64})
            (repo / "ledger" / "b.jsonl").write_text(legacy + "\n", encoding="utf-8", newline="\n")

            self.assertEqual(reconcile.check_config_hash_preimage(repo), [])
            self.assertEqual(reconcile.preimage_coverage(repo), (0, 1))

    # -- scenario-known -------------------------------------------------------

    def test_scenario_known_names_exactly_the_arms_the_exception_table_declares(self) -> None:
        """The real repo's unknown arms must equal the declared exceptions.

        Both directions matter. An arm appearing here that is not declared is an
        unattributable result nobody has accepted; a declared arm that stops appearing is a
        stale excuse. Pinning the set keeps the table from drifting in either direction.
        """
        found = reconcile.check_scenario_known(REPO)
        actual = {(d.subject, d.key) for d in found}
        declared = {
            (subj, key) for (check, subj, key) in reconcile.KNOWN if check == "scenario-known"
        }
        self.assertEqual(
            actual,
            declared,
            "the arms with no committed scenario no longer match the accepted list; an "
            "undeclared one is an unattributable result, a vanished one is a stale excuse",
        )

    def test_scenario_known_fires_on_an_arm_with_no_committed_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "ledger").mkdir(parents=True)
            (repo / "scenarios").mkdir(parents=True)
            (repo / "scenarios" / "real.toml").write_text(
                'name = "real"\nadapter = "claude-cli"\n', encoding="utf-8", newline="\n"
            )
            rows = [
                {"kind": "trial", "status": "completed", "scenario": "real"},
                {"kind": "trial", "status": "completed", "scenario": "ghost"},
            ]
            (repo / "ledger" / "b.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n"
            )

            found = reconcile.check_scenario_known(repo)
            self.assertEqual([(d.subject, d.key) for d in found], [("b", "ghost")])

    def test_scenario_names_walks_subdirectories(self) -> None:
        """The non-recursive glob fathom run uses would see 3 of 189 arms and cry wolf."""
        names = reconcile.scenario_names(REPO)
        self.assertGreater(
            len(names), 100, f"only {len(names)} arms discovered — the walk is not recursive"
        )

    def test_unexpected_filters_only_declared_exceptions(self) -> None:
        d1 = Discrepancy(check="c", subject="s", key="k1", detail="")
        d2 = Discrepancy(check="c", subject="s", key="k2", detail="")
        original = dict(reconcile.KNOWN)
        try:
            reconcile.KNOWN.clear()
            reconcile.KNOWN[d1.fingerprint] = "accepted for a reason"
            self.assertEqual(reconcile.unexpected([d1, d2]), [d2])
            self.assertEqual(reconcile.stale_exceptions([d1, d2]), [])
            self.assertEqual(reconcile.stale_exceptions([d2]), [d1.fingerprint])
        finally:
            reconcile.KNOWN.clear()
            reconcile.KNOWN.update(original)


if __name__ == "__main__":
    unittest.main()
