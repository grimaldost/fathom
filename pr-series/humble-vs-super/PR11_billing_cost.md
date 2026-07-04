## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §11 (and the certification's advisory (e))
- `src/fathom/adapters/claude_cli.py`, `src/fathom/adapters/base.py` — NOTE: the adapter ALREADY computes
  `cost_usd_est` on its run record (parsed from `total_cost_usd`). Do NOT re-implement that.
- `src/fathom/ledger.py` — the ledger `RunRecord` (has NO cost field today — the gap)
- `src/fathom/cli.py` — where the adapter record is mapped into the ledger record
- `src/fathom/report.py` — currently reads a never-emitted `usage['cost_usd']` key
- `docs/adr/0002-*` (append-only ledger), `docs/STATUS.md` (defect D2)

## Task
Repair the economy dead-end (the real root cause of D2): the adapter computes a cost estimate but it is dropped
at the ledger boundary and the report reads the wrong key. Do all of:
1. Add a `cost_usd_est` field (default `0.0`) to the ledger `RunRecord`; the ledger reader must default it to
   `0.0` for pre-existing lines (append-only: never rewrite old lines).
2. In `cli.py`, persist the adapter record's `cost_usd_est` into the ledger record.
3. In `report.py`, repoint the economy / efficiency USD column at the ledger `cost_usd_est` field instead of
   `usage['cost_usd']`.
4. (Recommended) add a token x price fallback estimate path so `cost_usd_est` is non-zero even when the CLI
   reports `total_cost_usd = 0` (subscription); price constants per the model-tiers rates.
5. Resolve and document the billing path (subscription credential vs passed-through `ANTHROPIC_API_KEY`) in
   `docs/STATUS.md`'s D2 entry.

## Constraints
- Append-only ledger: ADD a field; never rewrite existing ledger lines; readers tolerate its absence.
- This PR touches `claude_cli.py` / `cli.py` / `report.py` (shared with PR03/PR04/PR09) — it depends on all
  three and lands last to avoid conflicts.

## Starting file list
1. `src/fathom/ledger.py`
2. `src/fathom/cli.py`
3. `src/fathom/report.py`
4. `src/fathom/adapters/claude_cli.py` (only the optional token x price fallback, if added)
5. `tests/test_ledger.py`, `tests/test_report.py`, `docs/STATUS.md`

## Definition of done
- [ ] A parsed run with known token counts yields a non-zero `cost_usd_est` carried through the ledger record,
      and `fathom report` renders non-zero USD (spec §11 acceptance).
- [ ] Pre-existing ledger lines without the field still load (default `0.0`); no existing line is rewritten.
- [ ] `docs/STATUS.md` D2 records the resolved billing path.
- [ ] All quality gates pass.
