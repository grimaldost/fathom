"""Reconciliation — two independent derivations of one fact, compared until they agree.

Counting how every defect since 0.2.0 was actually discovered gives paid-measurement 6,
sustained-operation 6, **post-hoc-audit 3**, authoring-review 2, calibration-before-trust 1.
The third column is the one this module exists for.  Its defects share a property that makes
them invisible to every other method: **the run completed and every artifact was internally
self-consistent.**  No amount of buying or operating surfaces them.

- A gate probe shipped as a literal placeholder path, so it never executed and the arm
  silently ran as its own control.  It scored 9/10, was published, and was cited as the
  keystone contrast for a downstream programme.  Six weeks and a ~170k-form hash
  reconstruction later, its configuration turned out to be unrecoverable.
- A report was published against a 10-trial snapshot; an eleventh trial was appended to the
  same ledger in the same wave.  Three documents then carried three different control-pool
  sizes and three different p-values.  The suite was green throughout.
- A published multiplier (x3.81) was refuted against the saved streams it claimed to
  summarise, having been in production use as a budgeting unit the whole time.

What finds these is not more spend and not more patience.  It is **having two independent
derivations of the same fact and checking they agree**: a committed scenario against a
ledger's ``config_hash``; a report's *n* against the ledger's *n*; a stored cost against a
recomputation from the same row's own usage.  Where only one derivation exists, the defect
is undetectable by any means.

Exactly one such reconciliation was mechanized before this module (the ledger index), and it
cost a bespoke tool-plus-test pair to build.  Here a reconciliation is a registered function,
so the fourth one costs a function rather than a new pair.

## Known exceptions, and why they are self-expiring

Some discrepancies are permanent facts about committed history.  The void ``haiku-gate-sg``
arm has no preimage and never will — that *is* the finding, and it cannot be repaired
because the evidence is gone rather than wrong.  A check that stays red on committed data is
a check people delete or learn to skip, which is how a gate goes hollow.

So exceptions are declared, each with a reason, and **an exception whose discrepancy no
longer occurs is itself a failure** (:func:`stale_exceptions`).  Without that second
direction, exceptions accumulate silently until the gate asserts nothing — the vacuous shape
this repo keeps catching elsewhere.

Stdlib only; runs without uv.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import tomllib
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from fathom import ledgerindex

REPO = Path(__file__).resolve().parents[2]


@dataclasses.dataclass(frozen=True)
class Discrepancy:
    """One disagreement between two derivations of the same fact.

    ``key`` is the stable identity of the disagreement *within* its check — a ledger's
    ``config_hash``, a bank name, a row index.  It is what an exception is declared against,
    so it must not drift between runs on unchanged data.
    """

    check: str
    subject: str
    key: str
    detail: str

    @property
    def fingerprint(self) -> tuple[str, str, str]:
        return (self.check, self.subject, self.key)

    def __str__(self) -> str:
        return f"[{self.check}] {self.subject} ({self.key}): {self.detail}"


@dataclasses.dataclass(frozen=True)
class Reconciliation:
    """A named check: derive a fact two ways over *repo*, return where they disagree."""

    name: str
    describe: str
    run: Callable[[Path], list[Discrepancy]]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_ledger_index(repo: Path) -> list[Discrepancy]:
    """The committed index against a fresh render of ``ledger/``.

    Derivation A is ``docs/reports/LEDGER-INDEX.md`` as committed; derivation B is the index
    rendered from the ledgers as they stand now.  Any append to any ledger separates them
    until the index is re-stamped, and the re-render diff names which arms moved.
    """
    ledger_dir = repo / "ledger"
    index_path = repo / "docs" / "reports" / "LEDGER-INDEX.md"
    rendered = ledgerindex.render(ledger_dir)
    committed = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    if committed == rendered:
        return []
    return [
        Discrepancy(
            check="ledger-index",
            subject="docs/reports/LEDGER-INDEX.md",
            key="whole-document",
            detail=(
                "the committed index disagrees with a fresh render of ledger/. A ledger was "
                "appended to without re-stamping. Re-render with "
                "`python tools/ledger_index.py --write`, read the diff — it names the arms "
                "whose n moved — and update every document quoting those counts, pooled "
                "control totals or p-values before committing."
            ),
        )
    ]


def scenario_names(repo: Path) -> set[str]:
    """Every arm name declared by a scenario TOML anywhere under ``scenarios/``.

    The walk is **recursive** on purpose.  ``fathom run`` globs its scenario dir
    non-recursively (which is why ``--scenarios-dir`` is load-bearing), and reusing that
    behaviour here would see 3 of 189 arms and report near-total failure.  A file is treated
    as a scenario only when it declares both ``name`` and ``adapter``; TOMLs that merely live
    under a mounted plugin's asset tree are data, not arms.
    """
    names: set[str] = set()
    root = repo / "scenarios"
    if not root.is_dir():
        return names
    for toml_path in sorted(root.rglob("*.toml")):
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        name = data.get("name")
        if isinstance(name, str) and data.get("adapter"):
            names.add(name)
    return names


def ledger_rows(repo: Path) -> Iterator[tuple[str, dict]]:
    """(bank, row) for every parseable row of every committed ledger.

    ``ledger/archive/`` is out of scope: an archived ledger is a run that was invalidated on
    purpose, so holding it to the same contract would assert the opposite of what archiving
    means.
    """
    ledger_dir = repo / "ledger"
    if not ledger_dir.is_dir():
        return
    for path in sorted(ledger_dir.glob("*.jsonl")):
        for row in ledgerindex.rows(path):
            yield path.stem, row


def check_config_hash_preimage(repo: Path) -> list[Discrepancy]:
    """A stored ``config_hash`` against a fresh digest of its own stored preimage.

    This is the exact reconciliation, and it applies to rows written from 0.4.0 on.  Rows
    written earlier carry no preimage; they are **not** failures — an absent second
    derivation is a coverage gap, reported by :func:`preimage_coverage`, not a disagreement.
    Calling them failures would put 45% of committed history behind an exception table that
    churns with every unrelated plugin edit, which is the hollow gate this module exists to
    avoid.
    """
    found: list[Discrepancy] = []
    for bank, row in ledger_rows(repo):
        preimage = row.get("config_preimage")
        stored = row.get("config_hash")
        if not preimage or not stored:
            continue
        actual = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
        if actual != stored:
            found.append(
                Discrepancy(
                    check="config-hash-preimage",
                    subject=bank,
                    key=str(stored),
                    detail=(
                        f"row records config_hash {stored} but sha256 of its own stored "
                        f"preimage is {actual} — the row's identity does not match its "
                        "configuration, so the trial cannot be attributed"
                    ),
                )
            )
    return found


def check_scenario_known(repo: Path) -> list[Discrepancy]:
    """Every completed trial's arm name against the scenarios committed in the tree.

    This is the decidable half of "is this arm attributable".  It deliberately does not ask
    whether the *hash* reconstructs — that depends on a plugin ``tree_sha`` globbed from a
    live filesystem, so it is unstable by construction and 45% of history fails it.  It asks
    the question that has a stable answer: **was the configuration that produced these paid
    trials ever committed at all?**  When the answer is no, no correction can restate the
    number, because the evidence is gone rather than wrong.
    """
    known = scenario_names(repo)
    if not known:
        return []
    counts: dict[tuple[str, str], int] = {}
    for bank, row in ledger_rows(repo):
        if row.get("kind") != "trial" or row.get("status") != "completed":
            continue
        arm = row.get("scenario")
        if isinstance(arm, str) and arm and arm not in known:
            counts[(bank, arm)] = counts.get((bank, arm), 0) + 1
    return [
        Discrepancy(
            check="scenario-known",
            subject=bank,
            key=arm,
            detail=(
                f"{n} completed trial(s) name arm {arm!r}, but no scenario TOML in the tree "
                "declares it — the configuration that produced those paid trials was never "
                "committed, so they are historical-only and may not be cited as a result"
            ),
        )
        for (bank, arm), n in sorted(counts.items())
    ]


def version_sites(repo: Path) -> dict[str, str | None]:
    """The released version as each site states it; ``None`` where a site cannot be read.

    Three files state the released version independently: ``pyproject.toml`` (what the
    package says), ``.claude-plugin/plugin.json`` (what an installed plugin copy re-pulls
    on — the runtime fetches a plugin again only when this value moves), and the newest
    ``## [X.Y.Z]`` heading of ``CHANGELOG.md`` (what the record says shipped).
    ``[Unreleased]`` is not a site: entries accumulate there between cuts while every
    versioned site correctly stays at the previous release.
    """
    sites: dict[str, str | None] = {}

    version: str | None = None
    try:
        data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
        raw = data.get("project", {}).get("version")
        version = raw if isinstance(raw, str) else None
    except (OSError, tomllib.TOMLDecodeError):
        version = None
    sites["pyproject.toml"] = version

    version = None
    try:
        raw = json.loads((repo / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        found = raw.get("version")
        version = found if isinstance(found, str) else None
    except (OSError, json.JSONDecodeError):
        version = None
    sites[".claude-plugin/plugin.json"] = version

    version = None
    try:
        text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
        match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, flags=re.MULTILINE)
        version = match.group(1) if match else None
    except OSError:
        version = None
    sites["CHANGELOG.md"] = version

    return sites


def check_version_sites(repo: Path) -> list[Discrepancy]:
    """Every site's stated version against ``pyproject.toml``'s.

    The 0.4.0 cut is the incident: the release commit moved ``pyproject.toml``, ``uv.lock``
    and the changelog heading but left the plugin manifest at 0.3.0, so every installed
    plugin copy kept resolving the old tree — and the only test looking at the manifest
    asserted that *a* version exists, not that it means anything.  The bump was a hand-run
    ritual step, and this is the fact-derived-twice check that replaces the ritual's memory.
    """
    sites = version_sites(repo)
    reference = sites["pyproject.toml"]
    found: list[Discrepancy] = []
    for site, version in sites.items():
        if version is None:
            found.append(
                Discrepancy(
                    check="version-sites",
                    subject=site,
                    key="unreadable",
                    detail=(
                        "no released version could be read from this site, so it cannot be "
                        "held against the others — restore the [project] version, the "
                        "manifest's version field, or the newest `## [X.Y.Z]` heading"
                    ),
                )
            )
        elif reference is not None and version != reference:
            found.append(
                Discrepancy(
                    check="version-sites",
                    subject=site,
                    key=version,
                    detail=(
                        f"states {version} while pyproject.toml states {reference} — a "
                        "release moved one version site without the others; bump this site "
                        "to match (the release ritual owns all three in one commit)"
                    ),
                )
            )
    return found


def preimage_coverage(repo: Path) -> tuple[int, int]:
    """(rows carrying a preimage, rows total) — reported, never gated.

    The ratio is the honest statement of how much of the record the exact check can speak
    for.  It only moves forward, as new trials are bought.
    """
    total = 0
    with_preimage = 0
    for _bank, row in ledger_rows(repo):
        if row.get("kind") not in {"trial", "run"}:
            continue
        total += 1
        if row.get("config_preimage"):
            with_preimage += 1
    return with_preimage, total


CHECKS: tuple[Reconciliation, ...] = (
    Reconciliation(
        name="ledger-index",
        describe="the committed ledger index against a fresh render of ledger/",
        run=check_ledger_index,
    ),
    Reconciliation(
        name="config-hash-preimage",
        describe="each row's config_hash against a digest of its own stored preimage",
        run=check_config_hash_preimage,
    ),
    Reconciliation(
        name="scenario-known",
        describe="every completed trial's arm against the scenarios committed in the tree",
        run=check_scenario_known,
    ),
    Reconciliation(
        name="version-sites",
        describe=(
            "the released version in pyproject.toml, the plugin manifest, and the newest "
            "CHANGELOG heading"
        ),
        run=check_version_sites,
    ),
)


# ---------------------------------------------------------------------------
# Known exceptions — permanent facts about committed history
# ---------------------------------------------------------------------------

KNOWN: dict[tuple[str, str, str], str] = {
    ("scenario-known", "ablation-v2", "haiku-gate-sg"): (
        "The void arm. Its gate probe shipped as a literal placeholder path, so it never "
        "executed and the arm ran as its own control; a ~170k-form sweep found no preimage "
        "for its config_hash. The 10 trials are real spend and stay in the ledger, marked "
        "void wherever they are cited (tests/test_void_arms.py). Its replacement is the "
        "forked haiku-gate-sg2, which is committed and has not yet run."
    ),
    ("scenario-known", "ablation-v2", "lazy-gate"): (
        "A withdrawn stub, 2 trials, never part of the published matrix — "
        "docs/reports/2026-07-01-pr-pilot-ablation-v2-findings.md excludes it by name in the "
        "matrix heading. Its scenario file was never committed, which is consistent with the "
        "arm having been abandoned rather than measured."
    ),
}


# ---------------------------------------------------------------------------
# Running them
# ---------------------------------------------------------------------------


def registry(names: Iterable[str] | None = None) -> list[Reconciliation]:
    """The checks to run; *names* selects a subset. An unknown name is an error."""
    if names is None:
        return list(CHECKS)
    wanted = list(names)
    known = {c.name: c for c in CHECKS}
    missing = [n for n in wanted if n not in known]
    if missing:
        raise KeyError(f"unknown reconciliation(s): {', '.join(sorted(missing))}")
    return [known[n] for n in wanted]


def run_all(repo: Path = REPO, *, names: Iterable[str] | None = None) -> list[Discrepancy]:
    """Every discrepancy every selected check finds, exceptions included."""
    found: list[Discrepancy] = []
    for check in registry(names):
        found.extend(check.run(repo))
    return found


def unexpected(found: Iterable[Discrepancy]) -> list[Discrepancy]:
    """The discrepancies nobody has accepted — the ones that fail the gate."""
    return [d for d in found if d.fingerprint not in KNOWN]


def stale_exceptions(found: Iterable[Discrepancy]) -> list[tuple[str, str, str]]:
    """Declared exceptions whose discrepancy no longer occurs.

    A stale exception is a failure, not a tidiness issue: it is the mechanism by which an
    exception list grows until the gate it guards asserts nothing.
    """
    seen = {d.fingerprint for d in found}
    return [fp for fp in KNOWN if fp not in seen]
