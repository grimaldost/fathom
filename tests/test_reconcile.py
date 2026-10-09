"""The reconciliation gate, and the two ways it could go hollow.

Every check here derives one fact twice and fails while the derivations disagree.  The
interesting tests are not that it passes on a clean root — that is the easy half, and a
check that only ever passes is indistinguishable from one that asserts nothing.  They are:

1. **each check actually fires** when its fact is perturbed, and
2. **an exception expires** once the discrepancy it excuses stops occurring.

(2) is the load-bearing one.  Some discrepancies are permanent facts about committed history
— an arm whose configuration was never committed stays unattributable — so exceptions must
exist.  The moment they exist, the gate's failure mode changes from "red forever" to
"silently excused forever", and only the staleness direction catches that.

The engine carries no data, so the checks run against ``examples/data-root/``: a
small synthetic data root whose ledger rows were written by the engine's own scenario and
ledger code, with one declared exception.  Each failure case mutates a temporary copy of it.
The engine checkout itself is reconciled too, where only version-sites has anything to
compare.

Stdlib-only; runs without uv as ``python tests/test_reconcile.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
FIXTURE = ENGINE / "examples" / "data-root"
sys.path.insert(0, str(ENGINE / "src"))

from fathom import ledgerindex, reconcile  # noqa: E402
from fathom.reconcile import Discrepancy, KnownExceptionsError  # noqa: E402
from fathom.scenario import load_scenario, resolve_scenario  # noqa: E402

DRAFT = ("scenario-known", "example", "nudge-draft")
# The example declares [plan] repeats_per_cell = 2; the draft arm's cell holds one trial.
SHORT = ("replication", "example", "short:nudge-draft/add")


class _Resolver:
    """The CLI resolver's answers for a ``source = "none"`` arm with no plugins."""

    def resolve_model_id(self, model: str) -> str | None:
        return None

    def resolve_tool_repo_sha(self, repo: str) -> str:
        raise AssertionError("the fixture's arms declare no tool repo")

    def build_tool_invocation_cmd(self, repo: str) -> str:
        raise AssertionError("the fixture's arms declare no tool repo")

    def resolve_plugin_meta(self, plugin_dir: str) -> tuple[str, str, str]:
        raise AssertionError("the fixture's arms mount no plugins")


def _copy_fixture(tmp: str) -> Path:
    """A throwaway copy of the fixture, outside the engine tree."""
    root = Path(tmp) / "data-root"
    shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def _ledger(root: Path) -> Path:
    return root / "ledger" / "example.jsonl"


def _rewrite_rows(root: Path, change: Callable[[list[dict]], list[dict]]) -> None:
    """Rewrite the example ledger through *change*, then re-stamp the index.

    Re-stamping keeps the ledger-index check quiet, so a test sees only the check it
    perturbed.
    """
    path = _ledger(root)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in change(rows)),
        encoding="utf-8",
        newline="\n",
    )
    ledgerindex.write(root)


def _write_config(root: Path, text: str) -> Path:
    path = root / "fathom.toml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _fingerprints(found: object) -> list[tuple[str, str, str]]:
    return [d.fingerprint for d in found]  # type: ignore[attr-defined]


def _fathom(
    cwd: Path, *args: str, fathom_home: str | None = None
) -> subprocess.CompletedProcess[str]:
    """``python -m fathom <args>`` started in *cwd*, with FATHOM_HOME only if given."""
    env = dict(os.environ)
    # The developer's own FATHOM_HOME must not steer the child; a test sets its own.
    env.pop("FATHOM_HOME", None)
    if fathom_home is not None:
        env["FATHOM_HOME"] = fathom_home
    env["PYTHONPATH"] = str(ENGINE / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "fathom", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def _version_files(root: Path, *, package: str, manifest: str, heading: str) -> Path:
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "fathom"\nversion = "{package}"\n', encoding="utf-8", newline="\n"
    )
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "fathom", "version": manifest}), encoding="utf-8", newline="\n"
    )
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{heading}] - 2026-08-28\n\nEntries.\n", encoding="utf-8", newline="\n"
    )
    return root


