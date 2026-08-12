# cleanse

`normalize_keys(rows, field)` lower-cases and strips `field` on every row.
A value that is empty after stripping is not a usable key and becomes `None`.
