# Review of billing/prorate.py

## Defects

- credit: it truncates instead of rounding.
- net: the subtraction order looks wrong.
- is_refund: zero should probably be a refund.
