"""Tests for the context-size-v1 matched-pair bank and its verifiers (§2/§3).

Stdlib-runnable. Proves, BEFORE any paid spend, that the bank measures what the study
claims — interdependence-at-volume, holding the bug constant across a small vs large
workspace:

* ``TestBankIntegrity`` — loads 8 tasks; every task declares ≥2 ``hard_criteria`` and a
  ``[context]`` size/pair; every pair slug appears exactly twice (one small, one large);
  every ``original/`` stash is byte-identical to its fixture (regression-swap reintroduces
  the planted bug).
* ``TestPairIdentity`` (§2) — for each pair, the SMALL core modules + shipped tests +
  ``verify.py`` + ``hard_criteria`` are byte-identical in the LARGE twin (only the
  surrounding volume differs), and the large twin ships ≥30 additional modules.
* ``TestLargeCoherence`` (§3) — each large package imports cleanly (``compileall``); for
  interdependence pairs ≥8 distractors import a contract module (connected graph) and a
  symptom domain-term grep returns ≥5 candidates (FM-N1); the negative-control distractors
  import nothing under test (ignorable); no distractor name-stem-matches the buggy module.
* ``TestGradedness`` (§3) — for ALL 8 buggy fixtures the verifier emits a graded dict with
  ≥1 hard failure and no regression test (exit≠0); for each pair the reference fix flips
  every criterion true (exit 0); and the nonlocal-sku one-caller band-aid passes its own
  caller's criterion but FAILS the other (the interdependence is real, not band-aidable in
  one place).

Run directly: ``python tests/test_context_bank.py`` (exit 0 on success).
"""

import compileall
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "context-size-v1"
sys.path.insert(0, str(REPO / "src"))

EXPECTED_TASKS = {
    "shipping-tax-small",
    "shipping-tax-large",
    "loyalty-reward-small",
    "loyalty-reward-large",
    "nonlocal-sku-small",
    "nonlocal-sku-large",
    "slug-control-small",
    "slug-control-large",
}

# Per-pair structure: package, buggy module stem, the modules distractors import to form
# the graph (empty for the negative control), whether it is the negative control, and a
# couple of symptom domain terms that must be grep-non-unique in the large fixture.
PAIRS = {
    "shipping-tax": {
        "pkg": "shopcart",
        "buggy": "checkout",
        "import_targets": ["config", "rates"],
        "control": False,
        "terms": ["tax", "shipping"],
    },
    "loyalty-reward": {
        "pkg": "rewards",
        "buggy": "points",
        "import_targets": ["accounts", "loyalty"],
        "control": False,
        "terms": ["tier", "reward"],
    },
    "nonlocal-sku": {
        "pkg": "warehouse",
        "buggy": "keys",
        "import_targets": ["aliases", "keys"],
        "control": False,
        "terms": ["sku", "stock"],
    },
    "slug-control": {
        "pkg": "textkit",
        "buggy": "slug",
        "import_targets": [],
        "control": True,
        "terms": [],
    },
}

