"""Portfolio risk: covariance -> parametric VaR / Expected Shortfall -> risk parity.

Scenario
--------
A treasury desk holds an equal-weighted book of four liquid assets and wants a
daily risk readout: how much could the book lose on a bad day (VaR / Expected
Shortfall), *which* holding drives that risk, and how a risk-balanced
reallocation changes the picture.

What this demonstrates
----------------------
- Estimating a covariance matrix from a ``(T, N)`` daily-returns matrix with the
  Ledoit-Wolf shrinkage estimator (robust when ``T`` is not >> ``N``).
- Parametric 99% VaR and Expected Shortfall via ``compute_portfolio_risk``.
- Per-asset *risk contributions* -- equal weight is **not** equal risk.
- A risk-parity reallocation that equalizes each asset's risk contribution,
  and the VaR reduction it buys.

treasuryutils APIs
------------------
- ``treasuryutils.quanttools.math.covariance.estimate_ledoit_wolf_covariance``
- ``treasuryutils.quanttools.compute_portfolio_risk`` -> ``PortfolioRiskResult``
- ``treasuryutils.quanttools.optimize`` (mode ``'RISK_PARITY'``) -> ``TargetPortfolio``

Why treasuryutils, not hand-rolled
----------------------------------
A raw ``np.cov`` is ill-conditioned for short histories; Ledoit-Wolf shrinks it
toward a stable target. Parametric VaR/ES sign conventions and the ES closed form
are easy to flip, and risk contributions must reconcile to total variance. This is
the quanttools domain -- prefer its estimators and risk model over
``sklearn.covariance`` / ``scipy.optimize`` / hand-rolled NumPy. See
``references/quanttools_api.md``.

Note on ``optimize`` modes: ``RISK_PARITY`` (used here) and ``EQUAL_WEIGHT`` are
fully-invested, long-only by construction. ``MEAN_VARIANCE`` / ``MINIMUM_VARIANCE``
are tilt optimizers that do NOT impose a budget on their own -- a budget-free
``MINIMUM_VARIANCE`` is unbounded-below at w=0, so ``optimize`` fails closed with a
clear error rather than returning the degenerate all-zero portfolio. To make them
fully invested, add the budget constraint explicitly::

    from treasuryutils.quanttools import LimitDefinition, LimitType
    optimize(alpha, cov, current, [
        LimitDefinition(LimitType.FULLY_INVESTED, 1.0),  # sum(w) == 1
        LimitDefinition(LimitType.MIN_WEIGHT, 0.0),      # long-only
    ], mode='MINIMUM_VARIANCE')

Install
-------
``treasuryutils[quant-math]``  (NumPy + scipy; no cvxpy needed for risk parity)

Run
---
``python examples/04_portfolio_risk.py``  (or ``uv run python examples/04_portfolio_risk.py``)

Expected output (deterministic; seed = 42)
------------------------------------------
    === Portfolio risk: 4-asset book, 252 daily returns ===

    Equal weight  [0.25 0.25 0.25 0.25]
      daily VaR(99%) : 0.023819   (2.382% of book value)
      Expected Shortfall(99%): 0.027289
      annualized vol : 16.25%
      risk contribution share: A=29.1%  B=23.4%  C=12.6%  D=34.9%
      -> equal weight is NOT equal risk: ASSET_D drives 34.9%.

    Risk parity   [0.1978 0.2407 0.3977 0.1637]  (sum = 1.0)
      daily VaR(99%) : 0.021217   (-10.9% vs equal weight)
      annualized vol : 14.48%
      risk contribution share: A=25.0%  B=25.0%  C=25.0%  D=25.0%
      -> each asset now contributes equally to portfolio risk.
"""

from __future__ import annotations

import numpy as np

from treasuryutils.quanttools import PortfolioRiskResult, compute_portfolio_risk, optimize
from treasuryutils.quanttools.math.covariance import estimate_ledoit_wolf_covariance


