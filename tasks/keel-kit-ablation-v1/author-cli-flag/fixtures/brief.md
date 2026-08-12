# Brief — filter a batch by region

Operators running `tinyetl` against the shared order feed want to process one region at a time
instead of the whole feed.

What is wanted:

1. A `--region` option on the command line. Given `--region north`, the run processes only the
   rows whose `region` column is `north`; without it the run behaves exactly as it does today.
2. The option accepts only a region already listed in `KNOWN_REGIONS`. Anything else stops the
   run with a new `UnknownRegionError` rather than silently producing an empty batch.
3. The run summary keeps reporting the number of rows actually written.

Nothing about the record shape on disk changes.
