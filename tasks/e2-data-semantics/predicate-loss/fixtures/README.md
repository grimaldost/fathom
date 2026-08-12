# active-accounts extract

`active_accounts.py` is the port of the retiring platform's nightly extract. The
legacy query it replaces is in `legacy/accounts.sql`; the cutover criterion is in
`MIGRATION_NOTES.md`.

- `active_accounts.load_accounts(path)` -> list of row dicts
- `active_accounts.active_accounts(accounts, as_of)` -> list of extract rows

Sample data: `accounts.csv`.

Run the suite with:

```
python -m unittest discover -s tests -t .
```
