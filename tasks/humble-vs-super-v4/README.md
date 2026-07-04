# Task bank: `humble-vs-super-v4` — non-local root-cause bank (retune of v3)

v3's correctness traps **ceilinged**: opus-bare read each documented contract and
implemented every edge case correctly on a small, self-contained function — so
correctness didn't discriminate (only `regression_test_present` moved, as in v2). The
v3 calibration finding: *on readable, self-contained code, the discipline plugins buy
opus test/verification hygiene, not raw correctness.*

v4 attacks the one mechanism that survives that finding: **the bug is non-local and the
symptom site is the wrong place to fix it.** Reading the symptom site is no longer
enough — you have to *trace* to the root cause.

## The design rule (v4)

Each task:

1. The real bug is in an **innocent-looking shared helper** (`parse_line` doing
   `line.split()`; `page_key` returning the URL raw) — nothing about the helper *reads*
   as wrong.
2. The **symptom surfaces in a consumer** (`codes()` raises; pages split by query
   string), and the bug report points there — not at the helper.
3. A **second, independent consumer** uses the same helper, so a band-aid in the first
   consumer leaves the second broken — and edge cases (trailing tags; `top_page`'s
   winner) defeat the obvious consumer-local shortcuts.
4. The correct behavior is **documented** (package README) — discoverable by reading the
   contract + the failing inputs, not clairvoyant.

So a disciplined arm (systematic-debugging / root-cause-tracing) traces symptom → helper
and fixes the root cause, passing both consumer criteria. A symptom-driven one-shot
band-aids the consumer where it crashes and fails the other consumer / the edge cases.

| task | innocent root cause | symptom (consumer) | second consumer that defeats the band-aid |
|------|--------------------|--------------------|--------------------------------------------|
| `fix-nonlocal-parse` | `parse_line` = `line.split()` (ignores quoted messages) | `codes()` raises / `messages()` garbled | `messages` **and** `codes`; optional trailing TAG defeats `fields[-1]` / `join(fields[1:-1])` |
| `fix-nonlocal-urlkey` | `page_key` returns URL raw | pages split by query string / trailing slash | `top_page` re-calls `page_key`, so canonicalizing only inside `page_counts` fails it |

Each task also carries `no_regression` (shipped suite green — anchor) and
`regression_test_present` (the swap — the same test-discipline signal as v1/v2/v3; here
it doubles as a second root-cause signal, since reverting the buggy helper only reddens a
test that actually exercises the fixed root cause).

## Calibration (still empirical, still pilot-gated)

Whether opus-bare band-aids (→ discrimination) or reliably traces to the helper anyway
(→ another ceiling) is **empirical** — exactly what v3 taught us not to assume. Validate
with a cheap `bare` vs `stack-super` pilot before any powered matrix; see `V4_NOTES.md`.
If v4 ceilings too, that is itself a strong, publishable finding: opus correctness can't
be discriminated by these disciplines even on non-local bugs.

## Layout & verifier contract

Same as v1 — see `../humble-vs-super-v1/README.md` for the layout, the `bugfix_verify.py`
swap mechanism (reused **byte-identical**), and the blindness argument. Each `verify.py`
emits two non-local correctness criteria plus `no_regression` and
`regression_test_present`. The swap module is the **root-cause** file (`parse.py` /
`normalize.py`).