# Reference fixes (flip every criterion true) + a candidate regression test covering the
# two hard-criteria cases, keyed by pair. The fix module path is relative to fixtures/.
REF = {
    "shipping-tax": {
        "path": "shopcart/checkout.py",
        "fixed": (
            '"""Checkout total computation."""\n\n'
            "from decimal import Decimal\n\n"
            "from .config import FREE_SHIPPING_OVER, SHIPPING_FEE\n"
            "from .rates import TAX_RATE\n\n\n"
            "def grand_total(subtotal):\n"
            "    subtotal = Decimal(subtotal)\n"
            "    tax = subtotal * TAX_RATE\n"
            "    shipping = Decimal('0') if subtotal >= FREE_SHIPPING_OVER else SHIPPING_FEE\n"
            "    return subtotal + tax + shipping\n"
        ),
        "reg": (
            "import sys, unittest\n"
            "from decimal import Decimal\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
            "from shopcart.checkout import grand_total\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertEqual(grand_total(Decimal('60')), Decimal('64.80'))\n"
            "    def test_b(self):\n"
            "        self.assertEqual(grand_total(Decimal('40')), Decimal('48.19'))\n"
        ),
    },
    "loyalty-reward": {
        "path": "rewards/points.py",
        "fixed": (
            '"""Reward points calculation."""\n\n'
            "from decimal import Decimal\n\n"
            "from .accounts import tier_of\n"
            "from .loyalty import rate_for\n\n\n"
            "def reward(customer_id, spend):\n"
            "    spend = Decimal(spend)\n"
            "    return spend * rate_for(tier_of(customer_id))\n"
        ),
        "reg": (
            "import sys, unittest\n"
            "from decimal import Decimal\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
            "from rewards.points import reward\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertEqual(reward('c_gold', Decimal('100')), Decimal('2.00'))\n"
            "    def test_b(self):\n"
            "        self.assertEqual(reward('c_plat', Decimal('100')), Decimal('5.00'))\n"
        ),
    },
    "nonlocal-sku": {
        "path": "warehouse/keys.py",
        "fixed": (
            '"""Shared SKU key helper."""\n\n'
            "from .aliases import canonical\n\n\n"
            "def sku_key(sku):\n"
            "    return canonical(sku)\n"
        ),
        "reg": (
            "import sys, unittest\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
            "from warehouse.inventory import stock_for\n"
            "from warehouse.pricing import price_for\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertEqual("
            "stock_for('WIDGET', [('WIDGET', 3), ('WID', 2), ('WIDGET-V2', 1)]), 6)\n"
            "    def test_b(self):\n"
            "        self.assertEqual(price_for('WID', {'WIDGET': 999}), 999)\n"
        ),
    },
    "slug-control": {
        "path": "textkit/slug.py",
        "fixed": (
            '"""Slugify titles for URLs."""\n\n'
            "import re\n\n\n"
            "def slugify(title):\n"
            "    s = title.lower()\n"
            "    s = re.sub(r'[^a-z0-9]+', '-', s)\n"
            "    return s.strip('-')\n"
        ),
        "reg": (
            "import sys, unittest\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n"
            "from textkit.slug import slugify\n\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertEqual(slugify('Hello   World'), 'hello-world')\n"
            "    def test_b(self):\n"
            "        self.assertEqual(slugify('  Hi!  '), 'hi')\n"
        ),
    },
}

# nonlocal-sku band-aid: fix only inventory's caller, leave the shared root + pricing buggy.
BANDAID_SKU = (
    '"""Inventory stock lookups."""\n\n'
    "from .keys import sku_key  # noqa: F401\n"
    "from .aliases import canonical\n\n\n"
    "def stock_for(sku, ledger):\n"
    "    total = 0\n"
    "    for entry_sku, qty in ledger:\n"
    "        if canonical(entry_sku) == canonical(sku):\n"
    "            total += qty\n"
    "    return total\n"
)


def _context(task_id: str) -> dict:
    with open(BANK / task_id / "task.toml", "rb") as f:
        return tomllib.load(f).get("context", {})


