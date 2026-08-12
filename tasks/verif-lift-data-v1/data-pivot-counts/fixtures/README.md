# reshape

`pivot_counts(rows, rows_key, cols_key, columns)` returns one dict per distinct
row key, carrying a count for EVERY column in `columns` -- zero where there are
no rows. Several rows sharing a (row, column) pair accumulate.