class FixtureTests(unittest.TestCase):
    """The example data root agrees with itself, and gives every check something to compare."""

    def test_the_fixture_reconciles_clean(self) -> None:
        outcome = reconcile.run(FIXTURE)
        self.assertEqual([str(d) for d in outcome.unexpected], [])
        self.assertEqual(outcome.stale, [])
        self.assertTrue(outcome.ok)
        self.assertEqual(
            outcome.ran,
            ("ledger-index", "config-hash-preimage", "scenario-known", "replication"),
        )
        self.assertEqual([name for name, _reason in outcome.skipped], ["version-sites"])
        self.assertEqual(
            _fingerprints(outcome.found), [DRAFT, SHORT], "the declared exceptions are used"
        )
        self.assertEqual(outcome.excused, 2)
        self.assertEqual(outcome.warnings, [])

    def test_the_fixture_is_not_vacuous(self) -> None:
        """A clean result over nothing would prove nothing."""
        self.assertEqual(reconcile.root_kind(FIXTURE), "data root")
        self.assertTrue((FIXTURE / ledgerindex.INDEX_PATH).is_file())
        have, total = reconcile.preimage_coverage(FIXTURE)
        self.assertGreater(total, 0)
        self.assertEqual(have, total, "every fixture row carries its preimage")
        self.assertEqual(reconcile.scenario_names(FIXTURE), {"bare", "nudge"})
        self.assertEqual(list(reconcile.load_known(FIXTURE)), [DRAFT, SHORT])

    def test_the_fixture_rows_carry_the_hash_the_engine_computes(self) -> None:
        """Each committed arm resolves to exactly the identity its ledger rows record.

        This is the invariant the exact check rests on — sha256(preimage) == config_hash —
        asserted on the engine's own resolution rather than on stored rows alone, so the
        fixture cannot drift from what ``fathom run`` would write.
        """
        resolved = {}
        for path in sorted((FIXTURE / "scenarios").glob("*.toml")):
            sc = resolve_scenario(load_scenario(path), _Resolver())
            digest = hashlib.sha256(sc.config_preimage.encode("utf-8")).hexdigest()
            self.assertEqual(digest, sc.config_hash, f"{path.name}: preimage does not hash")
            resolved[sc.name] = sc
        self.assertEqual(set(resolved), {"bare", "nudge"})

        checked = 0
        for row in ledgerindex.rows(_ledger(FIXTURE)):
            if row.get("kind") != "trial" or row.get("scenario") not in resolved:
                continue
            sc = resolved[row["scenario"]]
            self.assertEqual(row["config_hash"], sc.config_hash, row["scenario"])
            self.assertEqual(row["config_preimage"], sc.config_preimage, row["scenario"])
            checked += 1
        self.assertEqual(checked, 4, "two repeats per committed arm")

    def test_no_fixture_file_holds_an_absolute_path(self) -> None:
        """The fixture is committed and runs on every machine, so nothing in it may be local."""
        pattern = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]|/home/|/Users/")
        for path in sorted(FIXTURE.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(pattern.search(text), f"{path.relative_to(FIXTURE)}")
            self.assertNotIn(str(ENGINE), text)


class EachCheckCanFail(unittest.TestCase):
    """Every check fires on a perturbed copy of the fixture, and names what moved."""

    def test_ledger_index_fires_when_a_ledger_moves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            with _ledger(root).open("a", encoding="utf-8", newline="\n") as fh:
                fh.write('{"kind": "trial", "scenario": "bare", "status": "errored"}\n')
            outcome = reconcile.run(root)
            self.assertEqual(
                _fingerprints(outcome.unexpected),
                [("ledger-index", "docs/reports/LEDGER-INDEX.md", "whole-document")],
            )
            self.assertIn(
                "`example` changed since the index was stamped", outcome.unexpected[0].detail
            )

    def test_ledger_index_names_a_header_change_as_one(self) -> None:
        """An engine release that rewords the header moves no ledger, and must not say so."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            index = root / ledgerindex.INDEX_PATH
            table = index.read_text(encoding="utf-8").split("| Bank |", 1)[1]
            index.write_text(
                "# Ledger index\n\nAn older header.\n\n| Bank |" + table,
                encoding="utf-8",
                newline="\n",
            )
            found = reconcile.check_ledger_index(root)
            self.assertEqual(
                [d.fingerprint for d in found],
                [("ledger-index", "docs/reports/LEDGER-INDEX.md", "whole-document")],
            )
            self.assertIn("no ledger moved", found[0].detail)
            self.assertNotIn("changed since the index was stamped", found[0].detail)
            self.assertNotIn("appended", found[0].detail)

    def test_ledger_index_fires_when_ledgers_have_no_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            (root / ledgerindex.INDEX_PATH).unlink()
            found = reconcile.check_ledger_index(root)
            self.assertEqual(len(found), 1)
            self.assertIn("no index has been rendered", found[0].detail)

    def test_config_hash_preimage_fires_when_a_row_disagrees_with_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            target = {}

            def corrupt(rows: list[dict]) -> list[dict]:
                row = next(r for r in rows if r.get("scenario") == "bare")
                row["config_preimage"] = row["config_preimage"].replace('"low"', '"high"')
                target["hash"] = row["config_hash"]
                return rows

            _rewrite_rows(root, corrupt)
            outcome = reconcile.run(root)
            self.assertEqual(
                _fingerprints(outcome.unexpected),
                [("config-hash-preimage", "example", target["hash"])],
            )

    def test_config_hash_preimage_is_silent_on_rows_that_predate_the_field(self) -> None:
        """A missing second derivation is a coverage gap, not a disagreement."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)

            def strip(rows: list[dict]) -> list[dict]:
                for row in rows:
                    row.pop("config_preimage", None)
                return rows

            _rewrite_rows(root, strip)
            self.assertEqual(reconcile.check_config_hash_preimage(root), [])
            self.assertEqual(reconcile.preimage_coverage(root), (0, 10))

    def test_scenario_known_fires_on_an_arm_with_no_committed_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            (root / "scenarios" / "nudge.toml").unlink()
            outcome = reconcile.run(root)
            self.assertEqual(
                _fingerprints(outcome.unexpected), [("scenario-known", "example", "nudge")]
            )

    def test_scenario_known_fires_when_the_exception_is_withdrawn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _write_config(root, "[data_root]\nschema = 1\n")
            outcome = reconcile.run(root)
            self.assertEqual(_fingerprints(outcome.unexpected), [DRAFT])

    def test_scenario_known_fires_on_every_arm_when_there_are_no_scenarios(self) -> None:
        """No scenarios/ at all is the worst case, not a reason to compare nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            shutil.rmtree(root / "scenarios")
            outcome = reconcile.run(root)
            self.assertEqual(
                _fingerprints(outcome.unexpected),
                [("scenario-known", "example", "bare"), ("scenario-known", "example", "nudge")],
            )

    def test_scenario_names_walks_subdirectories(self) -> None:
        """``fathom run`` globs one level; the check must see arms kept in subdirectories."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            nested = root / "scenarios" / "variants"
            nested.mkdir()
            (root / "scenarios" / "nudge.toml").rename(nested / "nudge.toml")
            (root / "scenarios" / "assets" / "notes.toml").write_text(
                'title = "an asset, not an arm"\n', encoding="utf-8", newline="\n"
            )
            self.assertEqual(reconcile.scenario_names(root), {"bare", "nudge"})

    def test_a_stale_exception_fails_the_gate(self) -> None:
        """Remove the excused trial: the exception must now fail, not linger."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _rewrite_rows(
                root, lambda rows: [r for r in rows if r.get("scenario") != "nudge-draft"]
            )
            outcome = reconcile.run(root)
            self.assertEqual(outcome.unexpected, [])
            self.assertEqual(outcome.stale, [DRAFT, SHORT])
            self.assertFalse(outcome.ok)

    def test_version_sites_fires_when_a_manifest_appears_and_disagrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(
                _copy_fixture(tmp), package="0.8.0", manifest="0.7.0", heading="0.8.0"
            )
            outcome = reconcile.run(root)
            self.assertEqual(outcome.skipped, ())
            self.assertEqual(
                _fingerprints(outcome.unexpected),
                [("version-sites", ".claude-plugin/plugin.json", "0.7.0")],
            )


class KnownExceptionsTests(unittest.TestCase):
    """``[[reconcile.known]]`` in fathom.toml: loaded as declared, or refused with a reason."""

    def test_a_root_without_fathom_toml_accepts_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(reconcile.load_known(Path(tmp)), {})

    def test_the_fixture_declares_its_exceptions_with_their_reasons(self) -> None:
        known = reconcile.load_known(FIXTURE)
        self.assertEqual(list(known), [DRAFT, SHORT])
        self.assertTrue(known[DRAFT].strip())
        self.assertTrue(known[SHORT].strip())

    def test_malformed_entries_are_refused_by_name(self) -> None:
        entry = 'check = "scenario-known"\nsubject = "example"\nkey = "nudge-draft"\n'
        cases = {
            "not toml": ("[data_root\n", "not valid TOML"),
            "reconcile not a table": ("reconcile = 1\n", "`reconcile` must be a table"),
            "known not an array": ("[reconcile.known]\n" + entry, "array of tables"),
            "entry not a table": ("reconcile = { known = [1] }\n", "entry 1 is not a table"),
            "missing field": ("[[reconcile.known]]\n" + entry, "entry 1 is missing reason"),
            "unknown field": (
                "[[reconcile.known]]\n" + entry + 'reason = "r"\nsince = "0.7.0"\n',
                "unknown field(s) since",
            ),
            "empty reason": (
                "[[reconcile.known]]\n" + entry + 'reason = "  "\n',
                "`reason` must be a non-empty string",
            ),
            "wrong type": (
                "[[reconcile.known]]\n"
                + entry.replace('key = "nudge-draft"', "key = 3")
                + 'reason = "r"\n',
                "`key` must be a non-empty string",
            ),
            "unknown check": (
                "[[reconcile.known]]\n"
                + entry.replace("scenario-known", "scenario-knwon")
                + 'reason = "r"\n',
                "not a registered reconciliation",
            ),
            "duplicate": (
                ("[[reconcile.known]]\n" + entry + 'reason = "r"\n') * 2,
                "entry 2 repeats",
            ),
        }
        for label, (text, message) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                # The case text comes first, so its top-level keys stay top-level.
                path = _write_config(Path(tmp), text + "\n[data_root]\nschema = 1\n")
                with self.assertRaises(KnownExceptionsError) as caught:
                    reconcile.load_known(Path(tmp))
                self.assertIn(message, str(caught.exception))
                self.assertIn(str(path), str(caught.exception), "the error names the file")

    def test_a_file_that_is_not_utf8_is_refused_by_name(self) -> None:
        """Windows PowerShell 5.1's `>` and Out-File write UTF-16 unless told otherwise."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            text = (root / "fathom.toml").read_text(encoding="utf-8")
            (root / "fathom.toml").write_bytes(text.encode("utf-16"))
            with self.assertRaises(KnownExceptionsError) as caught:
                reconcile.load_known(root)
            self.assertIn("UTF-16", str(caught.exception))
            self.assertIn("must be UTF-8", str(caught.exception))
            self.assertFalse(reconcile.is_data_root(root))

    def test_a_utf8_bom_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            raw = (root / "fathom.toml").read_bytes()
            (root / "fathom.toml").write_bytes(b"\xef\xbb\xbf" + raw)
            self.assertEqual(list(reconcile.load_known(root)), [DRAFT, SHORT])
            self.assertEqual(reconcile.root_kind(root), "data root")
            self.assertTrue(reconcile.run(root).ok)

    def test_a_malformed_file_stops_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _write_config(root, "[data_root]\nschema = 1\n[[reconcile.known]]\ncheck = 1\n")
            with self.assertRaises(KnownExceptionsError):
                reconcile.run(root)


class ExceptionScopeTests(unittest.TestCase):
    def test_unexpected_filters_only_declared_exceptions(self) -> None:
        d1 = Discrepancy(check="c", subject="s", key="k1", detail="")
        d2 = Discrepancy(check="c", subject="s", key="k2", detail="")
        known = {d1.fingerprint: "accepted for a reason"}
        self.assertEqual(reconcile.unexpected([d1, d2], known), [d2])
        self.assertEqual(reconcile.stale_exceptions([d1, d2], known), [])
        self.assertEqual(reconcile.stale_exceptions([d2], known), [d1.fingerprint])

    def test_a_subset_run_does_not_judge_exceptions_for_checks_it_left_out(self) -> None:
        """``--check ledger-index`` never looked for the draft arm, so it cannot call it stale."""
        outcome = reconcile.run(FIXTURE, names=["ledger-index"])
        self.assertEqual(outcome.ran, ("ledger-index",))
        self.assertEqual(outcome.stale, [])
        self.assertTrue(outcome.ok)

    def test_a_skipped_check_still_judges_its_exceptions(self) -> None:
        """An exception for a check that cannot apply here can never match, so it is stale."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            config = root / "fathom.toml"
            _write_config(
                root,
                config.read_text(encoding="utf-8")
                + '\n[[reconcile.known]]\ncheck = "version-sites"\nsubject = "CHANGELOG.md"\n'
                'key = "unreadable"\nreason = "copied from an engine checkout by mistake"\n',
            )
            outcome = reconcile.run(root)
            self.assertEqual(outcome.stale, [("version-sites", "CHANGELOG.md", "unreadable")])


class RegistryTests(unittest.TestCase):
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


class RootTests(unittest.TestCase):
    """The root is where the command runs, and an empty root has nothing to disagree about."""

    def test_the_engine_checkout_reconciles(self) -> None:
        self.assertEqual(reconcile.root_kind(ENGINE), "engine checkout")
        outcome = reconcile.run(ENGINE)
        self.assertEqual([str(d) for d in outcome.unexpected], [])
        self.assertEqual(outcome.stale, [])
        self.assertEqual(outcome.skipped, (), "version-sites applies to the engine")
        self.assertEqual(len(outcome.ran), len(reconcile.CHECKS))

    def test_a_root_with_no_ledgers_and_no_index_reconciles_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outcome = reconcile.run(root)
            self.assertEqual(outcome.found, ())
            self.assertTrue(outcome.ok)
            self.assertEqual(reconcile.preimage_coverage(root), (0, 0))
            self.assertIsNone(reconcile.root_kind(root))

    def test_the_default_root_is_the_working_directory(self) -> None:
        self.assertEqual(reconcile.resolve_root(), Path.cwd())
        self.assertEqual(reconcile.resolve_root(FIXTURE), FIXTURE)


class VersionSitesTests(unittest.TestCase):
    def test_version_sites_fires_when_the_manifest_lags_the_package(self) -> None:
        """Recreate the 0.4.0 slip — pyproject moved, the plugin manifest did not."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(Path(tmp), package="0.4.0", manifest="0.3.0", heading="0.4.0")
            found = reconcile.check_version_sites(root)
            self.assertEqual(
                [(d.subject, d.key) for d in found],
                [(".claude-plugin/plugin.json", "0.3.0")],
                "a manifest one release behind the package passed",
            )

    def test_version_sites_fires_when_the_changelog_heading_lags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(Path(tmp), package="0.4.0", manifest="0.4.0", heading="0.3.0")
            found = reconcile.check_version_sites(root)
            self.assertEqual([(d.subject, d.key) for d in found], [("CHANGELOG.md", "0.3.0")])

    def test_version_sites_skips_unreleased_and_reads_the_newest_cut(self) -> None:
        """Between cuts, [Unreleased] accumulates while every versioned site stays put."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(Path(tmp), package="0.4.0", manifest="0.4.0", heading="0.4.0")
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n- pending\n\n## [0.4.0] - 2026-08-28\n",
                encoding="utf-8",
                newline="\n",
            )
            self.assertEqual(reconcile.check_version_sites(root), [])

    def test_an_install_pin_that_lags_the_package_is_a_discrepancy(self) -> None:
        """The install lines stayed at @v0.8.0 through two releases before a review saw it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(Path(tmp), package="0.4.0", manifest="0.4.0", heading="0.4.0")
            line = "uv tool install git+https://github.com/owner/fathom@v{}\n"
            (root / "README.md").write_text(line.format("0.4.0") + line.format("0.3.0"))
            (root / "README-plugin.md").write_text(line.format("0.4.0"))
            (root / "skills/fathom-eval/reference").mkdir(parents=True)
            (root / "skills/fathom-eval/reference/authoring.md").write_text("No pin here.\n")
            found = reconcile.check_version_sites(root)
            self.assertEqual(
                [(d.subject, d.key) for d in found], [("README.md (install pin)", "0.3.0")]
            )
            sites = reconcile.version_sites(root)
            self.assertEqual(sites["README-plugin.md (install pin)"], "0.4.0")
            self.assertNotIn("skills/fathom-eval/reference/authoring.md (install pin)", sites)

    def test_version_sites_is_skipped_where_there_is_no_manifest(self) -> None:
        """A data root carries no plugin manifest; that is not an unreadable site."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(Path(tmp), package="0.4.0", manifest="0.4.0", heading="0.3.0")
            (root / ".claude-plugin" / "plugin.json").unlink()
            self.assertEqual(reconcile.check_version_sites(root), [])
            self.assertIsNotNone(reconcile.version_sites_skip(root))
            outcome = reconcile.run(root, names=["version-sites"])
            self.assertEqual(outcome.ran, ())
            self.assertEqual([name for name, _ in outcome.skipped], ["version-sites"])

    def test_an_unreadable_manifest_is_reported_rather_than_skipped(self) -> None:
        """Where the manifest exists, a site that cannot state a version cannot sit out."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _version_files(Path(tmp), package="0.4.0", manifest="0.4.0", heading="0.4.0")
            (root / ".claude-plugin" / "plugin.json").write_text(
                '{"name": "fathom"}', encoding="utf-8", newline="\n"
            )
            found = reconcile.check_version_sites(root)
            self.assertEqual(
                [(d.subject, d.key) for d in found],
                [(".claude-plugin/plugin.json", "unreadable")],
            )


class CliTests(unittest.TestCase):
    """``fathom reconcile`` reconciles the data root it finds, never the engine's install."""

    def test_the_data_root_is_found_from_anywhere(self) -> None:
        """Inside it, below it, and from elsewhere by --home or FATHOM_HOME: one answer."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            elsewhere = Path(tmp) / "elsewhere"
            elsewhere.mkdir()
            runs = {
                "inside": _fathom(root, "reconcile"),
                "nested": _fathom(root / "tasks" / "example", "reconcile"),
                "--home": _fathom(elsewhere, "--home", "../data-root", "reconcile"),
                "FATHOM_HOME": _fathom(elsewhere, "reconcile", fathom_home=str(root)),
            }
            outputs = set()
            for mode, proc in runs.items():
                with self.subTest(mode=mode):
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertIn(f"reconciling the data root at {root}", proc.stdout)
                    outputs.add(proc.stdout)
            self.assertEqual(len(outputs), 1)

    def test_fathom_home_from_an_engine_checkout_says_which_root_it_checks(self) -> None:
        proc = _fathom(ENGINE, "reconcile", fathom_home=str(FIXTURE))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"reconciling the data root at {FIXTURE}", proc.stdout)
        self.assertIn("unset FATHOM_HOME to check the engine", proc.stderr)

    def test_an_unmarked_directory_holding_a_ledger_is_refused(self) -> None:
        """Other commands use it with a warning; the gate needs the marker to check it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            (root / "fathom.toml").unlink()
            proc = _fathom(root, "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("neither a fathom data root", proc.stderr)
            self.assertIn("fathom init", proc.stderr)
            self.assertEqual(len(proc.stderr.strip().splitlines()), 1, proc.stderr)

    def test_a_named_root_that_is_neither_kind_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = _fathom(Path(tmp), "--home", ".", "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("neither a fathom data root", proc.stderr)

    def test_a_data_root_outside_the_engine_tree_reconciles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            proc = _fathom(root, "reconcile")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("reconciling the data root at", proc.stdout)
            self.assertIn("[SKIPPED] version-sites", proc.stdout)
            self.assertIn("preimage coverage: 10/10", proc.stdout)
            self.assertIn("RECONCILE: OK (4 check(s) run, 1 skipped", proc.stdout)
            self.assertIn("2 excused", proc.stdout)
            self.assertNotIn("warning(s)", proc.stdout)

    def test_the_engine_checkout_reports_no_rows_without_dividing_by_zero(self) -> None:
        proc = _fathom(ENGINE, "reconcile")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("reconciling the engine checkout", proc.stdout)
        self.assertIn("preimage coverage: no trial or run rows", proc.stdout)

    def test_a_disagreement_exits_13(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            with _ledger(root).open("a", encoding="utf-8", newline="\n") as fh:
                fh.write('{"kind": "run", "scenario": "bare"}\n')
            proc = _fathom(root, "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("[DISAGREES] [ledger-index]", proc.stdout)
            self.assertIn("RECONCILE: FAILED", proc.stdout)

    def test_a_stale_exception_exits_13(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _rewrite_rows(
                root, lambda rows: [r for r in rows if r.get("scenario") != "nudge-draft"]
            )
            proc = _fathom(root, "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("[STALE EXCEPTION]", proc.stdout)

    def test_a_directory_that_is_no_root_is_refused(self) -> None:
        """Running from the wrong directory would otherwise pass with nothing compared."""
        with tempfile.TemporaryDirectory() as tmp:
            proc = _fathom(Path(tmp), "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("neither a fathom data root", proc.stderr)

    def test_a_malformed_fathom_toml_is_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            _write_config(root, "[data_root]\nschema = 1\n[[reconcile.known]]\ncheck = 1\n")
            proc = _fathom(root, "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("[[reconcile.known]] entry 1", proc.stderr)

    def test_a_utf16_fathom_toml_is_named_not_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _copy_fixture(tmp)
            text = (root / "fathom.toml").read_text(encoding="utf-8")
            (root / "fathom.toml").write_bytes(text.encode("utf-16"))
            proc = _fathom(root, "reconcile")
            self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
            self.assertIn("must be UTF-8", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_list_and_an_unknown_check(self) -> None:
        listed = _fathom(FIXTURE, "reconcile", "--list")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        for check in reconcile.CHECKS:
            self.assertIn(check.name, listed.stdout)
        unknown = _fathom(FIXTURE, "reconcile", "--check", "no-such-check")
        self.assertEqual(unknown.returncode, 13)
        self.assertIn("no-such-check", unknown.stderr)


def _set_plan(root: Path, plan: str | None) -> None:
    """Rewrite the example bank.toml's plan: its three keys, then *plan* when given."""
    manifest = root / "tasks" / "example" / "bank.toml"
    text = 'name = "example"\ndataset_version = "1"\nholdout = []\n'
    manifest.write_text(text + (plan or ""), encoding="utf-8", newline="\n")


_DRAFT_ENTRY = (
    '[[reconcile.known]]\ncheck = "scenario-known"\nsubject = "example"\n'
    'key = "nudge-draft"\nreason = "kept for the test"\n'
)


class ReplicationTests(unittest.TestCase):
    """The `replication` check: a warning, never a failure, and excused like a disagreement."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = _copy_fixture(self._tmp.name)

    def test_it_is_registered_as_a_warning(self) -> None:
        severities = {c.name: c.severity for c in reconcile.CHECKS}
        self.assertEqual(severities.pop("replication"), "warn")
        self.assertEqual(set(severities.values()), {"fail"})

    def test_the_fixture_draws_one_short_cell(self) -> None:
        found = reconcile.check_replication(FIXTURE)
        self.assertEqual(_fingerprints(found), [SHORT])
        self.assertIn("1 completed trial", found[0].detail)
        self.assertIn("2", found[0].detail)

    def test_an_undeclared_plan_is_one_finding(self) -> None:
        _set_plan(self.root, None)
        found = reconcile.check_replication(self.root)
        self.assertEqual(_fingerprints(found), [("replication", "example", "undeclared")])
        self.assertIn("declares no [plan] repeats_per_cell", found[0].detail)

    def test_a_missing_or_malformed_manifest_reads_as_undeclared_and_says_which(self) -> None:
        manifest = self.root / "tasks" / "example" / "bank.toml"
        _set_plan(self.root, "[plan]\nrepeats_per_cell = true\n")
        (malformed,) = reconcile.check_replication(self.root)
        self.assertEqual(malformed.key, "undeclared")
        self.assertIn("malformed", malformed.detail)
        manifest.unlink()
        (missing,) = reconcile.check_replication(self.root)
        self.assertEqual(missing.key, "undeclared")
        self.assertIn("no tasks/example/bank.toml", missing.detail)

    def test_a_plan_of_one(self) -> None:
        _set_plan(self.root, "[plan]\nrepeats_per_cell = 1\n")
        found = reconcile.check_replication(self.root)
        self.assertEqual(_fingerprints(found), [("replication", "example", "one")])

    def test_every_short_cell_is_its_own_finding(self) -> None:
        _set_plan(self.root, "[plan]\nrepeats_per_cell = 3\n")
        found = reconcile.check_replication(self.root)
        self.assertEqual(
            [d.key for d in found],
            ["short:bare/add", "short:nudge/add", "short:nudge-draft/add"],
        )

    def test_a_ledger_without_a_completed_trial_draws_nothing(self) -> None:
        def errored(rows: list[dict]) -> list[dict]:
            for row in rows:
                if row.get("kind") == "trial":
                    row["status"] = "errored"
            return rows

        _rewrite_rows(self.root, errored)
        _set_plan(self.root, None)
        self.assertEqual(reconcile.check_replication(self.root), [])

    def test_only_the_current_dataset_version_counts(self) -> None:
        """A newer version with one completed cell is what the scorecard shows by default."""

        def bump(rows: list[dict]) -> list[dict]:
            extra = dict(next(r for r in rows if r.get("scenario") == "bare"))
            extra["dataset_version"] = "2"
            return [*rows, extra]

        _rewrite_rows(self.root, bump)
        self.assertEqual(
            [d.key for d in reconcile.check_replication(self.root)], ["short:bare/add"]
        )

    def test_a_warning_does_not_fail_the_gate(self) -> None:
        _set_plan(self.root, None)
        outcome = reconcile.run(self.root)
        self.assertEqual(outcome.unexpected, [])
        self.assertEqual(
            _fingerprints(outcome.warnings), [("replication", "example", "undeclared")]
        )
        self.assertEqual(outcome.stale, [SHORT], "the excuse for the short cell outlived it")
        self.assertFalse(outcome.ok)

    def test_an_excused_warning_is_counted_as_excused(self) -> None:
        outcome = reconcile.run(self.root)
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.warnings, [])
        self.assertEqual(outcome.excused, 2)

    def test_the_cli_prints_warnings_and_exits_0(self) -> None:
        _set_plan(self.root, "[plan]\nrepeats_per_cell = 3\n")
        _write_config(self.root, "[data_root]\nschema = 1\n" + _DRAFT_ENTRY)
        proc = _fathom(self.root, "reconcile")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        printed = [line for line in proc.stdout.splitlines() if line.startswith("[WARNING] ")]
        self.assertEqual(len(printed), 3, proc.stdout)
        self.assertTrue(
            printed[0].startswith("[WARNING] [replication] example (short:bare/add): "),
            printed[0],
        )
        last = proc.stdout.strip().splitlines()[-1]
        self.assertTrue(last.startswith("RECONCILE: OK ("), last)
        self.assertTrue(last.endswith(", 3 warning(s))"), last)
        self.assertIn("0 disagreement(s), 1 excused", last)

    def test_a_disagreement_and_a_warning_together_fail_on_the_disagreement(self) -> None:
        _set_plan(self.root, None)
        _write_config(self.root, "[data_root]\nschema = 1\n")
        proc = _fathom(self.root, "reconcile")
        self.assertEqual(proc.returncode, 13, proc.stdout + proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        self.assertTrue(last.startswith("RECONCILE: FAILED ("), last)
        self.assertIn("1 disagreement(s), 0 excused", last)
        self.assertTrue(last.endswith(", 1 warning(s))"), last)

    def test_the_report_and_the_check_count_the_same_cells(self) -> None:
        from fathom.report import render

        _set_plan(self.root, "[plan]\nrepeats_per_cell = 3\n")
        short = reconcile.check_replication(self.root)
        scorecard = render(
            "example",
            ledger_dir=self.root / "ledger",
            report_dir=self.root / "report",
            tasks_dir=self.root / "tasks",
        ).read_text(encoding="utf-8")
        self.assertIn(f"> **Directional:** {len(short)} of 3 arm x task cells", scorecard)


if __name__ == "__main__":
    unittest.main()
