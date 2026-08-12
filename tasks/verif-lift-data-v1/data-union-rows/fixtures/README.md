# setops

`union_rows(left, right, key)` concatenates both inputs and removes duplicate
`key` values, keeping the FIRST occurrence. Field order within a row does not
affect whether two rows are duplicates.
