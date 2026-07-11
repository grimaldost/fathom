#!/usr/bin/env python3
"""SessionStart hook: surface treasuryutils when it fits — never force it.

Fires when a Claude Code session starts. Two mutually exclusive outcomes,
otherwise silent:

1. **Present** — the project already depends on treasuryutils. Inject neutral
   context so a fresh/passive agent prefers the library's public API over
   reimplementing solved behaviour, and points at the consumer skills.

2. **Fitting but absent** — treasuryutils is NOT a dependency, but the project
   shows strong, specific treasury/finance signals the library covers. Emit ONE
   neutral, optional suggestion (once per project; silence with
   ``TREASURYUTILS_DISABLE_SUGGEST=1``). This never installs or uses anything.

Detection (tuned to avoid nagging ordinary projects):
- **Word-boundary** matching, never bare substring — so ``cdi`` does not match
  ``abcdi``.
- **High-specificity tokens only.** The signal set is restricted to treasury-
  specific, low-collision terms (``cdi``, ``sofr``, ``ptax``, ``dv01``,
  ``ifrs 9``, ``curva de juros``, …); a single hit is enough. Generic phrases
  that collide with ordinary ML / scheduling / engineering code (``business
  day``, ``covariance matrix``, ``yield curve``, ``quantlib``, …) are
  deliberately excluded — even in combination they are too ambiguous and would
  nag non-treasury projects.

When the project depends on treasuryutils, the injected context is prepended with a
**reference-staleness banner** whenever the shipped ``treasuryutils-usage`` references
were generated against a different library version than the one installed here, or have
aged past their declared ttl — the consume-time push channel that the 2026-07-10
stale-references incident lacked (references stamped ``1.5.2.dev`` reached a consumer
running tu ``1.8.0`` with no signal). Like every other feature here it is best-effort and
never raises.

Other constraints: never blocks a session (always exit 0); bounded, fast scan
(capped files/bytes; heavy dirs skipped).

Environment variables (all optional; each disables one best-effort feature, and the
session still proceeds silently otherwise):
  - ``TREASURYUTILS_DISABLE_STALENESS_BANNER=1`` — skip the reference-staleness banner
    described above (the deep version-reconciliation path in the ``treasuryutils-usage``
    skill still applies).
  - ``TREASURYUTILS_DISABLE_ENV_DIGEST=1`` — skip the live env-memory readiness snapshot
    (the agent is still routed to ``treasuryutils-env show``).
  - ``TREASURYUTILS_DISABLE_SUGGEST=1`` — silence the one-time "fitting but absent"
    suggestion for a project that does not depend on treasuryutils.

Exit codes:
  0 — Always (context priming is non-blocking).
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import importlib.metadata
import json
import os
import re
import sys
from pathlib import Path

# Dependency manifests scanned (whole-file) for a treasuryutils dependency.
_MANIFESTS = (
    'pyproject.toml',
    'uv.lock',
    'requirements.txt',
    'requirements-dev.txt',
    'Pipfile',
    'Pipfile.lock',
    'setup.cfg',
    'setup.py',
    'environment.yml',
)

# High-specificity treasury/finance markers the library directly covers. The set
# is deliberately restricted to low-collision, treasury-specific terms — each is
# strong enough to fire on its own. Generic phrases that collide with ordinary
# ML / scheduling / engineering code ('business day', 'covariance matrix',
# 'yield curve', 'quantlib', 'value at risk', ...) are intentionally NOT here:
# even in combination they are too ambiguous and would nag non-treasury projects.
# Matching is word-boundary + case-insensitive (see _COMPILED_TOKENS).
_DOMAIN_TOKENS = frozenset(
    {
        # rates
        'cdi',
        'selic',
        'ptax',
        'sofr',
        'cupom cambial',
        # curves
        'di curve',
        'di futuro',
        'curva de juros',
        # calendar / day-count conventions
        'bus/252',
        'act/360',
        'dias úteis',
        'dias uteis',
        'dia útil',
        'dia util',
        # accounting
        'ifrs 9',
        'ifrs9',
        'marcação a mercado',
        'marcacao a mercado',
        # risk
        'dv01',
        'pv01',
    }
)

# Word-boundary regexes: the token must not be flanked by another [a-z0-9], so
# 'cdi' matches the word 'cdi' but not 'abcdi'. Sorted for deterministic order.
_COMPILED_TOKENS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, re.compile(r'(?<![a-z0-9])' + re.escape(token) + r'(?![a-z0-9])'))
    for token in sorted(_DOMAIN_TOKENS)
)

_SKIP_DIRS = {
    '.git',
    '.venv',
    'venv',
    'node_modules',
    '__pycache__',
    '.mypy_cache',
    '.ruff_cache',
    '.pytest_cache',
    'dist',
    'build',
    '.tox',
    'site-packages',
}

_MAX_PY_FILES = 60
_MAX_BYTES_PER_FILE = 16_384

# Default freshness window for the reference-staleness banner when
# ``.generated_meta.json`` carries no ``ttl_hours`` (the value the generator stamps).
_DEFAULT_TTL_HOURS = 168.0


def _read_text(path: Path) -> str:
    """Best-effort capped text read; empty string on any failure."""
    try:
        with path.open('r', encoding='utf-8', errors='ignore') as fh:
            return fh.read(_MAX_BYTES_PER_FILE)
    except OSError:
        return ''


def _is_treasuryutils_itself(root: Path) -> bool:
    """True when the project IS the treasuryutils library (avoid self-announce)."""
    pyproject = _read_text(root / 'pyproject.toml')
    return 'name = "treasuryutils"' in pyproject or "name = 'treasuryutils'" in pyproject


def _depends_on_treasuryutils(root: Path) -> bool:
    """True when a dependency manifest references treasuryutils."""
    return any('treasuryutils' in _read_text(root / name) for name in _MANIFESTS)


def _iter_py_files(root: Path) -> list[Path]:
    """Bounded list of project .py files, heavy dirs skipped."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith('.')]
        for fn in filenames:
            if fn.endswith('.py'):
                found.append(Path(dirpath) / fn)
                if len(found) >= _MAX_PY_FILES:
                    return found
    return found


