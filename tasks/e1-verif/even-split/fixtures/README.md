# allocate

`allocate.split_amount(total, parts)` splits a whole number `total` into `parts`
integer shares.

Contract:

- `parts` is an integer >= 1 and `total` is an integer >= 0.
- Return a list of exactly `parts` non-negative integers whose sum is exactly `total`.
- The shares are as equal as possible: every share is either `total // parts` or one
  greater, and the `total % parts` extra units go to the earliest shares, so the list
  comes out non-increasing.

Examples:

    split_amount(100, 3) -> [34, 33, 33]
    split_amount(90, 3)  -> [30, 30, 30]
    split_amount(7, 2)   -> [4, 3]

Run the tests with:

    python -m unittest discover -s tests -t .
