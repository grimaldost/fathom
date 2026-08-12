# scoring

Both clamps in this module are INCLUSIVE at the bounds and clamp rather than
reject: a value below the low bound becomes the low bound, one above the high
bound becomes the high bound. `clamp_score` and `clamp_weight` differ only in
their bounds.
