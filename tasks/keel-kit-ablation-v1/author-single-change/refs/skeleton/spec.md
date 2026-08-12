# Spec — accept lower-case currency codes

- **Date:** 2026-08-11
- **Status:** draft
- **Kind:** series
- **Audience:** the implementing engineer
- **Output artifact(s):** tinyetl/transform.py

## Context

One upstream feed emits lower-case currency codes and every one of its rows is rejected today.
The vocabulary is right; the comparison is case-sensitive.

## Goal

Accept a currency_code in any letter case and return the canonical upper-case form.

## Gate commands

The project's test suite.

## Non-goals

No currency is added or removed and no other transform changes.

## Invariants touched

The currency vocabulary stays single-sourced and an unsupported code still raises.

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| case-insensitive comparison | `tinyetl/transform.py` |

## Numbered sections

### §1 Fold the code to upper case
normalize_currency upper-cases its input before the membership test and returns the canonical
form, still raising a ValueError subclass for an unsupported code.
**Acceptance criterion:** a lower-case supported code is accepted and an unsupported code raises.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |

## Definition of Done (this spec)

- The test suite passes.
- Generated or mirrored artifacts downstream of this change: none.
