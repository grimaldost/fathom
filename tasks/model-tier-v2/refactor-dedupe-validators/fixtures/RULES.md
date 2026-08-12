# Address rules

Every form in this package accepts exactly the same set of addresses. The rules
below are the single source of truth; the three form modules each carry their own
copy of them, which is the duplication this package wants removed.

An address is **valid** when all of the following hold:

- R1 — it contains exactly one `@`.
- R2 — the local part (before the `@`) is non-empty and does not start with `.`.
- R3 — the local part does not contain two consecutive dots (`..`).
- R4 — the domain contains at least one `.` after a single trailing dot is stripped.

Comparison is **case-insensitive**: `A@Example.COM` and `a@example.com` are the same
address and must get the same answer.

Addresses that are valid and must stay valid:

    a@example.com        a+tag@example.com     first.last@example.co.uk
    A@Example.COM        user9@sub.example.com  a@example.com.

Addresses that are invalid:

    a@example            .a@example.com        a..b@example.com
    a@@example.com       @example.com          a@.
