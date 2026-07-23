"""Equity factor features: momentum -> cross-sectional normalization -> alpha rank.

Scenario
--------
You run a small equity book and want a cross-sectional alpha score: rank a universe
by price momentum, standardized across the names so the scores are comparable. The
``equitytools`` feature functions do the look-back momentum math and the winsorized
cross-sectional z-scoring -- the parts that are easy to get subtly wrong by hand
(skip-month conventions, outlier clipping, available-case weighting).

What this demonstrates
----------------------
- ``attach_momentum_features`` over a historical bar panel: 12m-1m / 6m-1m / 3m / 1m
  cumulative-return momentum (the longer signals skip the most recent month to avoid
  short-term reversal). The panel COLUMN CONTRACT: ``security_id``, ``bar_date``,
  ``close``, ``adj_factor``, sorted by ``(security_id, bar_date)``.
- Taking the latest bar per name as the cross-sectional snapshot (one row per
  security), then ``normalize_cross_sectional`` to winsorize + z-score each feature
  and build a weighted ``z_composite`` alpha.
- Deterministic drift-only prices, so the ranking is exact and reproducible.

treasuryutils APIs
------------------
- ``treasuryutils.equitytools.features.attach_momentum_features``
- ``treasuryutils.equitytools.features.normalize_cross_sectional``
  (``feature_domains`` maps a domain -> its raw feature columns; ``domain_weights``
  the relative domain weights -- here a single ``momentum`` domain.)

Why treasuryutils, not hand-rolled
----------------------------------
The 12m-1m skip-month window, the +/-3 sigma winsorization before z-scoring, and the
available-case weighting (a name missing a feature is not penalized) are standard but
fiddly. ``equitytools`` encodes them once; a hand-rolled groupby/rank gets the
skip-month or the outlier clip wrong silently. See ``references/equitytools_api.md``.

Install
-------
``treasuryutils[equity]``

Run
---
``python examples/08_equity_factor_features.py``

Expected output (deterministic)
-------------------------------
    === Equity factor features: momentum -> cross-sectional alpha ===

    Universe (300 daily bars each, deterministic drift):
      ALFA3  daily drift +0.100%  (strong uptrend)
      BETA4  daily drift +0.050%
      GAMA3  daily drift +0.000%  (flat)
      DELT4  daily drift -0.050%
      ZETA4  daily drift -0.100%  (strong downtrend)

    Cross-sectional alpha (z_composite, momentum domain), best to worst:
      ALFA3   z_composite= +1.4649   mom_12m_1m= +25.97%
      BETA4   z_composite= +0.6785   mom_12m_1m= +12.24%
      GAMA3   z_composite= -0.0514   mom_12m_1m= +0.00%
      DELT4   z_composite= -0.7300   mom_12m_1m= -10.91%
      ZETA4   z_composite= -1.3620   mom_12m_1m= -20.64%

    (z_composite is mean-zero across the cross-section and ranks the names by
    standardized momentum -- the uptrenders score positive, the downtrenders negative.)
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from treasuryutils.equitytools.features import (
    attach_momentum_features,
    normalize_cross_sectional,
)

# (security_id, daily drift) -- pure drift, no noise, so momentum is exact.
_UNIVERSE: tuple[tuple[str, float], ...] = (
    ('ALFA3', 0.0010),
    ('BETA4', 0.0005),
    ('GAMA3', 0.0000),
    ('DELT4', -0.0005),
    ('ZETA4', -0.0010),
)
_N_DAYS = 300


def _bar_panel() -> pl.DataFrame:
    """A deterministic bar panel: close = 100 * (1 + drift)^t, adj_factor = 1."""
    start = dt.date(2023, 1, 2)
    rows: list[dict[str, object]] = [
        {
            'security_id': security_id,
            'bar_date': start + dt.timedelta(days=t),
            'close': 100.0 * (1.0 + drift) ** t,
            'adj_factor': 1.0,
        }
        for security_id, drift in _UNIVERSE
        for t in range(_N_DAYS)
    ]
    return pl.DataFrame(rows).sort(['security_id', 'bar_date'])


def main() -> None:
    print('=== Equity factor features: momentum -> cross-sectional alpha ===\n')

    print(f'Universe ({_N_DAYS} daily bars each, deterministic drift):')
    labels = {
        'ALFA3': '(strong uptrend)',
        'GAMA3': '(flat)',
        'ZETA4': '(strong downtrend)',
    }
    for security_id, drift in _UNIVERSE:
        print(f'  {security_id}  daily drift {drift:+.3%}  {labels.get(security_id, "")}'.rstrip())
    print()

    # 1. Momentum features over the full history.
    panel = attach_momentum_features(_bar_panel())

    # 2. Cross-sectional snapshot: the latest bar per security (one row each).
    as_of = panel['bar_date'].max()
    snapshot = panel.filter(pl.col('bar_date') == as_of)

    # 3. Winsorized cross-sectional z-score -> weighted alpha composite.
    scored = normalize_cross_sectional(
        snapshot,
        feature_domains={'momentum': ['mom_12m_1m', 'mom_3m']},
        domain_weights={'momentum': 1.0},
    )

    print('Cross-sectional alpha (z_composite, momentum domain), best to worst:')
    ranked = scored.sort('z_composite', descending=True)
    for row in ranked.iter_rows(named=True):
        print(
            f'  {row["security_id"]}   z_composite= {row["z_composite"]:+.4f}   '
            f'mom_12m_1m= {row["mom_12m_1m"]:+.2%}'
        )


if __name__ == '__main__':
    main()
