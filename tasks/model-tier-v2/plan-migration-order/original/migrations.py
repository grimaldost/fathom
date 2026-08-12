"""The migrations to be applied, and nothing that decides their order."""

# kind is "add" (a schema addition) or "backfill" (a data write over existing rows).
MIGRATIONS = [
    {"id": "m1", "table": "accounts", "kind": "add", "depends_on": []},
    {"id": "m2", "table": "invoices", "kind": "add", "depends_on": ["m1"]},
    {"id": "m3", "table": "accounts", "kind": "backfill", "depends_on": ["m1"]},
    {"id": "m4", "table": "invoices", "kind": "backfill", "depends_on": ["m2"]},
    {"id": "m5", "table": "ledger", "kind": "add", "depends_on": []},
    {"id": "m6", "table": "ledger", "kind": "backfill", "depends_on": ["m5", "m2"]},
    {"id": "m7", "table": "accounts", "kind": "add", "depends_on": []},
    {"id": "m8", "table": "invoices", "kind": "add", "depends_on": ["m7"]},
    {"id": "m9", "table": "ledger", "kind": "backfill", "depends_on": ["m6"]},
]


def by_id():
    """The migrations keyed by id."""
    return {m["id"]: m for m in MIGRATIONS}
