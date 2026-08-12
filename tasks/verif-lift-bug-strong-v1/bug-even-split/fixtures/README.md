# allocate

`split_amount(total, parts)` divides a whole `total` into `parts` integer
shares that are as equal as possible and add back up to `total` exactly.
Leftover units go to the earliest shares, so the shares come out
non-increasing.