def _tokens_in(text: str) -> set[str]:
    """Word-boundary token hits in already-lowercased text."""
    return {token for token, pattern in _COMPILED_TOKENS if pattern.search(text)}


def _fitting_signals(root: Path) -> list[str]:
    """Matched domain tokens if the project fits treasuryutils, else empty.

    Every token is high-specificity, so a single hit is enough. Scans manifests
    then a bounded .py sweep, short-circuiting on the first hit.
    """
    haystack = '\n'.join(_read_text(root / m) for m in _MANIFESTS).lower()
    matched = _tokens_in(haystack)

    if not matched:
        for py in _iter_py_files(root):
            matched |= _tokens_in(_read_text(py).lower())
            if matched:
                break

    return sorted(matched)


def _suggest_marker(root: Path) -> Path:
    """Per-project marker path under the user cache dir (not the repo)."""
    base = (
        os.environ.get('XDG_CACHE_HOME')
        or os.environ.get('LOCALAPPDATA')
        or str(Path.home() / '.cache')
    )
    digest = hashlib.sha256(str(root.resolve()).encode('utf-8')).hexdigest()[:16]
    return Path(base) / 'treasuryutils' / f'suggested-{digest}'


def _already_suggested(root: Path) -> bool:
    try:
        return _suggest_marker(root).exists()
    except OSError:
        return False


def _mark_suggested(root: Path) -> None:
    # Best-effort; a failed marker just means we may suggest again later.
    with contextlib.suppress(OSError):
        marker = _suggest_marker(root)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()


def _env_readiness_digest() -> str | None:
    """A compact, live env-memory snapshot — or None if unavailable.

    Best-effort. This hook runs under ``uv run python`` (the consumer's project venv), so
    treasuryutils is importable when the project depends on it. ``get_env_facts`` recomputes the
    cheap kinds (binding / auth / materialization) with no live connect and never raises; the
    import is guarded so a broken/absent install never breaks SessionStart. Set
    ``TREASURYUTILS_DISABLE_ENV_DIGEST=1`` to skip the snapshot (the agent is routed instead).
    """
    if os.environ.get('TREASURYUTILS_DISABLE_ENV_DIGEST'):
        return None
    try:
        from treasuryutils.envmemory import get_env_facts

        facts = get_env_facts().facts
    except Exception:  # never break a consumer's SessionStart on tu install/state
        return None

    bindings = {f.scope: dict(f.payload) for f in facts if 'binding' in str(f.kind)}
    if not bindings:
        return None
    materialized = sorted(f.scope for f in facts if 'materialization' in str(f.kind))
    needs_auth = sorted(
        ds
        for ds, p in bindings.items()
        if p.get('auth_profile') and not p.get('auth_profile_configured')
    )
    lines = [f'treasuryutils env-memory snapshot — {len(bindings)} datasets known:']
    if materialized:
        lines.append(f'  - materialized (cached, ready to read): {", ".join(materialized)}')
    if needs_auth:
        lines.append(f'  - need an unconfigured auth profile before use: {", ".join(needs_auth)}')
    if not materialized and not needs_auth:
        return None
    return '\n'.join(lines)


