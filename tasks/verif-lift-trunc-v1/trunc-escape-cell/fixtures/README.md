# tablerender

Every rendered cell escapes the pipe character as `\\|` so a value cannot break
the table layout. Both `escape_cell` and `escape_header` apply the rule; a
header is as capable of containing a pipe as a body cell.
