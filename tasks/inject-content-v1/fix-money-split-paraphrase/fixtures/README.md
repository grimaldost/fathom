# payments

Split a money amount (in whole cents) fairly among recipients.

- `split_amount(total_cents, n)` — divide `total_cents` among `n` recipients as evenly
  as possible.

The parts must sum **exactly** to `total_cents`. When the amount does not divide
evenly, the leftover cents are handed out one each to the **earliest** recipients, so
shares differ by at most one cent and the larger shares come first. See the
`split_amount` docstring for the full contract.

Run the tests: `python -m unittest discover -s tests -t .`
