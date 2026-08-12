# units

Abbreviation in this module rounds to one decimal and drops a trailing `.0`,
so 1000 reads `1k` and 1500 reads `1.5k`. `abbrev_count` and `abbrev_bytes`
share the rule; only their unit ladders differ.
