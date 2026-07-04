# score — fix-nonlocal-parse

- **author_score:** 70
- **band:** high
- **predicted tier:** strong / Opus (56-100)
- **rationale:** A non-local root-cause task. The symptoms surface in two consumers
  (`codes()` raises, `messages()` is garbled), but the real defect is the shared
  `parse_line` splitting on whitespace and so mis-handling quoted messages. A
  symptom-driven band-aid in one consumer fixes the reported case yet fails the other
  consumer and the tagged-line cases; only fixing the shared parser passes both hard
  criteria.
- **Capability Haiku is expected to LACK:** tracing two distinct surface symptoms back to
  a single shared upstream function (`parse_line`) and fixing the root cause there,
  instead of patching each consumer at the symptom site — the optional trailing TAG
  defeats the per-consumer band-aids (`fields[-1]`, `" ".join(fields[1:-1])`).
