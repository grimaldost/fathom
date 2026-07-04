# querytable

A tiny in-memory query engine over tables (lists of row dicts; values are `int` or
`None`). The **baseline** supports only equality filtering. The task is to implement
the full `where` (SQL three-valued NULL logic), `order_by` (stable, multi-key,
NULLS LAST in both directions), and `aggregate` (group-by + COUNT/SUM/AVG/MIN/MAX
with null-aware semantics). See the task instruction.

Run the baseline tests:

```
python -m unittest discover -s tests -t .
```
