# pathkit

`normalize(path)` collapses `.` and resolves `..` against the preceding
segment, including a `..` in final position. A `..` that would escape the root
is dropped.
