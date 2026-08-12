# Brief — report per-region counts in the run summary

Two downstream jobs read the summary `tinyetl` prints at the end of a run:

- `reporting-daily` reads the summary once a day and charts the volume written.
- `alerting-hourly` reads it every hour and pages when the volume drops to zero.

What is wanted:

1. The summary reports how many rows were written per region, alongside the total it already
   reports as `row_count`.
2. The total keeps its current name and meaning, so neither reader has to change on the same day
   the field is added.
3. Whatever the two readers need to do to pick up the new field is stated, per reader.
