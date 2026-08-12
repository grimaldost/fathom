# sched

`slots(start, end, step)` lists the slot start minutes in `[start, end)`.
A slot that begins exactly at `end - step` is included; one that would begin
at `end` is not.