def _demo_returns() -> tuple[np.ndarray, list[str]]:
    """A deterministic ``(T, N)`` returns matrix: one common factor + idiosyncratic noise.

    In production this matrix comes from real price history -- e.g.
    ``treasuryutils.quanttools.math.returns.returns_from_prices`` over a
    ``DatasetClient`` read. Here we synthesize it so the example runs anywhere.
    """
    rng = np.random.default_rng(42)
    n_assets, n_days = 4, 252
    common_factor = rng.normal(0.0, 0.01, n_days)
    betas = np.array([1.2, 0.9, 0.5, 1.5])  # ASSET_D is the most factor-sensitive
    idiosyncratic = rng.normal(0.0, 0.006, (n_days, n_assets))
    returns = common_factor[:, None] * betas[None, :] + idiosyncratic
    return returns, ['ASSET_A', 'ASSET_B', 'ASSET_C', 'ASSET_D']


def _contribution_share(result: PortfolioRiskResult) -> np.ndarray:
    rc = np.asarray(result.risk_contributions, dtype=np.float64)
    share: np.ndarray = rc / rc.sum()
    return share


def main() -> None:
    returns, security_ids = _demo_returns()

    # 1. Covariance from the returns matrix (Ledoit-Wolf shrinkage).
    covariance = estimate_ledoit_wolf_covariance(returns)

    # 2. Risk of the current equal-weighted book.
    equal_weight = np.full(len(security_ids), 1.0 / len(security_ids))
    eq = compute_portfolio_risk(
        equal_weight, covariance, confidence_level=0.99, security_ids=security_ids
    )
    eq_share = _contribution_share(eq)
    # Note: ``.var`` on the result is Value-at-Risk (a loss fraction), NOT variance.

    print('=== Portfolio risk: 4-asset book, 252 daily returns ===\n')
    print(f'Equal weight  {np.round(equal_weight, 4)}')
    print(f'  daily VaR(99%) : {eq.var:.6f}   ({eq.var:.3%} of book value)')
    print(f'  Expected Shortfall(99%): {eq.es:.6f}')
    print(f'  annualized vol : {eq.portfolio_volatility_annual:.2%}')
    print(
        '  risk contribution share: '
        + '  '.join(
            f'{sid[-1]}={share:.1%}' for sid, share in zip(security_ids, eq_share, strict=True)
        )
    )
    leader = security_ids[int(np.argmax(eq_share))]
    print(f'  -> equal weight is NOT equal risk: {leader} drives {eq_share.max():.1%}.\n')

    # 3. Risk-parity reallocation: equalize each asset's risk contribution.
    target = optimize(
        np.zeros(len(security_ids)),  # no alpha view: pure risk allocation
        covariance,
        equal_weight,  # current holdings (the starting point)
        constraints=[],  # RISK_PARITY is long-only + fully invested by construction
        mode='RISK_PARITY',
        security_ids=security_ids,
        portfolio_id='TREASURY_BOOK',
    )
    rp = compute_portfolio_risk(
        target.target_weights, covariance, confidence_level=0.99, security_ids=security_ids
    )
    rp_share = _contribution_share(rp)
    var_change = rp.var / eq.var - 1.0

    weights_repr = np.round(target.target_weights, 4)
    weight_sum = target.target_weights.sum()
    print(f'Risk parity   {weights_repr}  (sum = {weight_sum:.1f})')
    print(f'  daily VaR(99%) : {rp.var:.6f}   ({var_change:+.1%} vs equal weight)')
    print(f'  annualized vol : {rp.portfolio_volatility_annual:.2%}')
    print(
        '  risk contribution share: '
        + '  '.join(
            f'{sid[-1]}={share:.1%}' for sid, share in zip(security_ids, rp_share, strict=True)
        )
    )
    print('  -> each asset now contributes equally to portfolio risk.')


if __name__ == '__main__':
    main()
