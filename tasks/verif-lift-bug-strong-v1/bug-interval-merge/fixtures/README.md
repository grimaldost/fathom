# intervals

`merge_spans(spans)` merges overlapping AND touching half-open spans and
returns them sorted. `[0, 5]` and `[5, 9]` touch and merge to `[0, 9]`.
