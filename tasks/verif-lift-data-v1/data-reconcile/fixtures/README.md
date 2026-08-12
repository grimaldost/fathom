# recon

`reconcile(expected, actual)` returns `{key: actual - expected}` for every key
present on EITHER side, treating a missing side as 0, and omits keys whose
difference is zero.
