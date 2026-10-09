"""Reconciliation — two independent derivations of one fact, compared until they agree.

Some defects are invisible to every other way of finding them: **the run completed and every
artifact was internally self-consistent.**  No amount of buying or operating surfaces them.
Three shapes recur:

- A treatment arm's probe is written wrong (a placeholder path, say), so the treatment
  never executes and the arm silently runs as its own control.  It scores well, is written
  up, and is cited, and by the time anyone looks its configuration may be unrecoverable.
- A report quotes counts from a ledger snapshot, and a later trial is appended to the same
  ledger.  Documents written at different moments then quote different sample sizes and
  statistics, and every test stays green.
- A derived figure (a cost multiplier, say) is published and used as a working unit, and
  is only later checked against the raw data it claims to summarise.

What finds these is not more spend and not more patience.  It is **having two independent
derivations of the same fact and checking they agree**: a committed scenario against a
ledger's ``config_hash``; a report's *n* against the ledger's *n*; a stored cost against a
recomputation from the same row's own usage.  Where only one derivation exists, the defect
is undetectable by any means.

Here a reconciliation is a registered function, so adding one costs a function rather than
a new tool and test.

## Where it runs

The root is an explicit ``root`` argument or, by default, the working directory at call
time — never this file's location, which in an installed engine is a virtualenv's
site-packages.  ``fathom reconcile`` finds its root the way every fathom command finds a data
root (``--home``, ``FATHOM_HOME``, the nearest marked directory at or above the working
directory; see :mod:`fathom.home` and :func:`fathom.ledgerindex.check_root`).  Two kinds of
root carry facts worth reconciling:

- a **data root**: a ``fathom.toml`` with a ``[data_root]`` table, next to ``tasks/``,
  ``scenarios/``, ``ledger/`` and ``docs/reports/``;
- an **engine checkout**: the fathom source tree (``src/fathom/`` beside a
  ``pyproject.toml`` that names the ``fathom`` project) with ``.claude-plugin/plugin.json``
  at its root (:func:`fathom.ledgerindex.is_engine_checkout`).

The ledger and scenario checks find nothing to compare in an engine checkout, and the
version-sites check is skipped where there is no plugin manifest, as in a data root.

## Known exceptions, and why they are self-expiring

Some discrepancies are permanent facts about committed history.  An arm whose configuration
was never committed has no scenario to be held against and never will — that *is* the
finding, and it cannot be repaired because the evidence is gone rather than wrong.  A check
that stays red on committed data is a check people delete or learn to skip, which is how a
gate goes hollow.

So exceptions are declared in the root's ``fathom.toml``, each with a reason::

    [[reconcile.known]]
    check = "scenario-known"
    subject = "<bank>"
    key = "<arm>"
    reason = "why this discrepancy is accepted"

and **an exception whose discrepancy no longer occurs is itself a failure**
(:func:`stale_exceptions`).  Without that second direction, exceptions accumulate silently
until the gate asserts nothing — the vacuous shape this repo keeps catching elsewhere.  The
engine ships no exceptions of its own: they are facts about one data root's history, so
they live with that history.

Stdlib only; runs without uv.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import tomllib
from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path

from fathom import ledgerindex, replication

# How a root is recognised is defined once, in ledgerindex, so that ``fathom reconcile`` and
# ``python -m fathom.ledgerindex`` accept and refuse the same directories.  Re-exported here
# because the CLI and callers of this module name them through it.
CONFIG_FILE = ledgerindex.CONFIG_FILE
PLUGIN_MANIFEST = ledgerindex.PLUGIN_MANIFEST
# Front-door documents that tell a reader how to install a release. A pinned install line
# (`git+https://.../fathom@vX.Y.Z`) in one of them is a version site; a document without
# one is not. Nothing held these pins, and they stayed two releases behind.
INSTALL_PIN_DOCS = ("README.md", "README-plugin.md", "skills/fathom-eval/reference/authoring.md")
_INSTALL_PIN = re.compile(r"git\+https://\S+?/fathom@v(\d+\.\d+\.\d+)")
is_data_root = ledgerindex.is_data_root
root_kind = ledgerindex.root_kind
not_a_root_message = ledgerindex.not_a_root_message

Fingerprint = tuple[str, str, str]
# What a check's findings do to the gate: a "fail" finding is a disagreement, a "warn"
# finding is printed and never changes the exit code.
SEVERITY_FAIL = "fail"
SEVERITY_WARN = "warn"


def resolve_root(root: Path | None = None) -> Path:
    """The root to reconcile: *root* when given, else the working directory at call time."""
    return Path.cwd() if root is None else Path(root)


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
    # Set from the check that found it (``Reconciliation.severity``) when the check runs.
    severity: str = SEVERITY_FAIL

    @property
    def fingerprint(self) -> Fingerprint:
        return (self.check, self.subject, self.key)

    def __str__(self) -> str:
        return f"[{self.check}] {self.subject} ({self.key}): {self.detail}"


def _applies_everywhere(root: Path) -> str | None:
    return None


@dataclasses.dataclass(frozen=True)
class Reconciliation:
    """A named check: derive a fact two ways over *root*, return where they disagree.

    ``skip`` returns the reason the check does not apply at a root, or ``None`` when it
    does.  A skipped check is reported as skipped, never counted as passed silently.

    ``severity`` is ``"fail"`` (a finding is a disagreement and fails the gate) or ``"warn"``
    (a finding is printed as a warning and never fails it).  Either kind is excused by a
    ``[[reconcile.known]]`` entry the same way, and an entry that excuses nothing is stale
    either way.
    """

    name: str
    describe: str
    run: Callable[[Path], list[Discrepancy]]
    skip: Callable[[Path], str | None] = _applies_everywhere
    severity: str = SEVERITY_FAIL


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_ledger_index(root: Path) -> list[Discrepancy]:
    """The committed index against a fresh render of ``ledger/``.

    Derivation A is ``docs/reports/LEDGER-INDEX.md`` as committed; derivation B is the index
    rendered from the ledgers as they stand now.  Any append to any ledger separates them
    until the index is re-stamped, and the re-render diff names which arms moved.  A root
    with no ledgers and no index has nothing to stamp and agrees with itself.

    The detail says which ledgers moved, or that none did and only the engine's rendering
    of the index changed (:class:`fathom.ledgerindex.Staleness`); the key is the same
    either way, since neither is a discrepancy anyone should excuse.
    """
    stale = ledgerindex.staleness(root)
    if stale is None:
        return []
    return [
        Discrepancy(
            check="ledger-index",
            subject=ledgerindex.INDEX_PATH.as_posix(),
            key="whole-document",
            detail=stale.detail,
        )
    ]


def scenario_names(root: Path) -> set[str]:
    """Every arm name declared by a scenario TOML anywhere under ``scenarios/``.

    The walk is **recursive** on purpose.  ``fathom run`` globs its scenario dir
    non-recursively (which is why ``--scenarios-dir`` is load-bearing), and reusing that
    behaviour here would see only the top-level arms and report the rest as unknown.  A file
    is treated as a scenario only when it declares both ``name`` and ``adapter``; TOMLs that
    merely live under a mounted plugin's asset tree are data, not arms.
    """
    names: set[str] = set()
    scenarios = root / "scenarios"
    if not scenarios.is_dir():
        return names
    for toml_path in sorted(scenarios.rglob("*.toml")):
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            continue
        name = data.get("name")
        if isinstance(name, str) and data.get("adapter"):
            names.add(name)
    return names


def ledger_rows(root: Path) -> Iterator[tuple[str, dict]]:
    """(bank, row) for every parseable row of every committed ledger.

    ``ledger/archive/`` is out of scope: an archived ledger is a run that was invalidated on
    purpose, so holding it to the same contract would assert the opposite of what archiving
    means.
    """
    for path in ledgerindex.ledger_files(root / ledgerindex.LEDGER_DIR):
        for row in ledgerindex.rows(path):
            yield path.stem, row


def check_config_hash_preimage(root: Path) -> list[Discrepancy]:
    """A stored ``config_hash`` against a fresh digest of its own stored preimage.

    This is the exact reconciliation, and it applies to rows written from 0.4.0 on.  Rows
    written earlier carry no preimage; they are **not** failures — an absent second
    derivation is a coverage gap, reported by :func:`preimage_coverage`, not a disagreement.
    Calling them failures would put a large share of older history behind an exception
    table that churns with every unrelated plugin edit, which is the hollow gate this module
    exists to avoid.
    """
    found: list[Discrepancy] = []
    for bank, row in ledger_rows(root):
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


def check_scenario_known(root: Path) -> list[Discrepancy]:
    """Every completed trial's arm name against the scenarios committed in the tree.

    This is the decidable half of "is this arm attributable".  It deliberately does not ask
    whether the *hash* reconstructs — that depends on a plugin ``tree_sha`` globbed from a
    live filesystem, so it is unstable by construction.  It asks the question that has a
    stable answer: **was the configuration that produced these paid trials ever committed
    at all?**  When the answer is no, no correction can restate the number, because the
    evidence is gone rather than wrong.  A ledger with completed trials and no
    ``scenarios/`` at all fails on every arm, rather than passing for want of anything to
    compare.
    """
    known = scenario_names(root)
    counts: dict[tuple[str, str], int] = {}
    for bank, row in ledger_rows(root):
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


def version_sites_skip(root: Path) -> str | None:
    """Why version-sites does not apply at *root*, or ``None`` when it does.

    The released version is a fact about an engine checkout.  A data root has no plugin
    manifest and no engine changelog, so holding it to three sites it does not carry would
    fail every data root for a fact that is not its own.
    """
    if (root / PLUGIN_MANIFEST).exists():
        return None
    return f"no {PLUGIN_MANIFEST.as_posix()} at this root; version sites belong to the engine"


def version_sites(root: Path) -> dict[str, str | None]:
    """The released version as each site states it; ``None`` where a site cannot be read.

    Three files state the released version independently: ``pyproject.toml`` (what the
    package says), ``.claude-plugin/plugin.json`` (what an installed plugin copy re-pulls
    on — the runtime fetches a plugin again only when this value moves), and the newest
    ``## [X.Y.Z]`` heading of ``CHANGELOG.md`` (what the record says shipped).
    ``[Unreleased]`` is not a site: entries accumulate there between cuts while every
    versioned site correctly stays at the previous release. Each pinned install line in
    :data:`INSTALL_PIN_DOCS` is a site too (``<doc> (install pin)``), so a release that
    leaves a reader installing the previous tag fails here; a pin that disagrees wins over
    one that agrees, so one stale line in a document is not hidden by another.
    """
    sites: dict[str, str | None] = {}

    version: str | None = None
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        raw = data.get("project", {}).get("version")
        version = raw if isinstance(raw, str) else None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        version = None
    sites["pyproject.toml"] = version

    version = None
    try:
        raw = json.loads((root / PLUGIN_MANIFEST).read_text(encoding="utf-8"))
        found = raw.get("version") if isinstance(raw, dict) else None
        version = found if isinstance(found, str) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        version = None
    sites[PLUGIN_MANIFEST.as_posix()] = version

    version = None
    try:
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, flags=re.MULTILINE)
        version = match.group(1) if match else None
    except (OSError, UnicodeDecodeError):
        version = None
    sites["CHANGELOG.md"] = version

    for doc in INSTALL_PIN_DOCS:
        try:
            pins = _INSTALL_PIN.findall((root / doc).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if pins:
            stale = [pin for pin in pins if pin != sites["pyproject.toml"]]
            sites[f"{doc} (install pin)"] = stale[0] if stale else pins[0]

    return sites


def check_version_sites(root: Path) -> list[Discrepancy]:
    """Every site's stated version against ``pyproject.toml``'s.

    A release that moves ``pyproject.toml`` and the changelog heading but leaves the plugin
    manifest behind makes every installed plugin copy keep resolving the old tree, and a
    test that only asserts *a* version exists cannot see it.  The bump is a hand-run release
    step; this is the fact-derived-twice check that replaces remembering it.

    Returns nothing where :func:`version_sites_skip` says the check does not apply; the
    registry reports that as a skip.  Where the manifest exists, a site that cannot state a
    version is a discrepancy, not a skip.
    """
    if version_sites_skip(root) is not None:
        return []
    sites = version_sites(root)
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
                        "to match (the release ritual owns all of them in one commit)"
                    ),
                )
            )
    return found


def check_replication(root: Path) -> list[Discrepancy]:
    """Each bank's declared ``[plan] repeats_per_cell`` against the trials its ledger holds.

    A warning, not a failure (severity ``"warn"``): a result bought at too few repeats is
    still a result, and the reader is told it is directional.  For every ledger with at least
    one completed trial in its current ``dataset_version`` (the scorecard's default view),
    ``tasks/<bank>/bank.toml`` is read and the findings, subject the bank, are: ``undeclared``
    (no plan, no ``bank.toml``, or a malformed plan; the detail says which), ``one`` (a plan
    of 1), or one ``short:<arm>/<task>`` per cell holding fewer completed trials than a plan
    of 2 or more declares.  The cells are counted as the scorecard counts them
    (:mod:`fathom.replication`), so the two report the same cells.
    """
    by_bank: dict[str, list[dict]] = {}
    for bank, row in ledger_rows(root):
        by_bank.setdefault(bank, []).append(row)
    found: list[Discrepancy] = []
    consequence = "every result from this bank is directional, not replicated"
    for bank, rows in sorted(by_bank.items()):
        scoped = replication.current_version_rows(rows)
        if not any(r.get("kind") == "trial" and r.get("status") == "completed" for r in scoped):
            continue
        where = f"tasks/{bank}"
        reading = replication.read_plan(root / where)
        declared = reading.repeats_per_cell
        if declared is None:
            reason = replication.undeclared_reason(reading, where)
            found.append(Discrepancy("replication", bank, "undeclared", f"{reason}; {consequence}"))
            continue
        if declared == 1:
            found.append(
                Discrepancy(
                    "replication",
                    bank,
                    "one",
                    f"{where}/bank.toml declares {replication.REPEATS_KEY} = 1, one repeat per "
                    f"cell; {consequence}",
                )
            )
            continue
        for (arm, task), count in replication.assess(
            declared, replication.cell_counts(scoped)
        ).short:
            found.append(
                Discrepancy(
                    "replication",
                    bank,
                    f"short:{arm}/{task}",
                    f"{count} completed trial(s) against the {declared} that "
                    f"{replication.REPEATS_KEY} declares; a contrast that uses this cell is "
                    "directional, not replicated",
                )
            )
    return found


def preimage_coverage(root: Path) -> tuple[int, int]:
    """(rows carrying a preimage, rows total) — reported, never gated.

    The ratio is the honest statement of how much of the record the exact check can speak
    for.  It only moves forward, as new trials are bought.  ``(0, 0)`` means the root has no
    trial or run rows at all.
    """
    total = 0
    with_preimage = 0
    for _bank, row in ledger_rows(root):
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
            "CHANGELOG heading (engine checkouts only)"
        ),
        run=check_version_sites,
        skip=version_sites_skip,
    ),
    Reconciliation(
        name="replication",
        describe=(
            "each bank's [plan] repeats_per_cell against the completed trials per arm and "
            "task in its ledger (warns, never fails)"
        ),
        run=check_replication,
        severity=SEVERITY_WARN,
    ),
)


# ---------------------------------------------------------------------------
# Known exceptions — declared in the root's fathom.toml
# ---------------------------------------------------------------------------

KNOWN_FIELDS = ("check", "subject", "key", "reason")


class KnownExceptionsError(ValueError):
    """``fathom.toml``, or the ``[[reconcile.known]]`` entries in it, cannot be read as declared."""


def load_known(root: Path | None = None) -> dict[Fingerprint, str]:
    """The discrepancies *root* accepts, as ``{(check, subject, key): reason}``.

    Read from ``[[reconcile.known]]`` in ``<root>/fathom.toml``; a root without the file
    accepts nothing.  A file that is not UTF-8 TOML, or a malformed entry, raises
    :class:`KnownExceptionsError` naming the file and the entry: an exception that silently
    failed to load would turn the gate red for a reason nobody can see, and one that loaded
    with a typo'd check name would never match and never expire.
    """
    resolved = resolve_root(root)
    path = resolved / CONFIG_FILE
    try:
        data = ledgerindex.read_config(resolved)
    except ledgerindex.ConfigError as exc:
        raise KnownExceptionsError(str(exc)) from exc
    if data is None:
        return {}

    section = data.get("reconcile", {})
    if not isinstance(section, dict):
        raise KnownExceptionsError(f"{path}: `reconcile` must be a table")
    entries = section.get("known", [])
    if not isinstance(entries, list):
        raise KnownExceptionsError(
            f"{path}: `reconcile.known` must be an array of tables, written [[reconcile.known]]"
        )

    registered = sorted(c.name for c in CHECKS)
    known: dict[Fingerprint, str] = {}
    for number, entry in enumerate(entries, start=1):
        where = f"{path}: [[reconcile.known]] entry {number}"
        if not isinstance(entry, dict):
            raise KnownExceptionsError(f"{where} is not a table")
        missing = [f for f in KNOWN_FIELDS if f not in entry]
        if missing:
            raise KnownExceptionsError(f"{where} is missing {', '.join(missing)}")
        extra = sorted(set(entry) - set(KNOWN_FIELDS))
        if extra:
            raise KnownExceptionsError(
                f"{where} has unknown field(s) {', '.join(extra)}; "
                f"the fields are {', '.join(KNOWN_FIELDS)}"
            )
        for field in KNOWN_FIELDS:
            value = entry[field]
            if not isinstance(value, str) or not value.strip():
                raise KnownExceptionsError(f"{where}: `{field}` must be a non-empty string")
        if entry["check"] not in registered:
            raise KnownExceptionsError(
                f"{where} names check {entry['check']!r}, which is not a registered "
                f"reconciliation ({', '.join(registered)})"
            )
        fingerprint = (entry["check"], entry["subject"], entry["key"])
        if fingerprint in known:
            raise KnownExceptionsError(
                f"{where} repeats the check, subject and key of an earlier entry"
            )
        known[fingerprint] = entry["reason"]
    return known


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


def _execute(
    root: Path, checks: Iterable[Reconciliation]
) -> tuple[list[str], list[tuple[str, str]], list[Discrepancy]]:
    ran: list[str] = []
    skipped: list[tuple[str, str]] = []
    found: list[Discrepancy] = []
    for check in checks:
        reason = check.skip(root)
        if reason is not None:
            skipped.append((check.name, reason))
            continue
        ran.append(check.name)
        # The registry, not the check function, says what a finding does to the gate.
        found.extend(dataclasses.replace(d, severity=check.severity) for d in check.run(root))
    return ran, skipped, found


def run_all(root: Path | None = None, *, names: Iterable[str] | None = None) -> list[Discrepancy]:
    """Every discrepancy every selected, applicable check finds at *root*, exceptions included."""
    _ran, _skipped, found = _execute(resolve_root(root), registry(names))
    return found


def unexpected(found: Iterable[Discrepancy], known: Mapping[Fingerprint, str]) -> list[Discrepancy]:
    """The disagreements nobody has accepted — the ones that fail the gate.

    Findings of a ``"warn"`` check are left out: :func:`unexcused_warnings` lists them.
    """
    return [d for d in found if d.severity != SEVERITY_WARN and d.fingerprint not in known]


def unexcused_warnings(
    found: Iterable[Discrepancy], known: Mapping[Fingerprint, str]
) -> list[Discrepancy]:
    """The warnings nobody has accepted: printed, counted, and never a failure."""
    return [d for d in found if d.severity == SEVERITY_WARN and d.fingerprint not in known]


def stale_exceptions(
    found: Iterable[Discrepancy],
    known: Mapping[Fingerprint, str],
    *,
    checks: Iterable[str] | None = None,
) -> list[Fingerprint]:
    """Declared exceptions whose discrepancy no longer occurs.

    A stale exception is a failure, not a tidiness issue: it is the mechanism by which an
    exception list grows until the gate it guards asserts nothing.

    *checks* names the checks that were selected; an exception for a check left out of the
    run is not judged, since its discrepancy was never looked for.  A selected check that
    was skipped at this root counts as looked for and found nothing.
    """
    seen = {d.fingerprint for d in found}
    scope = None if checks is None else set(checks)
    return [fp for fp in known if fp not in seen and (scope is None or fp[0] in scope)]


@dataclasses.dataclass(frozen=True)
class Outcome:
    """One reconcile of one root: what ran, what was skipped, what was found and accepted."""

    root: Path
    ran: tuple[str, ...]
    skipped: tuple[tuple[str, str], ...]
    found: tuple[Discrepancy, ...]
    known: Mapping[Fingerprint, str]

    @property
    def unexpected(self) -> list[Discrepancy]:
        return unexpected(self.found, self.known)

    @property
    def stale(self) -> list[Fingerprint]:
        selected = self.ran + tuple(name for name, _reason in self.skipped)
        return stale_exceptions(self.found, self.known, checks=selected)

    @property
    def warnings(self) -> list[Discrepancy]:
        return unexcused_warnings(self.found, self.known)

    @property
    def excused(self) -> int:
        """Findings, disagreements and warnings alike, that an exception accepts."""
        return sum(1 for d in self.found if d.fingerprint in self.known)

    @property
    def ok(self) -> bool:
        return not self.unexpected and not self.stale


def run(root: Path | None = None, *, names: Iterable[str] | None = None) -> Outcome:
    """Reconcile *root* (default: the working directory) against its declared exceptions.

    Raises ``KeyError`` for an unknown check name and :class:`KnownExceptionsError` for a
    malformed ``fathom.toml``; both are failures of the gate itself, not of the data.
    """
    resolved = resolve_root(root)
    checks = registry(names)
    known = load_known(resolved)
    ran, skipped, found = _execute(resolved, checks)
    return Outcome(
        root=resolved,
        ran=tuple(ran),
        skipped=tuple(skipped),
        found=tuple(found),
        known=known,
    )
