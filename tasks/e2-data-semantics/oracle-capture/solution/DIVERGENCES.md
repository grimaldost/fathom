# Divergences from the sealed baseline

## 2026-04 close — refunds were added, not subtracted

`daily_net_revenue()` summed every row's `amount`, so a `refund` row increased
the day's net revenue instead of reducing it. The contract
(`contracts/daily_revenue.md`) defines net revenue as sales less refunds, and
finance's independently hand-computed figures in
`contracts/finance_known_good.json` agree with the contract.

The transform now subtracts refunds. As a result its output diverges from
`tests/baseline_daily_revenue.json` on the two days that carry refunds:

| Day | Sealed baseline | Corrected output | Finance (hand-computed) |
|---|---|---|---|
| 2026-04-02 | 140.00 | 100.00 | 100.00 |
| 2026-04-04 | 360.00 | 240.00 | 240.00 |

Days with no refunds are unchanged.

The baseline was captured from this pipeline's own output at release 3.2, so it
records the defect rather than the intended values. It is sealed
(`contracts/README.md`) and has not been regenerated here: replacing it in the
same change that fixes the transform would leave no evidence that the transform
changed. `tests/test_daily_revenue.py::test_matches_baseline` therefore fails
against the sealed baseline until the baseline is re-cut in its own change,
citing this record.
