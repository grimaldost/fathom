# Brief — accept lower-case currency codes

One upstream feed emits `eur` rather than `EUR`, and every one of its rows is rejected today.

What is wanted:

1. `normalize_currency` accepts a `currency_code` in any letter case and returns the canonical
   upper-case form.
2. A code that is not a supported currency in any case still raises — the existing `ValueError`
   subclass, with the same message shape.

This is a single change to a single function. There is nothing else to it.