def _env_readiness_block() -> str:
    """The env-memory readiness block: a live snapshot when available, plus the route.

    Surfacing the environment's data readiness (which datasets are bound, their auth, what is
    materialized) lets a fresh agent skip piecemeal probing (a measured win — see the dyno
    tu-memory eval). The computed snapshot is best-effort; the route always works.
    """
    route = (
        "Before data work, run `treasuryutils-env show` to see this environment's data "
        'readiness in one step — which datasets are bound, their auth, and what is materialized '
        '(it consolidates `doctor` + cache listing + dependency/resolution); '
        '`treasuryutils-env refresh` updates it. Treat it as the source of truth for what is '
        'usable now rather than assuming a dataset is available.'
    )
    snapshot = _env_readiness_digest()
    return f'{snapshot}\n{route}' if snapshot else route


def _reference_meta_path() -> Path:
    """Path to the generated references' ``.generated_meta.json`` sidecar.

    Resolved relative to this hook: ``hooks/`` and ``skills/`` are siblings under the
    plugin root, so the references live two parents up then down into the skill.
    """
    return (
        Path(__file__).resolve().parent.parent
        / 'skills'
        / 'treasuryutils-usage'
        / 'references'
        / '.generated_meta.json'
    )


def _read_reference_meta() -> dict[str, object] | None:
    """Best-effort parse of the references meta sidecar; None on any failure."""
    try:
        raw = _reference_meta_path().read_text(encoding='utf-8')
        data = json.loads(raw)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _installed_treasuryutils_version() -> str | None:
    """The installed ``treasuryutils`` distribution version, or None if unresolved.

    Runs under the consumer's venv (same as ``_env_readiness_digest``); guarded so a
    missing/broken install never breaks SessionStart.
    """
    try:
        return importlib.metadata.version('treasuryutils')
    except Exception:  # PackageNotFoundError and anything else metadata can raise
        return None


def _normalize_version(raw: str) -> tuple[tuple[int, ...], bool] | None:
    """(release-tuple, is_dev_release) for a PEP 440 version, or None if unparseable.

    Prefers ``packaging.version`` when importable — the hook must not hard-depend on it,
    since the consumer env may be bare — and otherwise falls back to a small subset that
    recovers just the base version and the dev-release flag the banner compares on.
    """
    try:
        from packaging.version import InvalidVersion, Version
    except ImportError:
        return _fallback_normalize_version(raw)
    try:
        parsed = Version(raw)
    except InvalidVersion:
        return None
    return (parsed.release, parsed.is_devrelease)


def _fallback_normalize_version(raw: str) -> tuple[tuple[int, ...], bool] | None:
    """Stdlib-only version normalization for envs without ``packaging`` installed."""
    match = re.match(r'\s*v?(\d+(?:\.\d+)*)', raw)
    if match is None:
        return None
    release = tuple(int(part) for part in match.group(1).split('.'))
    is_dev = re.search(r'(?<![a-z0-9])dev\d*', raw, re.IGNORECASE) is not None
    return (release, is_dev)


def _versions_diverge(stamp: str, installed: str) -> bool:
    """True when the reference stamp is stale versus the installed version.

    Stale means (a) the base versions differ, or (b) the stamp is a dev release while
    the install is a clean release (a mirror built from an unreleased tree). If either
    string is unparseable the version axis is inconclusive, so this returns False and
    the age axis is left to decide — never a false alarm on the version axis.
    """
    stamp_norm = _normalize_version(stamp)
    installed_norm = _normalize_version(installed)
    if stamp_norm is None or installed_norm is None:
        return False
    stamp_release, stamp_is_dev = stamp_norm
    installed_release, installed_is_dev = installed_norm
    if stamp_release != installed_release:
        return True
    return stamp_is_dev and not installed_is_dev


