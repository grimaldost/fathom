# retrier

Retry helpers. The starting project ships a small time helper (`elapsed`) only.

The feature to implement is specified in **[SPEC.md](SPEC.md)**: a `retry`
function with capped exponential backoff, bounded full-jitter, and faithful
error propagation.

Run the tests from the project root:

```sh
python -m unittest discover -s tests -t .
```
