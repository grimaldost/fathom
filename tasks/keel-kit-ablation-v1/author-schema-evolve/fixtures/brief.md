# Brief — carry a retry hint on every record

The two jobs that read the record stream have to re-poll a source when a batch lands late, and
today they guess how long to wait.

What is wanted:

1. Every written record carries a new `retry_after_s` field: an integer number of seconds a reader
   should wait before re-reading. It is derived from the batch, not supplied per row.
2. `schema_version` moves from 1 to 2, because a reader must be able to tell the two shapes apart.
3. A `migrate_v1_to_v2` conversion exists so an already-written v1 file can be read as v2 without
   re-running the batch that produced it.

Records already on disk must stay readable.
