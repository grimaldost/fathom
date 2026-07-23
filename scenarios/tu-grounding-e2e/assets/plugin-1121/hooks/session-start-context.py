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

Other constraints: never blocks a session (always exit 0); bounded, fast scan
(capped files/bytes; heavy dirs skipped).

Exit codes:
  0 — Always (context priming is non-blocking).
"""

from __future__ import annotations

import contextlib
import hashlib
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
            '`python -m treasuryutils.datatools doctor` to check source bindings. Upgrading '
            'to v1.1: pin `treasuryutils>=1.1.0` and clear the lakehouse cache once (source '
            'column names are now authoritative — see the v1.1 migration guide at '
            'https://github.com/stone-payments/treasuryutils/blob/main/docs/migration/v1.1.0.md).'
        )
        _emit(present_context + '\n\n' + _env_readiness_block())

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