def _run_verify(task_id: str, view: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(BANK / task_id / "verify.py"), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdout.strip(), f"{task_id}: verify emitted no JSON; stderr=\n{proc.stderr}"
    return json.loads(proc.stdout), proc.returncode


def _pkg_files(task_id: str, pkg: str) -> dict[str, str]:
    d = BANK / task_id / "fixtures" / pkg
    return {p.name: p.read_text(encoding="utf-8") for p in d.glob("*.py")}


def _load():
    from fathom.taskbank import load_bank

    return load_bank(BANK)


class TestBankIntegrity(unittest.TestCase):
    def test_loads_eight_tasks(self):
        bank = _load()
        self.assertEqual(bank.name, "context-size-v1")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual(sorted(t.id for t in bank.tasks), sorted(EXPECTED_TASKS))

    def test_two_hard_criteria_each(self):
        for t in _load().tasks:
            with self.subTest(task=t.id):
                hard = t.verify.get("hard_criteria")
                self.assertIsInstance(hard, list)
                self.assertGreaterEqual(len(hard), 2)

    def test_context_tags_and_pair_slugs(self):
        # every task has size in {small,large} + a pair slug; each slug twice (one each).
        by_pair: dict[str, set[str]] = {}
        for task_id in EXPECTED_TASKS:
            ctx = _context(task_id)
            self.assertIn(ctx.get("size"), ("small", "large"), f"{task_id}: bad [context] size")
            self.assertTrue(ctx.get("pair"), f"{task_id}: missing [context] pair")
            by_pair.setdefault(ctx["pair"], set()).add(ctx["size"])
        self.assertEqual(set(by_pair), set(PAIRS))
        for pair, sizes in by_pair.items():
            self.assertEqual(sizes, {"small", "large"}, f"{pair}: needs one small + one large")

    def test_stash_byte_identical_to_fixture(self):
        for task_id in EXPECTED_TASKS:
            with self.subTest(task=task_id):
                orig = BANK / task_id / "original"
                fixtures = BANK / task_id / "fixtures"
                for stashed in sorted(orig.glob("*.py")):
                    twins = [m for m in fixtures.rglob(stashed.name) if "tests" not in m.parts]
                    self.assertEqual(len(twins), 1, f"{task_id}: 1 twin for {stashed.name}")
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        twins[0].read_text(encoding="utf-8"),
                        f"{task_id}: stash {stashed.name} drifted",
                    )
                for stashed in sorted((orig / "tests").glob("*.py")):
                    twin = fixtures / "tests" / stashed.name
                    self.assertTrue(
                        twin.is_file(), f"{task_id}: missing fixture test {stashed.name}"
                    )
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        twin.read_text(encoding="utf-8"),
                        f"{task_id}: stash test {stashed.name} drifted",
                    )


class TestPairIdentity(unittest.TestCase):
    def test_core_and_verifier_identical_large_ships_more(self):
        for pair, spec in PAIRS.items():
            with self.subTest(pair=pair):
                pkg = spec["pkg"]
                small_core = _pkg_files(f"{pair}-small", pkg)
                large_core = _pkg_files(f"{pair}-large", pkg)
                # every SMALL core module is byte-identical in LARGE (buggy + contracts + init)
                for name, src in small_core.items():
                    self.assertIn(name, large_core, f"{pair}: large missing core {name}")
                    self.assertEqual(
                        src, large_core[name], f"{pair}: core {name} drifted small→large"
                    )
                # large ships >=30 additional modules (the distractors)
                self.assertGreaterEqual(
                    len(large_core) - len(small_core), 30, f"{pair}: <30 distractors"
                )
                # verify.py + hard_criteria identical across the pair
                self.assertEqual(
                    (BANK / f"{pair}-small" / "verify.py").read_text(encoding="utf-8"),
                    (BANK / f"{pair}-large" / "verify.py").read_text(encoding="utf-8"),
                    f"{pair}: verify.py drifted small→large",
                )
                self.assertEqual(
                    _hard(f"{pair}-small"), _hard(f"{pair}-large"), f"{pair}: hard_criteria drifted"
                )