def _references_expired(generated_at_utc: str | None, ttl_hours: float) -> bool:
    """True when the references are older than ``ttl_hours``; False if undeterminable."""
    if not generated_at_utc:
        return False
    try:
        generated = datetime.datetime.fromisoformat(generated_at_utc)
    except ValueError:
        return False
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=datetime.UTC)
    now = datetime.datetime.now(datetime.UTC)
    return (now - generated).total_seconds() > ttl_hours * 3600.0


def _meta_date(generated_at: str | None) -> str:
    """The calendar-date portion of an ISO stamp, for banner prose."""
    if not generated_at:
        return 'unknown date'
    return generated_at[:10] if len(generated_at) >= 10 else generated_at


def _version_mismatch_banner(stamp: str, generated_at: str | None, installed: str) -> str:
    """The LOUD banner for a VERSION mismatch (cases a/b) — names both versions."""
    return (
        'TREASURYUTILS REFERENCE STALENESS WARNING — the treasuryutils-usage skill '
        f'references were generated against tu {stamp} ({_meta_date(generated_at)}); '
        f'this environment runs tu {installed}. For ANY version-sensitive claim '
        '(available symbols, backend/expression support, deprecations), verify against '
        'the INSTALLED source or CHANGELOG before asserting — the references may describe '
        'an older API. Do not classify a capability as absent/deferred from the '
        'references alone. If you cannot check the installed source right now, say so and '
        'treat the capability as UNCERTAIN — do not assert it present or absent, and never '
        'invent a verification you did not perform.'
    )


def _age_expiry_banner(generated_at: str | None, ttl_hours: float) -> str:
    """The LOUD banner for AGE expiry (case c) — worded distinctly from the version one."""
    return (
        'TREASURYUTILS REFERENCE STALENESS WARNING — the treasuryutils-usage skill '
        f'references were generated on {_meta_date(generated_at)} and have aged past their '
        f'freshness window (ttl {ttl_hours:g}h). They may predate recent library changes; '
        'for ANY version-sensitive claim (available symbols, backend/expression support, '
        'deprecations), verify against the INSTALLED source or CHANGELOG before asserting '
        'rather than trusting the references alone. If you cannot verify right now, flag '
        'the capability as UNCERTAIN rather than asserting it from the references.'
    )


def _reference_staleness_banner() -> str | None:
    """A loud staleness banner when the shipped references no longer match this env.

    Returns the banner text (VERSION mismatch takes precedence over AGE expiry) or None
    when the references are current, when a needed input is missing/unreadable, or when
    silenced via ``TREASURYUTILS_DISABLE_STALENESS_BANNER``. Best-effort: never raises.
    """
    if os.environ.get('TREASURYUTILS_DISABLE_STALENESS_BANNER'):
        return None
    meta = _read_reference_meta()
    if meta is None:
        return None
    stamp = meta.get('treasuryutils_version')
    if not isinstance(stamp, str) or not stamp:
        return None

    generated_at = meta.get('generated_at_utc')
    generated_at = generated_at if isinstance(generated_at, str) else None
    ttl_raw = meta.get('ttl_hours')
    ttl_hours = float(ttl_raw) if isinstance(ttl_raw, (int, float)) else _DEFAULT_TTL_HOURS

    installed = _installed_treasuryutils_version()

    # (a)/(b) VERSION mismatch — needs both the stamp and a resolved installed version.
    if installed and _versions_diverge(stamp, installed):
        return _version_mismatch_banner(stamp, generated_at, installed)

    # (c) AGE expiry — a FALLBACK only for when the version axis cannot decide (tu not
    # importable, so ``installed is None``). A shipped mirror's ``generated_at`` is frozen
    # at package time; while its pinned version still resolves and matches, wall-clock age
    # carries no staleness signal the version axis has not already ruled out. Firing here
    # on a version-matched install is a cry-wolf that desensitises agents to the
    # version-mismatch banner (fresh-agent stress + static review, 2026-07-10).
    if installed is None and _references_expired(generated_at, ttl_hours):
        return _age_expiry_banner(generated_at, ttl_hours)

    return None


def _emit(context: str) -> None:
    """Print the additionalContext payload for Claude, then exit cleanly."""
    print(json.dumps({'additionalContext': context}))
    sys.exit(0)


