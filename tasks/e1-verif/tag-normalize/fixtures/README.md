# tagkit

`tagkit.normalize_tags(raw)` turns a comma-separated tag string into a normalized
list of tags.

Contract:

- Split `raw` on commas.
- Strip surrounding whitespace from each piece and fold it to lowercase.
- Drop pieces that are empty after stripping.
- Keep only the first occurrence of each tag, in the order the tags first appear; a
  later repeat of an already-seen tag (including a repeat that differs only in letter
  case) is discarded.

Examples:

    normalize_tags("red, green, blue") -> ["red", "green", "blue"]
    normalize_tags("Red, red, RED")    -> ["red"]
    normalize_tags("b, a, B, a, c")    -> ["b", "a", "c"]

Run the tests with:

    python -m unittest discover -s tests -t .