class TestLargeCoherence(unittest.TestCase):
    def test_compiles_clean(self):
        for pair, spec in PAIRS.items():
            with self.subTest(pair=pair):
                pkg_dir = BANK / f"{pair}-large" / "fixtures" / spec["pkg"]
                self.assertTrue(
                    compileall.compile_dir(str(pkg_dir), quiet=1, force=True),
                    f"{pair}: large fixture does not compile cleanly",
                )

    def test_distractor_graph_and_grep_resistance(self):
        for pair, spec in PAIRS.items():
            with self.subTest(pair=pair):
                pkg = spec["pkg"]
                small = set(_pkg_files(f"{pair}-small", pkg))
                large = _pkg_files(f"{pair}-large", pkg)
                distractors = {n: s for n, s in large.items() if n not in small}
                self.assertGreaterEqual(len(distractors), 30, f"{pair}: <30 distractors")
                buggy_stem = spec["buggy"]
                # no distractor name-stem-matches the buggy module (FM-N1)
                for name in distractors:
                    self.assertFalse(
                        name[:-3].startswith(buggy_stem),
                        f"{pair}: distractor {name} collides with target stem {buggy_stem}",
                    )
                if spec["control"]:
                    # negative control: distractors import NOTHING under test (ignorable)
                    for name, src in distractors.items():
                        self.assertNotIn(
                            f"import {buggy_stem}", src, f"{pair}: control distractor refs target"
                        )
                        self.assertNotIn(
                            f"from .{buggy_stem}", src, f"{pair}: control distractor refs target"
                        )
                else:
                    # >=8 distractors import a contract module (connected graph, FM-N2)
                    refs = sum(
                        1
                        for src in distractors.values()
                        if any(f"from .{c} import" in src for c in spec["import_targets"])
                    )
                    self.assertGreaterEqual(
                        refs, 8, f"{pair}: only {refs} distractors ref contracts"
                    )
                    # symptom domain terms are not uniquely greppable (>=5 candidates)
                    for term in spec["terms"]:
                        n = sum(1 for name in large if term in name)
                        self.assertGreaterEqual(n, 5, f"{pair}: grep {term} returns {n} (<5)")


class TestGradedness(unittest.TestCase):
    def test_buggy_fixture_graded_with_hard_failure(self):
        hard_by_task = {t.id: set(t.verify["hard_criteria"]) for t in _load().tasks}
        for task_id in EXPECTED_TASKS:
            with self.subTest(task=task_id):
                crit, code = _run_verify(task_id, BANK / task_id / "fixtures")
                for k in hard_by_task[task_id]:
                    self.assertIn(k, crit, f"{task_id}: hard {k} not emitted")
                self.assertTrue(
                    any(not crit[k] for k in hard_by_task[task_id]),
                    f"{task_id}: no hard criterion failed on buggy fixture",
                )
                self.assertFalse(crit.get("regression_test_present", False))
                self.assertNotEqual(code, 0)

    def test_reference_fix_passes_every_pair(self):
        for pair, ref in REF.items():
            with self.subTest(pair=pair), tempfile.TemporaryDirectory() as td:
                view = Path(td) / "view"
                shutil.copytree(BANK / f"{pair}-small" / "fixtures", view)
                (view / ref["path"]).write_text(ref["fixed"], encoding="utf-8")
                (view / "tests" / "test_reg.py").write_text(ref["reg"], encoding="utf-8")
                crit, code = _run_verify(f"{pair}-small", view)
                self.assertTrue(all(crit.values()), f"{pair}: not all true: {crit}")
                self.assertEqual(code, 0)

    def test_nonlocal_bandaid_fails_the_other_caller(self):
        # Fixing only inventory's caller (not the shared root) passes stock but fails price:
        # proves the task genuinely needs the shared-root fix (the interdependence is real).
        with tempfile.TemporaryDirectory() as td:
            view = Path(td) / "view"
            shutil.copytree(BANK / "nonlocal-sku-small" / "fixtures", view)
            (view / "warehouse" / "inventory.py").write_text(BANDAID_SKU, encoding="utf-8")
            crit, code = _run_verify("nonlocal-sku-small", view)
            self.assertTrue(crit["stock_merges_aliases"], "band-aid should pass its own caller")
            self.assertFalse(crit["price_merges_aliases"], "band-aid must fail the other caller")
            self.assertNotEqual(code, 0)


def _hard(task_id: str) -> list[str]:
    with open(BANK / task_id / "task.toml", "rb") as f:
        return tomllib.load(f)["verify"]["hard_criteria"]


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