def main() -> None:
    """Announce, propose, or stay silent based on the project's use/fit of tu."""
    # Drain stdin (the harness passes JSON) so we never break the pipe; cwd is
    # the project root for SessionStart hooks.
    with contextlib.suppress(OSError, ValueError):
        sys.stdin.read()

    root = Path(os.getcwd())

    if _is_treasuryutils_itself(root):
        sys.exit(0)

    if _depends_on_treasuryutils(root):
        present_context = (
            'This project depends on treasuryutils. Prefer its public API over '
            'reimplementing solved behaviour — every domain has concrete symbols to use '
            'instead of hand-rolling or reaching for a generic library:\n'
            '- Business-day / calendar math: treasuryutils.calendartools — add_workdays, '
            'net_workdays, is_workday, year_fraction, DayCountConvention (not numpy.busday_* '
            'or a hand-rolled day-count).\n'
            '- Yield curves: treasuryutils.financialtools.curves — CdiCurve, SofrCurve, '
            'IpcaCurve, CupomCambialCurve.\n'
            '- Instruments / cashflows / pricing: treasuryutils.financialtools — '
            'decode_instrument, generate_schedule, price_cashflows, compute_risk_metrics.\n'
            '- IFRS 9 accounting: treasuryutils.financialtools.accounting — '
            'classify_instruments, compute_amortized_cost, solve_eir, compute_ecl, '
            'assess_stage, compute_fair_value_changes.\n'
            '- Data ingestion / caching: treasuryutils.datatools — '
            "DatasetClient('<name>').get(covers=(lo, hi)) (fail-closed on staleness), "
            'ParquetUpsert (not raw pandas / pyarrow IO).\n'
            '- Covariance / portfolio risk / VaR / optimization: '
            'treasuryutils.quanttools.math.covariance — estimate_ewma_sample_covariance, '
            'estimate_ledoit_wolf_covariance; treasuryutils.quanttools — '
            'compute_portfolio_risk, optimize; treasuryutils.quanttools.analytics — '
            'compute_sharpe_ratio, compute_max_drawdown, compute_factor_attribution (not '
            'sklearn.covariance / scipy.optimize — they look like generic stats but '
            'treasuryutils provides the treasury-calibrated versions).\n'
            '- DataFrame ops / weighted averages: treasuryutils.compute — weighted_average '
            '(excludes nulls from BOTH numerator AND denominator, a subtle hand-rolled bug) '
            'and asof_aggregate.\n'
            'The `treasuryutils-usage` skill routes a task to the right module + API '
            'references (read its references before writing code); `setup-source-bindings` '
            'covers rebinding data sources and stateless/serverless deployment. If a read '
            'fails with SourceExtractionError / SourceAccessError, run '
            '`python -m treasuryutils.datatools doctor` to check source bindings. When '
            'upgrading treasuryutils, read CHANGELOG.md and docs/migration/ in the '
            'installed package for the version-specific steps (some upgrades require '
            'clearing the lakehouse cache once) rather than assuming any pinned version.'
        )
        body = present_context + '\n\n' + _env_readiness_block()
        # A reference-staleness banner, when present, is PREPENDED at the very top:
        # position is salience, and this is the push channel the incident lacked. The
        # helper is guarded internally, but wrap the call too so the "SessionStart never
        # fails" contract holds unconditionally even if a future edit slips a raise
        # through (belt-and-suspenders; the banner is best-effort, never load-bearing).
        banner = None
        with contextlib.suppress(Exception):
            banner = _reference_staleness_banner()
        if banner is not None:
            body = banner + '\n\n' + body
        _emit(body)

    # treasuryutils absent: propose only when it clearly fits, at most once.
    if os.environ.get('TREASURYUTILS_DISABLE_SUGGEST'):
        sys.exit(0)
    if _already_suggested(root):
        sys.exit(0)

    signals = _fitting_signals(root)
    if signals:
        _mark_suggested(root)
        _emit(
            'This project shows treasury/finance work that the treasuryutils '
            f'library covers (signals: {", ".join(signals)}) but does not depend '
            'on it. If you are writing new business-day calendars, yield curves, '
            'instrument pricing, IFRS 9 accounting, or portfolio-risk code, '
            'consider treasuryutils instead of reimplementing it. Do NOT install '
            'it, add a dependency, or refactor working code in response to this '
            'note — surface it only if the user asks, or when you are already '
            'adding new finance functionality; then use the `treasuryutils-usage` '
            'skill. One-time, optional suggestion (set TREASURYUTILS_DISABLE_SUGGEST=1 '
            'to silence).'
        )

    sys.exit(0)


if __name__ == '__main__':
    main()
