"""IFRS 9 impairment: effective interest rate, three-stage ECL, and the simplified matrix.

Scenario
--------
A lender must report an Expected Credit Loss (ECL) allowance under IFRS 9. Three
questions drive the number:

1. What is the loan's *effective interest rate* (EIR)? It is the discount rate for
   both amortized cost and ECL.
2. How big is the ECL, and how does it jump when a loan's credit risk increases
   significantly (the Stage 1 -> Stage 2 "SICR" event)?
3. For trade receivables, what does the *simplified approach* (provision matrix)
   give across aging buckets?

What this demonstrates
----------------------
- ``solve_eir`` -- the EIR of a loan from its cashflows (Newton-Raphson).
- ``compute_ecl_for_instrument`` -- single-instrument ECL with credit-state
  dispatch (ADR-0022): PERFORMING (12-month PD) vs SICR (lifetime PD) vs
  CREDIT_IMPAIRED (lifetime PD on a *net* interest basis).
- ``compute_simplified_ecl`` -- the IFRS 9.5.5.15 provision matrix for receivables.

treasuryutils APIs
------------------
- ``treasuryutils.financialtools.accounting.solve_eir``
- ``treasuryutils.financialtools.accounting.compute_ecl_for_instrument``
- ``treasuryutils.financialtools.accounting.compute_simplified_ecl``

Why treasuryutils, not hand-rolled
----------------------------------
ECL has rules that are easy to get subtly wrong: which PD horizon applies per stage
(12-month vs lifetime), discounting at the original EIR, and -- for credit-impaired
assets -- accruing interest on the *net* carrying amount rather than the gross.
``compute_ecl_for_instrument`` encodes the IFRS 9.5.5 credit-state dispatch; passing
``credit_state`` as a plain string keeps the call self-documenting. See
``references/financialtools_api.md``.

Install
-------
``treasuryutils[pricing]``

Run
---
``python examples/03_ifrs9_ecl.py``

Expected output (deterministic)
-------------------------------
    === IFRS 9 impairment ===

    1. Effective interest rate of a 3y loan (lend 1,000,000; receive 100k, 100k, 1,100k)
       EIR = 10.0000%   (this is the discount rate for amortized cost and ECL)

    2. Expected Credit Loss for that loan (EAD=1,000,000, LGD=45%, discounted at the EIR)
       Stage 1  PERFORMING        ECL =     8,551.73   (PD 2%, gross interest)
       Stage 2  SICR              ECL =    86,787.42   (PD 8%, gross interest)
       Stage 3  CREDIT_IMPAIRED   ECL =    86,787.42   (PD 8%, net interest)
       -> Stage 1->2 (a significant increase in credit risk) swaps the 12-month PD for the
          lifetime PD and raises the allowance ~10x. Stage 2->3 keeps the lifetime ECL but
          moves interest to a NET basis: the allowance is unchanged here -- the net basis
          governs interest accrual on the carrying amount, not the loss estimate itself.

    3. Simplified approach (provision matrix) for trade receivables
       current   balance=   5,000,000  loss_rate= 0.500%  ECL=    25,000.00
       1-30      balance=   1,200,000  loss_rate= 2.000%  ECL=    24,000.00
       31-60     balance=     600,000  loss_rate= 5.000%  ECL=    30,000.00
       61-90     balance=     300,000  loss_rate=10.000%  ECL=    30,000.00
       90+       balance=     150,000  loss_rate=30.000%  ECL=    45,000.00
       TOTAL     balance=   7,250,000                     ECL=   154,000.00
"""

from __future__ import annotations

import numpy as np
import polars as pl

from treasuryutils.financialtools.accounting import (
    compute_ecl_for_instrument,
    compute_simplified_ecl,
    solve_eir,
)
from treasuryutils.financialtools.domain.identifiers import CompoundingType


def main() -> None:
    print('=== IFRS 9 impairment ===\n')

    # 1. Effective interest rate of a 3-year loan from its cashflows.
    cashflow_amounts = np.array([100_000.0, 100_000.0, 1_100_000.0])
    cashflow_times = np.array([1.0, 2.0, 3.0])  # years from origination
    eir = solve_eir(
        cashflow_amounts,
        cashflow_times,
        initial_amount=1_000_000.0,
        compounding=CompoundingType.DISCRETE_ANNUAL,
    )
    print('1. Effective interest rate of a 3y loan (lend 1,000,000; receive 100k, 100k, 1,100k)')
    print(f'   EIR = {eir:.4%}   (this is the discount rate for amortized cost and ECL)\n')

    # 2. Three-stage ECL for the same loan (EAD=1,000,000, LGD=45%), discounted at the EIR.
    #    return_outcome=True returns an ECLOutcome so we can read the PD horizon and the
    #    interest basis the credit state selected -- not just the loss figure.
    stages = [
        ('Stage 1', 'PERFORMING'),
        ('Stage 2', 'SICR'),
        ('Stage 3', 'CREDIT_IMPAIRED_NON_POCI'),
    ]
    print('2. Expected Credit Loss for that loan (EAD=1,000,000, LGD=45%, discounted at the EIR)')
    for label, credit_state in stages:
        outcome = compute_ecl_for_instrument(
            credit_state=credit_state,
            return_outcome=True,
            pd_12m=0.02,
            pd_lifetime=0.08,
            lgd=0.45,
            ead=1_000_000.0,
            discount_rate=eir,
            remaining_life_years=3.0,
        )
        shown_state = credit_state.replace('_NON_POCI', '')
        print(
            f'   {label}  {shown_state:<16}  ECL = {outcome.ecl_amount:>12,.2f}   '
            f'(PD {outcome.pd_used:.0%}, {outcome.interest_basis} interest)'
        )
    print('   -> Stage 1->2 (a significant increase in credit risk) swaps the 12-month PD for the')
    print('      lifetime PD and raises the allowance ~10x. Stage 2->3 keeps the lifetime ECL but')
    print('      moves interest to a NET basis: the allowance is unchanged here -- the net basis')
    print('      governs interest accrual on the carrying amount, not the loss estimate itself.\n')

    # 3. Simplified approach (provision matrix) for trade receivables.
    receivables = pl.DataFrame(
        {
            'aging_bucket': ['current', '1-30', '31-60', '61-90', '90+'],
            'outstanding_balance': [5_000_000.0, 1_200_000.0, 600_000.0, 300_000.0, 150_000.0],
        }
    )
    # The loss_rate per bucket comes from the library's illustrative default matrix; in
    # production pass aging_buckets={'current': ..., ...} with your own historical rates.
    provision = compute_simplified_ecl(receivables, method='provision_matrix')
    print('3. Simplified approach (provision matrix) for trade receivables')
    for row in provision.iter_rows(named=True):
        print(
            f'   {row["aging_bucket"]:<8}  balance={row["outstanding_balance"]:>12,.0f}  '
            f'loss_rate={row["loss_rate"]:>7.3%}  ECL={row["simplified_ecl"]:>12,.2f}'
        )
    total_balance = provision['outstanding_balance'].sum()
    total_ecl = provision['simplified_ecl'].sum()
    print(f'   {"TOTAL":<8}  balance={total_balance:>12,.0f}  {"":>17}  ECL={total_ecl:>12,.2f}')


if __name__ == '__main__':
    main()
