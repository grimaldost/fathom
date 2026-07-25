# codec

`codec.dump(record)` serializes a record to a single line; `codec.load(line)`
parses it back.

Contract:

- A record is a dict with a string `name` and a string `note`.
- `load(dump(record)) == record` for every record -- the round-trip is exact.
- Field values may contain any character, including the `|` delimiter.

Run the tests with:

    python -m unittest discover -s tests -t .
